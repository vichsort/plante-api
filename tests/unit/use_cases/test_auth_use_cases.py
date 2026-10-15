import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.security.jwt_token_service import JwtTokenService
from src.domain.entities.user import User
from src.domain.exceptions import EmailAlreadyInUseError, UnauthorizedError
from src.domain.ports.token_service import TokenKind
from src.domain.use_cases.login_use_case import LoginUseCase
from src.domain.use_cases.register_user_use_case import (
    RegisterUserInputDTO,
    RegisterUserUseCase,
)
from src.domain.value_objects.ids import UserId
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation
from tests.fakes import FakeUnitOfWork


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
        password="secretpassword",
        country="BR",
        state="SP",
    ))

    assert result.id == user_id
    user_repo.get_by_email.assert_called_once_with("new@plante.org")
    hasher.hash.assert_called_once_with("secretpassword")
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
            password="secretpassword",
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

    result = await use_case.execute(email="user@plante.org", password="secretpassword")

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
        password="secretpassword",
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
