import uuid

import structlog
from celery import Celery, Task
from celery.schedules import crontab
from celery.signals import before_task_publish, task_postrun, task_prerun

from src.bootstrap.settings import get_settings

# Mesma URL do `RedisClient`: `REDIS_ENDPOINT` é só o host (antes o broker aceitava também uma
# URL completa, e com ela o worker conectava na fila mas o `RedisClient` dele quebrava)
broker_url = get_settings().redis_url

celery_app = Celery(
    "plante",
    broker=broker_url,
    backend=broker_url,
    # Carregados pelo worker ao subir; sem isto ele não registra nenhuma task (só nomes, sem
    # importar: `src.workers` fica acima desta camada)
    include=[
        "src.bootstrap.worker",
        "src.modules.identity.workers.tasks",
        "src.workers.garden_tasks",
    ],
)

# Celery 6 deixa de tentar reconectar ao broker na subida sem isto (hoje só avisa)
celery_app.conf.broker_connection_retry_on_startup = True

# Tarefas agendadas (`celery -A src.workers beat`, uma instância só). O crontab segue o fuso
# local: "03:00" é de madrugada no Brasil, longe da virada do dia e do horário de uso.
celery_app.conf.update(timezone=get_settings().local_timezone)
celery_app.conf.beat_schedule = {
    "garden-break-missed-streaks": {
        "task": "garden.break_missed_streaks",
        "schedule": crontab(hour=3, minute=0),
    },
}

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
