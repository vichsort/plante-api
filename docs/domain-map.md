# Mapa do domínio (transitório)

Regras de negócio de cada subdomínio enquanto o código ainda está nas camadas antigas
(`src/domain`, `src/adapters`, `src/api`, `src/workers`). **Este arquivo encolhe a cada módulo
migrado**: a seção do subdomínio vai para o `README.md` do módulo (Propósito, Decisões, Erros) e
sai daqui. Quando o último módulo migrar, o arquivo é apagado.

As regras de arquitetura estão no `ARCHITECTURE.md`; o kernel comum, em `src/shared/README.md`.

| Seção | Vai para o módulo |
| :--- | :--- |
| Autenticação & Identidade | `identity` |
| Identificação Botânica & Consenso | `identification` (+ `catalog`) |
| Gestão de Jardim & Cuidados | `garden` |
| Diagnóstico de Saúde | `health` |
| Perfil, Gamificação & Assinaturas | `subscription` e `achievements` |
| Dados de Treino & Anonimato | `training` |

---

## Autenticação & Identidade (`Identity Context`)
* **Propósito**: Gerenciar registro de usuários, autenticação JWT, verificação de e-mail OTP de 6 dígitos e renovação de tokens.
* **Entidades Principais**: `User`, `VerificationCode`, `UserLocation`.
* **Entradas (Use Cases)**: `RegisterUserUseCase`, `LoginUseCase`, `VerifyEmailUseCase`, `RefreshTokenUseCase`, `LogoutUseCase`.
* **Saídas/Saúde**: Geração de tokens de acesso JWT, envio de e-mails OTP via `IEmailSender`, persistência de dados de auditoria em `UserRepository`.
* **Regras de Negócio**:
  - Todo usuário nasce com status `pending_verification` e plano `FREE`.
  - E-mail é guardado e buscado na forma canônica (`normalize_email`: sem espaços nas pontas, em minúsculas) — cadastro, login e troca de e-mail não diferenciam maiúsculas. O banco garante com o CHECK `ck_users_email_normalized`.
  - Códigos OTP expiram em 15 minutos e são gerenciados no cache Redis (`RedisOtpRepository`).
  - **Senha forte** (`PasswordPolicy`: 8+ caracteres, uma maiúscula, um número) no cadastro e na troca de senha.
  - **Tokens:** access de 15 minutos, refresh de 30 dias, um refresh por usuário (login novo derruba a sessão anterior).
    - O refresh **rotaciona**: cada uso devolve um refresh novo. Reuso de um refresh já trocado revoga a sessão (sinal de roubo; um retry do app também derruba, efeito aceito). Todo token tem `jti`, então dois emitidos no mesmo segundo nunca são iguais.
    - **Decisão:** o logout revoga só o refresh. O access token é JWT sem estado e vale até expirar (no máximo 15 minutos). Uma lista de bloqueio no Redis custaria uma consulta por requisição, para cobrir uma janela curta.
  - **Troca de e-mail** (`PATCH /profile/email`): o endereço novo fica pendente (`pending_email`) e recebe um código; o e-mail atual continua entrando. `POST /auth/verify-email` com esse código confirma a troca (se outra conta tiver ficado com o endereço nesse meio-tempo, 409).

---

