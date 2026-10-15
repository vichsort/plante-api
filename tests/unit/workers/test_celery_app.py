from celery.app.utils import find_app

from src.adapters.events.celery_publisher import SEND_VERIFICATION_EMAIL_TASK
from src.infrastructure.celery_config import celery_app
from src.infrastructure.settings import get_settings


def test_worker_command_finds_the_app() -> None:
    # `celery -A src.workers worker` (comando do Dockerfile)
    assert find_app("src.workers") is celery_app


def test_worker_registers_published_and_scheduled_tasks() -> None:
    # O que o worker faz ao subir: importa os módulos de `include`
    celery_app.loader.import_default_modules()

    scheduled = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
    assert {SEND_VERIFICATION_EMAIL_TASK, *scheduled} <= set(celery_app.tasks)


def test_broker_uses_the_same_redis_url_as_the_app() -> None:
    # `REDIS_ENDPOINT` é só o host, para o broker e para o `RedisClient`
    assert celery_app.conf.broker_url == get_settings().redis_url
