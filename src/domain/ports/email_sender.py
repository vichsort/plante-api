from abc import ABC, abstractmethod

class IEmailSender(ABC):

    @abstractmethod
    async def send_verification_code(self, to_email: str, code: str) -> None:
        """Envia o código OTP de verificação para o email informado."""
        ...

    @abstractmethod
    async def send_password_changed_notice(self, to_email: str) -> None:
        """Notifica o usuário que sua senha foi alterada."""
        ...