"""pending email change

`users.pending_email`: a troca de e-mail só vale depois do código; até lá o e-mail atual segue
entrando (antes trocava na hora e a conta ficava trancada até a confirmação).

Revision ID: e1a7c3b5d9f2
Revises: d8b4e6f2a9c1
Create Date: 2026-10-16 14:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e1a7c3b5d9f2'
down_revision: str | None = 'd8b4e6f2a9c1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('pending_email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'pending_email')
