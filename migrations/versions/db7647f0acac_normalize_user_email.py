"""normalize users.email

E-mail passa a ser gravado sem espaços nas pontas e em minúsculas (`normalize_email` no
domínio). Linhas existentes são normalizadas antes do CHECK; se duas contas diferirem só pela
caixa, o UPDATE viola o índice único e a migration para (resolver à mão antes de rodar).

Revision ID: db7647f0acac
Revises: d44a59cc8835
Create Date: 2026-10-15 18:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'db7647f0acac'
down_revision: str | None = 'd44a59cc8835'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE users SET email = lower(btrim(email)) WHERE email <> lower(btrim(email))")
    op.create_check_constraint('ck_users_email_normalized', 'users', 'email = lower(btrim(email))')


def downgrade() -> None:
    op.drop_constraint('ck_users_email_normalized', 'users', type_='check')
