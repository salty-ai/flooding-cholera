"""Risk calculation algorithm for cholera outbreak prediction."""
from datetime import date, timedelta
from typing import Optional, Dict, Any, List
import logging
import math
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import LGA, CaseReport, EnvironmentalData, RiskScore, FloodEvent
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

    def _latest_data_date(self) -> date:
        """Most recent CaseReport.report_date, or today if there is no case data.

        Risk is anchored to the latest-available data date (not the wall-clock
        today) so that the 14-day recent-cases window actually overlaps real
        data when ingestion lags behind the current date — consistent with the
        dashboard endpoint's latest-available window.
        """
        latest = self.db.query(func.max(CaseReport.report_date)).scalar()
        return latest or date.today()

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
        days: int = 14,
        as_of: Optional[date] = None
    ) -> Dict[str, int]:
        """Get case and death counts for the recent period ending on as_of."""
        as_of = as_of or date.today()
        start_date = as_of - timedelta(days=days)

        result = self.db.query(
            func.sum(CaseReport.new_cases),
            func.sum(CaseReport.deaths)
        ).filter(
            CaseReport.lga_id == lga_id,
            CaseReport.report_date >= start_date,
            CaseReport.report_date <= as_of
        ).first()

        return {
            "cases": result[0] or 0,
            "deaths": result[1] or 0
        }

    def get_latest_environmental(
        self,
        lga_id: int,
        as_of: Optional[date] = None
    ) -> Optional[EnvironmentalData]:
        """Get most recent environmental data for an LGA on or before as_of."""
        as_of = as_of or date.today()
        return self.db.query(EnvironmentalData).filter(
            EnvironmentalData.lga_id == lga_id,
            EnvironmentalData.observation_date <= as_of
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
        lga,
        as_of_date: Optional[date] = None
    ) -> tuple:
        """
        Calculate risk score for a single LGA.

        Returns a 3-tuple: (overall_score, level, components).
        Does NOT persist a RiskScore row — callers (calculate_all / _persist_and_dict)
        are responsible for upserting the row.

        v2.0 weights fold in the flood_event_score component.
        """
        as_of = as_of_date or self._latest_data_date()

        env = self.get_latest_environmental(lga.id, as_of=as_of)
        ndwi = env.ndwi if env else None
        flood_extent = env.flood_extent_pct if env else None
        rainfall_7 = env.rainfall_7day_mm if env else None
        rainfall_30 = env.rainfall_30day_mm if env else None
        rainfall_mm = rainfall_7

        recent = self.get_recent_cases(lga.id, days=14, as_of=as_of)

        flood_score = self.calculate_flood_score(ndwi, flood_extent)
        flood_event_score = self.calculate_flood_event_score(
            lga.id, as_of_date=as_of
        )
        rainfall_score = self.calculate_rainfall_score(rainfall_7, rainfall_30)
        case_score = self.calculate_case_score(
            recent["cases"], recent["deaths"]
        )
        vulnerability_score = self.calculate_vulnerability_score(lga)

        overall = (
            self.W_FLOOD * flood_score
            + self.W_FLOOD_EVENT * flood_event_score
            + self.W_RAIN * rainfall_score
            + self.W_CASES * case_score
            + self.W_VULNERABILITY * vulnerability_score
        )
        overall = max(0.0, min(1.0, overall))
        level = RiskScore.get_level_from_score(overall)

        recent_flood_events = (
            self.db.query(FloodEvent)
            .filter(
                FloodEvent.lga_id == lga.id,
                FloodEvent.start_date >= as_of - timedelta(days=30),
                FloodEvent.start_date <= as_of,
            )
            .count()
        )

        components = {
            "flood_score": flood_score,
            "flood_event_score": flood_event_score,
            "rainfall_score": rainfall_score,
            "case_score": case_score,
            "vulnerability_score": vulnerability_score,
            "recent_flood_events": recent_flood_events,
            "rainfall_mm": rainfall_mm,
            "ndwi": ndwi,
            "recent_cases": recent["cases"],
            "recent_deaths": recent["deaths"],
        }
        return overall, level, components

    def _persist_and_dict(
        self,
        lga,
        score_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calculate, upsert a RiskScore row (v2.0 fields), commit, and return
        an API-shaped dict. Shared by calculate_all (loop body) and the
        single-LGA recalc endpoint.
        """
        score_date = score_date or self._latest_data_date()

        overall, level, components = self.calculate_for_lga(
            lga, as_of_date=score_date
        )
        level_str = level.value if hasattr(level, "value") else level

        existing = self.db.query(RiskScore).filter(
            RiskScore.lga_id == lga.id,
            RiskScore.score_date == score_date,
        ).first()

        if existing:
            existing.score = overall
            existing.level = level_str
            existing.flood_score = components["flood_score"]
            existing.rainfall_score = components["rainfall_score"]
            existing.case_score = components["case_score"]
            existing.vulnerability_score = components["vulnerability_score"]
            existing.flood_event_score = components["flood_event_score"]
            existing.recent_flood_events = components["recent_flood_events"]
            existing.rainfall_mm = components["rainfall_mm"]
            existing.ndwi = components["ndwi"]
            existing.recent_cases = components["recent_cases"]
            existing.recent_deaths = components["recent_deaths"]
            existing.algorithm_version = "2.0"
            risk_record = existing
        else:
            risk_record = RiskScore(
                lga_id=lga.id,
                score_date=score_date,
                score=overall,
                level=level_str,
                flood_score=components["flood_score"],
                rainfall_score=components["rainfall_score"],
                case_score=components["case_score"],
                vulnerability_score=components["vulnerability_score"],
                flood_event_score=components["flood_event_score"],
                recent_flood_events=components["recent_flood_events"],
                rainfall_mm=components["rainfall_mm"],
                ndwi=components["ndwi"],
                recent_cases=components["recent_cases"],
                recent_deaths=components["recent_deaths"],
                algorithm_version="2.0",
            )
            self.db.add(risk_record)

        self.db.commit()

        return {
            "lga_id": lga.id,
            "lga_name": lga.name,
            "score_date": score_date.isoformat(),
            "score": round(overall, 4),
            "level": level_str,
            "components": {
                "flood": round(components["flood_score"], 4),
                "flood_event": round(components["flood_event_score"], 4),
                "rainfall": round(components["rainfall_score"], 4),
                "cases": round(components["case_score"], 4),
                "vulnerability": round(components["vulnerability_score"], 4),
                "recent_flood_events": components["recent_flood_events"],
            },
            "raw_values": {
                "rainfall_7day_mm": components["rainfall_mm"],
                "ndwi": components["ndwi"],
                "recent_cases": components["recent_cases"],
                "recent_deaths": components["recent_deaths"],
            },
        }

    def calculate_all(
        self,
        score_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Calculate risk scores for all LGAs."""
        # Resolve the anchor date once so we don't re-query it per LGA.
        score_date = score_date or self._latest_data_date()
        lgas = self.db.query(LGA).all()
        results = []

        for lga in lgas:
            try:
                result = self._persist_and_dict(lga, score_date)
                results.append(result)
            except Exception as e:
                logger.error(f"Error calculating risk for LGA {lga.id}: {e}")
                results.append({
                    "lga_id": lga.id,
                    "lga_name": lga.name,
                    "error": str(e)
                })

        return results
