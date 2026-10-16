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
    PlantLimitExceededError,
    PlantNotFoundError,
    PlantNotReadyForWateringError,
)
from src.domain.exceptions.health import (
    HealthRecordNotFoundError,
)
from src.domain.exceptions.subscription import SubscriptionRequiredError

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
    "PlantLimitExceededError",
    "PlantNotFoundError",
    "PlantNotReadyForWateringError",
    "SubscriptionRequiredError",
    "WeakPasswordError",
]
