"""drop unique constraint on lgas.name

Revision ID: 5a6b7c8d9e0f
Revises: 30471e8f27bc
Create Date: 2026-07-09 17:00:00+00:00

LGA names are NOT unique across Nigeria (e.g. "Bassa" exists in both Kogi
and Plateau states). The unique index on ``lgas.name`` blocks loading the
national 774-LGA boundary dataset. ``pcode`` is the true unique key (already
uniquely constrained), and lookups disambiguate by name + state. This drops
the unique index and recreates it as a plain btree index for lookup speed.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5a6b7c8d9e0f'
down_revision: Union[str, None] = '30471e8f27bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_lgas_name', table_name='lgas')
    op.create_index('ix_lgas_name', 'lgas', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_lgas_name', table_name='lgas')
    op.create_index('ix_lgas_name', 'lgas', ['name'], unique=True)
