"""subscriptions table

Plano e cota diária de tokens saem de `users` para `subscriptions` (módulo subscription). Só quem
tem algo diferente do padrão ganha linha (PRO, ou já gastou tokens): sem linha = FREE com a cota
cheia, então o cadastro não precisa criar nada. O tipo `subscriptionTier` do Postgres é o mesmo.

Revision ID: f4c2a8d6e1b3
Revises: e1a7c3b5d9f2
Create Date: 2026-10-16 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f4c2a8d6e1b3'
down_revision: str | None = 'e1a7c3b5d9f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIER = postgresql.ENUM('FREE', 'PRO', name='subscriptionTier', create_type=False)


def upgrade() -> None:
    op.create_table(
        'subscriptions',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('tier', _TIER, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tokens_used_today', sa.Integer(), nullable=False),
        sa.Column('tokens_day', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.execute(
        """
        INSERT INTO subscriptions (user_id, tier, expires_at, tokens_used_today, tokens_day, created_at, updated_at)
        SELECT id, subscription, subscription_expires_at, tokens_used_today, tokens_day, now(), now()
        FROM users
        WHERE subscription <> 'FREE' OR tokens_day IS NOT NULL
        """
    )
    op.drop_column('users', 'subscription')
    op.drop_column('users', 'subscription_expires_at')
    op.drop_column('users', 'tokens_used_today')
    op.drop_column('users', 'tokens_day')


def downgrade() -> None:
    # Colunas voltam com o padrão de quem não tem linha; o default só existe durante a cópia
    op.add_column('users', sa.Column('subscription', _TIER, nullable=False, server_default='FREE'))
    op.add_column('users', sa.Column('tokens_used_today', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('tokens_day', sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE users SET
            subscription = s.tier,
            subscription_expires_at = s.expires_at,
            tokens_used_today = s.tokens_used_today,
            tokens_day = s.tokens_day
        FROM subscriptions s
        WHERE s.user_id = users.id
        """
    )
    op.alter_column('users', 'subscription', server_default=None)
    op.alter_column('users', 'tokens_used_today', server_default=None)
    op.drop_table('subscriptions')
