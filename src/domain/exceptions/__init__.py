from src.domain.exceptions.auth import (
    EmailAlreadyInUseError,
    ForbiddenError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
    WeakPasswordError,
)
from src.domain.exceptions.botany import (
    IdentificationNotFoundError,
    LowConfidenceError,
    NotAPlantError,
    PlantIdentificationError,
)
from src.domain.exceptions.garden import (
    PlantNotFoundError,
    PlantNotReadyForWateringError,
)
from src.domain.exceptions.health import (
    HealthRecordNotFoundError,
)

__all__ = [
    "EmailAlreadyInUseError",
    "ForbiddenError",
    "HealthRecordNotFoundError",
    "IdentificationNotFoundError",
    "InvalidCredentialsError",
    "InvalidVerificationCodeError",
    "LowConfidenceError",
    "NotAPlantError",
    "PlantIdentificationError",
    "PlantNotFoundError",
    "PlantNotReadyForWateringError",
    "WeakPasswordError",
]
