from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.adapters.persistence.models.user import UserModel
from src.modules.identity.adapters.persistence.repositories.user import UserRepository
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.user_location import UserLocation


def _new(email: str) -> User:
    return User.create_new(
        email=email,
        hashed_password="hashed_secret_password",
        location=UserLocation(country="BR", state="SP"),
        current_time=datetime.now(UTC),
    )


async def test_saved_user_is_found_by_id_and_email(db_session: AsyncSession) -> None:
    # Arrange
    repo = UserRepository(db_session)
    saved = await repo.save(_new("real_db@plante.org"))
    await db_session.commit()

    # Act
    by_id, by_email = await repo.get_by_id(saved.id), await repo.get_by_email("real_db@plante.org")

    # Assert
    assert by_id is not None and by_email is not None
    assert (by_id.id, by_email.id, by_id.location) == (saved.id, saved.id, UserLocation(country="BR", state="SP"))


async def test_saving_an_existing_user_updates_it(db_session: AsyncSession) -> None:
    # Arrange: antes o `save` fazia INSERT de novo e violava a PK
    repo = UserRepository(db_session)
    user = await repo.save(_new("update@plante.org"))
    await db_session.commit()
    loaded = await repo.get_by_id(user.id)
    assert loaded is not None
    loaded.request_email_change("novo@plante.org")

    # Act
    await repo.save(loaded)
    await db_session.commit()

    # Assert
    reloaded = await repo.get_by_id(user.id)
    assert reloaded is not None and reloaded.pending_email == "novo@plante.org"


async def test_soft_deleted_user_is_not_found(db_session: AsyncSession) -> None:
    # Arrange
    repo = UserRepository(db_session)
    saved = await repo.save(_new("deleted@plante.org"))
    await db_session.commit()
    model = await db_session.get(UserModel, saved.id)
    assert model is not None
    model.deleted_at = datetime.now(UTC)
    await db_session.commit()

    # Act
    by_id, by_email = await repo.get_by_id(saved.id), await repo.get_by_email("deleted@plante.org")

    # Assert
    assert (by_id, by_email) == (None, None)
