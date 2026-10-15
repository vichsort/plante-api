"""Entidades de domínio válidas para os testes, com valores padrão sobrescrevíveis."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.domain.entities.care_schedule import CareSchedule, CareType
from src.domain.entities.health_identification_sample import (
    HealthIdentificationSample,
    HealthSampleStatus,
)
from src.domain.entities.health_record import HealthRecord, HealthSeverity
from src.domain.entities.plant_identification_sample import (
    PlantIdentificationSample,
    SampleStatus,
)
from src.domain.entities.plant_species import EnrichmentStatus, PlantSpecies
from src.domain.entities.user import User
from src.domain.entities.user_plant import (
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.domain.value_objects.care_interval import CareInterval
from src.domain.value_objects.ids import (
    HealthRecordId,
    HealthSampleId,
    IdentificationSampleId,
    PlantSpeciesId,
    UserId,
    UserPlantId,
)
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def make_user(
    user_id: UserId | None = None,
    email: str = "user@plante.org",
    hashed_password: str = "hashed",
    is_verified: bool = True,
    tokens_used_today: int = 0,
    garden_count: int = 0,
    subscription: SubscriptionTier = SubscriptionTier.FREE,
    subscription_expires_at: datetime | None = None,
) -> User:
    return User(
        id=user_id or UserId(uuid4()),
        email=email,
        hashed_password=hashed_password,
        location=UserLocation(country="BR", state="SP"),
        is_verified=is_verified,
        subscription=subscription,
        created_at=NOW,
        tokens_used_today=tokens_used_today,
        garden_count=garden_count,
        subscription_expires_at=subscription_expires_at,
    )


def make_care_schedule(next_due_at: datetime | None = None) -> CareSchedule:
    return CareSchedule(
        care_type=CareType.WATER,
        interval=CareInterval(days=7),
        is_active=True,
        created_at=NOW,
        next_due_at=next_due_at,
    )


def make_user_plant(
    plant_id: UserPlantId | None = None,
    user_id: UserId | None = None,
    scientific_name: str = "Monstera deliciosa",
    care_schedule: CareSchedule | None = None,
) -> UserPlant:
    return UserPlant(
        id=plant_id or UserPlantId(uuid4()),
        user_id=user_id or UserId(uuid4()),
        scientific_name=scientific_name,
        identification_confidence=0.9,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        care_schedule=care_schedule or make_care_schedule(),
        added_at=NOW,
    )


def make_species(scientific_name: str = "Monstera deliciosa") -> PlantSpecies:
    return PlantSpecies(
        id=PlantSpeciesId(uuid4()),
        scientific_name=scientific_name,
        enrichment_status=EnrichmentStatus.PENDING,
        family="Araceae",
        genus="Monstera",
    )


def make_identification_sample(
    user_id: UserId | None = None,
    status: SampleStatus = SampleStatus.PENDING,
) -> PlantIdentificationSample:
    return PlantIdentificationSample(
        id=IdentificationSampleId(uuid4()),
        scientific_name="Monstera deliciosa",
        species_id=PlantSpeciesId(uuid4()),
        user_image_key="identifications/monstera.jpg",
        identification_confidence=0.9,
        identification_source="consensus",
        raw_response={},
        status=status,
        created_at=NOW,
        user_id=user_id or UserId(uuid4()),
        confirmed_at=NOW if status == SampleStatus.CONFIRMED else None,
    )


def make_health_record(
    user_id: UserId | None = None,
    user_plant_id: UserPlantId | None = None,
) -> HealthRecord:
    return HealthRecord(
        id=HealthRecordId(uuid4()),
        user_plant_id=user_plant_id or UserPlantId(uuid4()),
        scientific_name="Monstera deliciosa",
        vitality_score=0.4,
        severity=HealthSeverity.MODERATE,
        source="kindwise",
        image_key="health/monstera.jpg",
        diagnosed_at=NOW,
        user_id=user_id or UserId(uuid4()),
        issues_detected=("leaf_spots",),
        treatment_plan=("Remover folhas afetadas",),
    )


def make_health_sample(record: HealthRecord | None = None) -> HealthIdentificationSample:
    record = record or make_health_record()
    return HealthIdentificationSample(
        id=HealthSampleId(uuid4()),
        health_record_id=record.id,
        scientific_name=record.scientific_name,
        user_image_key=record.image_key,
        vitality_score=record.vitality_score,
        issues_detected=record.issues_detected,
        treatment_plan=record.treatment_plan,
        identification_source=record.source,
        raw_response={},
        status=HealthSampleStatus.CONFIRMED,
        created_at=NOW,
        user_id=record.user_id,
        confirmed_at=NOW,
    )


def days_from_now(days: int) -> datetime:
    return NOW + timedelta(days=days)
