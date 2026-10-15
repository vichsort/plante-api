# ARCHITECTURE.md — Diretrizes de Arquitetura & Guia do Desenvolvedor (PlantE API)

> **PlantE API** é uma plataforma *Open-Source* de identificação e gestão botânica para cultivo residencial. Este documento estabelece as diretrizes arquiteturais, os padrões de código, as fronteiras de domínio, o tratamento de erros e os mecanismos de extensão do projeto.

---

## 1. Princípios de Arquitetura & Filosofia de Design

O PlantE API é projetado sob os seguintes princípios inegociáveis:

1. **Arquitetura Hexagonal (Ports & Adapters)**:
   - A regra de negócio (**Domínio**) é pura e totalmente independente de frameworks Web (FastAPI), bancos de dados (SQLAlchemy), corretores de mensagem (Celery/Redis) ou APIs de terceiros (Kindwise, PlantNet, Gemini, AWS SES).
   - As dependências **SEMPRE apontam para dentro**:
     $$\text{API (HTTP/CLI)} \longrightarrow \text{Domain Use Cases} \longrightarrow \text{Domain Entities / Ports} \longleftarrow \text{Adapters}$$

2. **Injeção de Dependências Desacoplada (`dependency-injector`)**:
   - Nenhuma classe de Use Case instancia repositórios ou serviços diretamente. Todas as dependências são declaradas via abstrações (`Ports`) e injetadas pelo container central (`src/infrastructure/container.py`).

3. **Pragmatismo & Legibilidade**:
   - Manter a estrutura Hexagonal coesa (`src/domain/`, `src/adapters/`, `src/api/`) sem criar micro-módulos desnecessários ou sobre-engenharia prematura.

4. **Extensibilidade Open-Source via Plugin/Registry Pattern**:
   - Novas integrações de IA, gateways de notificação e sensores IoT devem ser adicionadas como novos `Adapters` implementando `Ports` existentes, sem alterar a regra de negócio do Domínio.

---

## 2. Mapa dos Sub-Domínios (Capabilities & Contextos de Negócio)

Embora o código viva em uma estrutura Hexagonal unificada, o domínio do **PlantE** se divide logicamente nas seguintes **Áreas de Capacidade**:

```
                               ┌────────────────────────────────────────┐
                               │             PlantE API                 │
                               └───────────────────┬────────────────────┘
                                                   │
         ┌───────────────────┬─────────────────────┼─────────────────────┬───────────────────┐
         │                   │                     │                     │                   │
┌────────┴────────┐ ┌────────┴────────┐   ┌────────┴────────┐   ┌────────┴────────┐ ┌────────┴────────┐
│  Autenticação   │ │   Identificação │   │    Gestão de    │   │   Diagnóstico   │ │    Perfil &      │
│  & Identidade   │ │    Botânica     │   │     Jardim      │   │    de Saúde     │ │  Assinaturas    │
└─────────────────┘ └─────────────────┘   └─────────────────┘   └─────────────────┘ └─────────────────┘
```

---

### 2.1. Sub-Domínio de Autenticação & Identidade (`Identity Context`)
* **Propósito**: Gerenciar registro de usuários, autenticação JWT, verificação de e-mail OTP de 6 dígitos e renovação de tokens.
* **Entidades Principais**: `User`, `VerificationCode`, `UserLocation`.
* **Entradas (Use Cases)**: `RegisterUserUseCase`, `LoginUseCase`, `VerifyEmailUseCase`, `RefreshTokenUseCase`, `LogoutUseCase`.
* **Saídas/Saúde**: Geração de tokens de acesso JWT, envio de e-mails OTP via `IEmailSender`, persistência de dados de auditoria em `UserRepository`.
* **Regras de Negócio**:
  - Todo usuário nasce com status `pending_verification` e plano `FREE`.
  - Códigos OTP expiram em 15 minutos e são gerenciados no cache Redis (`RedisOtpRepository`).

---

