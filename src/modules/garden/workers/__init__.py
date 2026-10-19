"""Tasks do módulo, para a composição registrar no worker (o beat agenda pelo nome)."""
from src.modules.garden.workers.tasks import (
    BREAK_MISSED_STREAKS_TASK,
    break_missed_streaks_task,
)

__all__ = ["BREAK_MISSED_STREAKS_TASK", "break_missed_streaks_task"]
