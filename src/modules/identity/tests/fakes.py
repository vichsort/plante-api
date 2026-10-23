"""
Dublês do identity: `FakeUserDirectory` para quem usa o módulo (outros módulos) e,
para os testes daqui, as portas em memória.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import uuid4

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.exceptions import TermsNotAcceptedError
from src.modules.identity.domain.ports.captcha_verifier import ICaptchaVerifier
from src.modules.identity.domain.ports.email_sender import IEmailSender
from src.modules.identity.domain.ports.otp_repository import IOtpRepository
from src.modules.identity.domain.ports.password_hasher import IPasswordHasher
from src.modules.identity.domain.ports.token_repository import ITokenRepository
from src.modules.identity.domain.ports.unit_of_work import IIdentityUnitOfWork
from src.modules.identity.domain.ports.user_repository import IUserRepository
from src.modules.identity.domain.services.user_directory import IUserDirectory
from src.modules.identity.domain.value_objects.terms import Terms
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.shared.domain import UserId, UserNotFoundError

TERMS = Terms(version="1", url="https://plante.test/terms")


def make_user(
    email: str = "user@plante.org",
    password: str = "Secret1password",
    is_verified: bool = True,
    terms_version: str | None = TERMS.version,
) -> User:
    """Conta válida (com os termos em vigor aceitos); a senha fica com o hash do `PlainHasher`."""
    return User(
        id=UserId(uuid4()),
        email=email,
        hashed_password=PlainHasher().hash(password),
        location=UserLocation(country="BR", state="SP"),
        is_verified=is_verified,
        created_at=datetime.now(UTC),
        terms_version=terms_version,
        terms_accepted_at=datetime.now(UTC) if terms_version else None,
    )


@dataclass
class FakeUserDirectory(IUserDirectory):
    """Todo usuário existe, mora em `location` e aceitou os termos, menos os de `missing` e `without_terms`."""
    location: UserLocation = field(default_factory=lambda: UserLocation(country="BR", state="SP"))
    missing: set[UserId] = field(default_factory=set)
    without_terms: set[UserId] = field(default_factory=set)

    async def id_by_email(self, email: str) -> UserId:
        raise UserNotFoundError("No account has this email.")

    async def ensure_exists(self, user_id: UserId) -> None:
        await self.region_of(user_id)

    async def region_of(self, user_id: UserId) -> UserLocation:
        if user_id in self.missing:
            raise UserNotFoundError(user_id=user_id)
        return self.location

    async def ensure_accepted_terms(self, user_id: UserId) -> None:
        await self.region_of(user_id)
        if user_id in self.without_terms:
            raise TermsNotAcceptedError(TERMS.version)


class InMemoryUserRepository(IUserRepository):
    def __init__(self, *users: User) -> None:
        self.by_id: dict[UserId, User] = {user.id: user for user in users}

    async def save(self, user: User) -> User:
        self.by_id[user.id] = user
        return user

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self.by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.by_id.values() if user.email == email), None)

    async def delete(self, user_id: UserId) -> None:
        self.by_id.pop(user_id, None)


class FakeIdentityUnitOfWork(IIdentityUnitOfWork):
    """Contas em memória (gravadas na hora, sem rollback) e contagem de commits."""

    def __init__(self, users: InMemoryUserRepository | None = None) -> None:
        self.users: InMemoryUserRepository = users or InMemoryUserRepository()
        self.commits = 0

    @property
    def joined(self) -> bool:
        return False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class PlainHasher(IPasswordHasher):
    """Hash legível e determinístico: os testes conferem a senha gravada sem o custo do bcrypt."""

    def hash(self, plain_password: str) -> str:
        return f"hashed:{plain_password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return hashed_password == self.hash(plain_password)


class InMemoryTokenRepository(ITokenRepository):
    """Um refresh token por usuário, como o Redis guarda."""

    def __init__(self) -> None:
        self.tokens: dict[UserId, str] = {}

    async def save_refresh_token(self, user_id: UserId, token: str, ttl_seconds: int) -> None:
        self.tokens[user_id] = token

    async def get_refresh_token(self, user_id: UserId) -> str | None:
        return self.tokens.get(user_id)

    async def delete_refresh_token(self, user_id: UserId) -> None:
        self.tokens.pop(user_id, None)


class InMemoryOtpRepository(IOtpRepository):
    def __init__(self) -> None:
        self.codes: dict[UserId, str] = {}

    async def save_code(self, user_id: UserId, code: str, expires_in_minutes: int = 15) -> None:
        self.codes[user_id] = code

    async def get_active_code_for_user(self, user_id: UserId) -> str | None:
        return self.codes.get(user_id)

    async def consume_code(self, user_id: UserId) -> None:
        self.codes.pop(user_id, None)


@dataclass
class RecordingEmailSender(IEmailSender):
    """Guarda os e-mails que seriam enviados: (destino, código ou `None` no aviso de senha)."""
    sent: list[tuple[str, str | None]] = field(default_factory=list)

    async def send_verification_code(self, to_email: str, code: str) -> None:
        self.sent.append((to_email, code))

    async def send_password_changed_notice(self, to_email: str) -> None:
        self.sent.append((to_email, None))


@dataclass
class StubCaptchaVerifier(ICaptchaVerifier):
    """Accepts only `valid_token`; `checked` keeps what it was asked."""
    valid_token: str = "captcha-ok"
    checked: list[tuple[str | None, str | None]] = field(default_factory=list)

    async def verify(self, token: str | None, client_ip: str | None) -> bool:
        self.checked.append((token, client_ip))
        return token == self.valid_token
