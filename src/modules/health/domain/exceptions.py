from uuid import UUID

from src.shared.domain import PlantEError


class HealthRecordNotFoundError(PlantEError):
    """O health record solicitado não existe ou não pertence ao usuário."""
    code = "PLANTE_4630_HEALTH_RECORD_NOT_FOUND"
    status_code = 404

    def __init__(self, record_id: UUID):
        super().__init__(
            message=f"Health record {record_id} not found.",
        )
