"""The email backends: SMTP speaks the chosen security, the log sends nothing, `.env` picks one."""
import smtplib
from collections.abc import Callable
from email.message import EmailMessage
from types import TracebackType

import pytest
import structlog

from src.modules.identity.adapters.email.log import LogEmailSender
from src.modules.identity.adapters.email.smtp import SmtpEmailSender, SmtpSecurity
from src.modules.identity.container import IdentityContainer


class _FakeSmtp:
    """Records what the sender asks of the server (`smtplib.SMTP` and `SMTP_SSL` share the calls)."""

    def __init__(self, kind: str, host: str, port: int) -> None:
        self.calls: list[str] = [f"{kind} {host}:{port}"]
        self.sent: list[EmailMessage] = []

    def __enter__(self) -> "_FakeSmtp":
        return self

    def __exit__(self, kind: type[BaseException] | None, error: BaseException | None, tb: TracebackType | None) -> None:
        self.calls.append("quit")

    def starttls(self, context: object) -> None:
        self.calls.append("starttls")

    def login(self, username: str, password: str) -> None:
        self.calls.append(f"login {username}")

    def send_message(self, message: EmailMessage) -> None:
        self.calls.append("send")
        self.sent.append(message)


@pytest.fixture
def servers(monkeypatch: pytest.MonkeyPatch) -> list[_FakeSmtp]:
    opened: list[_FakeSmtp] = []

    def server(kind: str) -> Callable[..., _FakeSmtp]:
        def open_server(host: str, port: int, **_: object) -> _FakeSmtp:
            opened.append(_FakeSmtp(kind, host, port))
            return opened[-1]
        return open_server

    monkeypatch.setattr(smtplib, "SMTP", server("plain"))
    monkeypatch.setattr(smtplib, "SMTP_SSL", server("ssl"))
    return opened


def _smtp(security: SmtpSecurity, username: str = "resend") -> SmtpEmailSender:
    return SmtpEmailSender(
        host="smtp.resend.com", port=587, username=username, password="key",
        sender_email="noreply@plante.org", security=security,
    )


@pytest.mark.parametrize("security, expected", [
    ("starttls", ["plain smtp.resend.com:587", "starttls", "login resend", "send", "quit"]),
    ("ssl", ["ssl smtp.resend.com:587", "login resend", "send", "quit"]),
])
async def test_smtp_sends_the_code_with_the_chosen_security(
    servers: list[_FakeSmtp], security: SmtpSecurity, expected: list[str],
) -> None:
    # Act
    await _smtp(security).send_verification_code("new@plante.org", "PLA-123-4-567")

    # Assert
    (server,) = servers
    assert server.calls == expected
    (message,) = server.sent
    assert (message["From"], message["To"]) == ("noreply@plante.org", "new@plante.org")
    assert "PLA-123-4-567" in message.get_content()


async def test_smtp_without_credentials_does_not_log_in(servers: list[_FakeSmtp]) -> None:
    # Act: a local relay
    await _smtp("none", username="").send_password_changed_notice("user@plante.org")

    # Assert
    (server,) = servers
    assert server.calls == ["plain smtp.resend.com:587", "send", "quit"]


async def test_log_sender_writes_the_message_and_sends_nothing() -> None:
    # Act
    with structlog.testing.capture_logs() as logs:
        await LogEmailSender().send_verification_code("new@plante.org", "PLA-123-4-567")

    # Assert
    (entry,) = logs
    assert (entry["event"], entry["to"]) == ("email.not_sent", "new@plante.org")
    assert "PLA-123-4-567" in entry["body"]


@pytest.mark.parametrize("backend, expected", [("log", LogEmailSender), ("smtp", SmtpEmailSender)])
def test_the_backend_comes_from_the_settings(backend: str, expected: type) -> None:
    # Arrange
    container = IdentityContainer(
        email_backend=backend, email_from="noreply@plante.org", aws_region="us-east-1",
        smtp_host="smtp.resend.com", smtp_port=587, smtp_username="resend", smtp_password="key", smtp_security="starttls",
    )

    # Act
    sender = container.email_sender()

    # Assert
    assert isinstance(sender, expected)
