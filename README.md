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
- 💧 **Rotina de rega** com sequência de regas no prazo
- 🏆 **Sistema de conquistas** para engajamento do usuário

---

## Arquitetura

Monólito modular, hexagonal por dentro de cada módulo: um subdomínio por pasta em `src/modules/`, com o domínio puro e as dependências apontando para dentro. O kernel comum fica em `src/shared/`, e a composição (container, settings, Celery) em `src/bootstrap/`. `src/workers` é só a entrada do Celery (`celery -A src.workers`).

As regras (layout, imports, erros, testes) estão no [`ARCHITECTURE.md`](ARCHITECTURE.md) e a maioria é conferida no CI. Cada módulo explica o próprio propósito e as decisões no `README.md` dele.

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
| Storage | Disco local ou S3-compatível (AWS S3, Cloudflare R2) |
| E-mail | SMTP (qualquer provedor) ou AWS SES |
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

### 7. Inicie os workers

```bash
uv run celery -A src.workers worker --loglevel=info   # tasks (e-mail de verificação)
uv run celery -A src.workers beat --loglevel=info     # agendadas (sequência de rega); uma instância só
```

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
| `SECRET_KEY` | Chave secreta para JWT (e, derivada dela, a dos links de imagem) |
| `STORAGE_BACKEND` | `local` (padrão: pasta do servidor, servida pela API) ou `s3` |
| `STORAGE_LOCAL_ROOT` | Pasta das imagens com `local` (padrão `data/images`; faça backup) |
| `PUBLIC_API_URL` | Endereço da API visto pelo cliente (os links de imagem locais apontam para ele) |
| `S3_BUCKET` / `S3_ENDPOINT_URL` | Bucket e, para R2 ou outro S3-compatível, o endereço |
| `AWS_ACCESS_KEY_ID` | Credencial AWS (S3 + SES) |
| `AWS_SECRET_ACCESS_KEY` | Credencial AWS |
| `EMAIL_BACKEND` | `log` (padrão: só escreve no log), `smtp` ou `ses` |
| `EMAIL_FROM` | Remetente dos e-mails |
| `EMAIL_VERIFICATION_REQUIRED` | `false` enquanto não houver provedor: a conta já nasce verificada |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_SECURITY` | Provedor SMTP (`starttls`, `ssl` ou `none`) |
| `TURNSTILE_SECRET_KEY` | Chave secreta do Cloudflare Turnstile (captcha do cadastro); vazia desliga |
| `TERMS_VERSION` / `TERMS_URL` | Versão vigente dos termos e o link do texto (no site); versão nova exige novo aceite |
| `PROVIDER_DAILY_LIMIT` | Identificações + diagnósticos por dia no serviço inteiro (padrão 30) |

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