"""Risk calculation algorithm for cholera outbreak prediction."""
from datetime import date, timedelta
from typing import Optional, Dict, Any, List
import logging
import math
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import LGA, CaseReport, EnvironmentalData, RiskScore
from app.models.environmental import RiskLevel
from app.services.groundsource_importer import compute_flood_event_score_inputs

logger = logging.getLogger(__name__)


class RiskCalculator:
    """
    Calculate cholera risk scores based on multiple factors:
    - Flood indicators (NDWI, flood extent)
    - Rainfall data
    - Recent case counts
    - Vulnerability factors (water/sanitation coverage)
    """

    # v2.0 weights (satellite flood + flood events split the old 0.4 flood budget)
    W_FLOOD = 0.25
    W_FLOOD_EVENT = 0.20
    W_RAIN = 0.20
    W_CASES = 0.25
    W_VULNERABILITY = 0.10

    # Normalization parameters
    MAX_RAINFALL_MM = 200.0  # Max expected 7-day rainfall
    MAX_RECENT_CASES = 50    # Max cases for normalization
    NDWI_THRESHOLD = 0.3     # NDWI above this indicates water/flooding

    def __init__(self, db: Session):
        self.db = db

    def normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-1 range."""
        if value is None:
            return 0.0
        if max_val == min_val:
            return 0.0
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))

    def calculate_flood_score(
        self,
        ndwi: Optional[float],
        flood_extent_pct: Optional[float]
    ) -> float:
        """Calculate flood risk component."""
        if ndwi is None and flood_extent_pct is None:
            return 0.0

        score = 0.0

        # NDWI contribution (higher NDWI = more water)
        if ndwi is not None:
            # NDWI ranges from -1 to 1, water typically > 0.3
            ndwi_normalized = self.normalize(ndwi, -0.5, 0.8)
            score += ndwi_normalized * 0.6

        # Flood extent contribution
        if flood_extent_pct is not None:
            extent_normalized = self.normalize(flood_extent_pct, 0, 30)
            score += extent_normalized * 0.4

        return min(1.0, score)

    def calculate_rainfall_score(
        self,
        rainfall_7day_mm: Optional[float],
        rainfall_30day_mm: Optional[float] = None
    ) -> float:
        """Calculate rainfall risk component."""
        if rainfall_7day_mm is None:
            return 0.0

        # 7-day rainfall is primary indicator
        score = self.normalize(rainfall_7day_mm, 0, self.MAX_RAINFALL_MM)

        # 30-day adds context for sustained wet conditions
        if rainfall_30day_mm is not None:
            sustained_score = self.normalize(rainfall_30day_mm, 0, 500)
            score = score * 0.7 + sustained_score * 0.3

        return score

    def calculate_case_score(
        self,
        recent_cases: int,
        recent_deaths: int = 0
    ) -> float:
        """Calculate epidemiological risk component."""
        # Base score from case count
        case_score = self.normalize(recent_cases, 0, self.MAX_RECENT_CASES)

        # Death multiplier (deaths indicate severity)
        if recent_deaths > 0 and recent_cases > 0:
            cfr = recent_deaths / recent_cases
            # High CFR increases risk
            if cfr > 0.05:
                case_score = min(1.0, case_score * 1.3)

        return case_score

    def calculate_vulnerability_score(self, lga: LGA) -> float:
        """
        Calculate vulnerability based on infrastructure factors.
        Lower water/sanitation coverage = higher vulnerability.
        """
        water = lga.water_coverage_pct or 50
        sanitation = lga.sanitation_coverage_pct or 50

        # Invert: lower coverage = higher vulnerability
        water_vuln = 1 - (water / 100)
        sanitation_vuln = 1 - (sanitation / 100)

        return (water_vuln * 0.5 + sanitation_vuln * 0.5)

    def get_recent_cases(
        self,
        lga_id: int,
        days: int = 14
    ) -> Dict[str, int]:
        """Get case and death counts for recent period."""
        start_date = date.today() - timedelta(days=days)

        result = self.db.query(
            func.sum(CaseReport.new_cases),
            func.sum(CaseReport.deaths)
        ).filter(
            CaseReport.lga_id == lga_id,
            CaseReport.report_date >= start_date
        ).first()

        return {
            "cases": result[0] or 0,
            "deaths": result[1] or 0
        }

    def get_latest_environmental(self, lga_id: int) -> Optional[EnvironmentalData]:
        """Get most recent environmental data for an LGA."""
        return self.db.query(EnvironmentalData).filter(
            EnvironmentalData.lga_id == lga_id
        ).order_by(
            EnvironmentalData.observation_date.desc()
        ).first()

    def calculate_flood_event_score(
        self,
        lga_id: int,
        as_of_date: Optional[date] = None,
        lookback_days: int = 30,
    ) -> float:
        """Groundsource event-based flood score in [0,1]."""
        from app.models import FloodEvent
        as_of = as_of_date or date.today()
        start = as_of - timedelta(days=lookback_days)
        events = (
            self.db.query(FloodEvent)
            .filter(
                FloodEvent.lga_id == lga_id,
                FloodEvent.start_date >= start,
                FloodEvent.start_date <= as_of,
            )
            .order_by(FloodEvent.start_date.desc())
            .all()
        )
        if not events:
            return 0.0
        total = 0.0
        for e in events:
            dt = (as_of - e.start_date).days
            total += compute_flood_event_score_inputs(e.area_km2, dt)
        return 1.0 - math.exp(-total)

    def calculate_for_lga(
        self,
        lga_id: int,
        score_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calculate risk score for a single LGA.

        Returns dict with score, level, and component breakdowns.
        """
        if score_date is None:
            score_date = date.today()

        lga = self.db.query(LGA).filter(LGA.id == lga_id).first()
        if not lga:
            return {"error": f"LGA {lga_id} not found"}

        # Get input data
        env_data = self.get_latest_environmental(lga_id)
        case_data = self.get_recent_cases(lga_id)

        # Calculate component scores
        flood_score = 0.0
        rainfall_score = 0.0
        rainfall_mm = None
        ndwi = None

        if env_data:
            flood_score = self.calculate_flood_score(
                env_data.ndwi,
                env_data.flood_extent_pct
            )
            rainfall_score = self.calculate_rainfall_score(
                env_data.rainfall_7day_mm,
                env_data.rainfall_30day_mm
            )
            rainfall_mm = env_data.rainfall_7day_mm
            ndwi = env_data.ndwi

        case_score = self.calculate_case_score(
            case_data["cases"],
            case_data["deaths"]
        )

        vulnerability_score = self.calculate_vulnerability_score(lga)

        # Calculate weighted composite score
        total_score = (
            flood_score * self.W_FLOOD +
            rainfall_score * self.W_RAIN +
            case_score * self.W_CASES +
            vulnerability_score * self.W_VULNERABILITY
        )

        # Determine risk level
        level = RiskScore.get_level_from_score(total_score)

        # Create/update risk score record
        existing = self.db.query(RiskScore).filter(
            RiskScore.lga_id == lga_id,
            RiskScore.score_date == score_date
        ).first()

        if existing:
            existing.score = total_score
            existing.level = level.value if hasattr(level, 'value') else level
            existing.flood_score = flood_score
            existing.rainfall_score = rainfall_score
            existing.case_score = case_score
            existing.vulnerability_score = vulnerability_score
            existing.rainfall_mm = rainfall_mm
            existing.ndwi = ndwi
            existing.recent_cases = case_data["cases"]
            existing.recent_deaths = case_data["deaths"]
            risk_record = existing
        else:
            risk_record = RiskScore(
                lga_id=lga_id,
                score_date=score_date,
                score=total_score,
                level=level.value if hasattr(level, 'value') else level,
                flood_score=flood_score,
                rainfall_score=rainfall_score,
                case_score=case_score,
                vulnerability_score=vulnerability_score,
                rainfall_mm=rainfall_mm,
                ndwi=ndwi,
                recent_cases=case_data["cases"],
                recent_deaths=case_data["deaths"]
            )
            self.db.add(risk_record)

        self.db.commit()

        return {
            "lga_id": lga_id,
            "lga_name": lga.name,
            "score_date": score_date.isoformat(),
            "score": round(total_score, 4),
            "level": level.value if hasattr(level, 'value') else level,
            "components": {
                "flood": round(flood_score, 4),
                "rainfall": round(rainfall_score, 4),
                "cases": round(case_score, 4),
                "vulnerability": round(vulnerability_score, 4)
            },
            "raw_values": {
                "rainfall_7day_mm": rainfall_mm,
                "ndwi": ndwi,
                "recent_cases": case_data["cases"],
                "recent_deaths": case_data["deaths"]
            }
        }

    def calculate_all(
        self,
        score_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Calculate risk scores for all LGAs."""
        lgas = self.db.query(LGA).all()
        results = []

        for lga in lgas:
            try:
                result = self.calculate_for_lga(lga.id, score_date)
                results.append(result)
            except Exception as e:
                logger.error(f"Error calculating risk for LGA {lga.id}: {e}")
                results.append({
                    "lga_id": lga.id,
                    "lga_name": lga.name,
                    "error": str(e)
                })

        return results
