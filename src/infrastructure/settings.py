from functools import lru_cache

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
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://{self.redis_user}:{self.redis_password}@{self.redis_endpoint}:{self.redis_port}"
        return f"redis://{self.redis_endpoint}:{self.redis_port}"

    # IA
    gemini_api_key: str | None = None
    kindwise_api_key: str | None = None
    plantnet_api_key: str | None = None
    plant_id_api_key: str | None = None
    # Circuit breaker de cada provedor de IA (Kindwise, PlantNet)
    ai_breaker_failure_threshold: int = 5
    ai_breaker_recovery_timeout_seconds: float = 30.0

    # Auth
    secret_key: str = "dev_secret_key_change_in_production"
    jwt_algorithm: str = "HS256"

    # Aws
    aws_region: str = "us-east-1"
    s3_bucket: str = "plante-bucket-name"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    ses_sender_email: str = "noreply@plante.app"

    # App
    debug: bool = False
    # Dia do jardim (rega, sequência, cron diário): nome IANA do fuso
    garden_timezone: str = "America/Sao_Paulo"
    consensus_enabled: bool = True

@lru_cache
def get_settings() -> Settings:
    return Settings()