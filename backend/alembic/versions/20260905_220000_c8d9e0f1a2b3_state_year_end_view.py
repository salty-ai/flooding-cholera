"""add year-end state view for copilot-safe aggregation

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-09-05
"""
from alembic import op

revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None

VIEW = "state_cholera_year_end"

def upgrade():
    # One row per (state, year): the highest-epi-week analysis-safe cumulative
    # record. This is the ONLY correct way to get a state's yearly burden from
    # the cumulative SitRep series; summing weekly rows double-counts.
    op.execute(f"""
    CREATE OR REPLACE VIEW {VIEW} AS
    SELECT DISTINCT ON (state, year)
        state, year, epi_week AS year_end_epi_week, report_date,
        suspected_cases, deaths, cfr, confidence, source_url
    FROM state_cholera_records
    WHERE monotonic_ok IS TRUE
    ORDER BY state, year, epi_week DESC;
    """)
    op.execute(f"COMMENT ON VIEW {VIEW} IS 'Year-end (max epi-week, monotonic_ok) state cholera snapshot. Use this for any per-state or national yearly total. NEVER SUM state_cholera_records across weeks: it is cumulative.';")

def downgrade():
    op.execute(f"DROP VIEW IF EXISTS {VIEW};")
