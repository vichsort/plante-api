from src.domain.exceptions import WeakPasswordError

MIN_PASSWORD_LENGTH = 8


class PasswordPolicy:
    """Força mínima da senha: vale no cadastro e na troca de senha."""

    @staticmethod
    def enforce_strong(password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(f"A senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres.")
        if not any(c.isupper() for c in password):
            raise WeakPasswordError("A senha deve conter ao menos uma letra maiúscula.")
        if not any(c.isdigit() for c in password):
            raise WeakPasswordError("A senha deve conter ao menos um número.")
