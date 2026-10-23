"""users: terms acceptance

Sign-up records which version of the terms the user accepted, and when (LGPD: the photos go to the
identification providers and become an anonymous training dataset). Existing accounts have none and
accept on their next use of the AI.

Revision ID: e3f5a7b9c2d4
Revises: d2e4f6a8b1c3
Create Date: 2026-10-23 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e3f5a7b9c2d4'
down_revision: str | None = 'd2e4f6a8b1c3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('terms_version', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('terms_accepted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'terms_accepted_at')
    op.drop_column('users', 'terms_version')
