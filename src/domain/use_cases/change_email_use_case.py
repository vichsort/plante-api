from dataclasses import dataclass

from src.domain.exceptions import EmailAlreadyInUseError, InvalidCredentialsError
from src.domain.ports.email_sender import IEmailSender
from src.domain.ports.otp_repository import IOtpRepository
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.email import normalize_email
from src.domain.value_objects.verification_code import VerificationCode
from src.shared.domain import UserId, UserNotFoundError


@dataclass(frozen=True)
class ChangeEmailInputDTO:
    user_id: UserId
    current_password: str
    new_email: str

class ChangeEmailUseCase:
    raises = (EmailAlreadyInUseError, InvalidCredentialsError, UserNotFoundError)

    def __init__(
        self,
        uow: IUnitOfWork,
        otp_repo: IOtpRepository,
        hasher: IPasswordHasher,
        email_sender: IEmailSender,
    ) -> None:
        self.uow = uow
        self.otp_repo = otp_repo
        self.hasher = hasher
        self.email_sender = email_sender

    async def execute(self, dto: ChangeEmailInputDTO) -> None:
        new_email = normalize_email(dto.new_email)

        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)

            if not self.hasher.verify(dto.current_password, user.hashed_password):
                raise InvalidCredentialsError()

            existing = await uow.users.get_by_email(new_email)
            if existing is not None:
                raise EmailAlreadyInUseError()

            user.request_email_change(new_email=new_email)
            await uow.users.save(user)
            await uow.commit()

        raw_code = VerificationCode.generate().raw_code
        await self.otp_repo.save_code(user_id=user.id, code=raw_code)
        await self.email_sender.send_verification_code(to_email=new_email, code=raw_code)