## Identificação Botânica & Consenso (`Botany Identification Context`)
* **Propósito**: Processar imagens enviadas pelo usuário, consultar múltiplos provedores de visão computacional/IA (Kindwise, PlantNet) e determinar a identificação taxonômica exata ou por consenso.
* **Entidades Principais**: `Identification` (histórico do usuário), `PlantSpecies`.
* **Políticas**: `ConsensusPolicy` (calcula concordância exata, por gênero ou fallback).
* **Entradas (Use Cases)**: `IdentifyPlantUseCase`, `GiveIdentificationFeedbackUseCase`.
* **Ports Requeridos**: `IImageSanitizer`, `IPlantIdentifier` (Kindwise, PlantNet, consenso), `IImageStorage`, `IUnitOfWork` (`identifications`, `species`, `reference_images`, `training`).
* **Regras de Negócio**:
  - `POST /identify` **não cria planta no jardim**: grava a identificação (lado do usuário) e a amostra de treino anônima (seção "Dados de Treino"). Verifica só os tokens do dia; o limite do jardim vale ao adicionar ao jardim.
  - A foto é limpa antes de qualquer uso (`IImageSanitizer`, adapter Pillow): orientação aplicada, todos os metadados removidos (EXIF, GPS, aparelho, data), regravada em JPEG. Aceita JPEG/PNG/WebP; HEIC, arquivo que não é imagem ou imagem acima de 60 MP → `PLANTE_4013`.
  - Feedback (`POST /identify/{id}/feedback`): `correct | wrong | unsure` + sugestão opcional de espécie. A qualquer momento, quantas vezes o usuário quiser; cada resposta é um evento na amostra de treino.
  - **Consenso (`ConsensusIdentifier`, ativo com `CONSENSUS_ENABLED=true`)**: Kindwise e PlantNet são consultados em paralelo (timeout de 10s cada) e a `ConsensusPolicy` escolhe a espécie:
    - Acordo exato → média ponderada (Kindwise 60%, PlantNet 40%), `source="consensus"`.
    - Acordo de gênero → vence o maior score, `source="consensus_partial"`, sempre `low_confidence`.
    - Desacordo total → vence o Kindwise, salvo se o PlantNet tiver 20 pontos percentuais a mais; sempre `low_confidence`.
    - Um provedor falha → o outro decide sozinho (`source` = nome dele). Os dois falham → `InvalidImageError` prevalece sobre `ExternalServiceError`.
    - **Veto**: se o Kindwise afirmar que a imagem não é planta (`is_plant.binary == false` → `NotAPlantError`), a requisição falha com `PLANTE_4013` mesmo que o PlantNet tenha devolvido uma espécie. Outras falhas do Kindwise (sugestões vazias, imagem ilegível) não vetam.
    - As imagens de referência (`similar_images`) vêm do provedor cujos dados venceram (Kindwise no acordo exato) e são gravadas com a origem correta (`kindwise_similar` / `plantnet_similar`).
    - Os sinais (`IdentificationResult.signals`) juntam o que cada provedor que respondeu disse (o que falhou fica de fora). Com o consenso desligado, só os do Kindwise.

---

## Gestão de Jardim & Cuidados (`Garden Management Context`)
* **Propósito**: Manter a coleção de plantas do usuário (o "jardim"), controlar rotinas de rega, adubação e acompanhar a frequência de cuidados (`Streak`).
* **Entidades Principais**: `UserPlant`, `CareSchedule`, `Streak`.
* **Entradas (Use Cases)**: `AddPlantToGardenUseCase`, `WaterPlantUseCase`, `GetUserGardenUseCase`, `GetPlantDetailsUseCase`, `DeleteUserPlantUseCase`, `BreakStreakCronUseCase` (worker).
* **Ports Requeridos**: `IUnitOfWork` (`user_plants`, `identifications`, `training`).
* **Regras de Negócio**:
  - Uma planta só entra no jardim a partir de uma identificação (`POST /garden` com `identification_id`): é aí que o `UserPlant` é criado. Repetir com a mesma identificação devolve a planta existente.
  - Limite do plano conta as plantas **ativas** no jardim (`count_by_user`; não há contador guardado): FREE até 3, PRO até 50 (`SubscriptionPolicy.enforce_can_add_to_garden`).
  - Adicionar ao jardim registra um sinal implícito positivo (`added_to_garden`) na amostra de treino da identificação.
  - **Rega e sequência** (`CareSchedule`, `Streak`): o vencimento é um **dia do calendário local** (`LocalCalendar`, fuso em `LOCAL_TIMEZONE`, padrão `America/Sao_Paulo`), não um instante. A janela vai de 1 dia antes a 1 dia depois do vencimento. Antes dela a rega é recusada (`PLANTE_4016`); dentro dela soma 1 à sequência; depois dela é aceita, mas a sequência recomeça em 1. Uma rega por dia. A primeira rega (sem vencimento) vale a qualquer dia. Cada rega recalcula o vencimento (dia da rega + intervalo).
  - O cron diário `garden.break_missed_streaks` (beat, 03:00 no fuso local) zera a sequência das plantas cuja janela passou inteira e publica `StreakBrokenEvent`. Rodar de novo no mesmo dia não quebra nada a mais.
  - Exclusão de plantas utiliza **Soft Delete** (`deleted_at.is_(None)`). **Não é rejeição da identificação** (a planta pode ter morrido): identificação e dado de treino não mudam.

