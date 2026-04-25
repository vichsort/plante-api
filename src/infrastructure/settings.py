from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Banco
    db_host: str
    db_port: int = 5432
    db_user: str
    db_password: str
    db_name: str

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # Redis
    redis_user: str = "default"
    redis_password: str
    redis_endpoint: str
    redis_port: int

    @property
    def redis_url(self) -> str:
        return (
            f"redis://{self.redis_user}:{self.redis_password}"
            f"@{self.redis_endpoint}:{self.redis_port}"
        )

    # IA
    gemini_api_key: str
    plantnet_api_key: str | None = None

    # Auth
    secret_key: str
    jwt_algorithm: str = "HS256"

    # Aws
    aws_region: str = "us-east-1"
    s3_bucket: str = "plante-bucket-name"
    aws_access_key_id: str
    aws_secret_access_key: str
    ses_sender_email: str

    # Firebase
    google_application_credentials: str

    # App
    debug: bool = False

@lru_cache
def get_settings() -> Settings:
    return Settings()