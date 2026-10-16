"""Tasks do módulo e a rota evento → task, para a composição."""
from src.modules.identity.workers.tasks import (
    SEND_VERIFICATION_EMAIL_TASK,
    route_event,
    send_verification_email_task,
)

__all__ = ["SEND_VERIFICATION_EMAIL_TASK", "route_event", "send_verification_email_task"]
