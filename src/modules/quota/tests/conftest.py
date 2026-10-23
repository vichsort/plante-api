"""Contas para a FK de `quotas`: o módulo não conhece o identity, então grava a linha direto."""
from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.shared.domain import UserId


@pytest.fixture
def account(session_factory: async_sessionmaker[AsyncSession]) -> Callable[[], Awaitable[UserId]]:
    async def create() -> UserId:
        user_id = UserId(uuid4())
        async with session_factory() as session:
            await session.execute(
                text(
                    "INSERT INTO users (id, email, hashed_password, location_country, location_state, is_verified, created_at, updated_at)"
                    " VALUES (:id, :email, 'hash', 'BR', 'SP', true, now(), now())"
                ),
                {"id": user_id, "email": f"{user_id}@plante.org"},
            )
            await session.commit()
        return user_id

    return create