---

## Diagnóstico de Saúde Botânica (`Health Diagnosis Context`)
* **Propósito**: Analisar sintomas em folhas/caule enviados por foto, classificar a severidade (low, moderate, high, critical) e gerar um plano de recuperação botânica.
* **Entidades Principais**: `HealthRecord` (histórico do usuário).
* **Entradas (Use Cases)**: `DiagnoseHealthUseCase`, `GiveHealthFeedbackUseCase`, `GetHealthHistoryUseCase`.
* **Ports Requeridos**: `IImageSanitizer`, `IHealthAnalyzer`, `IPlantEnricher`, `IImageStorage`, `IUnitOfWork` (`health_records`, `training`).
* **Regras de Negócio**:
  - `POST /diagnose` grava o diagnóstico (lado do usuário, com `training_sample_id`) e a amostra de treino de saúde na hora, já com as imagens de referência das doenças rehospedadas. Aceita `latitude`/`longitude` opcionais (só a grade aproximada vai para o treino).
  - Feedback (`POST /diagnose/{id}/feedback`): `correct | wrong | unsure`, a qualquer momento. Substituiu a antiga confirmação (e a resposta pendente no Redis, que expirava).

---

## Perfil, Gamificação & Assinaturas (`Profile & Gamification Context`)
* **Propósito**: Gerenciar dados cadastrais do usuário, troca de senha/e-mail, controle de limites de assinatura (`FREE` vs `PRO`) e concessão de conquistas (`Badges`).
* **Entidades Principais**: `Achievement`, `SubscriptionTier`.
* **Políticas**: `SubscriptionPolicy`.
* **Entradas (Use Cases)**: `ChangeEmailUseCase`, `ChangePasswordUseCase`, `UpdateLocationFallbackUseCase`, `UpgradeSubscriptionUseCase`, `ListUserAchievementsUseCase`.
* **Ports Requeridos**: `IAchievementRepository`, `IUserRepository`.
* **Regras de Negócio**:
  - O plano `PRO` desbloqueia até 50 plantas no jardim e consultas avançadas de saúde.
  - Vale o plano **ativo** (`User.get_active_tier`): PRO vencido conta como FREE.
  - **Cota diária de tokens** (FREE 3, PRO 30), no dia local (`LocalCalendar`). Zera sozinha na primeira cobrança de um dia novo (`User.tokens_day`), sem cron.
  - Custos: identificar 1; diagnóstico 1, mais 1 pelo complemento do Gemini (só chamado se os 2 couberem no saldo, e só cobrado se entregue); análise profunda 2. O saldo é conferido **antes** de chamar os provedores.

---

