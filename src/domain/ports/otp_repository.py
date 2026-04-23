from abc import ABC, abstractmethod

class IOtpRepository(ABC):
    """
    Porta de saída para armazenamento de senhas de uso único (OTPs).
    Isola o Domínio da tecnologia de cache (ex: Redis ou Memcached).
    """

    @abstractmethod
    async def save_code(self, user_id: int, code: str, expires_in_minutes: int = 15) -> None:
        """Salva um novo código de verificação para o usuário com um tempo de expiração."""
        ...

    @abstractmethod
    async def get_active_code_for_user(self, user_id: int) -> str | None:
        """
        Busca o código ativo do usuário. 
        Retorna None se o código não existir ou já tiver expirado.
        """
        ...

    @abstractmethod
    async def consume_code(self, user_id: int) -> None:
        """
        Deleta/Invalida o código após o uso bem-sucedido, 
        garantindo que ele não possa ser usado duas vezes.
        """
        ...