### 2.2. Sub-Domínio de Identificação Botânica & Consenso (`Botany Identification Context`)
* **Propósito**: Processar imagens enviadas pelo usuário, consultar múltiplos provedores de visão computacional/IA (Kindwise, PlantNet) e determinar a identificação taxonômica exata ou por consenso.
* **Entidades Principais**: `PlantIdentificationSample`, `PlantSpecies`.
* **Políticas**: `ConsensusPolicy` (calcula concordância exata, por gênero ou fallback).
* **Entradas (Use Cases)**: `IdentifyPlantUseCase`, `ConfirmPlantIdentificationUseCase`.
* **Ports Requeridos**: `IPlantIdentifier` (Kindwise, PlantNet, Gemini), `IIdentificationSampleRepository`, `IPlantSpeciesRepository`.
* **Regras de Negócio**:
  - Se dois provedores concordarem com o mesmo nome científico acima de 80% de confiança, a amostra é confirmada automaticamente por consenso.
  - **Consenso (`ConsensusIdentifier`, ativo com `CONSENSUS_ENABLED=true`)**: Kindwise e PlantNet são consultados em paralelo (timeout de 10s cada) e a `ConsensusPolicy` escolhe a espécie:
    - Acordo exato → média ponderada (Kindwise 60%, PlantNet 40%), `source="consensus"`.
    - Acordo de gênero → vence o maior score, `source="consensus_partial"`, sempre `low_confidence`.
    - Desacordo total → vence o Kindwise, salvo se o PlantNet tiver 20 pontos percentuais a mais; sempre `low_confidence`.
    - Um provedor falha → o outro decide sozinho (`source` = nome dele). Os dois falham → `InvalidImageError` prevalece sobre `ExternalServiceError`.
    - **Veto**: se o Kindwise afirmar que a imagem não é planta (`is_plant.binary == false` → `NotAPlantError`), a requisição falha com `PLANTE_4013` mesmo que o PlantNet tenha devolvido uma espécie. Outras falhas do Kindwise (sugestões vazias, imagem ilegível) não vetam.
    - As imagens de referência (`similar_images`) vêm do provedor cujos dados venceram (Kindwise no acordo exato) e são gravadas com a origem correta (`kindwise_similar` / `plantnet_similar`).
    - O `raw_response` da amostra guarda as duas respostas: `{"kindwise": ..., "plantnet": ...}`, com `null` para o provedor que falhou. Com o consenso desligado, guarda só a resposta do Kindwise.
  - Samples confirmadas há mais de 30 dias passam por worker diário de **anonimização** para alimentar a base pública de treinamento ML sem expor o `user_id`.

---

### 2.3. Sub-Domínio de Gestão de Jardim & Cuidados (`Garden Management Context`)
* **Propósito**: Manter a coleção de plantas do usuário (o "jardim"), controlar rotinas de rega, adubação e acompanhar a frequência de cuidados (`Streak`).
* **Entidades Principais**: `UserPlant`, `CareSchedule`, `Streak`.
* **Entradas (Use Cases)**: `AddPlantToGardenUseCase`, `WaterPlantUseCase`, `GetUserGardenUseCase`, `GetPlantDetailsUseCase`, `DeleteUserPlantUseCase`.
* **Ports Requeridos**: `IUserPlantRepository`.
* **Regras de Negócio**:
  - Usuários do plano `FREE` possuem limite estrito de até 3 plantas ativas no jardim (`SubscriptionPolicy`).
  - Cada rega efetuada no prazo incrementa o `Streak` (sequência) do usuário e recalcula o próximo vencimento em `CareSchedule`.
  - Exclusão de plantas utiliza **Soft Delete** (`deleted_at.is_(None)`), preservando o histórico para auditoria.

---

### 2.4. Sub-Domínio de Diagnóstico de Saúde Botânica (`Health Diagnosis Context`)
* **Propósito**: Analisar sintomas em folhas/caule enviados por foto, classificar a severidade (low, moderate, high, critical) e gerar um plano de recuperação botânica.
* **Entidades Principais**: `HealthRecord`, `HealthIdentificationSample`.
* **Entradas (Use Cases)**: `DiagnoseHealthUseCase`, `ConfirmHealthDiagnosisUseCase`, `GetHealthHistoryUseCase`.
* **Ports Requeridos**: `IHealthAnalyzer`, `IHealthRecordRepository`, `IHealthIdentificationSampleRepository`, `IHealthRawResponseRepository`.
* **Regras de Negócio**:
  - Respostas brutas da API de saúde são salvas no Redis (`RedisHealthRawResponseRepository`) para auditoria e fallback.

---

