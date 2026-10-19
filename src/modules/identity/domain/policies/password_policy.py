from src.modules.identity.domain.exceptions import WeakPasswordError

MIN_PASSWORD_LENGTH = 8


class PasswordPolicy:
    """Minimum password strength, on sign-up and on password change."""

    @staticmethod
    def enforce_strong(password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(f"The password must have at least {MIN_PASSWORD_LENGTH} characters.")
        if not any(c.isupper() for c in password):
            raise WeakPasswordError("The password must have at least one uppercase letter.")
        if not any(c.isdigit() for c in password):
            raise WeakPasswordError("The password must have at least one digit.")
