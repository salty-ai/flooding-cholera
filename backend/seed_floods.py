"""Bulk-load Google Groundsource flood events into PostGIS.

Runner analogous to ``seed_cholera.py``: downloads the public Groundsource
Parquet from Zenodo (no credentials required) and streams it through
``import_groundsource``, which filters to the Nigeria bbox and spatial-joins
each event to an LGA.

Usage:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python seed_floods.py                 # download + import
    PYTHONPATH=. python seed_floods.py /path/file.parquet  # import a local file
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal  # noqa: E402
from app.services.groundsource_importer import (  # noqa: E402
    download_groundsource,
    import_groundsource,
)

# Land the parquet under backend/data/ (the canonical data dir, holding
# cholera_real/ and boundaries/), not the repo-root data/ that the two-dirname
# seed_cholera.py pattern resolves to. One dirname = backend/, so
# backend/data/groundsource_2026.parquet — gitignored so the ~700MB download
# never enters version control.
DEFAULT_DEST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "groundsource_2026.parquet",
)


def main(parquet_path: str = DEFAULT_DEST, skip_download: bool = False) -> dict:
    # If a local path is supplied and exists, import it directly (manual-download
    # fallback for when the Zenodo record page format changes).
    if skip_download or (parquet_path != DEFAULT_DEST and os.path.exists(parquet_path)):
        print(f"Skipping download; importing {parquet_path}")
    else:
        os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
        parquet_path = download_groundsource(parquet_path)

    db = SessionLocal()
    try:
        result = import_groundsource(db, parquet_path)
        print(result)
        return result
    finally:
        db.close()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DEST
    main(arg)
