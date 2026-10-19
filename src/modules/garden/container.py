from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.catalog import ISpeciesRegistry
from src.modules.garden.adapters.persistence.unit_of_work import (
    SqlAlchemyGardenUnitOfWork,
)
from src.modules.garden.domain.services.plant_lookup import PlantLookup
from src.modules.garden.domain.use_cases.add_plant import AddPlantToGardenUseCase
from src.modules.garden.domain.use_cases.break_missed_streaks import (
    BreakStreakCronUseCase,
)
from src.modules.garden.domain.use_cases.delete_plant import DeleteUserPlantUseCase
from src.modules.garden.domain.use_cases.get_garden import GetUserGardenUseCase
from src.modules.garden.domain.use_cases.get_plant_details import (
    GetPlantDetailsUseCase,
)
from src.modules.garden.domain.use_cases.water_plant import WaterPlantUseCase
from src.modules.identification import IIdentificationLookup
from src.modules.identity import IUserDirectory
from src.modules.subscription import IGardenQuota
from src.modules.training import ITrainingRecorder
from src.shared.domain import IDomainPublisher, LocalCalendar


class GardenContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    publisher: providers.Dependency[IDomainPublisher] = providers.Dependency()
    calendar: providers.Dependency[LocalCalendar] = providers.Dependency()
    users: providers.Dependency[IUserDirectory] = providers.Dependency()
    quota: providers.Dependency[IGardenQuota] = providers.Dependency()
    training: providers.Dependency[ITrainingRecorder] = providers.Dependency()
    identifications: providers.Dependency[IIdentificationLookup] = providers.Dependency()
    catalog: providers.Dependency[ISpeciesRegistry] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyGardenUnitOfWork, session_factory=session_factory)
    lookup = providers.Factory(PlantLookup, uow=unit_of_work)

    add_plant_use_case = providers.Factory(
        AddPlantToGardenUseCase,
        uow=unit_of_work,
        publisher=publisher,
        calendar=calendar,
        users=users,
        quota=quota,
        training=training,
        identifications=identifications,
    )
    get_garden_use_case = providers.Factory(GetUserGardenUseCase, uow=unit_of_work, calendar=calendar)
    get_plant_details_use_case = providers.Factory(
        GetPlantDetailsUseCase,
        uow=unit_of_work,
        calendar=calendar,
        catalog=catalog,
    )
    delete_plant_use_case = providers.Factory(DeleteUserPlantUseCase, uow=unit_of_work)
    water_plant_use_case = providers.Factory(
        WaterPlantUseCase,
        uow=unit_of_work,
        publisher=publisher,
        calendar=calendar,
    )
    break_missed_streaks_use_case = providers.Factory(
        BreakStreakCronUseCase,
        uow=unit_of_work,
        publisher=publisher,
        calendar=calendar,
    )
