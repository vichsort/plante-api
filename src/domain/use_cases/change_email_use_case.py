from dataclasses import dataclass
import secrets

from src.domain.exceptions import (
    UserNotFoundError,
    InvalidCredentialsError,
    EmailAlreadyInUseError,
)
from src.domain.ports.email_sender import IEmailSender
from src.domain.ports.otp_repository import IOtpRepository
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.verification_code import VerificationCode

@dataclass(frozen=True)
class ChangeEmailInputDTO:
    user_id: int
    current_password: str
    new_email: str

class ChangeEmailUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        otp_repo: IOtpRepository,
        hasher: IPasswordHasher,
        email_sender: IEmailSender,
    ) -> None:
        self.user_repo = user_repo
        self.otp_repo = otp_repo
        self.hasher = hasher
        self.email_sender = email_sender

    async def execute(self, dto: ChangeEmailInputDTO) -> None:
        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(dto.user_id)

        if not self.hasher.verify(dto.current_password, user.hashed_password):
            raise InvalidCredentialsError()

        existing = await self.user_repo.get_by_email(dto.new_email)
        if existing is not None:
            raise EmailAlreadyInUseError(dto.new_email)

        # Gera o código OTP usando o VO para garantir formato e checksum
        raw_code = VerificationCode.generate().raw_code

        user.change_email(new_email=dto.new_email)
        await self.user_repo.save(user)

        await self.otp_repo.save_code(user_id=user.id, code=raw_code)
        await self.email_sender.send_verification_code(to_email=dto.new_email, code=raw_code)


def _generate_otp_code() -> str:
    """
    Gera código no formato PLA-XXX-C-XXX onde C é o dígito verificador.
    Usa secrets para segurança criptográfica.
    """
    digits = [secrets.randbelow(10) for _ in range(6)]
    checksum = sum(digits) % 10
    return f"PLA{''.join(map(str, digits[:3]))}{checksum}{''.join(map(str, digits[3:]))}"