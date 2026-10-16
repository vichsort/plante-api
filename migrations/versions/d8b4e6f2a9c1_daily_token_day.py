"""daily token day

`users.tokens_day`: dia local a que `tokens_used_today` se refere. A cota diária zera na primeira
cobrança de um dia novo (antes nada zerava o contador, e o FREE ficava sem tokens). Linhas
existentes ficam com NULL: o contador antigo deixa de valer e a cota volta cheia.

Revision ID: d8b4e6f2a9c1
Revises: c7f3a9e2d1b8
Create Date: 2026-10-16 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd8b4e6f2a9c1'
down_revision: str | None = 'c7f3a9e2d1b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('tokens_day', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'tokens_day')
