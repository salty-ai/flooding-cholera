"""create alerts table

Revision ID: a1b2c3d4e5f6
Revises: 6c9553630121
Create Date: 2026-07-06 00:12:00+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6c9553630121'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('lga_id', sa.Integer, sa.ForeignKey('lgas.id'), nullable=True),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('triggered_by', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('acknowledged_at', sa.DateTime, nullable=True),
        sa.Column('acknowledged_by', sa.Integer, nullable=True),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)
    op.create_index('ix_alerts_lga_id', 'alerts', ['lga_id'])
    op.create_index('ix_alerts_level', 'alerts', ['level'])
    op.create_index('ix_alerts_severity', 'alerts', ['severity'])
    op.create_index('ix_alerts_type', 'alerts', ['type'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])
    op.create_index('ix_alerts_is_active', 'alerts', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_alerts_is_active', table_name='alerts')
    op.drop_index('ix_alerts_created_at', table_name='alerts')
    op.drop_index('ix_alerts_type', table_name='alerts')
    op.drop_index('ix_alerts_severity', table_name='alerts')
    op.drop_index('ix_alerts_level', table_name='alerts')
    op.drop_index('ix_alerts_lga_id', table_name='alerts')
    op.drop_index(op.f('ix_alerts_id'), table_name='alerts')
    op.drop_table('alerts')
