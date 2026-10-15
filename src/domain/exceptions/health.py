from uuid import UUID

from src.domain.exceptions.base import PlantEError


class HealthRecordNotFoundError(PlantEError):
    """O health record solicitado não existe ou não pertence ao usuário."""
    code = "PLANTE_4017_HEALTH_RECORD_NOT_FOUND"
    status_code = 404

    def __init__(self, record_id: UUID):
        super().__init__(
            message=f"Health record {record_id} not found.",
        )


class RawResponseExpiredError(PlantEError):
    """Raw response do Kindwise expirou no Redis (TTL 24h)."""
    code = "PLANTE_4018_RAW_RESPONSE_EXPIRED"
    status_code = 410

    def __init__(self, record_id: UUID):
        super().__init__(
            message=f"Raw response for health record {record_id} has expired. Please run a new diagnosis.",
        )
