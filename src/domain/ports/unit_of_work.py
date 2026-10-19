from src.domain.ports.achievement_repository import IAchievementRepository
from src.domain.ports.health_record_repository import IHealthRecordRepository
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.shared.domain import IUnitOfWork as SharedUnitOfWork


class IUnitOfWork(SharedUnitOfWork):
    """
    UoW do código em camadas antigo (regras em `src.shared.domain.IUnitOfWork`). Perde um
    repositório a cada módulo migrado; cada módulo tem a própria porta de UoW.
    """

    user_plants: IUserPlantRepository
    health_records: IHealthRecordRepository
    achievements: IAchievementRepository
