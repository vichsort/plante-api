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

| Código de Erro (`code`) | Categoria / Descrição | HTTP Status |
| :--- | :--- | :---: |
| `PLANTE_4001_PLANT_NOT_FOUND` | Planta informada não foi encontrada ou foi removida. | 404 |
| `PLANTE_4002_USER_NOT_FOUND` | Usuário não encontrado no banco de dados. | 404 |
| `PLANTE_4003_INVALID_OTP` | Código OTP de verificação inválido ou expirado. | 400 |
| `PLANTE_4004_EMAIL_ALREADY_EXISTS` | Tentativa de cadastro com e-mail já registrado. | 409 |
| `PLANTE_4005_FREE_TIER_PLANT_LIMIT` | Limite de 3 plantas do plano FREE atingido. | 403 |
| `PLANTE_4006_UNAUTHORIZED` | Credenciais inválidas ou token JWT expirado. | 401 |
| `PLANTE_4007_INVALID_PASSWORD` | Senha atual incorreta durante alteração de perfil. | 400 |
| `PLANTE_4029_RATE_LIMIT_EXCEEDED` | Limite de requisições por minuto excedido (ver `RateLimitMiddleware`). | 429 |

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

## 6. Qualidade de Código & Checklist de Contribuição (CI/CD)

Antes de abrir um Pull Request no repositório, o contribuidor deve garantir:

```bash
# 1. Executar a suíte completa de testes automatizados
uv run pytest

# 2. Verificar linting e formatação de código
uv run ruff check .
```

---