## Dados de Treino & Anonimato (`Training Data`, transversal)
* **Propósito**: Montar o dataset que treina a IA própria do PlantE a partir das identificações e diagnósticos, **sem nenhum dado pessoal**. Requisito inegociável: a IA treinada não pode ser pessoalizada, e apagar planta ou conta nunca remove dado de treino.
* **Entidades Principais** (`src/domain/entities/training.py`): `TrainingIdentificationSample`, `TrainingHealthSample`, `TrainingFeedback`.
* **Ports Requeridos**: `ITrainingRepository` (só acrescenta; não há remoção), `IImageStorage.upload_training_image`.
* **Separação na gravação**: cada `/identify` e `/diagnose` grava duas coisas sem ligação de volta:

  | | Lado do usuário (`identifications`, `user_plants`, `health_records`) | Treino (`training_*`) |
  | :--- | :--- | :--- |
  | Dono | `user_id`; tudo sai com o usuário (FKs `CASCADE`) | ninguém; sem `user_id`, sem FK para tabelas do usuário |
  | Foto | a do usuário (`identifications/…`) | cópia própria, chave aleatória em `training/…`, nunca devolvida ao cliente |
  | Tempo | horário exato (`created_at`, `diagnosed_at`) | só o mês (`period`); as tabelas não usam o `AuditMixin` |
  | Local | — | estado do perfil + grade de ~11 km (GPS arredondado a 1 casa decimal), só se o cliente mandou o GPS |
  | Provedor | — | sinais filtrados (`provider_signals.py`): sugestões e probabilidades por provedor, `is_plant`, consenso, versão do modelo |

  O vínculo é **de mão única**: `identifications.training_sample_id` e `health_records.training_sample_id` apontam para a amostra; a amostra nunca aponta de volta. O vínculo some quando o dado do usuário é apagado.
* **O que nunca entra no treino**: `user_id` ou qualquer ID do lado do usuário; GPS exato; URL/chave da foto do usuário; EXIF; do Kindwise, `access_token` (dá acesso à identificação, com a foto, na API deles), `input` (ecoa coordenadas, URL da foto e data/hora), `custom_id` e horários; do PlantNet, `query` e `remainingIdentificationRequests`. Os adapters descartam esses campos ao montar os sinais.
* **Feedback = sinal, não confirmação**: eventos acumulados (`TrainingFeedback`, sem `user_id`), explícitos (`correct | wrong | unsure` + sugestão) ou implícitos (`added_to_garden`; futuro: motivo da exclusão, cuidado continuado). A confiança de cada rótulo **não** é calculada na gravação: a engine de confiança (planejada, ver `todo.md`) pesa os sinais brutos na exportação, com versão, para os pesos poderem mudar sem migrar dados.
* **Modelo de ameaça**: o alvo é o dataset como artefato (exportado, usado no treino, compartilhado). Quem tem acesso a produção sempre pode cruzar dados; isso não justifica complexidade extra.
* **Guardas automáticas**: `tests/integration/persistence/test_training_tables.py` (colunas numa lista fechada, FKs só entre tabelas de treino, nenhum horário exato), `tests/unit/adapters/test_provider_fixtures.py` (respostas reais dos provedores com dados ecoados não vazam para os sinais) e `tests/integration/test_user_and_training_flow.py` (fluxo completo; depois de apagar o usuário, o treino fica inteiro e sem nada que aponte para ele).

---

## Erros dos subdomínios

Os erros comuns (`PLANTE_4000`, `4013`, `4029`, `5001`, `4220`, `5000`, `5003`) estão em
`src/shared/README.md`.

