"""Admin endpoints for bulk data import."""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.rate_limiter import limiter
from app.seed_cholera import DEFAULT_CSV
from app.services.cholera_adapter import import_cholera_monthly
from app.services.groundsource_importer import import_groundsource

router = APIRouter(prefix="/api/admin/data", tags=["Admin"])


class PathBody(BaseModel):
    path: str | None = None


@router.post("/cholera-import")
@limiter.limit("2/minute")
def cholera_import(request: Request, body: PathBody = None, db: Session = Depends(get_db)):
    csv_path = body.path if body and body.path else DEFAULT_CSV
    if not os.path.exists(csv_path):
        raise HTTPException(404, f"CSV not found: {csv_path}")
    return import_cholera_monthly(db, csv_path)


@router.post("/groundsource-import")
@limiter.limit("1/minute")
def groundsource_import(request: Request, body: PathBody, db: Session = Depends(get_db)):
    if not body or not body.path or not os.path.exists(body.path):
        raise HTTPException(404, "parquet path required and must exist")
    return import_groundsource(db, body.path)
