"""Load nationwide Nigerian LGA boundaries from HDX COD-AB ADM2 GeoJSON."""
import json
import logging
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import shape, MultiPolygon, Polygon

from app.models import LGA

logger = logging.getLogger(__name__)


def _to_multipolygon(geom):
    s = shape(geom)
    if isinstance(s, Polygon):
        s = MultiPolygon([s])
    return s


def load_national_lgas(db: Session, geojson_path: str) -> int:
    """Upsert all 774 LGAs from the ADM2 GeoJSON. Returns count upserted."""
    with open(geojson_path, "r") as f:
        gj = json.load(f)

    count = 0
    for feat in gj.get("features", []):
        p = feat["properties"]
        pcode = p.get("adm2_pcode")
        name = p.get("adm2_name")
        if not pcode or not name:
            continue

        existing = db.query(LGA).filter_by(pcode=pcode).first()
        geom = _to_multipolygon(feat["geometry"])
        values = dict(
            name=name,
            code=pcode,
            pcode=pcode,
            state=p.get("adm1_name"),
            area_sq_km=p.get("area_sqkm"),
            centroid_lat=p.get("center_lat"),
            centroid_lon=p.get("center_lon"),
            geometry=from_shape(geom, srid=4326),
        )
        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
        else:
            db.add(LGA(**values))
        count += 1

    db.commit()
    logger.info(f"Loaded {count} national LGAs")
    return count
