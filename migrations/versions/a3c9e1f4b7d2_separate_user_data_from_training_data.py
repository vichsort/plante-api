"""separate user data from anonymous training data

Plano C (todo.md): o que é do usuário e o que treina a IA passam a ser tabelas sem ligação de
volta.

- `plant_identification_samples` → `identifications` (histórico do usuário, apagado com ele) +
  `training_identification_samples` (anônima).
- `health_identification_samples` → `training_health_samples` (anônima); `health_records`
  ganha o vínculo de mão única `training_sample_id`.
- `training_feedback`: eventos de feedback (explícito ou implícito) sobre as amostras.
- `user_plants.identification_id`: planta só entra no jardim a partir de uma identificação.
- `users.garden_count` sai (passa a ser contado); `health_records.user_id` vira `CASCADE`.

Tabelas de treino não têm `user_id`, FK para tabelas do usuário nem horário exato (só o mês).
Escrita para banco vazio: com dados nas tabelas antigas, a migração as descarta.

Revision ID: a3c9e1f4b7d2
Revises: db7647f0acac
Create Date: 2026-10-15 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3c9e1f4b7d2'
down_revision: str | None = 'db7647f0acac'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_HEALTH_SEVERITY = postgresql.ENUM(
    'healthy', 'low', 'moderate', 'high', 'critical', name='healthSeverity', create_type=False
)


def _location_columns() -> list[sa.Column[object]]:
    return [
        sa.Column('period', sa.Date(), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('grid_latitude', sa.Float(), nullable=True),
        sa.Column('grid_longitude', sa.Float(), nullable=True),
    ]


def upgrade() -> None:
    # Amostras antigas (misturavam dado do usuário com dado de treino)
    op.drop_index(op.f('ix_health_identification_samples_user_id'), table_name='health_identification_samples')
    op.drop_index(op.f('ix_health_identification_samples_status'), table_name='health_identification_samples')
    op.drop_index(op.f('ix_health_identification_samples_scientific_name'), table_name='health_identification_samples')
    op.drop_index(op.f('ix_health_identification_samples_health_record_id'), table_name='health_identification_samples')
    op.drop_table('health_identification_samples')
    sa.Enum(name='healthSampleStatus').drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f('ix_plant_identification_samples_user_id'), table_name='plant_identification_samples')
    op.drop_index(op.f('ix_plant_identification_samples_status'), table_name='plant_identification_samples')
    op.drop_index(op.f('ix_plant_identification_samples_scientific_name'), table_name='plant_identification_samples')
    op.drop_table('plant_identification_samples')

    # Dataset de treino
    op.create_table('training_identification_samples',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('image_key', sa.String(length=500), nullable=False),
        sa.Column('scientific_name', sa.String(length=255), nullable=False),
        sa.Column('family', sa.String(length=255), nullable=True),
        sa.Column('genus', sa.String(length=255), nullable=True),
        sa.Column('gbif_id', sa.String(length=50), nullable=True),
        sa.Column('provider_entity_id', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('low_confidence', sa.Boolean(), nullable=False),
        sa.Column('signals', sa.JSON(), nullable=False),
        *_location_columns(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_training_identification_samples_scientific_name'), 'training_identification_samples', ['scientific_name'], unique=False)
    op.create_index(op.f('ix_training_identification_samples_period'), 'training_identification_samples', ['period'], unique=False)

    op.create_table('training_health_samples',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('image_key', sa.String(length=500), nullable=False),
        sa.Column('scientific_name', sa.String(length=255), nullable=False),
        sa.Column('vitality_score', sa.Float(), nullable=False),
        sa.Column('severity', _HEALTH_SEVERITY, nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('issues_detected', sa.JSON(), nullable=False),
        sa.Column('treatment_plan', sa.JSON(), nullable=False),
        sa.Column('reference_image_keys', sa.JSON(), nullable=False),
        sa.Column('recovery_estimate_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('signals', sa.JSON(), nullable=False),
        *_location_columns(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_training_health_samples_scientific_name'), 'training_health_samples', ['scientific_name'], unique=False)
    op.create_index(op.f('ix_training_health_samples_period'), 'training_health_samples', ['period'], unique=False)

    op.create_table('training_feedback',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('identification_sample_id', sa.UUID(), nullable=True),
        sa.Column('health_sample_id', sa.UUID(), nullable=True),
        sa.Column('verdict', sa.Enum('correct', 'wrong', 'unsure', name='feedbackVerdict'), nullable=False),
        sa.Column('origin', sa.Enum('explicit', 'added_to_garden', name='feedbackOrigin'), nullable=False),
        sa.Column('suggested_name', sa.String(length=255), nullable=True),
        sa.Column('given_on', sa.Date(), nullable=False),
        sa.CheckConstraint(
            '(identification_sample_id IS NULL) <> (health_sample_id IS NULL)',
            name='ck_training_feedback_one_target',
        ),
        sa.ForeignKeyConstraint(['identification_sample_id'], ['training_identification_samples.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['health_sample_id'], ['training_health_samples.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_training_feedback_identification_sample_id'), 'training_feedback', ['identification_sample_id'], unique=False)
    op.create_index(op.f('ix_training_feedback_health_sample_id'), 'training_feedback', ['health_sample_id'], unique=False)

    # Lado do usuário
    op.create_table('identifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('training_sample_id', sa.UUID(), nullable=False),
        sa.Column('species_id', sa.UUID(), nullable=False),
        sa.Column('scientific_name', sa.String(length=255), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('image_key', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['training_sample_id'], ['training_identification_samples.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['species_id'], ['plant_species.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('training_sample_id'),
    )
    op.create_index(op.f('ix_identifications_user_id'), 'identifications', ['user_id'], unique=False)

    op.add_column('user_plants', sa.Column('identification_id', sa.UUID(), nullable=False))
    op.create_index(op.f('ix_user_plants_identification_id'), 'user_plants', ['identification_id'], unique=False)
    op.create_foreign_key(
        'user_plants_identification_id_fkey', 'user_plants', 'identifications',
        ['identification_id'], ['id'], ondelete='CASCADE',
    )

    op.add_column('health_records', sa.Column('training_sample_id', sa.UUID(), nullable=False))
    op.create_unique_constraint('health_records_training_sample_id_key', 'health_records', ['training_sample_id'])
    op.create_foreign_key(
        'health_records_training_sample_id_fkey', 'health_records', 'training_health_samples',
        ['training_sample_id'], ['id'], ondelete='RESTRICT',
    )
    # Diagnóstico é dado pessoal: sai com o usuário (antes SET NULL)
    op.drop_constraint('health_records_user_id_fkey', 'health_records', type_='foreignkey')
    op.create_foreign_key(
        'health_records_user_id_fkey', 'health_records', 'users', ['user_id'], ['id'], ondelete='CASCADE'
    )

    op.drop_column('users', 'garden_count')


def downgrade() -> None:
    op.add_column('users', sa.Column('garden_count', sa.Integer(), server_default='0', nullable=False))

    op.drop_constraint('health_records_user_id_fkey', 'health_records', type_='foreignkey')
    op.create_foreign_key(
        'health_records_user_id_fkey', 'health_records', 'users', ['user_id'], ['id'], ondelete='SET NULL'
    )
    op.drop_constraint('health_records_training_sample_id_fkey', 'health_records', type_='foreignkey')
    op.drop_constraint('health_records_training_sample_id_key', 'health_records', type_='unique')
    op.drop_column('health_records', 'training_sample_id')

    op.drop_constraint('user_plants_identification_id_fkey', 'user_plants', type_='foreignkey')
    op.drop_index(op.f('ix_user_plants_identification_id'), table_name='user_plants')
    op.drop_column('user_plants', 'identification_id')

    op.drop_index(op.f('ix_identifications_user_id'), table_name='identifications')
    op.drop_table('identifications')
    op.drop_index(op.f('ix_training_feedback_health_sample_id'), table_name='training_feedback')
    op.drop_index(op.f('ix_training_feedback_identification_sample_id'), table_name='training_feedback')
    op.drop_table('training_feedback')
    sa.Enum(name='feedbackOrigin').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='feedbackVerdict').drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f('ix_training_health_samples_period'), table_name='training_health_samples')
    op.drop_index(op.f('ix_training_health_samples_scientific_name'), table_name='training_health_samples')
    op.drop_table('training_health_samples')
    op.drop_index(op.f('ix_training_identification_samples_period'), table_name='training_identification_samples')
    op.drop_index(op.f('ix_training_identification_samples_scientific_name'), table_name='training_identification_samples')
    op.drop_table('training_identification_samples')

    op.create_table('plant_identification_samples',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scientific_name', sa.String(length=255), nullable=False),
        sa.Column('species_id', sa.UUID(), nullable=False),
        sa.Column('user_image_key', sa.String(length=500), nullable=False),
        sa.Column('identification_confidence', sa.Float(), nullable=False),
        sa.Column('identification_source', sa.String(length=50), nullable=False),
        sa.Column('raw_response', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('has_deep_analysis', sa.Boolean(), nullable=False),
        sa.Column('has_nutritional_analysis', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['species_id'], ['plant_species.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_plant_identification_samples_scientific_name'), 'plant_identification_samples', ['scientific_name'], unique=False)
    op.create_index(op.f('ix_plant_identification_samples_status'), 'plant_identification_samples', ['status'], unique=False)
    op.create_index(op.f('ix_plant_identification_samples_user_id'), 'plant_identification_samples', ['user_id'], unique=False)
    op.create_table('health_identification_samples',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('health_record_id', sa.UUID(), nullable=False),
        sa.Column('scientific_name', sa.String(length=255), nullable=False),
        sa.Column('user_image_key', sa.String(length=500), nullable=False),
        sa.Column('reference_image_keys', sa.JSON(), nullable=False),
        sa.Column('vitality_score', sa.Float(), nullable=False),
        sa.Column('issues_detected', sa.JSON(), nullable=False),
        sa.Column('treatment_plan', sa.JSON(), nullable=False),
        sa.Column('identification_source', sa.String(length=50), nullable=False),
        sa.Column('raw_response', sa.JSON(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'rejected', name='healthSampleStatus'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovery_estimate_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(['health_record_id'], ['health_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_health_identification_samples_health_record_id'), 'health_identification_samples', ['health_record_id'], unique=True)
    op.create_index(op.f('ix_health_identification_samples_scientific_name'), 'health_identification_samples', ['scientific_name'], unique=False)
    op.create_index(op.f('ix_health_identification_samples_status'), 'health_identification_samples', ['status'], unique=False)
    op.create_index(op.f('ix_health_identification_samples_user_id'), 'health_identification_samples', ['user_id'], unique=False)
