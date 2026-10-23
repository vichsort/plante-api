"""The image keys migration turns every stored S3 URL into its key and leaves anything else alone."""
from pathlib import Path
from uuid import uuid4

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import Connection, create_engine, text

_ROOT = Path(__file__).parents[3]
_BEFORE = "c9d1e3f5a7b2"
_BUCKET = "https://plante-bucket.s3.us-east-1.amazonaws.com/"


def _migrate(connection: Connection, direction: str, revision: str) -> None:
    config = AlembicConfig(str(_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_ROOT / "migrations"))
    config.attributes["connection"] = connection
    getattr(alembic_command, direction)(config, revision)


def _insert(connection: Connection, sql: str, **values: str) -> None:
    connection.execute(text(sql), values)


def test_stored_urls_become_keys(postgres_url: str) -> None:
    # Arrange: the schema before the migration, with a row of each table holding URLs
    engine = create_engine(postgres_url)
    user, species, sample, health_sample, identification, plant = (str(uuid4()) for _ in range(6))
    try:
        with engine.connect() as connection, connection.begin() as transaction:  # DDL included, undone at the end
            _migrate(connection, "downgrade", _BEFORE)
            _insert(
                connection,
                "INSERT INTO users (id, email, hashed_password, location_country, location_state, is_verified, created_at, updated_at)"
                " VALUES (:id, :email, 'hash', 'BR', 'SP', true, now(), now())",
                id=user, email=f"{user}@plante.org",
            )
            _insert(
                connection,
                "INSERT INTO plant_species (id, scientific_name, common_names, enrichment_status, created_at, updated_at)"
                " VALUES (:id, 'Monstera deliciosa', '[]', 'pending', now(), now())",
                id=species,
            )
            _insert(
                connection,
                "INSERT INTO training_identification_samples (id, image_key, scientific_name, confidence, source,"
                " low_confidence, signals, period, country, state)"
                " VALUES (:id, 'training/identifications/a.jpg', 'Monstera deliciosa', 0.9, 'kindwise', false, '{}',"
                " '2026-10-01', 'BR', 'SP')",
                id=sample,
            )
            _insert(
                connection,
                "INSERT INTO identifications (id, user_id, training_sample_id, species_id, scientific_name, confidence,"
                " source, image_key, created_at, updated_at)"
                " VALUES (:id, :user, :sample, :species, 'Monstera deliciosa', 0.9, 'kindwise', :url, now(), now())",
                id=identification, user=user, sample=sample, species=species,
                url=f"{_BUCKET}identifications/{user}/monstera_deliciosa/1.jpg",
            )
            _insert(
                connection,
                "INSERT INTO user_plants (id, user_id, identification_id, scientific_name, identification_confidence,"
                " identification_source, status, added_at, primary_image_url, streak_count, care_type,"
                " care_interval_days, care_is_active, care_climate_adjusted, care_created_at, created_at, updated_at)"
                " VALUES (:id, :user, :identification, 'Monstera deliciosa', 0.9, 'kindwise', 'identified', now(), :url,"
                " 0, 'water', 7, true, false, now(), now(), now())",
                id=plant, user=user, identification=identification,
                url=f"{_BUCKET}identifications/{user}/monstera_deliciosa/1.jpg",
            )
            _insert(
                connection,
                "INSERT INTO training_health_samples (id, image_key, scientific_name, vitality_score, severity, source,"
                " issues_detected, treatment_plan, reference_image_keys, signals, period, country, state)"
                " VALUES (:id, 'training/identifications/b.jpg', 'Monstera deliciosa', 0.4, 'moderate', 'kindwise',"
                " '[]', '[]', :references, '{}', '2026-10-01', 'BR', 'SP')",
                id=health_sample,
                references=f'["{_BUCKET}species/references/monstera_deliciosa/2.jpg", "https://other.example/3.jpg"]',
            )
            _insert(
                connection,
                "INSERT INTO health_records (id, user_plant_id, user_id, training_sample_id, scientific_name,"
                " diagnosed_at, vitality_score, severity, source, image_key, created_at, updated_at)"
                " VALUES (:id, :plant, :user, :sample, 'Monstera deliciosa', now(), 0.4, 'moderate', 'kindwise', :url,"
                " now(), now())",
                id=str(uuid4()), plant=plant, user=user, sample=health_sample,
                url=f"{_BUCKET}identifications/{user}/monstera_deliciosa/4.jpg",
            )
            _insert(
                connection,
                "INSERT INTO plant_reference_images (id, scientific_name, storage_key, source, created_at, updated_at)"
                " VALUES (:id, 'Monstera deliciosa', :url, 'kindwise_similar', now(), now())",
                id=str(uuid4()), url=f"{_BUCKET}species/references/monstera_deliciosa/2.jpg",
            )

            # Act
            _migrate(connection, "upgrade", "head")

            # Assert
            stored = connection.execute(text(
                "SELECT (SELECT image_key FROM identifications), (SELECT primary_image_key FROM user_plants),"
                " (SELECT image_key FROM health_records), (SELECT storage_key FROM plant_reference_images),"
                " (SELECT reference_image_keys::text FROM training_health_samples)"
            )).one()
            assert tuple(stored) == (
                f"identifications/{user}/monstera_deliciosa/1.jpg",
                f"identifications/{user}/monstera_deliciosa/1.jpg",
                f"identifications/{user}/monstera_deliciosa/4.jpg",
                "species/references/monstera_deliciosa/2.jpg",
                '["species/references/monstera_deliciosa/2.jpg", "https://other.example/3.jpg"]',
            )
            transaction.rollback()
    finally:
        engine.dispose()
