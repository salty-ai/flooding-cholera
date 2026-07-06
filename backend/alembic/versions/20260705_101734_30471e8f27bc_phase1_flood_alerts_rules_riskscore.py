"""phase1 flood alerts rules riskscore

Revision ID: 30471e8f27bc
Revises: a1b2c3d4e5f6
Create Date: 2026-07-05 10:17:34.449060+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision: str = '30471e8f27bc'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'flood_events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('uuid', sa.String(64), nullable=False, unique=True),
        sa.Column('lga_id', sa.Integer, sa.ForeignKey('lgas.id'), nullable=True),
        sa.Column('geometry', Geometry('GEOMETRY', srid=4326), nullable=True),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('duration_days', sa.Integer, nullable=True),
        sa.Column('area_km2', sa.Float, nullable=True),
        sa.Column('data_source', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_flood_events_uuid', 'flood_events', ['uuid'], unique=True)
    op.create_index('ix_flood_events_lga_id', 'flood_events', ['lga_id'])
    op.create_index('ix_flood_events_start_date', 'flood_events', ['start_date'])
    op.create_index('ix_flood_events_lga_start', 'flood_events', ['lga_id', 'start_date'])
    op.execute("CREATE INDEX ix_flood_events_geometry ON flood_events USING GIST (geometry)")

    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('description', sa.String(500)),
        sa.Column('metric', sa.String(50), nullable=False),
        sa.Column('operator', sa.String(4), nullable=False),
        sa.Column('threshold', sa.Float, nullable=False),
        sa.Column('window_days', sa.Integer, nullable=False, server_default='0'),
        sa.Column('severity', sa.String(20), nullable=False, server_default='warning'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # NOTE: The original brief also added `lga_id` and `message` columns to `alerts`
    # (plus `ix_alerts_lga_id`). Those already exist on the live `alerts` table
    # (lga_id FK -> lgas.id with ix_alerts_lga_id, and message Text NOT NULL),
    # so they are intentionally omitted here to avoid duplicate-column errors.
    op.add_column('alerts', sa.Column('rule_id', sa.Integer, sa.ForeignKey('alert_rules.id'), nullable=True))
    op.add_column('alerts', sa.Column('triggered_value', sa.Float, nullable=True))
    op.create_index('ix_alerts_rule_id', 'alerts', ['rule_id'])

    op.add_column('risk_scores', sa.Column('flood_event_score', sa.Float, nullable=True))
    op.add_column('risk_scores', sa.Column('recent_flood_events', sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column('risk_scores', 'recent_flood_events')
    op.drop_column('risk_scores', 'flood_event_score')

    op.drop_index('ix_alerts_rule_id', 'alerts')
    op.drop_column('alerts', 'triggered_value')
    op.drop_column('alerts', 'rule_id')
    # NOTE: lga_id / message / ix_alerts_lga_id are NOT dropped — they pre-existed
    # this migration and are owned by an earlier schema.

    op.drop_table('alert_rules')

    op.execute("DROP INDEX IF EXISTS ix_flood_events_geometry")
    op.drop_index('ix_flood_events_lga_start', 'flood_events')
    op.drop_index('ix_flood_events_start_date', 'flood_events')
    op.drop_index('ix_flood_events_lga_id', 'flood_events')
    op.drop_index('ix_flood_events_uuid', 'flood_events')
    op.drop_table('flood_events')
