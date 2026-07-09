"""Pydantic schemas for API validation and serialization."""
from datetime import datetime, date
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ============ LGA Schemas ============

class LGABase(BaseModel):
    """Base LGA schema."""
    name: str
    code: str
    population: Optional[int] = None
    area_sq_km: Optional[float] = None
    headquarters: Optional[str] = None


class LGACreate(LGABase):
    """Schema for creating an LGA."""
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    water_coverage_pct: float = 50.0
    sanitation_coverage_pct: float = 50.0
    health_facilities_count: int = 0


class LGAResponse(LGABase):
    """Schema for LGA response."""
    id: int
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    water_coverage_pct: Optional[float] = None
    sanitation_coverage_pct: Optional[float] = None
    health_facilities_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LGAWithGeometry(LGAResponse):
    """LGA response including GeoJSON geometry."""
    geometry: Optional[dict] = None  # GeoJSON geometry


class LGAListResponse(BaseModel):
    """Response containing list of LGAs with pagination."""
    total: int
    lgas: List[LGAResponse]
    skip: int = 0
    limit: int = 100


# ============ Case Report Schemas ============

class CaseReportBase(BaseModel):
    """Base case report schema."""
    lga_id: int
    report_date: date
    new_cases: int = 0
    deaths: int = 0


class CaseReportCreate(CaseReportBase):
    """Schema for creating a case report."""
    ward_id: Optional[int] = None
    epi_week: Optional[int] = None
    epi_year: Optional[int] = None
    suspected_cases: int = 0
    confirmed_cases: int = 0
    recoveries: int = 0
    cases_under_5: int = 0
    cases_5_to_14: int = 0
    cases_15_plus: int = 0
    cases_male: int = 0
    cases_female: int = 0
    source: str = "uploaded"
    source_file: Optional[str] = None
    notes: Optional[str] = None


class CaseReportResponse(CaseReportBase):
    """Schema for case report response."""
    id: int
    ward_id: Optional[int] = None
    epi_week: Optional[int] = None
    epi_year: Optional[int] = None
    suspected_cases: int = 0
    confirmed_cases: int = 0
    recoveries: int = 0
    cfr: Optional[float] = None
    source: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Environmental Data Schemas ============

class EnvironmentalDataBase(BaseModel):
    """Base environmental data schema."""
    lga_id: int
    observation_date: date


class EnvironmentalDataCreate(EnvironmentalDataBase):
    """Schema for creating environmental data."""
    rainfall_mm: Optional[float] = None
    rainfall_7day_mm: Optional[float] = None
    rainfall_30day_mm: Optional[float] = None
    ndwi: Optional[float] = None
    flood_extent_pct: Optional[float] = None
    flood_observed: bool = False
    lst_day: Optional[float] = None
    lst_night: Optional[float] = None
    ndvi: Optional[float] = None
    data_source: Optional[str] = None


class EnvironmentalDataResponse(EnvironmentalDataBase):
    """Schema for environmental data response."""
    id: int
    rainfall_mm: Optional[float] = None
    rainfall_7day_mm: Optional[float] = None
    ndwi: Optional[float] = None
    flood_extent_pct: Optional[float] = None
    flood_observed: bool = False
    lst_day: Optional[float] = None
    lst_night: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Risk Score Schemas ============

class RiskScoreBase(BaseModel):
    """Base risk score schema."""
    lga_id: int
    score_date: date
    score: float = Field(..., ge=0.0, le=1.0)
    level: str  # green, yellow, red


class RiskScoreCreate(RiskScoreBase):
    """Schema for creating a risk score."""
    flood_score: Optional[float] = None
    rainfall_score: Optional[float] = None
    case_score: Optional[float] = None
    vulnerability_score: Optional[float] = None
    rainfall_mm: Optional[float] = None
    ndwi: Optional[float] = None
    recent_cases: Optional[int] = None
    recent_deaths: Optional[int] = None


class RiskScoreResponse(RiskScoreBase):
    """Schema for risk score response."""
    id: int
    flood_score: Optional[float] = None
    rainfall_score: Optional[float] = None
    case_score: Optional[float] = None
    vulnerability_score: Optional[float] = None
    recent_cases: Optional[int] = None
    recent_deaths: Optional[int] = None
    calculated_at: datetime
    algorithm_version: str

    class Config:
        from_attributes = True


class RiskScoreWithLGA(RiskScoreResponse):
    """Risk score with LGA name included."""
    lga_name: str


# ============ Alert Schemas ============

class AlertBase(BaseModel):
    """Base alert schema."""
    lga_id: Optional[int] = None
    level: str = Field(..., pattern="^(green|yellow|red)$")
    severity: str = Field(..., pattern="^(info|warning|critical)$")
    type: str
    title: str = Field(..., max_length=200)
    message: str


class AlertCreate(AlertBase):
    """Schema for creating an alert."""
    triggered_by: Optional[dict] = None


class AlertResponse(AlertBase):
    """Schema for alert response."""
    id: int
    triggered_by: Optional[dict] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class AlertWithLGA(AlertResponse):
    """Alert response with LGA name included."""
    lga_name: Optional[str] = None


class AlertListResponse(BaseModel):
    """Response containing list of alerts with pagination."""
    total: int
    alerts: List[AlertWithLGA]
    skip: int = 0
    limit: int = 100


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""
    user_id: Optional[int] = None


# ============ Analytics Schemas ============

class TimeSeriesPoint(BaseModel):
    """Single point in time series."""
    date: date
    value: float


class LGAAnalytics(BaseModel):
    """Analytics data for an LGA."""
    lga_id: int
    lga_name: str
    cases_time_series: List[TimeSeriesPoint]
    deaths_time_series: List[TimeSeriesPoint]
    rainfall_time_series: List[TimeSeriesPoint]
    risk_time_series: List[TimeSeriesPoint]
    total_cases: int
    total_deaths: int
    avg_risk_score: float
    current_risk_level: str


# ============ Upload Schemas ============

class UploadResponse(BaseModel):
    """Response for file upload."""
    success: bool
    message: str
    records_imported: int = 0
    records_failed: int = 0
    errors: List[str] = []


# ============ GeoJSON Schemas ============

class GeoJSONFeature(BaseModel):
    """GeoJSON Feature."""
    type: str = "Feature"
    id: Optional[int] = None
    properties: dict
    geometry: dict


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]


# ============ Dashboard Schemas ============

class DashboardSummary(BaseModel):
    """Dashboard summary statistics."""
    total_lgas: int
    total_cases: int
    total_deaths: int
    lgas_high_risk: int
    lgas_medium_risk: int
    lgas_low_risk: int
    avg_rainfall_7day: float
    last_updated: Optional[datetime] = None
    # Real alert engine (replaces derived risk-level counts)
    active_alerts_count: int = 0
    alert_level: str = "green"
    # New integration data
    flood_events_count: int = 0
    # Date-awareness: the window actually queried
    applied_window_start: Optional[date] = None
    applied_window_end: Optional[date] = None
    max_data_date: Optional[date] = None


# ============ Alert Rule Schemas ============

class AlertRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    metric: str
    operator: str
    threshold: float
    window_days: int = 0
    severity: str = "warning"
    enabled: bool = True

class AlertRuleCreate(AlertRuleBase):
    pass

class AlertRuleResponse(AlertRuleBase):
    id: int
    class Config:
        from_attributes = True
