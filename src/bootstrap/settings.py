from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Banco
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "plante"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # Redis
    redis_user: str = "default"
    redis_password: str = ""
    redis_endpoint: str = "localhost"
    redis_port: int = 6379
    # Curtos: Redis lento não pode segurar toda requisição (rate limit roda em todas as rotas)
    redis_socket_timeout_seconds: float = 0.5
    redis_connect_timeout_seconds: float = 0.5

    @property
    def kindwise_key(self) -> str | None:
        """`KINDWISE_API_KEY`, ou o nome antigo (`PLANT_ID_API_KEY`) para quem ainda o usa."""
        return self.kindwise_api_key or self.plant_id_api_key

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://{self.redis_user}:{self.redis_password}@{self.redis_endpoint}:{self.redis_port}"
        return f"redis://{self.redis_endpoint}:{self.redis_port}"

    # IA
    gemini_api_key: str | None = None
    kindwise_api_key: str | None = None
    plantnet_api_key: str | None = None
    # Nome antigo da chave do Kindwise: o container lia só ele, e o `.env.example` e o README
    # documentam `KINDWISE_API_KEY` (com o `.env` do exemplo, o Kindwise recebia a chave vazia)
    plant_id_api_key: str | None = None
    # Circuit breaker de cada provedor de IA (Kindwise, PlantNet)
    ai_breaker_failure_threshold: int = 5
    ai_breaker_recovery_timeout_seconds: float = 30.0

    # Auth
    secret_key: str = "dev_secret_key_change_in_production"
    jwt_algorithm: str = "HS256"

    # Image storage: `local` keeps the photos in a folder of the server, served by the API through
    # signed links; `s3` is any S3-compatible storage (AWS, or Cloudflare R2 with S3_ENDPOINT_URL)
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: str = "data/images"
    # Address the client uses to reach the API: the local storage's links point to it
    public_api_url: str = "http://localhost:8000"
    # How long an image link lasts (the local storage's last between one and two of these)
    image_link_ttl_seconds: int = 3600

    # Email: `log` only writes the messages to the log (development, or no provider yet); `smtp` is
    # any provider (Resend, Brevo, Gmail...); `ses` is AWS
    email_backend: Literal["log", "smtp", "ses"] = "log"
    email_from: str = "noreply@plante.app"
    # Off: accounts are born verified, no code is sent, and an email change applies at once
    email_verification_required: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    # `starttls` (port 587), `ssl` (port 465) or `none` (a local relay only)
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"

    # Aws
    aws_region: str = "us-east-1"
    s3_bucket: str = "plante-bucket-name"
    s3_endpoint_url: str | None = None
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # App
    debug: bool = False
    # Dia local (rega, sequência, cota diária de tokens, cron): nome IANA do fuso
    local_timezone: str = "America/Sao_Paulo"
    consensus_enabled: bool = True

    # Quota (docs/decisions/2026-10-19-funding-and-quota.md): `standard` is everyone's and goes up as
    # donations cover the costs; `extended` is granted by the maintainer, by request
    quota_standard_max_plants: int = 3
    quota_standard_daily_tokens: int = 3
    quota_extended_max_plants: int = 10
    quota_extended_daily_tokens: int = 10
    # The whole service's identifications and diagnoses per local day (1 Kindwise credit each),
    # however many accounts there are
    provider_daily_limit: int = 30

@lru_cache
def get_settings() -> Settings:
    return Settings()