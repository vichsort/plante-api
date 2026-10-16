from src.shared.domain import PlantEError


class InvalidCredentialsError(PlantEError):
    """Dados de autenticação incorretos."""
    code = "PLANTE_4007_WRONG_CREDENTIALS"
    status_code = 400

    def __init__(self, message: str = "Wrong credentials inserted."):
        super().__init__(message=message)


class EmailAlreadyInUseError(PlantEError):
    """O email já está em uso por outro usuário."""
    code = "PLANTE_4004_EMAIL_ALREADY_IN_USE"
    status_code = 409

    def __init__(self, message: str = "Email already in use."):
        super().__init__(message=message)


class WeakPasswordError(PlantEError):
    """Senha fraca ou inválida."""
    code = "PLANTE_4008_WEAK_PASSWORD"
    status_code = 400

    def __init__(self, message: str = "Weak password."):
        super().__init__(message=message)


class InvalidVerificationCodeError(PlantEError):
    """Código OTP inválido ou expirado."""
    code = "PLANTE_4003_INVALID_VERIFICATION_CODE"
    status_code = 400

    def __init__(self, message: str = "Invalid verification code."):
        super().__init__(message=message)