### 2.5. Sub-Domínio de Perfil, Gamificação & Assinaturas (`Profile & Gamification Context`)
* **Propósito**: Gerenciar dados cadastrais do usuário, troca de senha/e-mail, controle de limites de assinatura (`FREE` vs `PRO`) e concessão de conquistas (`Badges`).
* **Entidades Principais**: `Achievement`, `SubscriptionTier`.
* **Políticas**: `SubscriptionPolicy`.
* **Entradas (Use Cases)**: `ChangeEmailUseCase`, `ChangePasswordUseCase`, `UpdateLocationFallbackUseCase`, `UpgradeSubscriptionUseCase`, `ListUserAchievementsUseCase`.
* **Ports Requeridos**: `IAchievementRepository`, `IUserRepository`.
* **Regras de Negócio**:
  - O plano `PRO` desbloqueia plantas ilimitadas no jardim e consultas avançadas de saúde.

---

## 3. Padrão de Tratamento de Erros & Hierarquia (`src/domain/exceptions/`)

Para garantir previsibilidade total e evitar exceções genéricas/frouxas, todo o código do PlantE segue uma hierarquia de erros tipados herdando de `DomainException`.

### 3.1. Estrutura da Hierarquia de Exceções

```
                             ┌────────────────────────┐
                             │    DomainException     │
                             └───────────┬────────────┘
                                         │
       ┌───────────────────┬─────────────┴─────────────┬───────────────────┐
       │                   │                           │                   │
┌──────┴──────┐   ┌────────┴────────┐         ┌────────┴────────┐ ┌────────┴────────┐
│ EntityNotFound │ │ BusinessRule    │         │ Unauthorized    │ │ QuotaExceeded   │
│ Exception   │   │ ViolationException │       │ Exception       │ │ Exception       │
└─────────────┘   └─────────────────┘         └─────────────────┘ └─────────────────┘
```

### 3.2. Catálogo Padronizado de Códigos de Erro

Cada exceção carrega um **Código Único Máquina-Readable** e um **Status HTTP Padrão**:

| Código de Erro (`code`) | Exceção | Descrição | HTTP Status |
| :--- | :--- | :--- | :---: |
| `PLANTE_4000_DOMAIN_ERROR` | `PlantEError` | Base de todos os erros de domínio; não deve chegar ao cliente sem subclasse. | 400 |
| `PLANTE_4001_PLANT_NOT_FOUND` | `PlantNotFoundError` | Planta não existe ou não pertence ao usuário. | 404 |
| `PLANTE_4002_USER_NOT_FOUND` | `UserNotFoundError` | Usuário não encontrado. | 404 |
| `PLANTE_4003_INVALID_VERIFICATION_CODE` | `InvalidVerificationCodeError` | Código OTP inválido ou expirado. | 400 |
| `PLANTE_4004_EMAIL_ALREADY_IN_USE` | `EmailAlreadyInUseError` | E-mail já usado por outro usuário (cadastro ou troca de e-mail). | 409 |
| `PLANTE_4005_FREE_TIER_PLANT_LIMIT` | `PlantLimitExceededError` | Plano FREE atingiu o limite de plantas no jardim (`SubscriptionPolicy`). | 403 |
| `PLANTE_4006_UNAUTHORIZED` | `UnauthorizedError` | Token ausente, inválido ou expirado; login com credenciais erradas. | 401 |
| `PLANTE_4007_WRONG_CREDENTIALS` | `InvalidCredentialsError` | Senha atual incorreta ao alterar e-mail ou senha. | 400 |
| `PLANTE_4008_WEAK_PASSWORD` | `WeakPasswordError` | Nova senha não atende à política de senha. | 400 |
| `PLANTE_4009_FORBIDDEN` | `ForbiddenError` | Autenticado, mas sem permissão sobre o recurso (ex.: planta de outro usuário). | 403 |
| `PLANTE_4010_IDENTIFICATION_FAILED` | `PlantIdentificationError` | A IA não identificou a planta com confiança suficiente. | 422 |
| `PLANTE_4011_LOW_CONFIDENCE` | `LowConfidenceError` | Confiança da identificação abaixo de 60% (`ConfidenceScore.is_rejected`). | 422 |
| `PLANTE_4012_IDENTIFICATION_NOT_FOUND` | `IdentificationNotFoundError` | Identificação não existe ou não pertence ao usuário. | 404 |
| `PLANTE_4013_INVALID_IMAGE` | `InvalidImageError`, `NotAPlantError` | Imagem ilegível ou sem planta. Regras abaixo. | 400 |
| `PLANTE_4014_SPECIES_NOT_FOUND` | `SpeciesNotFoundError` | Espécie não existe. | 404 |
| `PLANTE_4015_SAMPLE_NOT_FOUND` | `SampleNotFoundError` | Amostra de identificação não existe. | 404 |
| `PLANTE_4016_NOT_READY_FOR_WATERING` | `PlantNotReadyForWateringError` | Rega antes do intervalo ou no mesmo dia (`UserPlant.water()`). | 400 |
| `PLANTE_4017_HEALTH_RECORD_NOT_FOUND` | `HealthRecordNotFoundError` | Diagnóstico não existe ou não pertence ao usuário. | 404 |
| `PLANTE_4018_RAW_RESPONSE_EXPIRED` | `RawResponseExpiredError` | Resposta bruta do Kindwise expirou no Redis (TTL 24h) antes da confirmação. | 410 |
| `PLANTE_4019_SUBSCRIPTION_REQUIRED` | `SubscriptionRequiredError` | Recurso exclusivo do plano Pro ou tokens diários esgotados (`SubscriptionPolicy`). | 403 |
| `PLANTE_4029_RATE_LIMIT_EXCEEDED` | `RateLimitExceededError` | Limite de requisições por minuto excedido (`RateLimitMiddleware`). | 429 |
| `PLANTE_4220_VALIDATION_ERROR` | — (FastAPI) | Corpo, query ou path da requisição inválidos. | 422 |
| `PLANTE_5000_INTERNAL_ERROR` | — (handler genérico) | Exceção inesperada; detalhes só no log. | 500 |
| `PLANTE_5001_EXTERNAL_SERVICE_ERROR` | `ExternalServiceError` | Provedor externo falhou (Kindwise, PlantNet, Gemini, Firebase, clima). Regras abaixo. | 502 |
| `PLANTE_5002_GEOCODING_ERROR` | `GeocodingError` | Serviço de geocodificação falhou. | 502 |
| `PLANTE_5003_SERVICE_NOT_READY` | — (probe) | Readiness: Postgres ou Redis indisponível (`/health/readiness`). | 503 |

