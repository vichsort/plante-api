<div align="center">

<img src="assets/logo.svg" alt="PlantE Logo" width="120" />

# PlantE API

**Identificação botânica inteligente para o cultivo residencial.**  
Transformando uma câmera em um tutor completo de saúde vegetal.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Issues](https://img.shields.io/github/issues/vichsort/plante-api?style=flat-square&color=f59e0b)](https://github.com/vichsort/plante-api/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-22c55e?style=flat-square)](https://github.com/vichsort/plante-api/pulls)

</div>

---

## Sobre o projeto

PlantE é um sistema de identificação e gestão botânica focado em cultivo residencial. O objetivo é democratizar a jardinagem através de tecnologia - transformando uma simples foto em um diagnóstico completo de saúde vegetal, com lembretes inteligentes, alertas climáticos e tratamentos guiados passo a passo.

Ao inserir uma imagem, você estará contribuindo para a construção de uma base de dados de botânica brasileira doméstica, que poderá ser referenciada por artigos acadêmicos, instituições ESG no futuro! Para melhor entender, acesse o site oficial do [PlantE](https://www.planteai.org)!

Este repositório contém o **backend da plataforma**, construído com arquitetura hexagonal para garantir máxima testabilidade e independência de infraestrutura.

### Funcionalidades

- 🌿 **Identificação de espécies** via foto com consensus engine (PlantNet + Kindwise)
- 🔬 **Diagnóstico de saúde** e detecção de pragas/doenças
- 💧 **Lembretes inteligentes** de rega e poda por worker assíncrono
- 🌦️ **Alertas climáticos** integrados via Open-Meteo
- 🔔 **Notificações push** via Firebase Cloud Messaging
- 🏆 **Sistema de conquistas** para engajamento do usuário

---

## Arquitetura

O projeto segue **Arquitetura Hexagonal (Ports & Adapters)**, garantindo que o domínio de negócio nunca dependa de infraestrutura.

```
src/
├── domain/          # Regras de negócio puras — zero dependências externas
│   ├── entities/    # Plant, HealthRecord, UserPlant...
│   ├── use_cases/   # IdentifyPlant, DiagnoseHealth, ScheduleCare...
│   ├── ports/       # Interfaces ABC (IPlantIdentifier, IRepository...)
│   └── policies/    # SubscriptionPolicy, ConsensusPolicy
├── adapters/        # Implementações concretas das ports
│   ├── ai/          # Gemini, PlantNet, Kindwise, Consensus Engine
│   ├── persistence/ # SQLAlchemy models + repositories
│   ├── storage/     # S3
│   ├── weather/     # Open-Meteo + Nominatim
│   └── notifications/ # Firebase FCM
├── api/             # Routers FastAPI + schemas Pydantic
├── workers/         # Tasks Celery por domínio
└── infrastructure/  # Container DI, settings, engine async
```

**MUITO IMPORTANTE:** dependências sempre apontam para dentro. Adapters conhecem o domínio. O domínio nunca conhece adapters.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Runtime | Python 3.12 + FastAPI + Uvicorn (ASGI) |
| Banco de dados | PostgreSQL 16 + SQLAlchemy 2 (async) + Alembic |
| Cache / Broker | Redis 7 |
| Workers | Celery 5 + Celery Beat |
| IA principal | Google Gemini API |
| IA consensus | PlantNet + Kindwise |
| Push notifications | Firebase Cloud Messaging |
| Clima | Open-Meteo (gratuita) |
| Storage | AWS S3 |
| E-mail | AWS SES |
| Logs | structlog (JSON estruturado) |
| Gerenciador de pacotes | uv |

---

## Pré-requisitos

- [Python 3.12+](https://python.org)
- [uv](https://docs.astral.sh/uv/) — gerenciador de pacotes
- [Docker](https://docker.com/products/docker-desktop) — para rodar PostgreSQL e Redis localmente

---

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/vichsort/plante-api.git
cd plante-api
```

### 2. Instale as dependências

```bash
uv sync --extra dev
```

### 3. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env com suas credenciais
```

### 4. Suba a infraestrutura local

```bash
docker compose up -d
```

Isso sobe PostgreSQL e Redis em containers. A API e os workers rodam diretamente na sua máquina com `uv run`.

### 5. Rode as migrations

```bash
uv run alembic upgrade head
```

### 6. Inicie a API

```bash
uv run uvicorn src.main:app --reload
```

A API estará disponível em `http://localhost:8000`.  
Documentação interativa: `http://localhost:8000/docs`

---

## Comandos úteis

```bash
# Subir infra (postgres + redis)
docker compose up -d

# Derrubar infra
docker compose down

# Reset total (apaga volumes)
docker compose down -v

# Gerar nova migration após alterar um model
uv run alembic revision --autogenerate -m "descricao_da_mudanca"

# Aplicar migrations
uv run alembic upgrade head

# Reverter última migration
uv run alembic downgrade -1

# Rodar testes
uv run pytest

# Instalar nova dependência
uv add nome-da-lib
```

---

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Descrição |
|---|---|
| `DB_HOST` | Host do PostgreSQL |
| `DB_USER` | Usuário do banco |
| `DB_PASSWORD` | Senha do banco |
| `DB_NAME` | Nome do banco |
| `REDIS_ENDPOINT` | Host do Redis |
| `REDIS_PASSWORD` | Senha do Redis (deixe vazio para dev local) |
| `GEMINI_API_KEY` | Chave da API do Google Gemini |
| `KINDWISE_API_KEY` | Chave da API da Kindwise |
| `PLANTNET_API_KEY` | Chave da API do PlantNet |
| `SECRET_KEY` | Chave secreta para JWT |
| `AWS_ACCESS_KEY_ID` | Credencial AWS (S3 + SES) |
| `AWS_SECRET_ACCESS_KEY` | Credencial AWS |
| `SES_SENDER_EMAIL` | E-mail remetente cadastrado no SES |
| `GOOGLE_APPLICATION_CREDENTIALS` | Caminho para o JSON do Firebase |

---

## Contribuindo

Contribuições são muito bem-vindas! O projeto foi estruturado para facilitar a entrada de novos colaboradores.

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feat/minha-feature`)
3. Respeite a arquitetura hexagonal — domínio nunca importa infraestrutura
4. Escreva testes para o que foi adicionado
5. Abra um Pull Request descrevendo o que foi feito

Para dúvidas sobre a arquitetura, abra uma [issue](https://github.com/vichsort/plante-api/issues) antes de implementar.

---

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para mais informações.

---

<div align="center">
  <sub>Para você 🌱 plantar mais que no solo!</sub>
</div>