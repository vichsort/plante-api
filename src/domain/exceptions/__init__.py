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
    PlantIdentificationError,
    SampleNotFoundError,
    SpeciesNotFoundError,
)
from src.domain.exceptions.external import ExternalServiceError, GeocodingError
from src.domain.exceptions.garden import (
    PlantLimitExceededError,
    PlantNotFoundError,
    PlantNotReadyForWateringError,
)
from src.domain.exceptions.health import (
    HealthRecordNotFoundError,
    RawResponseExpiredError,
)
from src.domain.exceptions.subscription import SubscriptionRequiredError

__all__ = [
    "DomainException",
    "EmailAlreadyInUseError",
    "ExternalServiceError",
    "ForbiddenError",
    "GeocodingError",
    "HealthRecordNotFoundError",
    "IdentificationNotFoundError",
    "InvalidCredentialsError",
    "InvalidImageError",
    "InvalidVerificationCodeError",
    "LowConfidenceError",
    "PlantEError",
    "PlantIdentificationError",
    "PlantLimitExceededError",
    "PlantNotFoundError",
    "PlantNotReadyForWateringError",
    "RawResponseExpiredError",
    "SampleNotFoundError",
    "SpeciesNotFoundError",
    "SubscriptionRequiredError",
    "UnauthorizedError",
    "UserNotFoundError",
    "WeakPasswordError",
]
