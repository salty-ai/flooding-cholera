# backend/app/routers/reports.py
"""Surveillance report endpoints."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
import io
from sqlalchemy.orm import Session

from app.database import get_db
from app.rate_limiter import limiter
from app.services.report_service import build_surveillance_report, render_report_pdf, render_report_csv

router = APIRouter(prefix="/api/reports", tags=["Reports"])


def _scope(lga_id, state):
    if lga_id:
        return {"level": "lga", "lga_id": lga_id}
    if state:
        return {"level": "state", "state": state}
    return {"level": "national"}


@router.get("/surveillance")
@limiter.limit("20/minute")
def surveillance_report(
    request: Request,
    period: str = Query("monthly", pattern="^(weekly|monthly)$"),
    lga_id: int | None = Query(None),
    state: str | None = Query(None),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
):
    return build_surveillance_report(db, period, _scope(lga_id, state), from_date, to_date)


@router.get("/surveillance/export")
@limiter.limit("10/minute")
def surveillance_export(
    request: Request,
    period: str = Query("monthly", pattern="^(weekly|monthly)$"),
    format: str = Query("pdf", pattern="^(pdf|csv)$"),
    lga_id: int | None = Query(None),
    state: str | None = Query(None),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
):
    report = build_surveillance_report(db, period, _scope(lga_id, state), from_date, to_date)
    if format == "pdf":
        return StreamingResponse(io.BytesIO(render_report_pdf(report)), media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=surveillance_report.pdf"})
    return StreamingResponse(io.BytesIO(render_report_csv(report)), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=surveillance_report.csv"})
