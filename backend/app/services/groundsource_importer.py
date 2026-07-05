"""Import Google Groundsource flood events into PostGIS."""
import logging
import math
import os
from datetime import date, datetime
from typing import Optional, Dict

import pyarrow.parquet as pq
from shapely import wkb
from geoalchemy2.shape import from_shape
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LGA, FloodEvent

logger = logging.getLogger(__name__)
settings = get_settings()


def compute_flood_event_score_inputs(area_km2: Optional[float], days_since_start: float) -> float:
    """Per-event value = recency_weight * area_weight. Pure (unit-tested)."""
    if area_km2 is None or area_km2 <= 0:
        area_w = 0.0
    else:
        area_w = max(0.0, min(1.0, area_km2 / 500.0))
    recency_w = math.exp(-max(0.0, days_since_start) / 14.0)
    return recency_w * area_w


def download_groundsource(dest_path: str, url: str = "https://zenodo.org/records/18647054") -> str:
    """Download the Groundsource Parquet from Zenodo if not present."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1_000_000:
        logger.info(f"Groundsource parquet already present at {dest_path}")
        return dest_path
    import requests
    logger.info(f"Downloading Groundsource parquet from {url}")
    # Zenodo record page lists the parquet file; resolve the direct file URL.
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    # Find the parquet download link in the record page
    import re
    m = re.search(r'href="([^"]+\.parquet)"', resp.text)
    if not m:
        raise RuntimeError("Could not locate parquet file URL on Zenodo record page")
    file_url = m.group(1)
    if file_url.startswith("/"):
        file_url = "https://zenodo.org" + file_url
    with requests.get(file_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    logger.info(f"Downloaded {os.path.getsize(dest_path)} bytes to {dest_path}")
    return dest_path


def _parse_date(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # ISO datetime fallback (e.g. "2024-06-01T00:00:00Z")
    iso = s[:-1] if s.endswith("Z") else s
    try:
        return datetime.fromisoformat(iso).date()
    except ValueError:
        return None


def import_groundsource(
    db: Session,
    parquet_path: str,
    bbox: Optional[Dict[str, float]] = None,
    batch_size: int = 5000,
) -> Dict[str, int]:
    """Stream-read Groundsource parquet, filter to bbox, spatial-join to LGAs, upsert."""
    bbox = bbox or settings.nigeria_bbox
    min_lon, max_lon = bbox["min_lon"], bbox["max_lon"]
    min_lat, max_lat = bbox["min_lat"], bbox["max_lat"]

    # Load LGA geometries once for in-memory spatial join
    lgas = db.query(LGA.id, LGA.geometry, LGA.name).all()
    from geoalchemy2.shape import to_shape
    lga_shapes = []
    for lga_id, geom, _name in lgas:
        if geom is None:
            continue
        try:
            lga_shapes.append((lga_id, to_shape(geom)))
        except Exception:
            continue

    pf = pq.ParquetFile(parquet_path)
    imported = skipped = no_lga = 0

    for batch in pf.iter_batches(batch_size=batch_size):
        df = batch.to_pandas()
        existing_uuids = set(
            r[0] for r in db.query(FloodEvent.uuid).filter(
                FloodEvent.uuid.in_(df["uuid"].tolist())
            ).all()
        )
        for _, row in df.iterrows():
            uuid = row["uuid"]
            if uuid in existing_uuids:
                skipped += 1
                continue
            try:
                geom = wkb.loads(row["geometry"])
            except Exception:
                skipped += 1
                continue
            # bbox prefilter
            if geom.is_empty:
                skipped += 1
                continue
            minx, miny, maxx, maxy = geom.bounds
            if not (minx <= max_lon and maxx >= min_lon and miny <= max_lat and maxy >= min_lat):
                skipped += 1
                continue
            start = _parse_date(row.get("start_date"))
            end = _parse_date(row.get("end_date")) or start
            if not start:
                skipped += 1
                continue
            lga_id = None
            for lid, lshape in lga_shapes:
                if geom.intersects(lshape):
                    lga_id = lid
                    break
            if lga_id is None:
                no_lga += 1
            else:
                imported += 1
            duration = None
            if end and start and end >= start:
                duration = (end - start).days + 1
            fe = FloodEvent(
                uuid=uuid,
                lga_id=lga_id,
                geometry=from_shape(geom, srid=4326),
                start_date=start,
                end_date=end,
                duration_days=duration,
                area_km2=float(row["area_km2"]) if row.get("area_km2") is not None else None,
                data_source="groundsource",
            )
            db.add(fe)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        logger.info(f"Groundsource batch: imported={imported} skipped={skipped} no_lga={no_lga}")

    logger.info(f"Groundsource import complete: imported={imported} skipped={skipped} no_lga={no_lga}")
    return {"imported": imported, "skipped": skipped, "no_lga": no_lga}
