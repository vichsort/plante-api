"""Base do Unit of Work contra o Postgres: uma transação física, com dono, à qual outros UoW se juntam."""
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.shared.adapters import SqlAlchemyUnitOfWork


class _ProbeUnitOfWork(SqlAlchemyUnitOfWork):
    """UoW mínimo: grava uma linha numa tabela temporária, sem depender de módulo nenhum."""

    def _bind(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(self, value: str) -> None:
        await self.session.execute(text("INSERT INTO probe (value) VALUES (:value)"), {"value": value})


@pytest.fixture
async def factory(session_factory: async_sessionmaker[AsyncSession]) -> async_sessionmaker[AsyncSession]:
    async with session_factory() as session:
        await session.execute(text("CREATE TABLE IF NOT EXISTS probe (value text)"))
        await session.commit()
    return session_factory


async def _values(factory: async_sessionmaker[AsyncSession]) -> list[str]:
    async with factory() as session:
        return list((await session.execute(text("SELECT value FROM probe ORDER BY value"))).scalars())


async def test_owner_commits_what_the_joined_unit_wrote(factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    outer, inner = _ProbeUnitOfWork(factory), _ProbeUnitOfWork(factory)
    value = uuid4().hex

    # Act
    async with outer:
        outer_joined = outer.joined
        async with inner:
            inner_joined = inner.joined
            same_session = inner.session is outer.session
            await inner.insert(value)
        await outer.commit()

    # Assert
    assert (outer_joined, inner_joined, same_session) == (False, True, True)
    assert value in await _values(factory)


async def test_owner_rollback_discards_what_the_joined_unit_wrote(factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    outer, inner = _ProbeUnitOfWork(factory), _ProbeUnitOfWork(factory)
    value = uuid4().hex

    # Act
    async with outer:
        async with inner:
            await inner.insert(value)
        # sai sem commit

    # Assert
    assert value not in await _values(factory)


async def test_joined_unit_cannot_commit(factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    outer, inner = _ProbeUnitOfWork(factory), _ProbeUnitOfWork(factory)

    # Act & Assert
    async with outer, inner:
        with pytest.raises(RuntimeError, match="Only the unit of work that opened"):
            await inner.commit()


async def test_after_the_owner_closes_a_new_unit_opens_its_own_transaction(factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    first, second = _ProbeUnitOfWork(factory), _ProbeUnitOfWork(factory)
    async with first:
        pass

    # Act
    async with second:
        joined = second.joined

    # Assert
    assert joined is False
