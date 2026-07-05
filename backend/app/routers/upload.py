"""Data upload endpoints."""
import os
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.orm import Session
import pandas as pd

from app.database import get_db
from app.models import LGA, CaseReport
from app.schemas import UploadResponse
from app.services.data_importer import DataImporter
from app.services.risk_calculator import RiskCalculator
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/upload", tags=["Upload"])

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_data(
    request: Request,
    file: UploadFile = File(...),
    data_type: str = Form("cases", description="Type of data: cases, environmental"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Upload CSV or Excel file with case/environmental data."""
    # Validate file type
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Read file content with size limit
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # Parse file
        if file_ext == ".csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        # Import data
        importer = DataImporter(db)

        if data_type == "cases":
            result = importer.import_case_data(df, source_file=file.filename)
        elif data_type == "environmental":
            result = importer.import_environmental_data(df, source_file=file.filename)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data_type: {data_type}. Use 'cases' or 'environmental'"
            )

        # Trigger risk recalculation in background
        if background_tasks and result["records_imported"] > 0:
            background_tasks.add_task(recalculate_risks, db)

        return UploadResponse(
            success=True,
            message=f"Successfully imported {result['records_imported']} records",
            records_imported=result["records_imported"],
            records_failed=result["records_failed"],
            errors=result.get("errors", [])
        )

    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/recalculate-risks")
@limiter.limit("5/minute")
def trigger_risk_recalculation(
    request: Request,
    lga_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Manually trigger risk recalculation."""
    calculator = RiskCalculator(db)

    if lga_id:
        lga = db.query(LGA).filter(LGA.id == lga_id).first()
        if not lga:
            raise HTTPException(status_code=404, detail="LGA not found")
        results = [calculator._persist_and_dict(lga)]
    else:
        results = calculator.calculate_all()

    return {
        "success": True,
        "message": f"Recalculated risk scores for {len(results)} LGAs",
        "results": results
    }


def recalculate_risks(db: Session):
    """Background task to recalculate all risk scores."""
    calculator = RiskCalculator(db)
    calculator.calculate_all()


@router.get("/template/{data_type}")
@limiter.limit("60/minute")
def get_upload_template(request: Request, data_type: str):
    """Get CSV template for data upload."""
    if data_type == "cases":
        return {
            "description": "Template for cholera case data upload",
            "columns": [
                {"name": "lga_name", "type": "string", "required": True, "description": "Name of the LGA"},
                {"name": "report_date", "type": "date (YYYY-MM-DD)", "required": True, "description": "Date of report"},
                {"name": "new_cases", "type": "integer", "required": True, "description": "Number of new cases"},
                {"name": "deaths", "type": "integer", "required": False, "description": "Number of deaths"},
                {"name": "suspected_cases", "type": "integer", "required": False, "description": "Number of suspected cases"},
                {"name": "confirmed_cases", "type": "integer", "required": False, "description": "Number of confirmed cases"},
                {"name": "recoveries", "type": "integer", "required": False, "description": "Number of recoveries"},
                {"name": "ward_name", "type": "string", "required": False, "description": "Ward name if available"}
            ],
            "example_row": {
                "lga_name": "Calabar Municipal",
                "report_date": "2024-01-15",
                "new_cases": 5,
                "deaths": 0,
                "suspected_cases": 3,
                "confirmed_cases": 2
            }
        }
    elif data_type == "environmental":
        return {
            "description": "Template for environmental data upload",
            "columns": [
                {"name": "lga_name", "type": "string", "required": True, "description": "Name of the LGA"},
                {"name": "observation_date", "type": "date (YYYY-MM-DD)", "required": True, "description": "Date of observation"},
                {"name": "rainfall_mm", "type": "float", "required": False, "description": "Daily rainfall in mm"},
                {"name": "flood_observed", "type": "boolean", "required": False, "description": "Was flooding observed?"},
                {"name": "ndwi", "type": "float (-1 to 1)", "required": False, "description": "Normalized Difference Water Index"}
            ],
            "example_row": {
                "lga_name": "Calabar Municipal",
                "observation_date": "2024-01-15",
                "rainfall_mm": 25.5,
                "flood_observed": False,
                "ndwi": 0.2
            }
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid data_type. Use 'cases' or 'environmental'")
