from dataclasses import dataclass

import structlog

from src.modules.identity.domain.exceptions import InvalidCredentialsError
from src.modules.identity.domain.ports.password_hasher import IPasswordHasher
from src.modules.identity.domain.ports.token_repository import ITokenRepository
from src.modules.identity.domain.ports.unit_of_work import IIdentityUnitOfWork
from src.shared.domain import (
    ExternalServiceError,
    IImageStorage,
    UserId,
    UserNotFoundError,
)

log = structlog.stdlib.get_logger()


@dataclass(frozen=True)
class DeleteAccountInputDTO:
    user_id: UserId
    password: str


class DeleteAccountUseCase:
    """
    Deletes the account for good, confirmed with the password (LGPD: no personal data is kept).

    - The user row goes, and the database takes garden, identifications, diagnoses, quota
      and achievements along (`CASCADE`). The training data has no link to the user and stays.
    - The email is free right away for a new account.
    - The refresh token is revoked; the access token dies on its own within minutes (and finds no
      user meanwhile).
    - The photos go after the commit. If the storage fails, the account is still gone and the
      failure is logged for a manual cleanup: the photos live under the user's own prefix.
    """

    raises = (InvalidCredentialsError, UserNotFoundError)

    def __init__(
        self,
        uow: IIdentityUnitOfWork,
        hasher: IPasswordHasher,
        token_repo: ITokenRepository,
        storage: IImageStorage,
    ) -> None:
        self.uow = uow
        self.hasher = hasher
        self.token_repo = token_repo
        self.storage = storage

    async def execute(self, dto: DeleteAccountInputDTO) -> None:
        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)
            if not self.hasher.verify(dto.password, user.hashed_password):
                raise InvalidCredentialsError("Wrong password.")
            await uow.users.delete(user.id)
            await uow.commit()

        await self.token_repo.delete_refresh_token(user.id)
        try:
            deleted = await self.storage.delete_user_images(user.id)
        except ExternalServiceError as exc:
            log.error("account.photos_not_deleted", user_id=str(user.id), error=exc.message)
        else:
            log.info("account.deleted", user_id=str(user.id), photos_deleted=deleted)
