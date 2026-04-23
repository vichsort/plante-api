from abc import ABC, abstractmethod

class IPasswordHasher(ABC):
    """
    Porta de hashing da senha do usuário.
    Organiza e orquestra o processo de hashing, sem se importar com a implementação concreta.
    """

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Gera um hash seguro a partir da senha em texto puro."""
        ...