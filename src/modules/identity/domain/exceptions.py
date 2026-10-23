from src.shared.domain import PlantEError


class InvalidCredentialsError(PlantEError):
    """Wrong email or password (the session, if any, is still valid)."""
    code = "PLANTE_4102_WRONG_CREDENTIALS"
    status_code = 400

    def __init__(self, message: str = "Wrong email or password."):
        super().__init__(message=message)


class EmailNotVerifiedError(PlantEError):
    """The password is right, but the account email was not verified yet."""
    code = "PLANTE_4120_EMAIL_NOT_VERIFIED"
    status_code = 403

    def __init__(self, message: str = "Email not verified. Check your inbox for the verification code."):
        super().__init__(message=message)


class EmailAlreadyInUseError(PlantEError):
    """The email is already used by another account."""
    code = "PLANTE_4140_EMAIL_ALREADY_IN_USE"
    status_code = 409

    def __init__(self, message: str = "Email already in use."):
        super().__init__(message=message)


class WeakPasswordError(PlantEError):
    """The password does not meet the password policy."""
    code = "PLANTE_4100_WEAK_PASSWORD"
    status_code = 400

    def __init__(self, message: str = "Weak password."):
        super().__init__(message=message)


class InvalidVerificationCodeError(PlantEError):
    """The verification code is malformed, expired or not the one sent."""
    code = "PLANTE_4101_INVALID_VERIFICATION_CODE"
    status_code = 400

    def __init__(self, message: str = "Invalid verification code."):
        super().__init__(message=message)


class CaptchaFailedError(PlantEError):
    """The captcha token is missing, invalid, expired or already used: solve the captcha again."""
    code = "PLANTE_4103_CAPTCHA_FAILED"
    status_code = 400

    def __init__(self) -> None:
        super().__init__(message="Captcha verification failed. Solve the captcha again.")


class TermsNotAcceptedError(PlantEError):
    """The user has not accepted the terms in force: accept them (sign-up, or `POST /profile/terms`)."""
    code = "PLANTE_4121_TERMS_NOT_ACCEPTED"
    status_code = 403

    def __init__(self, current_version: str) -> None:
        super().__init__(
            message=f"Accept the terms in force (version {current_version}) to continue.",
            details={"current_version": current_version},
        )
