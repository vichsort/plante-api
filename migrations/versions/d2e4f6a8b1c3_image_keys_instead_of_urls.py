"""image keys instead of public URLs

The image columns held the full public S3 URL (`https://<bucket>.s3.<region>.amazonaws.com/<key>`):
anyone with it saw the photo, and changing storage broke every stored row. They now hold only the
key, and the API signs a link when it answers. The garden column is renamed to say so
(`primary_image_url` -> `primary_image_key`).

The downgrade only renames the column back: the rows stay keys (the bucket and region of the old
URLs are not known here).

Revision ID: d2e4f6a8b1c3
Revises: c9d1e3f5a7b2
Create Date: 2026-10-23 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2e4f6a8b1c3'
down_revision: str | None = 'c9d1e3f5a7b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Only our own S3 URLs: anything else is left as it is
_S3_URL = r'^https?://[^/]+\.amazonaws\.com/'
_COLUMNS = (
    ('identifications', 'image_key'),
    ('health_records', 'image_key'),
    ('plant_reference_images', 'storage_key'),
    ('user_plants', 'primary_image_key'),
)


def upgrade() -> None:
    op.alter_column('user_plants', 'primary_image_url', new_column_name='primary_image_key')
    for table, column in _COLUMNS:
        op.execute(
            f"UPDATE {table} SET {column} = regexp_replace({column}, '{_S3_URL}', '') WHERE {column} ~ '{_S3_URL}'"
        )
    op.execute(
        "UPDATE training_health_samples SET reference_image_keys = ("
        f" SELECT coalesce(json_agg(regexp_replace(item, '{_S3_URL}', '')), '[]'::json)"
        " FROM json_array_elements_text(reference_image_keys) AS item"
        ")"
    )


def downgrade() -> None:
    op.alter_column('user_plants', 'primary_image_key', new_column_name='primary_image_url')
