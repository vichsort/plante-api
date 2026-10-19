from dataclasses import dataclass

from src.domain.exceptions import EmailAlreadyInUseError, InvalidVerificationCodeError
from src.domain.ports.otp_repository import IOtpRepository
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.verification_code import VerificationCode
from src.shared.domain import UserId, UserNotFoundError


@dataclass(frozen=True)
class VerifyEmailInputDTO:
    user_id: UserId
    raw_code: str

class VerifyEmailUseCase:
    """
    Confirma o código enviado por e-mail. Serve ao cadastro (verifica a conta) e à troca de e-mail
    (o endereço pendente vira o e-mail da conta).
    """

    raises = (EmailAlreadyInUseError, InvalidVerificationCodeError, UserNotFoundError)

    def __init__(
        self,
        uow: IUnitOfWork,
        otp_repo: IOtpRepository,
    ) -> None:
        self.uow = uow
        self.otp_repo = otp_repo

    async def execute(self, dto: VerifyEmailInputDTO) -> None:
        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if not user:
                raise UserNotFoundError(user_id=dto.user_id)

            if user.is_verified and user.pending_email is None:
                return

            try:
                submitted_code = VerificationCode(dto.raw_code)
            except ValueError as e:
                raise InvalidVerificationCodeError() from e

            expected_code_str = await self.otp_repo.get_active_code_for_user(user.id)
            if not expected_code_str or submitted_code.raw_code != expected_code_str:
                raise InvalidVerificationCodeError()

            if user.pending_email is not None:
                # Outra conta pode ter ficado com o endereço desde o pedido de troca
                if await uow.users.get_by_email(user.pending_email):
                    raise EmailAlreadyInUseError()
                user.confirm_email_change()
            else:
                user.verify_email()
            await uow.users.save(user)
            await uow.commit()

        # O código só é consumido depois que a verificação foi gravada
        await self.otp_repo.consume_code(user.id)
