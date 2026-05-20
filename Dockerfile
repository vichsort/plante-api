# =============================================================================
# builder
# =============================================================================
FROM python:3.12-slim AS builder

# Instala uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copia apenas os arquivos de dependência primeiro (cache layer)
COPY pyproject.toml uv.lock ./

# Instala dependências do env sem dev dependencies
RUN uv sync --frozen --no-dev

# =============================================================================
# runtime
# =============================================================================
FROM python:3.12-slim AS runtime

# Cria usuário não-root (boa prática de segurança)
RUN groupadd --system plante && useradd --system --gid plante plante

WORKDIR /app

# Copia o venv gerado no builder
COPY --from=builder /app/.venv /app/.venv

# Copia o código fonte
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Garante que o venv tem prioridade no PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER plante

EXPOSE 8000

# Comando padrão: API
# Para workers, sobrescreva no docker-compose de produção:
#   command: celery -A src.workers worker ...
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]