from dataclasses import dataclass
from src.domain.exceptions import UserNotFoundError, InvalidVerificationCodeError
from src.domain.value_objects.verification_code import VerificationCode
from src.domain.ports.user_repository import IUserRepository
from src.domain.ports.otp_repository import IOtpRepository

@dataclass(frozen=True)
class VerifyEmailInputDTO:
    user_id: int
    raw_code: str

class VerifyEmailUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        otp_repo: IOtpRepository
    ):
        self.user_repo = user_repo
        self.otp_repo = otp_repo

    async def execute(self, dto: VerifyEmailInputDTO) -> dict:
        user = self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(dto.user_id)

        if user.is_verified:
            return {"message": "Sua conta já está verificada."}

        # Instancia o VO (Se o formato estiver quebrado ou o Checksum falhar, 
        # o VO lança ValueError e a requisição morre aqui).
        try:
            submitted_code = VerificationCode(dto.raw_code)
        except ValueError as e:
            raise InvalidVerificationCodeError() from e

        # Verifica contra o banco de dados / cache (O código enviado é o mesmo que geramos?)
        expected_code_str = self.otp_repo.get_active_code_for_user(user.id)
        if not expected_code_str or submitted_code.raw_code != expected_code_str:
            raise InvalidVerificationCodeError()

        # Muta o estado da Entidade (Libera a IA)
        user.verify_email()

        # Salva o usuário e descarta o código usado (para não ser reutilizado)
        self.user_repo.save(user)
        self.otp_repo.consume_code(user.id)

        return {"message": "E-mail verificado com sucesso! Bem-vindo ao PlantE."}