import structlog

from src.modules.identity.adapters.email.messages import (
    EmailMessage,
    password_changed,
    verification_code,
)
from src.modules.identity.domain.ports.email_sender import IEmailSender

log = structlog.stdlib.get_logger()


class LogEmailSender(IEmailSender):
    """
    Sends nothing: writes the message to the log. For development, or while there is no provider
    (with verification off, only the password notice comes here). The log carries the codes, so it
    is no backend for production with verification on.
    """

    async def send_verification_code(self, to_email: str, code: str) -> None:
        self._write(to_email, verification_code(code))

    async def send_password_changed_notice(self, to_email: str) -> None:
        self._write(to_email, password_changed())

    def _write(self, to_email: str, message: EmailMessage) -> None:
        log.info("email.not_sent", to=to_email, subject=message.subject, body=message.body)
