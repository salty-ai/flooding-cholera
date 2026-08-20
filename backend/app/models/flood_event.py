"""Flood event model — historical flood events (Groundsource & NEMA)."""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base


class FloodEvent(Base):
    __tablename__ = "flood_events"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(64), unique=True, nullable=False, index=True)
    lga_id = Column(Integer, ForeignKey("lgas.id"), nullable=True, index=True)
    state_name = Column(String(100), nullable=True, index=True)
    lga_name = Column(String(100), nullable=True, index=True)

    geometry = Column(Geometry('GEOMETRY', srid=4326), nullable=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=True)
    area_km2 = Column(Float, nullable=True)

    # NEMA Human Impact Metrics
    year = Column(Integer, nullable=True, index=True)
    disaster_type = Column(String(100), nullable=True, default="Flood")
    affected_households = Column(Integer, nullable=True, default=0)
    affected_individuals = Column(Integer, nullable=True, default=0)
    displaced_households = Column(Integer, nullable=True, default=0)
    displaced_individuals = Column(Integer, nullable=True, default=0)
    injuries = Column(Integer, nullable=True, default=0)

    data_source = Column(String(50), nullable=False, default="groundsource")
    created_at = Column(DateTime, default=datetime.utcnow)

    lga = relationship("LGA")

    def __repr__(self):
        return f"<FloodEvent(uuid={self.uuid}, lga={self.lga_name}, state={self.state_name}, start={self.start_date})>"
