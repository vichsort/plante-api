# Mapa do domínio (transitório)

Regras de negócio de cada subdomínio enquanto o código ainda está nas camadas antigas
(`src/domain`, `src/adapters`, `src/api`, `src/workers`). **Este arquivo encolhe a cada módulo
migrado**: a seção do subdomínio vai para o `README.md` do módulo (Propósito, Decisões, Erros) e
sai daqui. Quando o último módulo migrar, o arquivo é apagado.

Já migrados: `training`, `catalog`, `subscription`, `identity`, `identification` e `garden` (README de cada um em `src/modules/`).

As regras de arquitetura estão no `ARCHITECTURE.md`; o kernel comum, em `src/shared/README.md`.

| Seção | Vai para o módulo |
| :--- | :--- |
| Diagnóstico de Saúde | `health` |
| Gamificação | `achievements` |

---

## Diagnóstico de Saúde Botânica (`Health Diagnosis Context`)
* **Propósito**: Analisar sintomas em folhas/caule enviados por foto, classificar a severidade (low, moderate, high, critical) e gerar um plano de recuperação botânica.
* **Entidades Principais**: `HealthRecord` (histórico do usuário).
* **Entradas (Use Cases)**: `DiagnoseHealthUseCase`, `GiveHealthFeedbackUseCase`, `GetHealthHistoryUseCase`.
* **Ports Requeridos**: `IImageSanitizer`, `IHealthAnalyzer` (adapter Kindwise sobre o `KindwiseClient` do shared), `IPlantEnricher`, `IImageStorage`, `IUnitOfWork` (`health_records`), `IPlantLookup` (garden), `ITrainingRecorder` (training).
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
| `PLANTE_4017_HEALTH_RECORD_NOT_FOUND` | `HealthRecordNotFoundError` | Diagnóstico não existe ou não pertence ao usuário. | 404 |

**`PLANTE_4013`:** quando cada provedor de identificação gera imagem inválida está em `src/modules/identification/README.md`. A saúde segue a mesma regra do Kindwise (`is_plant.binary == false` → `NotAPlantError`; 400 só com `Invalid image`).

---
