"""add state pcode to lgas

Revision ID: 6c9553630121
Revises: a56dfd1b07a8
Create Date: 2026-07-05 09:24:20.103210+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c9553630121'
down_revision: Union[str, None] = 'a56dfd1b07a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('lgas', sa.Column('state', sa.String(100), nullable=True))
    op.add_column('lgas', sa.Column('pcode', sa.String(20), nullable=True))
    op.create_index('ix_lgas_state', 'lgas', ['state'])
    op.create_unique_constraint('uq_lgas_pcode', 'lgas', ['pcode'])


def downgrade():
    op.drop_constraint('uq_lgas_pcode', 'lgas')
    op.drop_index('ix_lgas_state', 'lgas')
    op.drop_column('lgas', 'pcode')
    op.drop_column('lgas', 'state')
