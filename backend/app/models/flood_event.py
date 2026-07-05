"""Flood event model — historical flood events (Groundsource)."""
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
    geometry = Column(Geometry('GEOMETRY', srid=4326), nullable=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=True)
    area_km2 = Column(Float, nullable=True)
    data_source = Column(String(50), nullable=False, default="groundsource")
    created_at = Column(DateTime, default=datetime.utcnow)

    lga = relationship("LGA")

    def __repr__(self):
        return f"<FloodEvent(uuid={self.uuid}, lga_id={self.lga_id}, start={self.start_date})>"
