from src.modules.garden.domain.ports.user_plant_repository import IUserPlantRepository
from src.shared.domain import IUnitOfWork


class IGardenUnitOfWork(IUnitOfWork):
    """As plantas do jardim dentro da transação (regras em `src.shared.domain.IUnitOfWork`)."""

    user_plants: IUserPlantRepository
