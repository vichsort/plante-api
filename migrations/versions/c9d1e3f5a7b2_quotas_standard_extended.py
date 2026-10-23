"""quotas: standard and extended levels

There is no paid plan (docs/decisions/2026-10-19-funding-and-quota.md): `subscriptions` becomes
`quotas`, its `tier` column becomes `level`, and the `subscriptionTier` type becomes `quotaLevel`
with `FREE`/`PRO` renamed to `standard`/`extended` (metadata only, rows are not rewritten).

Every PRO row came from the public upgrade route, removed in 0.1.3, so none is legitimate: every row
goes back to `standard` with no deadline. The downgrade restores the names, not those rows.

Revision ID: c9d1e3f5a7b2
Revises: b8e2d4f6a1c3
Create Date: 2026-10-19 22:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c9d1e3f5a7b2'
down_revision: str | None = 'b8e2d4f6a1c3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('ALTER TYPE "subscriptionTier" RENAME VALUE \'FREE\' TO \'standard\'')
    op.execute('ALTER TYPE "subscriptionTier" RENAME VALUE \'PRO\' TO \'extended\'')
    op.execute('ALTER TYPE "subscriptionTier" RENAME TO "quotaLevel"')
    op.rename_table('subscriptions', 'quotas')
    op.alter_column('quotas', 'tier', new_column_name='level')
    op.execute('ALTER TABLE quotas RENAME CONSTRAINT subscriptions_pkey TO quotas_pkey')
    op.execute('ALTER TABLE quotas RENAME CONSTRAINT subscriptions_user_id_fkey TO quotas_user_id_fkey')
    op.execute("UPDATE quotas SET level = 'standard', expires_at = NULL")


def downgrade() -> None:
    op.execute('ALTER TABLE quotas RENAME CONSTRAINT quotas_user_id_fkey TO subscriptions_user_id_fkey')
    op.execute('ALTER TABLE quotas RENAME CONSTRAINT quotas_pkey TO subscriptions_pkey')
    op.alter_column('quotas', 'level', new_column_name='tier')
    op.rename_table('quotas', 'subscriptions')
    op.execute('ALTER TYPE "quotaLevel" RENAME TO "subscriptionTier"')
    op.execute('ALTER TYPE "subscriptionTier" RENAME VALUE \'extended\' TO \'PRO\'')
    op.execute('ALTER TYPE "subscriptionTier" RENAME VALUE \'standard\' TO \'FREE\'')
