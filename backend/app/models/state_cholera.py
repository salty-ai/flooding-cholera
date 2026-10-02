"""State-level cholera surveillance records.

Verified state-level cumulative records systematically extracted from the 84
successfully-parsed NCDC Cholera Situation Reports (2021-2025). One row =
one state's cumulative-to-date figures as of one report's publication.

This is the national data tier described in the manuscript: real, official,
state-resolution data. It deliberately does NOT redistribute state totals to
LGAs — the platform's LGA choropleth is populated only with observed pilot
data (four Cross River LGAs), and no synthetic LGA values are derived here.
"""
from sqlalchemy import Column, Integer, String, Float, Date, Boolean, Index, UniqueConstraint

from app.database import Base


class StateCholeraRecord(Base):
    __tablename__ = "state_cholera_records"
    __table_args__ = (
        UniqueConstraint("state", "year", "epi_week", name="uq_state_year_week"),
        Index("ix_state_cholera_year", "year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(100), nullable=False, index=True)  # Nigerian state or FCT
    year = Column(Integer, nullable=False)
    epi_week = Column(Integer, nullable=False)
    report_date = Column(Date, nullable=False)  # week start (Monday of that epi week, ISO)
    month = Column(String(12))

    # Cumulative year-to-date figures exactly as published by NCDC
    suspected_cases = Column(Integer, nullable=True)
    deaths = Column(Integer, nullable=True)
    cfr = Column(Float, nullable=True)

    # QC metadata from the extraction pipeline
    confidence = Column(String(20))        # 'high' | 'reassembled'
    monotonic_ok = Column(Boolean, default=True)  # False = within-state cumulative decrease
    extraction_method = Column(String(40))  # 'text_cluster_plaintext' | 'text_cluster_ocr'
    source_url = Column(String(500))        # exact NCDC sitrep PDF

    def __repr__(self):
        return (
            f"<StateCholeraRecord(state={self.state}, {self.year} "
            f"wk{self.epi_week}, cases={self.suspected_cases}, deaths={self.deaths})>"
        )
