from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.domain.entities.care_schedule import CareSchedule, CareType
from src.domain.entities.user import User
from src.domain.entities.user_plant import (
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.domain.exceptions import PlantNotReadyForWateringError
from src.domain.value_objects.care_interval import CareInterval
from src.domain.value_objects.ids import IdentificationId
from src.domain.value_objects.streak import Streak
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation


def test_user_creation_and_email_validation():
    now = datetime.now(UTC)
    user = User.create_new(
        email="dev@plante.org",
        hashed_password="hashed_pass",
        location=UserLocation(country="BR", state="SP"),
        current_time=now,
    )

    assert user.email == "dev@plante.org"
    assert user.is_verified is False
    assert user.subscription == SubscriptionTier.FREE

    with pytest.raises(ValueError, match="Invalid email address"):
        User.create_new(
            email="invalid-email",
            hashed_password="hash",
            location=UserLocation(country="BR", state="SP"),
            current_time=now,
        )

def test_user_plant_watering_streak():
    now = datetime.now(UTC)
    # Rega com vencimento no passado (pronta para regar)
    past_due = now - timedelta(days=1)
    care = CareSchedule(
        care_type=CareType.WATER,
        interval=CareInterval(days=2),
        is_active=True,
        next_due_at=past_due,
        created_at=now - timedelta(days=10),
    )

    plant = UserPlant(
        id=None,
        user_id=None,
        scientific_name="Monstera deliciosa",
        identification_confidence=0.95,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        added_at=now - timedelta(days=10),
        care_schedule=care,
        identification_id=IdentificationId(uuid4()),
        watering_streak=Streak(current_count=1, last_action_time=now - timedelta(days=1)),
    )

    # Executa rega
    plant.water(now)

    assert plant.last_watered_at == now
    assert plant.watering_streak.current_count == 2
    assert plant.care_schedule.next_due_at > now

def test_user_plant_water_too_early_raises():
    now = datetime.now(UTC)
    # Rega com vencimento no futuro (ainda não precisa regar)
    future_due = now + timedelta(days=2)
    care = CareSchedule(
        care_type=CareType.WATER,
        interval=CareInterval(days=3),
        is_active=True,
        next_due_at=future_due,
        created_at=now,
    )

    plant = UserPlant(
        id=None,
        user_id=None,
        scientific_name="Monstera deliciosa",
        identification_confidence=0.95,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        added_at=now,
        care_schedule=care,
        identification_id=IdentificationId(uuid4()),
    )

    with pytest.raises(PlantNotReadyForWateringError):
        plant.water(now)


def test_user_email_is_normalized_on_creation_and_change():
    user = User.create_new(
        email=" Dev@Plante.ORG ",
        hashed_password="hash",
        location=UserLocation(country="BR", state="SP"),
        current_time=datetime.now(UTC),
    )
    assert user.email == "dev@plante.org"

    user.change_email("  Novo@Plante.org")
    assert user.email == "novo@plante.org"
