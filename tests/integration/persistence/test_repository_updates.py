"""`save` de entidade já persistida atualiza a linha (antes fazia INSERT e violava a PK)."""
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.repositories.user_repository import UserRepository
from src.domain.entities.user import User
from src.domain.value_objects.user_location import UserLocation


async def test_saving_existing_user_updates_it(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.save(User.create_new(
        email="update@plante.org",
        hashed_password="hash",
        location=UserLocation(country="BR", state="SP"),
        current_time=datetime.now(UTC),
    ))
    await db_session.commit()

    loaded = await repo.get_by_id(user.id)
    assert loaded is not None
    loaded.consume_identify_token()
    await repo.save(loaded)
    await db_session.commit()

    reloaded = await repo.get_by_id(user.id)
    assert reloaded is not None
    assert reloaded.tokens_used_today == 1
