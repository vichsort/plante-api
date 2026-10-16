import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.security.jwt_token_service import JwtTokenService
from src.domain.entities.user import User
from src.domain.exceptions import EmailAlreadyInUseError, WeakPasswordError
from src.domain.ports.token_service import TokenKind
from src.domain.use_cases.login_use_case import REFRESH_TOKEN_TTL, LoginUseCase
from src.domain.use_cases.refresh_token_use_case import RefreshTokenUseCase
from src.domain.use_cases.register_user_use_case import (
    RegisterUserInputDTO,
    RegisterUserUseCase,
)
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation
from src.shared.domain import UnauthorizedError, UserId
from tests.fakes import FakeUnitOfWork, InMemoryTokenRepository


@pytest.mark.asyncio
async def test_register_user_success():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None

    user_id = UserId(uuid.uuid4())
    fake_user = User(
        id=user_id,
        email="new@plante.org",
        hashed_password="hashed_secret",
        location=UserLocation(country="BR", state="SP"),
        is_verified=False,
        subscription=SubscriptionTier.FREE,
        created_at=datetime.now(UTC),
    )
    user_repo.save.return_value = fake_user

    hasher = MagicMock()
    hasher.hash.return_value = "hashed_secret"

    publisher = AsyncMock()

    use_case = RegisterUserUseCase(uow=FakeUnitOfWork(users=user_repo), hasher=hasher, publisher=publisher)

    result = await use_case.execute(RegisterUserInputDTO(
        email="new@plante.org",
        password="Secret1password",
        country="BR",
        state="SP",
    ))

    assert result.id == user_id
    user_repo.get_by_email.assert_called_once_with("new@plante.org")
    hasher.hash.assert_called_once_with("Secret1password")
    user_repo.save.assert_called_once()
    publisher.publish.assert_called_once()

@pytest.mark.asyncio
async def test_register_user_email_already_in_use():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = MagicMock()

    hasher = MagicMock()
    publisher = AsyncMock()

    use_case = RegisterUserUseCase(uow=FakeUnitOfWork(users=user_repo), hasher=hasher, publisher=publisher)

    with pytest.raises(EmailAlreadyInUseError):
        await use_case.execute(RegisterUserInputDTO(
            email="existing@plante.org",
            password="Secret1password",
            country="BR",
            state="SP",
        ))

@pytest.mark.asyncio
async def test_login_user_success():
    fake_user = User(
        id=UserId(uuid.uuid4()),
        email="user@plante.org",
        hashed_password="hashed_secret",
        location=UserLocation(country="BR", state="SP"),
        is_verified=True,
        subscription=SubscriptionTier.FREE,
        created_at=datetime.now(UTC),
    )

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = fake_user

    hasher = MagicMock()
    hasher.verify.return_value = True

    token_repo = AsyncMock()

    use_case = LoginUseCase(
        uow=FakeUnitOfWork(users=user_repo),
        hasher=hasher,
        token_repo=token_repo,
        token_service=JwtTokenService(secret_key="testsecretkey-with-at-least-32-bytes", algorithm="HS256"),
    )

    result = await use_case.execute(email="user@plante.org", password="Secret1password")

    tokens = JwtTokenService(secret_key="testsecretkey-with-at-least-32-bytes", algorithm="HS256")
    assert tokens.verify(result.access_token, TokenKind.ACCESS) == fake_user.id
    assert tokens.verify(result.refresh_token, TokenKind.REFRESH) == fake_user.id
    assert result.token_type == "bearer"
    token_repo.save_refresh_token.assert_called_once()

@pytest.mark.asyncio
async def test_login_invalid_password_raises():
    fake_user = User(
        id=UserId(uuid.uuid4()),
        email="user@plante.org",
        hashed_password="hashed_secret",
        location=UserLocation(country="BR", state="SP"),
        is_verified=True,
        subscription=SubscriptionTier.FREE,
        created_at=datetime.now(UTC),
    )

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = fake_user

    hasher = MagicMock()
    hasher.verify.return_value = False

    token_repo = AsyncMock()

    use_case = LoginUseCase(
        uow=FakeUnitOfWork(users=user_repo),
        hasher=hasher,
        token_repo=token_repo,
        token_service=JwtTokenService(secret_key="testsecretkey-with-at-least-32-bytes", algorithm="HS256"),
    )

    with pytest.raises(UnauthorizedError, match="Invalid email or password"):
        await use_case.execute(email="user@plante.org", password="wrongpassword")


async def test_register_normalizes_email_before_lookup_and_save():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    user_repo.save.side_effect = lambda user: user
    hasher = MagicMock()
    hasher.hash.return_value = "hashed_secret"

    use_case = RegisterUserUseCase(uow=FakeUnitOfWork(users=user_repo), hasher=hasher, publisher=AsyncMock())
    result = await use_case.execute(RegisterUserInputDTO(
        email="  New.User@Plante.ORG ",
        password="Secret1password",
        country="BR",
        state="SP",
    ))

    user_repo.get_by_email.assert_called_once_with("new.user@plante.org")
    assert result.email == "new.user@plante.org"


async def test_login_looks_up_normalized_email():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    use_case = LoginUseCase(uow=FakeUnitOfWork(users=user_repo), hasher=MagicMock(), token_repo=AsyncMock(), token_service=MagicMock())

    with pytest.raises(UnauthorizedError):
        await use_case.execute(email="Dev@Plante.org", password="x")

    user_repo.get_by_email.assert_called_once_with("dev@plante.org")


@pytest.mark.asyncio
async def test_register_rejects_a_weak_password():
    # Arrange: antes só a troca de senha validava a força
    user_repo = AsyncMock()
    use_case = RegisterUserUseCase(uow=FakeUnitOfWork(users=user_repo), hasher=MagicMock(), publisher=AsyncMock())

    # Act & Assert
    with pytest.raises(WeakPasswordError):
        await use_case.execute(RegisterUserInputDTO(email="fraca@plante.org", password="123", country="BR", state="SP"))
    user_repo.save.assert_not_called()


def _refresh_setup() -> tuple[RefreshTokenUseCase, InMemoryTokenRepository, UserId, str]:
    tokens = JwtTokenService(secret_key="test-secret-key-with-32-bytes-min!", algorithm="HS256")
    repo = InMemoryTokenRepository()
    user_id = UserId(uuid.uuid4())
    first = tokens.issue(user_id, TokenKind.REFRESH, REFRESH_TOKEN_TTL)
    repo.tokens[user_id] = first
    return RefreshTokenUseCase(token_repo=repo, token_service=tokens), repo, user_id, first


@pytest.mark.asyncio
async def test_refresh_rotates_the_refresh_token():
    # Arrange
    use_case, repo, user_id, first = _refresh_setup()

    # Act
    result = await use_case.execute(first)

    # Assert: tokens emitidos no mesmo segundo também são diferentes (jti)
    assert result.refresh_token != first
    assert repo.tokens[user_id] == result.refresh_token


@pytest.mark.asyncio
async def test_reusing_a_rotated_refresh_token_revokes_the_session():
    # Arrange
    use_case, repo, user_id, first = _refresh_setup()
    second = (await use_case.execute(first)).refresh_token

    # Act
    with pytest.raises(UnauthorizedError):
        await use_case.execute(first)

    # Assert: o token novo também deixou de valer (quem tinha o antigo pode ser um ladrão)
    assert user_id not in repo.tokens
    with pytest.raises(UnauthorizedError):
        await use_case.execute(second)
