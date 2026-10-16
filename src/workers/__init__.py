"""Workers do Celery: `celery -A src.workers worker` (e `beat` para as tarefas agendadas)."""
from src.bootstrap.celery_config import celery_app

__all__ = ["celery_app"]
