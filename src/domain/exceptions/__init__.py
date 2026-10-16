from src.domain.exceptions.auth import (
    EmailAlreadyInUseError,
    ForbiddenError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
    UnauthorizedError,
    UserNotFoundError,
    WeakPasswordError,
)
from src.domain.exceptions.base import DomainException, PlantEError
from src.domain.exceptions.botany import (
    IdentificationNotFoundError,
    InvalidImageError,
    LowConfidenceError,
    NotAPlantError,
    PlantIdentificationError,
    SpeciesNotFoundError,
)
from src.domain.exceptions.external import ExternalServiceError
from src.domain.exceptions.garden import (
    PlantLimitExceededError,
    PlantNotFoundError,
    PlantNotReadyForWateringError,
)
from src.domain.exceptions.health import (
    HealthRecordNotFoundError,
)
from src.domain.exceptions.rate_limit import RateLimitExceededError
from src.domain.exceptions.subscription import SubscriptionRequiredError

__all__ = [
    "DomainException",
    "EmailAlreadyInUseError",
    "ExternalServiceError",
    "ForbiddenError",
    "HealthRecordNotFoundError",
    "IdentificationNotFoundError",
    "InvalidCredentialsError",
    "InvalidImageError",
    "InvalidVerificationCodeError",
    "LowConfidenceError",
    "NotAPlantError",
    "PlantEError",
    "PlantIdentificationError",
    "PlantLimitExceededError",
    "PlantNotFoundError",
    "PlantNotReadyForWateringError",
    "RateLimitExceededError",
    "SpeciesNotFoundError",
    "SubscriptionRequiredError",
    "UnauthorizedError",
    "UserNotFoundError",
    "WeakPasswordError",
]
