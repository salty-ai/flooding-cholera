"""
Bulk import 46,146 FMOH National Health Facility Registry records from GeoJSON.
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import LGA, HealthFacility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FMOH_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "external_real",
    "fmoh_nigeriahealthfacilities.json.json",
)


def seed_fmoh_facilities(db: Session, json_path: str = FMOH_JSON_PATH):
    if not os.path.exists(json_path):
        logger.error(f"FMOH GeoJSON file not found at {json_path}")
        return

    logger.info(f"Loading FMOH health facilities from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    logger.info(f"Loaded {len(features)} total facility features from GeoJSON.")

    # Build LGA name & state lookup
    lgas = db.query(LGA).all()
    lga_lookup = {}
    for lga in lgas:
        # Match (lga_name.lower(), state.lower()) -> id
        if lga.name and lga.state:
            key = (lga.name.lower().strip(), lga.state.lower().strip())
            lga_lookup[key] = lga.id
            # Also key by lga_name alone
            lga_lookup[lga.name.lower().strip()] = lga.id

    # Check existing count
    existing_count = db.query(HealthFacility).count()
    if existing_count > 40000:
        logger.info(f"Database already contains {existing_count} facilities. Skipping re-import.")
        return

    # Truncate or clean existing if small/seeded
    db.query(HealthFacility).delete()
    db.commit()

    objects = []
    batch_size = 2000

    for i, feat in enumerate(features):
        props = feat.get("properties", {})
        geometry = feat.get("geometry", {})
        coords = geometry.get("coordinates") if geometry else None

        lon, lat = None, None
        point_geom = None
        if coords and len(coords) >= 2:
            lon, lat = float(coords[0]), float(coords[1])
            try:
                point_geom = from_shape(Point(lon, lat), srid=4326)
            except Exception:
                point_geom = None

        lga_name = props.get("lga_name")
        state_name = props.get("state_name")
        lga_id = None
        if lga_name:
            ln = str(lga_name).lower().strip()
            sn = str(state_name).lower().strip() if state_name else ""
            if (ln, sn) in lga_lookup:
                lga_id = lga_lookup[(ln, sn)]
            elif ln in lga_lookup:
                lga_id = lga_lookup[ln]

        fac = HealthFacility(
            global_id=props.get("global_id"),
            name=props.get("name") or "Unnamed Facility",
            alternate_name=props.get("alternate_name"),
            type=props.get("type") or "Primary",
            category=props.get("category") or "Primary Health Center",
            functional_status=props.get("functional_status") or "Functional",
            state_name=props.get("state_name"),
            state_code=props.get("state_code"),
            lga_name=props.get("lga_name"),
            lga_code=str(props.get("lga_code")) if props.get("lga_code") is not None else None,
            ward_code=str(props.get("ward_code")) if props.get("ward_code") is not None else None,
            lga_id=lga_id,
            latitude=lat,
            longitude=lon,
            location=point_geom,
        )
        objects.append(fac)

        if len(objects) >= batch_size:
            db.bulk_save_objects(objects)
            db.commit()
            logger.info(f"Imported batch {i + 1}/{len(features)} facilities...")
            objects = []

    if objects:
        db.bulk_save_objects(objects)
        db.commit()

    total_now = db.query(HealthFacility).count()
    logger.info(f"Successfully imported {total_now} FMOH health facilities into database.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_fmoh_facilities(db)
    finally:
        db.close()
