"""
`SqlAlchemyUnitOfWork` contra o Postgres: só o que é confirmado fica gravado. Antes dele nada era
persistido (nenhum `commit` em `src`) e os testes não viam porque confirmavam à mão.
"""
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.persistence.repositories.user_repository import UserRepository
from src.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.domain.events.domain_events import DomainEvent, UserRegisteredEvent
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.use_cases.register_user_use_case import (
    RegisterUserInputDTO,
    RegisterUserUseCase,
)
from tests.factories import make_user, make_user_plant


async def _user_exists(session_factory: async_sessionmaker[AsyncSession], email: str) -> bool:
    async with session_factory() as session:
        return await UserRepository(session).get_by_email(email) is not None


async def test_commit_persists_changes(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.users.save(make_user(email="commit@plante.org"))
        await uow.commit()

    assert await _user_exists(session_factory, "commit@plante.org")


async def test_leaving_without_commit_discards_changes(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.users.save(make_user(email="no-commit@plante.org"))

    assert not await _user_exists(session_factory, "no-commit@plante.org")


async def test_exception_discards_changes(session_factory: async_sessionmaker[AsyncSession]) -> None:
    with pytest.raises(RuntimeError):
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.users.save(make_user(email="boom@plante.org"))
            raise RuntimeError("falha no meio do use case")

    assert not await _user_exists(session_factory, "boom@plante.org")


async def test_repositories_share_one_transaction(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        user = await uow.users.save(make_user(email="shared@plante.org"))
        # A FK user_plants.user_id só é satisfeita se os dois repositórios usam a mesma transação
        plant = await uow.user_plants.save(make_user_plant(user_id=user.id))
        await uow.commit()

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert await uow.user_plants.get_by_id(plant.id) is not None


async def test_can_be_reopened_and_rejects_nesting(session_factory: async_sessionmaker[AsyncSession]) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory)
    async with uow:
        with pytest.raises(RuntimeError, match="already open"):
            async with uow:
                pass
    async with uow:
        await uow.users.save(make_user(email="reopen@plante.org"))
        await uow.commit()

    assert await _user_exists(session_factory, "reopen@plante.org")


class _PublisherThatChecksPersistence(IDomainPublisher):
    """Ao receber o evento, confere numa sessão separada que o usuário já foi gravado."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.user_was_persisted: bool | None = None

    async def publish(self, event: DomainEvent) -> None:
        assert isinstance(event, UserRegisteredEvent)
        self.user_was_persisted = await _user_exists(self._session_factory, event.email)


async def test_register_persists_user_before_publishing(session_factory: async_sessionmaker[AsyncSession]) -> None:
    publisher = _PublisherThatChecksPersistence(session_factory)
    hasher = MagicMock()
    hasher.hash.return_value = "hashed"
    use_case = RegisterUserUseCase(uow=SqlAlchemyUnitOfWork(session_factory), hasher=hasher, publisher=publisher)

    await use_case.execute(RegisterUserInputDTO(email="E2E@Plante.org", password="Secret123", country="BR", state="SP"))

    assert publisher.user_was_persisted is True
    assert await _user_exists(session_factory, "e2e@plante.org")
