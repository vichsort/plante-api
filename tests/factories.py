"""Entidades de domínio válidas para os testes, com valores padrão sobrescrevíveis."""
from datetime import UTC, date, datetime
from uuid import uuid4

from src.modules.catalog import EnrichmentStatus, PlantSpecies, PlantSpeciesId
from src.modules.garden import UserPlantId
from src.modules.garden.domain.entities.care_schedule import CareSchedule, CareType
from src.modules.garden.domain.entities.user_plant import (
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.modules.garden.domain.value_objects.care_interval import CareInterval
from src.modules.health import HealthRecord, HealthRecordId
from src.modules.identification import Identification, IdentificationId
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.modules.training import (
    DiseaseSuggestion,
    HealthSeverity,
    HealthSignals,
    IdentificationSignals,
    SpeciesSuggestion,
    TrainingHealthSample,
    TrainingHealthSampleId,
    TrainingIdentificationSample,
    TrainingIdentificationSampleId,
    TrainingLocation,
)
from src.shared.domain import LocalCalendar, UserId

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
CALENDAR = LocalCalendar.from_name("America/Sao_Paulo")


def make_user(
    user_id: UserId | None = None,
    email: str = "user@plante.org",
    hashed_password: str = "hashed",
    is_verified: bool = True,
) -> User:
    return User(
        id=user_id or UserId(uuid4()),
        email=email,
        hashed_password=hashed_password,
        location=UserLocation(country="BR", state="SP"),
        is_verified=is_verified,
        created_at=NOW,
    )


def make_care_schedule(next_due_on: date | None = None) -> CareSchedule:
    return CareSchedule(
        care_type=CareType.WATER,
        interval=CareInterval(days=7),
        is_active=True,
        created_at=NOW,
        next_due_on=next_due_on,
    )


def make_user_plant(
    plant_id: UserPlantId | None = None,
    user_id: UserId | None = None,
    scientific_name: str = "Monstera deliciosa",
    care_schedule: CareSchedule | None = None,
    identification_id: IdentificationId | None = None,
) -> UserPlant:
    return UserPlant(
        id=plant_id or UserPlantId(uuid4()),
        user_id=user_id or UserId(uuid4()),
        scientific_name=scientific_name,
        identification_confidence=0.9,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        care_schedule=care_schedule or make_care_schedule(),
        identification_id=identification_id or IdentificationId(uuid4()),
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


MONTH = NOW.date().replace(day=1)
LOCATION = TrainingLocation(country="BR", state="SP", grid_latitude=-23.5, grid_longitude=-46.6)


def make_identification_signals() -> tuple[IdentificationSignals, ...]:
    return (
        IdentificationSignals(
            provider="kindwise",
            suggestions=(
                SpeciesSuggestion("Monstera deliciosa", 0.9, family="Araceae", genus="Monstera"),
                SpeciesSuggestion("Monstera adansonii", 0.05, family="Araceae", genus="Monstera"),
            ),
            is_plant_probability=0.99,
            model_version="plant_id:5.0",
        ),
        IdentificationSignals(
            provider="plantnet",
            suggestions=(SpeciesSuggestion("Monstera deliciosa", 0.86, gbif_id="2868241"),),
            model_version="2025-01-17 (7.3)",
        ),
    )


def make_training_identification_sample(scientific_name: str = "Monstera deliciosa") -> TrainingIdentificationSample:
    return TrainingIdentificationSample(
        id=TrainingIdentificationSampleId(uuid4()),
        image_key="training/identifications/monstera.jpg",
        scientific_name=scientific_name,
        confidence=0.9,
        source="consensus",
        low_confidence=False,
        signals=make_identification_signals(),
        period=MONTH,
        location=LOCATION,
        family="Araceae",
        genus="Monstera",
    )


def make_identification(
    user_id: UserId,
    training_sample_id: TrainingIdentificationSampleId,
    species_id: PlantSpeciesId,
    scientific_name: str = "Monstera deliciosa",
) -> Identification:
    return Identification(
        id=IdentificationId(uuid4()),
        user_id=user_id,
        training_sample_id=training_sample_id,
        species_id=species_id,
        scientific_name=scientific_name,
        confidence=0.9,
        source="consensus",
        image_key="identifications/monstera.jpg",
        created_at=NOW,
    )


def make_training_health_sample() -> TrainingHealthSample:
    return TrainingHealthSample(
        id=TrainingHealthSampleId(uuid4()),
        image_key="training/identifications/health.jpg",
        scientific_name="Monstera deliciosa",
        vitality_score=0.4,
        severity=HealthSeverity.MODERATE,
        source="kindwise",
        signals=HealthSignals(
            provider="kindwise",
            is_healthy_probability=0.4,
            diseases=(DiseaseSuggestion("leaf_spots", 0.7),),
            is_plant_probability=0.98,
        ),
        period=MONTH,
        location=LOCATION,
        issues_detected=("leaf_spots",),
    )


def make_health_record(
    user_id: UserId | None = None,
    user_plant_id: UserPlantId | None = None,
    training_sample_id: TrainingHealthSampleId | None = None,
) -> HealthRecord:
    return HealthRecord(
        id=HealthRecordId(uuid4()),
        user_plant_id=user_plant_id or UserPlantId(uuid4()),
        scientific_name="Monstera deliciosa",
        vitality_score=0.4,
        severity=HealthSeverity.MODERATE,
        source="kindwise",
        image_key="health/monstera.jpg",
        training_sample_id=training_sample_id or TrainingHealthSampleId(uuid4()),
        diagnosed_at=NOW,
        user_id=user_id or UserId(uuid4()),
        issues_detected=("leaf_spots",),
        treatment_plan=("Remover folhas afetadas",),
    )