**`PLANTE_4013` — quando um provedor de IA gera imagem inválida:**
* Kindwise: `is_plant.binary == false` explícito → `NotAPlantError` (campo ausente segue o fluxo normal); lista de sugestões vazia → `InvalidImageError`; HTTP 400 → `InvalidImageError` **só** se o corpo contiver o marcador `Invalid image` (outros 400 são payload nosso malformado → `ExternalServiceError(retryable=False)` + log `provider.request_rejected`).
* PlantNet: HTTP 400 com `Unsupported file type` ou 404 com `Species not found` → `InvalidImageError`; outros 400 (ex.: `organs` inválido) → `ExternalServiceError(retryable=False)`.
* Consenso: `NotAPlantError` do Kindwise veta a resposta do PlantNet (ver 2.2).

**`PLANTE_5001` — `retryable`:**
* `retryable=True`: falha transitória (rede, timeout, 5xx, 429). Só essas contam para abrir o circuit breaker do provedor.
* `retryable=False`: requisição rejeitada pelo provedor (payload nosso inválido, 401/403 de chave mal configurada — logado como `provider.misconfigured`). Não abre o circuito.
* Circuito aberto também responde `PLANTE_5001`. No `/diagnose`, falha do Gemini não derruba a resposta: o diagnóstico volta só com o Kindwise.

**Erros declarados por use case:** cada use case lista em `raises` os erros de domínio que pode lançar — os `raise` do próprio módulo (conferidos por `tests/unit/use_cases/test_declared_errors.py`) e os vindos de policies, entidades e ports (listados à mão). As rotas documentam o OpenAPI com `error_responses(*UseCase.raises)`.

### 3.3. Envelope Uniforme de Resposta HTTP (`ApiResponse[T]`)