| Código de Erro (`code`) | Exceção | Descrição | HTTP Status |
| :--- | :--- | :--- | :---: |
| `PLANTE_4001_PLANT_NOT_FOUND` | `PlantNotFoundError` | Planta não existe ou não pertence ao usuário. | 404 |
| `PLANTE_4002_USER_NOT_FOUND` | `UserNotFoundError` | Usuário não encontrado. | 404 |
| `PLANTE_4003_INVALID_VERIFICATION_CODE` | `InvalidVerificationCodeError` | Código OTP inválido ou expirado. | 400 |
| `PLANTE_4004_EMAIL_ALREADY_IN_USE` | `EmailAlreadyInUseError` | E-mail já usado por outro usuário (cadastro ou troca de e-mail). | 409 |
| `PLANTE_4005_FREE_TIER_PLANT_LIMIT` | `PlantLimitExceededError` | Plano FREE atingiu o limite de plantas no jardim (`SubscriptionPolicy`). | 403 |
| `PLANTE_4006_UNAUTHORIZED` | `UnauthorizedError` | Token ausente, inválido ou expirado; login com credenciais erradas. | 401 |
| `PLANTE_4007_WRONG_CREDENTIALS` | `InvalidCredentialsError` | Senha atual incorreta ao alterar e-mail ou senha. | 400 |
| `PLANTE_4008_WEAK_PASSWORD` | `WeakPasswordError` | Senha (cadastro ou troca) não atende à `PasswordPolicy`. | 400 |
| `PLANTE_4009_FORBIDDEN` | `ForbiddenError` | Autenticado, mas sem permissão sobre o recurso (ex.: planta de outro usuário). | 403 |
| `PLANTE_4010_IDENTIFICATION_FAILED` | `PlantIdentificationError` | A IA não identificou a planta com confiança suficiente. | 422 |
| `PLANTE_4011_LOW_CONFIDENCE` | `LowConfidenceError` | Confiança da identificação abaixo de 60% (`ConfidenceScore.is_rejected`). | 422 |
| `PLANTE_4012_IDENTIFICATION_NOT_FOUND` | `IdentificationNotFoundError` | Identificação não existe ou não pertence ao usuário (feedback, adicionar ao jardim). | 404 |
| `PLANTE_4014_SPECIES_NOT_FOUND` | `SpeciesNotFoundError` | Espécie não existe. | 404 |
| `PLANTE_4016_NOT_READY_FOR_WATERING` | `PlantNotReadyForWateringError` | Rega antes da janela (vencimento − 1 dia) ou segunda rega no mesmo dia (`UserPlant.water()`). | 400 |
| `PLANTE_4017_HEALTH_RECORD_NOT_FOUND` | `HealthRecordNotFoundError` | Diagnóstico não existe ou não pertence ao usuário. | 404 |
| `PLANTE_4019_SUBSCRIPTION_REQUIRED` | `SubscriptionRequiredError` | Recurso exclusivo do plano Pro ou tokens diários esgotados (`SubscriptionPolicy`). | 403 |

**`PLANTE_4013` — quando um provedor de IA gera imagem inválida:**
* Kindwise: `is_plant.binary == false` explícito → `NotAPlantError` (campo ausente segue o fluxo normal); lista de sugestões vazia → `InvalidImageError`; HTTP 400 → `InvalidImageError` **só** se o corpo contiver o marcador `Invalid image` (outros 400 são payload nosso malformado → `ExternalServiceError(retryable=False)` + log `provider.request_rejected`).
* PlantNet: HTTP 400 com `Unsupported file type` ou 404 com `Species not found` → `InvalidImageError`; outros 400 (ex.: `organs` inválido) → `ExternalServiceError(retryable=False)`.
* Consenso: `NotAPlantError` do Kindwise veta a resposta do PlantNet (ver "Identificação Botânica").

---

## Extensão

### Como Adicionar um Novo Provedor de IA Botânica (`IPlantIdentifier`)
1. Crie o novo adapter em `src/adapters/ai/<nome_provedor>/<nome_provedor>_adapter.py`.
2. Implemente a interface `IPlantIdentifier` definida em `src/domain/ports/plant_identifier.py`.
3. Registre a nova classe no container `AdaptersContainer` em `src/bootstrap/containers/adapters.py`.
4. Adicione os testes unitários correspondentes em `tests/unit/adapters/`.

### Como Adicionar um Novo Provedor de Envio de E-mail
1. Crie o novo adapter implementando `IEmailSender`.
2. Configure o provedor no container e a chave de configuração em `Settings` (`src/bootstrap/settings.py`).
