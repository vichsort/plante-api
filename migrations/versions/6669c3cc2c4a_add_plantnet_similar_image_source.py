"""add plantnet_similar image source

Revision ID: 6669c3cc2c4a
Revises: f90d8237dd07
Create Date: 2026-10-15 09:30:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6669c3cc2c4a'
down_revision: str | None = 'f90d8237dd07'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE \"imageSource\" ADD VALUE IF NOT EXISTS 'plantnet_similar'")


def downgrade() -> None:
    # Postgres não remove valor de enum: recria o tipo sem ele. Falha se ainda houver linhas usando o valor.
    op.execute('ALTER TYPE "imageSource" RENAME TO "imageSource_old"')
    op.execute("CREATE TYPE \"imageSource\" AS ENUM ('kindwise_similar', 'user_confirmed')")
    op.execute(
        'ALTER TABLE plant_reference_images ALTER COLUMN source '
        'TYPE "imageSource" USING source::text::"imageSource"'
    )
    op.execute('DROP TYPE "imageSource_old"')
