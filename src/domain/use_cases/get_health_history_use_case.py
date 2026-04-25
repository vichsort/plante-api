from dataclasses import dataclass
from src.domain.exceptions import PlantNotFoundError
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.health_record_repository import IHealthRecordRepository

@dataclass(frozen=True)
class GetHealthHistoryInputDTO:
    user_id: int
    user_plant_id: int
    limit: int = 20

class GetHealthHistoryUseCase:
    def __init__(
        self,
        user_plant_repo: IUserPlantRepository,
        health_repo: IHealthRecordRepository,
    ) -> None:
        self._user_plant_repo = user_plant_repo
        self._health_repo = health_repo

    async def execute(self, dto: GetHealthHistoryInputDTO) -> list[dict]:
        user_plant = await self._user_plant_repo.get_by_id(dto.user_plant_id, dto.user_id)
        if not user_plant:
            raise PlantNotFoundError(dto.user_plant_id)

        records = await self._health_repo.list_by_plant(
            user_plant_id=dto.user_plant_id,
            limit=dto.limit,
        )

        return [
            {
                "health_record_id": r.id,
                "diagnosed_at": r.diagnosed_at.isoformat(),
                "severity": r.severity.value,
                "vitality_score": r.vitality_score,
                "is_healthy": r.is_healthy,
                "issues_detected": list(r.issues_detected),
                "treatment_plan": list(r.treatment_plan),
                "recovery_estimate_days": r.recovery_estimate_days,
                "image_key": r.image_key,
            }
            for r in records
        ]