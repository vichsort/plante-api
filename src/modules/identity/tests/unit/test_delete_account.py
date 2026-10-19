"""Account deletion: for good, confirmed with the password, photos included."""
from dataclasses import dataclass, field

import pytest
from structlog.testing import capture_logs

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.exceptions import InvalidCredentialsError
from src.modules.identity.domain.use_cases.delete_account import (
    DeleteAccountInputDTO,
    DeleteAccountUseCase,
)
from src.modules.identity.tests.fakes import (
    FakeIdentityUnitOfWork,
    InMemoryTokenRepository,
    InMemoryUserRepository,
    PlainHasher,
    make_user,
)
from src.shared.domain import ExternalServiceError, UserId
from src.shared.tests.fakes import RecordingImageStorage

PASSWORD = "Secret1password"


class _BrokenStorage(RecordingImageStorage):
    async def delete_user_images(self, user_id: UserId) -> int:
        raise ExternalServiceError(service="S3", retryable=True)


@dataclass
class _Delete:
    user: User = field(default_factory=make_user)
    storage: RecordingImageStorage = field(default_factory=RecordingImageStorage)
    tokens: InMemoryTokenRepository = field(default_factory=InMemoryTokenRepository)
    uow: FakeIdentityUnitOfWork = field(init=False)

    def __post_init__(self) -> None:
        self.uow = FakeIdentityUnitOfWork(InMemoryUserRepository(self.user))
        self.tokens.tokens[self.user.id] = "refresh"

    async def run(self, password: str = PASSWORD) -> None:
        use_case = DeleteAccountUseCase(self.uow, PlainHasher(), self.tokens, self.storage)
        await use_case.execute(DeleteAccountInputDTO(user_id=self.user.id, password=password))


async def test_deleting_takes_the_account_its_session_and_its_photos() -> None:
    # Arrange
    delete = _Delete()

    # Act
    await delete.run()

    # Assert
    assert await delete.uow.users.get_by_id(delete.user.id) is None
    assert await delete.uow.users.get_by_email(delete.user.email) is None  # free for a new account
    assert delete.uow.commits == 1
    assert delete.user.id not in delete.tokens.tokens
    assert delete.storage.deleted_users == [delete.user.id]


async def test_a_wrong_password_deletes_nothing() -> None:
    # Arrange
    delete = _Delete()

    # Act & Assert
    with pytest.raises(InvalidCredentialsError):
        await delete.run(password="Wr0ng!Password")
    assert await delete.uow.users.get_by_id(delete.user.id) is not None
    assert delete.tokens.tokens[delete.user.id] == "refresh"
    assert delete.storage.deleted_users == []


async def test_the_account_goes_even_if_the_photos_cannot() -> None:
    # Arrange
    delete = _Delete(storage=_BrokenStorage())

    # Act
    with capture_logs() as logs:
        await delete.run()

    # Assert: logged for a manual cleanup of the user's prefix
    assert await delete.uow.users.get_by_id(delete.user.id) is None
    assert any(entry["event"] == "account.photos_not_deleted" for entry in logs)
