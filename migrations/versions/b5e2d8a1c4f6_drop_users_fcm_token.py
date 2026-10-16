"""drop users.fcm_token

Push (Firebase Cloud Messaging) saiu sem nunca ter enviado nada. Se voltar, o token do aparelho
mora num módulo de notificações próprio (um usuário pode ter vários aparelhos), não no `users`.

Revision ID: b5e2d8a1c4f6
Revises: a3c9e1f4b7d2
Create Date: 2026-10-16 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b5e2d8a1c4f6'
down_revision: str | None = 'a3c9e1f4b7d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column('users', 'fcm_token_updated_at')
    op.drop_column('users', 'fcm_token')


def downgrade() -> None:
    op.add_column('users', sa.Column('fcm_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('fcm_token_updated_at', sa.DateTime(timezone=True), nullable=True))
