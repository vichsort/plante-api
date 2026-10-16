"""care due date as local calendar day

O vencimento da rega era um instante (meia-noite UTC do dia calculado em UTC) e a planta
"atrasava" desde o primeiro minuto do dia do vencimento. Passa a ser um dia do calendário local
(`GardenCalendar`); a janela de ±1 dia é regra do domínio. A data gravada antes é a do UTC, a
mesma que o código antigo calculou.

Revision ID: c7f3a9e2d1b8
Revises: b5e2d8a1c4f6
Create Date: 2026-10-16 11:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7f3a9e2d1b8'
down_revision: str | None = 'b5e2d8a1c4f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        'user_plants', 'care_next_due_at',
        new_column_name='care_next_due_on',
        type_=sa.Date(),
        postgresql_using="(care_next_due_at AT TIME ZONE 'UTC')::date",
    )


def downgrade() -> None:
    op.alter_column(
        'user_plants', 'care_next_due_on',
        new_column_name='care_next_due_at',
        type_=sa.DateTime(timezone=True),
        postgresql_using="care_next_due_on::timestamp AT TIME ZONE 'UTC'",
    )
