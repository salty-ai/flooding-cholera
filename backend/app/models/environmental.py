"""Environmental data and risk score models."""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class RiskLevel(str, enum.Enum):
    """Risk level classification."""
    GREEN = "green"    # Low risk: < 0.3
    YELLOW = "yellow"  # Medium risk: 0.3 - 0.6
    RED = "red"        # High risk: > 0.6


class EnvironmentalData(Base):
    """Environmental/satellite data for an LGA on a specific date."""

    __tablename__ = "environmental_data"

    id = Column(Integer, primary_key=True, index=True)
    lga_id = Column(Integer, ForeignKey("lgas.id"), nullable=False, index=True)

    # Date of observation
    observation_date = Column(Date, nullable=False, index=True)

    # Rainfall data (NASA GPM)
    rainfall_mm = Column(Float, nullable=True)  # Daily precipitation in mm
    rainfall_7day_mm = Column(Float, nullable=True)  # 7-day cumulative
    rainfall_30day_mm = Column(Float, nullable=True)  # 30-day cumulative

    # Flood indicators (Sentinel-1, MODIS)
    ndwi = Column(Float, nullable=True)  # Normalized Difference Water Index (-1 to 1)
    flood_extent_pct = Column(Float, nullable=True)  # % of LGA area flooded
    flood_observed = Column(Boolean, default=False)

    # Temperature (MODIS LST)
    lst_day = Column(Float, nullable=True)  # Land surface temp day (Celsius)
    lst_night = Column(Float, nullable=True)  # Land surface temp night (Celsius)

    # Vegetation (for water body detection)
    ndvi = Column(Float, nullable=True)  # Normalized Difference Vegetation Index

    # Data quality
    cloud_cover_pct = Column(Float, nullable=True)
    data_source = Column(String(50), nullable=True)  # GEE, NASA_GPM, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lga = relationship("LGA", back_populates="environmental_data")

    def __repr__(self):
        return f"<EnvironmentalData(lga_id={self.lga_id}, date={self.observation_date})>"


class RiskScore(Base):
    """Calculated risk score for an LGA."""

    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    lga_id = Column(Integer, ForeignKey("lgas.id"), nullable=False, index=True)

    # Score date
    score_date = Column(Date, nullable=False, index=True)

    # Overall risk score (0-1)
    score = Column(Float, nullable=False)
    level = Column(String(20), nullable=False)  # green, yellow, red

    # Component scores (0-1 normalized)
    flood_score = Column(Float, nullable=True)
    rainfall_score = Column(Float, nullable=True)
    case_score = Column(Float, nullable=True)
    vulnerability_score = Column(Float, nullable=True)

    # Raw values used in calculation
    rainfall_mm = Column(Float, nullable=True)
    ndwi = Column(Float, nullable=True)
    recent_cases = Column(Integer, nullable=True)
    recent_deaths = Column(Integer, nullable=True)
    flood_event_score = Column(Float, nullable=True)
    recent_flood_events = Column(Integer, nullable=True)

    # Calculation metadata
    calculated_at = Column(DateTime, default=datetime.utcnow)
    algorithm_version = Column(String(20), default="2.0")
    notes = Column(Text, nullable=True)

    # Relationships
    lga = relationship("LGA", back_populates="risk_scores")

    def __repr__(self):
        return f"<RiskScore(lga_id={self.lga_id}, date={self.score_date}, score={self.score}, level={self.level})>"

    @classmethod
    def get_level_from_score(cls, score: float) -> str:
        """Determine risk level from score."""
        if score < 0.3:
            return RiskLevel.GREEN
        elif score < 0.6:
            return RiskLevel.YELLOW
        else:
            return RiskLevel.RED
