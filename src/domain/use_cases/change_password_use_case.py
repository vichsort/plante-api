from dataclasses import dataclass

from src.domain.exceptions import InvalidCredentialsError, WeakPasswordError
from src.domain.policies.password_policy import PasswordPolicy
from src.domain.ports.email_sender import IEmailSender
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.shared.domain import UserId, UserNotFoundError


@dataclass(frozen=True)
class ChangePasswordInputDTO:
    user_id: UserId
    current_password: str
    new_password: str


class ChangePasswordUseCase:
    raises = (InvalidCredentialsError, UserNotFoundError, WeakPasswordError)

    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        email_sender: IEmailSender,
    ) -> None:
        self.uow = uow
        self.hasher = hasher
        self.email_sender = email_sender

    async def execute(self, dto: ChangePasswordInputDTO) -> None:
        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)

            if not self.hasher.verify(dto.current_password, user.hashed_password):
                raise InvalidCredentialsError()

            PasswordPolicy.enforce_strong(dto.new_password)

            if self.hasher.verify(dto.new_password, user.hashed_password):
                raise WeakPasswordError("A nova senha não pode ser igual à atual.")

            new_hash = self.hasher.hash(dto.new_password)
            user.change_password(new_hashed_password=new_hash)

            await uow.users.save(user)
            await uow.commit()

        await self.email_sender.send_password_changed_notice(to_email=user.email)

