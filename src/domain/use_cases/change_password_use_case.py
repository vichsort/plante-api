from dataclasses import dataclass

from src.domain.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    WeakPasswordError,
)
from src.domain.ports.email_sender import IEmailSender
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import UserId

_MIN_PASSWORD_LENGTH = 8

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

            _validate_password_strength(dto.new_password)

            if self.hasher.verify(dto.new_password, user.hashed_password):
                raise WeakPasswordError("A nova senha não pode ser igual à atual.")

            new_hash = self.hasher.hash(dto.new_password)
            user.change_password(new_hashed_password=new_hash)

            await uow.users.save(user)
            await uow.commit()

        await self.email_sender.send_password_changed_notice(to_email=user.email)


def _validate_password_strength(password: str) -> None:
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(f"A senha deve ter no mínimo {_MIN_PASSWORD_LENGTH} caracteres.")
    if not any(c.isupper() for c in password):
        raise WeakPasswordError("A senha deve conter ao menos uma letra maiúscula.")
    if not any(c.isdigit() for c in password):
        raise WeakPasswordError("A senha deve conter ao menos um número.")