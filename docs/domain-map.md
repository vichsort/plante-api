# Mapa do domínio (transitório)

Regras de negócio de cada subdomínio enquanto o código ainda está nas camadas antigas
(`src/domain`, `src/adapters`, `src/api`, `src/workers`). **Este arquivo encolhe a cada módulo
migrado**: a seção do subdomínio vai para o `README.md` do módulo (Propósito, Decisões, Erros) e
sai daqui. Quando o último módulo migrar, o arquivo é apagado.

Já migrados: `training`, `catalog`, `subscription`, `identity` e `identification` (README de cada um em `src/modules/`).

As regras de arquitetura estão no `ARCHITECTURE.md`; o kernel comum, em `src/shared/README.md`.

| Seção | Vai para o módulo |
| :--- | :--- |
| Gestão de Jardim & Cuidados | `garden` |
| Diagnóstico de Saúde | `health` |
| Gamificação | `achievements` |

---

## Gestão de Jardim & Cuidados (`Garden Management Context`)
* **Propósito**: Manter a coleção de plantas do usuário (o "jardim"), controlar rotinas de rega, adubação e acompanhar a frequência de cuidados (`Streak`).
* **Entidades Principais**: `UserPlant`, `CareSchedule`, `Streak`.
* **Entradas (Use Cases)**: `AddPlantToGardenUseCase`, `WaterPlantUseCase`, `GetUserGardenUseCase`, `GetPlantDetailsUseCase`, `DeleteUserPlantUseCase`, `BreakStreakCronUseCase` (worker).
* **Ports Requeridos**: `IUnitOfWork` (`user_plants`), `IIdentificationLookup` (identification), `ITrainingRecorder` (training).
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
* **Ports Requeridos**: `IImageSanitizer`, `IHealthAnalyzer` (adapter Kindwise sobre o `KindwiseClient` do shared), `IPlantEnricher`, `IImageStorage`, `IUnitOfWork` (`health_records`, `training`).
* **Regras de Negócio**:
  - `POST /diagnose` grava o diagnóstico (lado do usuário, com `training_sample_id`) e a amostra de treino de saúde na hora, já com as imagens de referência das doenças rehospedadas. Aceita `latitude`/`longitude` opcionais (só a grade aproximada vai para o treino).
  - Feedback (`POST /diagnose/{id}/feedback`): `correct | wrong | unsure`, a qualquer momento. Substituiu a antiga confirmação (e a resposta pendente no Redis, que expirava).

---

## Gamificação (`Gamification Context`)
* **Propósito**: Concessão e listagem de conquistas (`Badges`). Conta e perfil: `src/modules/identity/README.md`; plano e cota de tokens: `src/modules/subscription/README.md`.
* **Entidades Principais**: `Achievement`.
* **Entradas (Use Cases)**: `ListUserAchievementsUseCase`.
* **Ports Requeridos**: `IAchievementRepository`.

---

## Erros dos subdomínios

Os erros comuns (`PLANTE_4000`, `4002`, `4006`, `4013`, `4029`, `5001`, `4220`, `5000`, `5003`) estão em
`src/shared/README.md`.

| Código de Erro (`code`) | Exceção | Descrição | HTTP Status |
| :--- | :--- | :--- | :---: |
| `PLANTE_4001_PLANT_NOT_FOUND` | `PlantNotFoundError` | Planta não existe ou não pertence ao usuário. | 404 |
| `PLANTE_4009_FORBIDDEN` | `ForbiddenError` | Autenticado, mas sem permissão sobre o recurso (ex.: planta de outro usuário). | 403 |
| `PLANTE_4016_NOT_READY_FOR_WATERING` | `PlantNotReadyForWateringError` | Rega antes da janela (vencimento − 1 dia) ou segunda rega no mesmo dia (`UserPlant.water()`). | 400 |
| `PLANTE_4017_HEALTH_RECORD_NOT_FOUND` | `HealthRecordNotFoundError` | Diagnóstico não existe ou não pertence ao usuário. | 404 |

**`PLANTE_4013`:** quando cada provedor de identificação gera imagem inválida está em `src/modules/identification/README.md`. A saúde segue a mesma regra do Kindwise (`is_plant.binary == false` → `NotAPlantError`; 400 só com `Invalid image`).

---
