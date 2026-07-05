"""Alert rule definitions consumed by the alert engine."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)
    metric = Column(String(50), nullable=False)        # risk_score|flood_event_count|new_cases|cfr
    operator = Column(String(4), nullable=False)        # >|>=|<|<=
    threshold = Column(Float, nullable=False)
    window_days = Column(Integer, nullable=False, default=0)
    severity = Column(String(20), nullable=False, default="warning")
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AlertRule(id={self.id}, name={self.name})>"
