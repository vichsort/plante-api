from uuid import uuid4

import pytest

from src.modules.identity.adapters.security.jwt_token_service import JwtTokenService
from src.modules.identity.domain.ports.token_service import TokenKind
from src.modules.identity.domain.use_cases.login import REFRESH_TOKEN_TTL
from src.modules.identity.domain.use_cases.refresh_token import RefreshTokenUseCase
from src.modules.identity.tests.fakes import InMemoryTokenRepository
from src.shared.domain import UnauthorizedError, UserId


def _setup() -> tuple[RefreshTokenUseCase, InMemoryTokenRepository, UserId, str]:
    tokens = JwtTokenService(secret_key="test-secret-key-with-32-bytes-min!", algorithm="HS256")
    repo = InMemoryTokenRepository()
    user_id = UserId(uuid4())
    first = tokens.issue(user_id, TokenKind.REFRESH, REFRESH_TOKEN_TTL)
    repo.tokens[user_id] = first
    return RefreshTokenUseCase(token_repo=repo, token_service=tokens), repo, user_id, first


async def test_refresh_rotates_the_refresh_token() -> None:
    # Arrange
    use_case, repo, user_id, first = _setup()

    # Act
    result = await use_case.execute(first)

    # Assert: tokens emitidos no mesmo segundo também são diferentes (jti)
    assert result.refresh_token != first
    assert repo.tokens[user_id] == result.refresh_token


async def test_reusing_a_rotated_refresh_token_revokes_the_session() -> None:
    # Arrange
    use_case, repo, user_id, first = _setup()
    second = (await use_case.execute(first)).refresh_token

    # Act
    with pytest.raises(UnauthorizedError):
        await use_case.execute(first)

    # Assert: o token novo também deixou de valer (quem tinha o antigo pode ser um ladrão)
    assert user_id not in repo.tokens
    with pytest.raises(UnauthorizedError):
        await use_case.execute(second)


async def test_logged_out_refresh_token_is_refused() -> None:
    # Arrange
    use_case, repo, user_id, first = _setup()
    del repo.tokens[user_id]

    # Act & Assert
    with pytest.raises(UnauthorizedError, match="revoked"):
        await use_case.execute(first)
