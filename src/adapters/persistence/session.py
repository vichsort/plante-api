from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.infrastructure.settings import Settings

def build_engine(settings: Settings):
    return create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        echo=settings.debug,
    )

def build_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = build_engine(settings)
    return async_sessionmaker(engine, expire_on_commit=False)

async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session