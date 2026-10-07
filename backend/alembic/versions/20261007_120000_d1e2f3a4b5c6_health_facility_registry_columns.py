"""add eHealth Africa health facility registry columns

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-10-07

Adds the columns backing the HealthFacility model extension for the
eHealth Africa master facility list (via UN OCHA HDX):
global_id, alternate_name, category, functional_status, state_name,
state_code, lga_name, lga_code, ward_code. latitude/longitude/location
already exist from the initial schema.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "health_facilities"

COLUMNS = [
    sa.Column("global_id", sa.String(), nullable=True),
    sa.Column("alternate_name", sa.String(), nullable=True),
    sa.Column("category", sa.String(), nullable=True),
    sa.Column("functional_status", sa.String(), nullable=True),
    sa.Column("state_name", sa.String(), nullable=True),
    sa.Column("state_code", sa.String(), nullable=True),
    sa.Column("lga_name", sa.String(), nullable=True),
    sa.Column("lga_code", sa.String(), nullable=True),
    sa.Column("ward_code", sa.String(), nullable=True),
]


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns(TABLE)}
    for col in COLUMNS:
        if col.name not in existing:
            op.add_column(TABLE, col)


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns(TABLE)}
    for col in reversed(COLUMNS):
        if col.name in existing:
            op.drop_column(TABLE, col.name)
