import pytest

from src.modules.identity.adapters.security.jwt_token_service import JwtTokenService
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.events import UserRegisteredEvent
from src.modules.identity.domain.exceptions import (
    CaptchaFailedError,
    EmailAlreadyInUseError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    TermsNotAcceptedError,
    WeakPasswordError,
)
from src.modules.identity.domain.ports.token_service import TokenKind
from src.modules.identity.domain.use_cases.login import LoginUseCase
from src.modules.identity.domain.use_cases.register_user import (
    RegisterUserInputDTO,
    RegisterUserUseCase,
)
from src.modules.identity.tests.fakes import (
    TERMS,
    FakeIdentityUnitOfWork,
    InMemoryTokenRepository,
    InMemoryUserRepository,
    PlainHasher,
    StubCaptchaVerifier,
    make_user,
)
from src.shared.domain import DomainEvent, IDomainPublisher

TOKENS = JwtTokenService(secret_key="testsecretkey-with-at-least-32-bytes", algorithm="HS256")


class _Publisher(IDomainPublisher):
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


def _register(
    uow: FakeIdentityUnitOfWork, publisher: _Publisher | None = None, verification_required: bool = True,
) -> RegisterUserUseCase:
    return RegisterUserUseCase(
        uow=uow, hasher=PlainHasher(), publisher=publisher or _Publisher(), captcha=StubCaptchaVerifier(),
        terms=TERMS, verification_required=verification_required,
    )


def _dto(
    email: str = "new@plante.org", password: str = "Secret1password", captcha_token: str | None = "captcha-ok",
    terms: str | None = "1",
) -> RegisterUserInputDTO:
    return RegisterUserInputDTO(
        email=email, password=password, country="BR", state="SP", accepted_terms_version=terms,
        captcha_token=captcha_token, client_ip="203.0.113.7",
    )


def _login(*users: User, verification_required: bool = True) -> tuple[LoginUseCase, InMemoryTokenRepository]:
    tokens = InMemoryTokenRepository()
    uow = FakeIdentityUnitOfWork(InMemoryUserRepository(*users))
    use_case = LoginUseCase(
        uow=uow, hasher=PlainHasher(), token_repo=tokens, token_service=TOKENS, verification_required=verification_required,
    )
    return use_case, tokens


async def test_register_saves_an_unverified_user_and_announces_it() -> None:
    # Arrange
    uow, publisher = FakeIdentityUnitOfWork(), _Publisher()

    # Act
    user = await _register(uow, publisher).execute(_dto())

    # Assert
    assert await uow.users.get_by_email("new@plante.org") is user
    assert (user.is_verified, user.hashed_password, uow.commits) == (False, "hashed:Secret1password", 1)
    assert (user.terms_version, user.terms_accepted_at is not None) == ("1", True)  # the consent on record
    assert publisher.events == [UserRegisteredEvent(
        occurred_on=publisher.events[0].occurred_on, user_id=user.id, email=user.email, requires_verification=True,
    )]


async def test_register_without_verification_creates_a_verified_account() -> None:
    # Arrange: no provider sends the code yet
    uow, publisher = FakeIdentityUnitOfWork(), _Publisher()

    # Act
    user = await _register(uow, publisher, verification_required=False).execute(_dto())

    # Assert: verified, and the event says no code is needed
    assert user.is_verified
    (event,) = publisher.events
    assert isinstance(event, UserRegisteredEvent) and not event.requires_verification


@pytest.mark.parametrize("token", [None, "forged"])
async def test_register_without_a_valid_captcha_creates_nothing(token: str | None) -> None:
    # Arrange: the address is even taken, and the bot still learns nothing
    uow, publisher = FakeIdentityUnitOfWork(InMemoryUserRepository(make_user(email="existing@plante.org"))), _Publisher()

    # Act & Assert
    with pytest.raises(CaptchaFailedError):
        await _register(uow, publisher).execute(_dto(email="existing@plante.org", captcha_token=token))
    assert (uow.commits, publisher.events) == (0, [])


@pytest.mark.parametrize("terms", [None, "0"])
async def test_register_without_accepting_the_terms_in_force_creates_nothing(terms: str | None) -> None:
    # Arrange
    uow = FakeIdentityUnitOfWork()

    # Act & Assert
    with pytest.raises(TermsNotAcceptedError):
        await _register(uow).execute(_dto(terms=terms))
    assert uow.users.by_id == {}


async def test_register_with_an_email_in_use_fails() -> None:
    # Arrange
    uow = FakeIdentityUnitOfWork(InMemoryUserRepository(make_user(email="existing@plante.org")))

    # Act & Assert
    with pytest.raises(EmailAlreadyInUseError):
        await _register(uow).execute(_dto(email="Existing@Plante.org"))


async def test_register_normalizes_the_email() -> None:
    # Act
    user = await _register(FakeIdentityUnitOfWork()).execute(_dto(email="  New.User@Plante.ORG "))

    # Assert
    assert user.email == "new.user@plante.org"


async def test_register_rejects_a_weak_password() -> None:
    # Arrange: antes só a troca de senha validava a força
    uow = FakeIdentityUnitOfWork()

    # Act & Assert
    with pytest.raises(WeakPasswordError):
        await _register(uow).execute(_dto(password="123"))
    assert uow.users.by_id == {}


async def test_login_issues_access_and_refresh_tokens() -> None:
    # Arrange
    user = make_user()
    use_case, tokens = _login(user)

    # Act
    result = await use_case.execute(email="User@Plante.org", password="Secret1password")

    # Assert
    assert TOKENS.verify(result.access_token, TokenKind.ACCESS) == user.id
    assert TOKENS.verify(result.refresh_token, TokenKind.REFRESH) == user.id
    assert (result.token_type, tokens.tokens[user.id]) == ("bearer", result.refresh_token)


@pytest.mark.parametrize("email, password", [("user@plante.org", "wrong"), ("nobody@plante.org", "Secret1password")])
async def test_login_with_wrong_credentials_is_refused(email: str, password: str) -> None:
    # Arrange
    use_case, _ = _login(make_user())

    # Act & Assert
    with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
        await use_case.execute(email=email, password=password)


async def test_login_before_verifying_the_email_is_refused() -> None:
    # Arrange
    use_case, _ = _login(make_user(is_verified=False))

    # Act & Assert
    with pytest.raises(EmailNotVerifiedError):
        await use_case.execute(email="user@plante.org", password="Secret1password")


async def test_login_without_verification_lets_an_unverified_account_in() -> None:
    # Arrange: an account created while verification was on, never verified
    use_case, _ = _login(make_user(is_verified=False), verification_required=False)

    # Act
    result = await use_case.execute(email="user@plante.org", password="Secret1password")

    # Assert
    assert result.access_token
