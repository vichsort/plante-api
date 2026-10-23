import asyncio
import smtplib
import ssl
from email.message import EmailMessage as MimeMessage
from typing import Literal

from src.modules.identity.adapters.email.messages import (
    EmailMessage,
    password_changed,
    verification_code,
)
from src.modules.identity.domain.ports.email_sender import IEmailSender

SmtpSecurity = Literal["starttls", "ssl", "none"]
_TIMEOUT_SECONDS = 15.0


class SmtpEmailSender(IEmailSender):
    """
    Any SMTP provider (Resend, Brevo, Gmail...). The standard library's client runs in a thread;
    one connection per message is plenty at a few emails a day. A failure raises, and the Celery
    task that sends the code retries it.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        sender_email: str,
        security: SmtpSecurity,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender_email
        self._security = security

    async def send_verification_code(self, to_email: str, code: str) -> None:
        await asyncio.to_thread(self._send, to_email, verification_code(code))

    async def send_password_changed_notice(self, to_email: str) -> None:
        await asyncio.to_thread(self._send, to_email, password_changed())

    def _send(self, to_email: str, message: EmailMessage) -> None:
        mime: MimeMessage[str, str] = MimeMessage()
        mime["From"] = self._sender
        mime["To"] = to_email
        mime["Subject"] = message.subject
        mime.set_content(message.body)

        context = ssl.create_default_context()
        smtp = (
            smtplib.SMTP_SSL(self._host, self._port, timeout=_TIMEOUT_SECONDS, context=context)
            if self._security == "ssl"
            else smtplib.SMTP(self._host, self._port, timeout=_TIMEOUT_SECONDS)
        )
        with smtp:
            if self._security == "starttls":
                smtp.starttls(context=context)
            if self._username:
                smtp.login(self._username, self._password)
            smtp.send_message(mime)
