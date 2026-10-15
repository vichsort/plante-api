import os
import uuid

import structlog
from celery import Celery, Task
from celery.signals import before_task_publish, task_postrun, task_prerun

broker_url = os.getenv("REDIS_ENDPOINT", "redis://localhost:6379/0")
if not broker_url.startswith("redis://"):
    pwd = os.getenv("REDIS_PASSWORD", "")
    host = os.getenv("REDIS_ENDPOINT", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    auth = f":{pwd}@" if pwd else ""
    broker_url = f"redis://{auth}{host}:{port}/0"

celery_app = Celery(
    "plante",
    broker=broker_url,
    backend=broker_url,
    # Carregados pelo worker ao subir; sem isto ele não registra nenhuma task (só nomes, sem
    # importar: `src.workers` fica acima desta camada)
    include=[
        "src.workers.notification_tasks",
    ],
)

# Tarefas agendadas (`celery -A src.workers beat`). A anonimização diária saiu: dado de treino
# já nasce anônimo, separado do dado do usuário.
celery_app.conf.beat_schedule = {}

# Correlation ID: a task herda o ID da requisição que a publicou. O nome evita `correlation_id`,
# que o Celery já usa como ID da própria task.
_CORRELATION_HEADER = "plante_correlation_id"


@before_task_publish.connect
def _attach_correlation_id(headers: dict[str, object] | None = None, **_: object) -> None:
    correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
    if headers is not None and correlation_id:
        headers[_CORRELATION_HEADER] = correlation_id


@task_prerun.connect
def _bind_correlation_id(task: object = None, **_: object) -> None:
    # Tasks do beat (sem requisição de origem) ganham um ID próprio por execução
    correlation_id = getattr(task.request, _CORRELATION_HEADER, None) if isinstance(task, Task) else None
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id or str(uuid.uuid4()))


@task_postrun.connect
def _clear_correlation_id(**_: object) -> None:
    structlog.contextvars.clear_contextvars()
