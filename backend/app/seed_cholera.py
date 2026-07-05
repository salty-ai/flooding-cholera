"""Bulk-load the real nationwide cholera CSV."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal  # noqa: E402
from app.services.cholera_adapter import import_cholera_monthly  # noqa: E402

DEFAULT_CSV = os.path.join(
    os.path.dirname(__file__), "data", "cholera_real", "nigeria_cholera_2020_2025.csv"
)


def main(csv_path: str = DEFAULT_CSV):
    db = SessionLocal()
    try:
        result = import_cholera_monthly(db, csv_path)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV)