Todas as respostas HTTP do sistema (sucesso ou erro) são embrulhadas na mesma estrutura JSON:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "PLANTE_4005_FREE_TIER_PLANT_LIMIT",
    "message": "Você atingiu o limite de 3 plantas do plano gratuito. Faça upgrade para o plano PRO.",
    "details": { "current_count": 3, "max_allowed": 3 }
  },
  "meta": {
    "timestamp": "2026-08-10T16:35:00Z"
  }
}
```

---

## 4. Padrões de Extensão para Desenvolvedores Open-Source

### 4.1. Como Adicionar um Novo Provedor de IA Botânica (`IPlantIdentifier`)
1. Crie o novo adapter em `src/adapters/ai/<nome_provedor>/<nome_provedor>_adapter.py`.
2. Implemente a interface `IPlantIdentifier` definida em `src/domain/ports/plant_identifier.py`.
3. Registre a nova classe no container `AdaptersContainer` em `src/infrastructure/containers/adapters.py`.
4. Adicione os testes unitários correspondentes em `tests/unit/adapters/`.

### 4.2. Como Adicionar um Novo Provedor de Envio de E-mail ou Push Notification
1. Crie o novo adapter implementando `IEmailSender` ou `INotificationSender`.
2. Configure o provedor no container e a chave de configuração em `Settings` (`src/infrastructure/settings.py`).

---

## 5. Padrões de Execução de Workers Assíncronos (Celery)

Para evitar vazamento de conexões de banco de dados e loops de eventos concorrentes:
- Todas as tarefas do Celery que chamam Use Cases ou Repositórios assíncronos **DEVEM** utilizar o decorator `@run_async` de `src/workers/async_runner.py`.
- O worker aceita injeção defensiva de `container: Container | None = None` para permitir testes unitários isolados com mocks.

---

## 6. Tipagem Estrita

`Any` é proibido: nem escrito (`disallow_any_explicit` + ruff `ANN401`), nem vindo de expressões ou decorators (`disallow_any_expr`, `disallow_any_decorated`). `cast` e `# type: ignore` não são usados para silenciar o checker.

* **Pydantic nas bordas, dataclasses no domínio.** Dado que vem de fora do processo entra por um modelo Pydantic: respostas de Kindwise/PlantNet/Gemini/Open-Meteo/Nominatim (`src/adapters/**`), claims do JWT, valores lidos do Redis, argumentos de tasks do Celery e corpo das requisições (`src/api/schemas/`). Dado criado dentro do processo é dataclass tipada: entidades, value objects, DTOs dos ports e saídas dos use cases. O domínio não depende do Pydantic.
* **IDs**: `NewType` sobre `UUID` por entidade (`UserId`, `UserPlantId`… em `src/domain/value_objects/ids.py`), gerados pelo domínio na criação (nunca pelo banco). O mypy impede passar o ID de uma entidade no lugar do de outra.
* **JSON opaco** (`raw_response`, `details` de erro): `JsonValue` / `JsonObject` (`src/domain/value_objects/json_value.py`), alias recursivo exato de JSON. Quem precisa ler um campo usa um modelo próprio na borda, não navega no JSON.
* **Origens**: `Literal` (`IdentificationOrigin`, `HealthSource`…), enums de texto são `StrEnum`.
* **Resposta fora do contrato** de um provedor é falha do provedor: `ExternalServiceError` não retryable + log `provider.unexpected_response`. O Gemini usa saída estruturada (`response_schema` = o modelo Pydantic), então é obrigado a responder no formato validado.
* **Cola de biblioteca**: alguns módulos falam com bibliotecas que tipam a própria API com `Any` (SQLAlchemy ORM, decorators do FastAPI/dependency_injector/Celery, redis-py, google-genai, PyJWT; o typeshed tipa até toda corrotina como `Coroutine[Any, Any, T]`). Esses módulos estão listados no `pyproject.toml`, com o motivo de cada um; neles só a checagem de expressões/decorators é desligada (`Any` escrito continua proibido) e o dado que sai para o domínio já sai tipado. Cada biblioteca fica isolada no menor módulo possível (ex.: `RedisClient`, `GeminiClient`, `JwtTokenService`). Bibliotecas sem tipos ganham stubs mínimos em `typings/` (ex.: `firebase_admin`).

---

## 7. Qualidade de Código & Checklist de Contribuição (CI/CD)

Antes de abrir um Pull Request no repositório, o contribuidor deve garantir (o CI roda os três em todo push e PR):

```bash
# 1. Executar a suíte completa de testes automatizados (persistência em Postgres via testcontainers: requer Docker)
uv run pytest

# 2. Verificar linting e formatação de código
uv run ruff check src tests migrations

# 3. Verificar tipagem estrita
uv run mypy
```

Testes de contrato contra as APIs reais dos provedores ficam fora do padrão e do CI (gastam créditos): `uv run pytest -m contract`.

---
