"""add health_records.user_id

O modelo e o domínio já usavam a coluna (dono do diagnóstico), mas ela nunca foi criada:
todo INSERT em health_records falhava.

Revision ID: d44a59cc8835
Revises: 6669c3cc2c4a
Create Date: 2026-10-15 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd44a59cc8835'
down_revision: str | None = '6669c3cc2c4a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('health_records', sa.Column('user_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_health_records_user_id'), 'health_records', ['user_id'], unique=False)
    op.create_foreign_key(
        'health_records_user_id_fkey', 'health_records', 'users', ['user_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('health_records_user_id_fkey', 'health_records', type_='foreignkey')
    op.drop_index(op.f('ix_health_records_user_id'), table_name='health_records')
    op.drop_column('health_records', 'user_id')
