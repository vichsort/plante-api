# Mapa do domínio (transitório)

Regras de negócio de cada subdomínio enquanto o código ainda está nas camadas antigas
(`src/domain`, `src/adapters`, `src/api`, `src/workers`). **Este arquivo encolhe a cada módulo
migrado**: a seção do subdomínio vai para o `README.md` do módulo (Propósito, Decisões, Erros) e
sai daqui. Quando o último módulo migrar, o arquivo é apagado.

Já migrados: `training`, `catalog` e `subscription` (README de cada um em `src/modules/`).

As regras de arquitetura estão no `ARCHITECTURE.md`; o kernel comum, em `src/shared/README.md`.

| Seção | Vai para o módulo |
| :--- | :--- |
| Autenticação & Identidade | `identity` |
| Identificação Botânica & Consenso | `identification` (+ `catalog`) |
| Gestão de Jardim & Cuidados | `garden` |
| Diagnóstico de Saúde | `health` |
| Perfil & Gamificação | `identity` (perfil) e `achievements` |

---

## Autenticação & Identidade (`Identity Context`)
* **Propósito**: Gerenciar registro de usuários, autenticação JWT, verificação de e-mail OTP de 6 dígitos e renovação de tokens.
* **Entidades Principais**: `User`, `VerificationCode`, `UserLocation`.
* **Entradas (Use Cases)**: `RegisterUserUseCase`, `LoginUseCase`, `VerifyEmailUseCase`, `RefreshTokenUseCase`, `LogoutUseCase`.
* **Saídas/Saúde**: Geração de tokens de acesso JWT, envio de e-mails OTP via `IEmailSender`, persistência de dados de auditoria em `UserRepository`.
* **Regras de Negócio**:
  - Todo usuário nasce com status `pending_verification` (e sem linha em `subscriptions`, ou seja, FREE).
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
  - `POST /identify` **não cria planta no jardim**: grava a identificação (lado do usuário) e a amostra de treino anônima (`src/modules/training/README.md`). Verifica só os tokens do dia; o limite do jardim vale ao adicionar ao jardim.
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
  - Limite do plano conta as plantas **ativas** no jardim (`count_by_user`; não há contador guardado), conferido pelo `IGardenQuota` do subscription.
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

## Perfil & Gamificação (`Profile & Gamification Context`)
* **Propósito**: Gerenciar dados cadastrais do usuário, troca de senha/e-mail e concessão de conquistas (`Badges`). Plano e cota de tokens: `src/modules/subscription/README.md`.
* **Entidades Principais**: `Achievement`.
* **Entradas (Use Cases)**: `ChangeEmailUseCase`, `ChangePasswordUseCase`, `UpdateLocationFallbackUseCase`, `ListUserAchievementsUseCase`.
* **Ports Requeridos**: `IAchievementRepository`, `IUserRepository`.

---

## Erros dos subdomínios

Os erros comuns (`PLANTE_4000`, `4002`, `4006`, `4013`, `4029`, `5001`, `4220`, `5000`, `5003`) estão em
`src/shared/README.md`.

| Código de Erro (`code`) | Exceção | Descrição | HTTP Status |
| :--- | :--- | :--- | :---: |
| `PLANTE_4001_PLANT_NOT_FOUND` | `PlantNotFoundError` | Planta não existe ou não pertence ao usuário. | 404 |
| `PLANTE_4003_INVALID_VERIFICATION_CODE` | `InvalidVerificationCodeError` | Código OTP inválido ou expirado. | 400 |
| `PLANTE_4004_EMAIL_ALREADY_IN_USE` | `EmailAlreadyInUseError` | E-mail já usado por outro usuário (cadastro ou troca de e-mail). | 409 |
| `PLANTE_4007_WRONG_CREDENTIALS` | `InvalidCredentialsError` | Senha atual incorreta ao alterar e-mail ou senha. | 400 |
| `PLANTE_4008_WEAK_PASSWORD` | `WeakPasswordError` | Senha (cadastro ou troca) não atende à `PasswordPolicy`. | 400 |
| `PLANTE_4009_FORBIDDEN` | `ForbiddenError` | Autenticado, mas sem permissão sobre o recurso (ex.: planta de outro usuário). | 403 |
| `PLANTE_4010_IDENTIFICATION_FAILED` | `PlantIdentificationError` | A IA não identificou a planta com confiança suficiente. | 422 |
| `PLANTE_4011_LOW_CONFIDENCE` | `LowConfidenceError` | Confiança da identificação abaixo de 60% (`ConfidenceScore.is_rejected`). | 422 |
| `PLANTE_4012_IDENTIFICATION_NOT_FOUND` | `IdentificationNotFoundError` | Identificação não existe ou não pertence ao usuário (feedback, adicionar ao jardim). | 404 |
| `PLANTE_4016_NOT_READY_FOR_WATERING` | `PlantNotReadyForWateringError` | Rega antes da janela (vencimento − 1 dia) ou segunda rega no mesmo dia (`UserPlant.water()`). | 400 |
| `PLANTE_4017_HEALTH_RECORD_NOT_FOUND` | `HealthRecordNotFoundError` | Diagnóstico não existe ou não pertence ao usuário. | 404 |

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
