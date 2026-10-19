"""feedback origins for the plant removal reasons

Taking a plant out of the garden with a reason becomes an implicit signal on the identification
label: `removed_misidentified` votes WRONG; the others come with UNSURE (an event, no vote).

Revision ID: b8e2d4f6a1c3
Revises: f4c2a8d6e1b3
Create Date: 2026-10-19 20:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b8e2d4f6a1c3'
down_revision: str | None = 'f4c2a8d6e1b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = ('removed_misidentified', 'removed_died', 'removed_gave_away', 'removed_other')


def upgrade() -> None:
    for value in _NEW:
        op.execute(f"ALTER TYPE \"feedbackOrigin\" ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres does not drop enum values: recreate the type without them. Fails while rows still use them.
    op.execute('ALTER TYPE "feedbackOrigin" RENAME TO "feedbackOrigin_old"')
    op.execute("CREATE TYPE \"feedbackOrigin\" AS ENUM ('explicit', 'added_to_garden')")
    op.execute(
        'ALTER TABLE training_feedback ALTER COLUMN origin '
        'TYPE "feedbackOrigin" USING origin::text::"feedbackOrigin"'
    )
    op.execute('DROP TYPE "feedbackOrigin_old"')
