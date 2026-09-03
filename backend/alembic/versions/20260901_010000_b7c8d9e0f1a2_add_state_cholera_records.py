"""add state_cholera_records table (verified NCDC state-level tier)

Revision ID: b7c8d9e0f1a2
Revises: 5a6b7c8d9e0f
Create Date: 2026-09-01
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = '5a6b7c8d9e0f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'state_cholera_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('epi_week', sa.Integer(), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('month', sa.String(length=12), nullable=True),
        sa.Column('suspected_cases', sa.Integer(), nullable=True),
        sa.Column('deaths', sa.Integer(), nullable=True),
        sa.Column('cfr', sa.Float(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('monotonic_ok', sa.Boolean(), nullable=True),
        sa.Column('extraction_method', sa.String(length=40), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('state', 'year', 'epi_week', name='uq_state_year_week'),
    )
    op.create_index('ix_state_cholera_records_state', 'state_cholera_records', ['state'])
    op.create_index(op.f('ix_state_cholera_records_id'), 'state_cholera_records', ['id'])
    op.create_index('ix_state_cholera_year', 'state_cholera_records', ['year'])
    op.create_index('ix_state_cholera_records_year', 'state_cholera_records', ['year'])


def downgrade() -> None:
    op.drop_index('ix_state_cholera_records_year', table_name='state_cholera_records')
    op.drop_index('ix_state_cholera_year', table_name='state_cholera_records')
    op.drop_index(op.f('ix_state_cholera_records_id'), table_name='state_cholera_records')
    op.drop_index('ix_state_cholera_records_state', table_name='state_cholera_records')
    op.drop_table('state_cholera_records')
