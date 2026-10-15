from dataclasses import dataclass

from src.domain.exceptions import InvalidVerificationCodeError, UserNotFoundError
from src.domain.ports.otp_repository import IOtpRepository
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.ids import UserId
from src.domain.value_objects.verification_code import VerificationCode


@dataclass(frozen=True)
class VerifyEmailInputDTO:
    user_id: UserId
    raw_code: str

class VerifyEmailUseCase:
    raises = (InvalidVerificationCodeError, UserNotFoundError)

    def __init__(
        self,
        user_repo: IUserRepository,
        otp_repo: IOtpRepository,
    ) -> None:
        self.user_repo = user_repo
        self.otp_repo = otp_repo

    async def execute(self, dto: VerifyEmailInputDTO) -> None:
        user = await self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(user_id=dto.user_id)

        if user.is_verified:
            return

        try:
            submitted_code = VerificationCode(dto.raw_code)
        except ValueError as e:
            raise InvalidVerificationCodeError() from e

        expected_code_str = await self.otp_repo.get_active_code_for_user(user.id)
        if not expected_code_str or submitted_code.raw_code != expected_code_str:
            raise InvalidVerificationCodeError()

        user.verify_email()

        await self.user_repo.save(user)
        await self.otp_repo.consume_code(user.id)