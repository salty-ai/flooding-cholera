"""Alert model for surveillance system notifications."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Alert(Base):
    """Alert model for system notifications and warnings.

    Alerts are triggered based on:
    - Flood warnings from satellite data
    - Case spikes (epidemiological events)
    - Rainfall thresholds
    - Risk score changes
    - Manual notifications
    """

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    lga_id = Column(Integer, ForeignKey("lgas.id"), nullable=True, index=True)

    # Alert classification
    level = Column(String(20), nullable=False, index=True)  # green, yellow, red
    severity = Column(String(20), nullable=False, index=True)  # info, warning, critical
    type = Column(String(50), nullable=False, index=True)  # flood_warning, case_spike, rainfall_alert, etc.

    # Alert content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Rule tracking
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=True, index=True)
    triggered_value = Column(Float, nullable=True)

    # Metadata
    triggered_by = Column(JSON, nullable=True)  # Conditions that triggered the alert

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, nullable=True)  # User ID who acknowledged
    resolved_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    lga = relationship("LGA", foreign_keys=[lga_id])

    def __repr__(self):
        return f"<Alert(id={self.id}, type={self.type}, severity={self.severity}, lga_id={self.lga_id})>"

    @property
    def is_acknowledged(self) -> bool:
        """Check if alert has been acknowledged."""
        return self.acknowledged_at is not None

    @property
    def is_resolved(self) -> bool:
        """Check if alert has been resolved."""
        return self.resolved_at is not None

    def acknowledge(self, user_id: int = None):
        """Mark alert as acknowledged."""
        if not self.acknowledged_at:
            self.acknowledged_at = datetime.utcnow()
            self.acknowledged_by = user_id

    def resolve(self):
        """Mark alert as resolved and inactive."""
        if not self.resolved_at:
            self.resolved_at = datetime.utcnow()
            self.is_active = False
