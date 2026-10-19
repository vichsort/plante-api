"""
`SqlAlchemyUnitOfWork` contra o Postgres: só o que é confirmado fica gravado. Antes dele nada era
persistido (nenhum `commit` em `src`) e os testes não viam porque confirmavam à mão.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.achievements.adapters.persistence.unit_of_work import (
    SqlAlchemyAchievementsUnitOfWork,
)
from src.modules.catalog.adapters.persistence.unit_of_work import (
    SqlAlchemyCatalogUnitOfWork,
)
from src.modules.catalog.domain.services.species_registry import SpeciesRegistry
from src.modules.garden.adapters.persistence.unit_of_work import (
    SqlAlchemyGardenUnitOfWork,
)
from src.modules.identification.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentificationUnitOfWork,
)
from src.modules.identity.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)
from src.modules.training.adapters.persistence.unit_of_work import (
    SqlAlchemyTrainingUnitOfWork,
)
from src.modules.training.domain.services.recorder import TrainingRecorder
from tests.factories import (
    make_identification,
    make_species,
    make_training_identification_sample,
    make_user,
    make_user_plant,
)


async def _user_exists(session_factory: async_sessionmaker[AsyncSession], email: str) -> bool:
    async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
        return await uow.users.get_by_email(email) is not None


async def test_commit_persists_changes(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
        await uow.users.save(make_user(email="commit@plante.org"))
        await uow.commit()

    assert await _user_exists(session_factory, "commit@plante.org")


async def test_leaving_without_commit_discards_changes(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
        await uow.users.save(make_user(email="no-commit@plante.org"))

    assert not await _user_exists(session_factory, "no-commit@plante.org")


async def test_exception_discards_changes(session_factory: async_sessionmaker[AsyncSession]) -> None:
    with pytest.raises(RuntimeError):
        async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
            await uow.users.save(make_user(email="boom@plante.org"))
            raise RuntimeError("falha no meio do use case")

    assert not await _user_exists(session_factory, "boom@plante.org")


async def test_repositories_share_one_transaction(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with SqlAlchemyAchievementsUnitOfWork(session_factory) as uow:
        # A cadeia de FKs (usuário → identificação → planta, espécie, amostra de treino) só é
        # satisfeita se todos os repositórios usam a mesma transação, inclusive os dos módulos
        # (identity, catalog, training, identification, garden), que se juntam à transação aberta aqui
        async with SqlAlchemyIdentityUnitOfWork(session_factory) as accounts:
            user = await accounts.users.save(make_user(email="shared@plante.org"))
        species = await SpeciesRegistry(SqlAlchemyCatalogUnitOfWork(session_factory)).save(make_species("Pilea peperomioides"))
        training = make_training_identification_sample("Pilea peperomioides")
        await TrainingRecorder(SqlAlchemyTrainingUnitOfWork(session_factory)).record_identification_sample(training)
        async with SqlAlchemyIdentificationUnitOfWork(session_factory) as identifications:
            identification = await identifications.identifications.save(make_identification(
                user_id=user.id, training_sample_id=training.id, species_id=species.id, scientific_name="Pilea peperomioides",
            ))
        async with SqlAlchemyGardenUnitOfWork(session_factory) as garden:
            plant = await garden.user_plants.save(make_user_plant(user_id=user.id, identification_id=identification.id))
        await uow.commit()

    async with SqlAlchemyGardenUnitOfWork(session_factory) as garden:
        assert await garden.user_plants.get_by_id(plant.id) is not None


async def test_can_be_reopened_and_rejects_nesting(session_factory: async_sessionmaker[AsyncSession]) -> None:
    uow = SqlAlchemyIdentityUnitOfWork(session_factory)
    async with uow:
        with pytest.raises(RuntimeError, match="already open"):
            async with uow:
                pass
    async with uow:
        await uow.users.save(make_user(email="reopen@plante.org"))
        await uow.commit()

    assert await _user_exists(session_factory, "reopen@plante.org")
