"""Health facility models."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.database import Base


class HealthFacility(Base):
    """Health facility (Hospital, Clinic, Primary Health Center, etc.)."""
    __tablename__ = "health_facilities"

    id = Column(Integer, primary_key=True, index=True)
    global_id = Column(String, index=True, nullable=True)
    name = Column(String, index=True)
    alternate_name = Column(String, nullable=True)
    type = Column(String, index=True)  # Primary, Secondary, Tertiary
    category = Column(String, index=True, nullable=True)  # Primary Health Center, General Hospital, etc.
    functional_status = Column(String, index=True, nullable=True)  # Functional, Partially Functional, Not Functional, Unknown

    state_name = Column(String, index=True, nullable=True)
    state_code = Column(String, nullable=True)
    lga_name = Column(String, index=True, nullable=True)
    lga_code = Column(String, nullable=True)
    ward_code = Column(String, nullable=True)

    lga_id = Column(Integer, ForeignKey("lgas.id"), nullable=True)

    # Geolocation
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # PostGIS point geometry
    location = Column(Geometry('POINT', srid=4326), nullable=True)

    # Relationships
    lga = relationship("LGA", back_populates="facilities")
