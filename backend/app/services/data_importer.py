"""Data importer for Excel/CSV cholera and environmental data."""
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.models import LGA, Ward, CaseReport, EnvironmentalData

logger = logging.getLogger(__name__)


class DataImporter:
    """Import and validate data from Excel/CSV files."""

    def __init__(self, db: Session):
        self.db = db
        self._lga_cache: Dict[str, int] = {}
        self._build_lga_cache()

    def _build_lga_cache(self):
        """Build cache of LGA name -> ID, plus (name, state) -> ID."""
        self._lga_cache: Dict[str, int] = {}
        self._state_cache: Dict[str, int] = {}
        lgas = self.db.query(LGA).all()
        for lga in lgas:
            key = lga.name.lower()
            self._lga_cache.setdefault(key, lga.id)
            self._lga_cache.setdefault(key.replace(" ", ""), lga.id)
            if lga.pcode:
                self._lga_cache.setdefault(lga.pcode.upper(), lga.id)
            if lga.state:
                self._state_cache[f"{key}__{lga.state.lower()}"] = lga.id

    def _find_lga_id(self, lga_name: str, state: str = None) -> Optional[int]:
        if not lga_name:
            return None
        name_lower = str(lga_name).lower().strip()

        # State-disambiguated exact match first
        state_cache = getattr(self, "_state_cache", {}) or {}
        if state:
            skey = f"{name_lower}__{str(state).lower().strip()}"
            if skey in state_cache:
                return state_cache[skey]
            skey_nospace = f"{name_lower.replace(' ', '')}__{str(state).lower().strip()}"
            if skey_nospace in state_cache:
                return state_cache[skey_nospace]

        # Direct match
        if name_lower in self._lga_cache:
            return self._lga_cache[name_lower]
        name_no_spaces = name_lower.replace(" ", "")
        if name_no_spaces in self._lga_cache:
            return self._lga_cache[name_no_spaces]

        # pcode (uppercase) match
        pc = self._lga_cache.get(name_lower.upper())
        if pc is not None:
            return pc
        # Partial/substring match
        for cached_name, lga_id in self._lga_cache.items():
            if name_lower in cached_name or cached_name in name_lower:
                return lga_id
        return None

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse various date formats."""
        if value is None or pd.isna(value):
            return None

        if isinstance(value, (datetime, date)):
            return value.date() if isinstance(value, datetime) else value

        if isinstance(value, str):
            # Try common formats
            formats = [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%d-%m-%Y",
                "%Y/%m/%d"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue

        return None

    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Safely convert value to integer."""
        if value is None or pd.isna(value):
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def _safe_float(self, value: Any, default: float = None) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def import_case_data(
        self,
        df: pd.DataFrame,
        source_file: str = None
    ) -> Dict[str, Any]:
        """
        Import cholera case data from DataFrame.

        Expected columns:
        - lga_name or lga (required)
        - report_date or date (required)
        - new_cases or cases (required)
        - deaths (optional)
        - suspected_cases (optional)
        - confirmed_cases (optional)
        - ward_name or ward (optional)
        """
        records_imported = 0
        records_failed = 0
        errors = []

        # Normalize column names
        df.columns = [col.lower().strip().replace(" ", "_") for col in df.columns]

        # Find LGA column
        lga_col = None
        for col in ["lga_name", "lga", "local_government", "local_govt"]:
            if col in df.columns:
                lga_col = col
                break

        if not lga_col:
            errors.append("No LGA column found (expected: lga_name, lga, or local_government)")
            return {"records_imported": 0, "records_failed": len(df), "errors": errors}

        # Find date column
        date_col = None
        for col in ["report_date", "date", "week_ending", "epi_week_end"]:
            if col in df.columns:
                date_col = col
                break

        if not date_col:
            errors.append("No date column found (expected: report_date, date, or week_ending)")
            return {"records_imported": 0, "records_failed": len(df), "errors": errors}

        # Find cases column
        cases_col = None
        for col in ["new_cases", "cases", "total_cases", "cholera_cases"]:
            if col in df.columns:
                cases_col = col
                break

        if not cases_col:
            errors.append("No cases column found (expected: new_cases, cases, or total_cases)")
            return {"records_imported": 0, "records_failed": len(df), "errors": errors}

        # Process rows
        for idx, row in df.iterrows():
            try:
                lga_name = row[lga_col]
                lga_id = self._find_lga_id(lga_name)

                if not lga_id:
                    errors.append(f"Row {idx + 2}: Unknown LGA '{lga_name}'")
                    records_failed += 1
                    continue

                report_date = self._parse_date(row[date_col])
                if not report_date:
                    errors.append(f"Row {idx + 2}: Invalid date '{row[date_col]}'")
                    records_failed += 1
                    continue

                new_cases = self._safe_int(row[cases_col])

                # Check for existing record
                existing = self.db.query(CaseReport).filter(
                    CaseReport.lga_id == lga_id,
                    CaseReport.report_date == report_date
                ).first()

                if existing:
                    # Update existing
                    existing.new_cases = new_cases
                    existing.deaths = self._safe_int(row.get("deaths", 0))
                    existing.suspected_cases = self._safe_int(row.get("suspected_cases", 0))
                    existing.confirmed_cases = self._safe_int(row.get("confirmed_cases", 0))
                    existing.recoveries = self._safe_int(row.get("recoveries", 0))
                else:
                    # Create new record
                    case_report = CaseReport(
                        lga_id=lga_id,
                        report_date=report_date,
                        new_cases=new_cases,
                        deaths=self._safe_int(row.get("deaths", 0)),
                        suspected_cases=self._safe_int(row.get("suspected_cases", 0)),
                        confirmed_cases=self._safe_int(row.get("confirmed_cases", 0)),
                        recoveries=self._safe_int(row.get("recoveries", 0)),
                        cases_under_5=self._safe_int(row.get("cases_under_5", 0)),
                        cases_5_to_14=self._safe_int(row.get("cases_5_to_14", 0)),
                        cases_15_plus=self._safe_int(row.get("cases_15_plus", 0)),
                        cases_male=self._safe_int(row.get("cases_male", 0)),
                        cases_female=self._safe_int(row.get("cases_female", 0)),
                        source="uploaded",
                        source_file=source_file
                    )
                    self.db.add(case_report)

                records_imported += 1

            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
                records_failed += 1
                continue

        self.db.commit()

        return {
            "records_imported": records_imported,
            "records_failed": records_failed,
            "errors": errors[:20]  # Limit errors returned
        }

    def import_environmental_data(
        self,
        df: pd.DataFrame,
        source_file: str = None
    ) -> Dict[str, Any]:
        """
        Import environmental data from DataFrame.

        Expected columns:
        - lga_name or lga (required)
        - observation_date or date (required)
        - rainfall_mm (optional)
        - ndwi (optional)
        - flood_observed (optional)
        """
        records_imported = 0
        records_failed = 0
        errors = []

        # Normalize column names
        df.columns = [col.lower().strip().replace(" ", "_") for col in df.columns]

        # Find LGA column
        lga_col = None
        for col in ["lga_name", "lga", "local_government"]:
            if col in df.columns:
                lga_col = col
                break

        if not lga_col:
            errors.append("No LGA column found")
            return {"records_imported": 0, "records_failed": len(df), "errors": errors}

        # Find date column
        date_col = None
        for col in ["observation_date", "date", "obs_date"]:
            if col in df.columns:
                date_col = col
                break

        if not date_col:
            errors.append("No date column found")
            return {"records_imported": 0, "records_failed": len(df), "errors": errors}

        # Process rows
        for idx, row in df.iterrows():
            try:
                lga_name = row[lga_col]
                lga_id = self._find_lga_id(lga_name)

                if not lga_id:
                    errors.append(f"Row {idx + 2}: Unknown LGA '{lga_name}'")
                    records_failed += 1
                    continue

                obs_date = self._parse_date(row[date_col])
                if not obs_date:
                    errors.append(f"Row {idx + 2}: Invalid date")
                    records_failed += 1
                    continue

                # Check for existing record
                existing = self.db.query(EnvironmentalData).filter(
                    EnvironmentalData.lga_id == lga_id,
                    EnvironmentalData.observation_date == obs_date
                ).first()

                if existing:
                    # Update existing
                    if "rainfall_mm" in df.columns:
                        existing.rainfall_mm = self._safe_float(row.get("rainfall_mm"))
                    if "ndwi" in df.columns:
                        existing.ndwi = self._safe_float(row.get("ndwi"))
                    if "flood_observed" in df.columns:
                        existing.flood_observed = bool(row.get("flood_observed"))
                else:
                    # Create new record
                    env_data = EnvironmentalData(
                        lga_id=lga_id,
                        observation_date=obs_date,
                        rainfall_mm=self._safe_float(row.get("rainfall_mm")),
                        ndwi=self._safe_float(row.get("ndwi")),
                        flood_observed=bool(row.get("flood_observed", False)),
                        flood_extent_pct=self._safe_float(row.get("flood_extent_pct")),
                        lst_day=self._safe_float(row.get("lst_day")),
                        lst_night=self._safe_float(row.get("lst_night")),
                        data_source="uploaded"
                    )
                    self.db.add(env_data)

                records_imported += 1

            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
                records_failed += 1
                continue

        self.db.commit()

        return {
            "records_imported": records_imported,
            "records_failed": records_failed,
            "errors": errors[:20]
        }

    def import_line_list_data(
        self,
        df: pd.DataFrame,
        source_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import line-list case data (one row per patient).
        Aggregates by LGA and Date.
        """
        records_imported = 0
        records_failed = 0
        errors = []

        # Normalize columns
        df.columns = [col.lower().strip().replace("\n", "").replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_") for col in df.columns]
        
        # Mapping for the specific Excel file provided
        # 'Date of Onset\n(dd-mmm-yyyy)' -> 'date_of_onset_dd_mmm_yyyy'
        
        lga_col = "lga"
        date_col = "date_of_onset_dd_mmm_yyyy"
        outcome_col = "outcome"
        
        # Verify columns exist
        if lga_col not in df.columns or date_col not in df.columns:
             # Try to find date col if exact name match fails
            found_date = False
            for col in df.columns:
                if "date" in col and "onset" in col:
                    date_col = col
                    found_date = True
                    break
            
            if not found_date:
                return {
                    "records_imported": 0, 
                    "records_failed": len(df), 
                    "errors": ["Line list format not recognized (missing LGA or Onset Date)"]
                }

        # Process: Group by LGA and Date
        # First, parse dates and clean LGAs
        valid_rows = []
        
        for idx, row in df.iterrows():
            try:
                lga_name = row.get(lga_col)
                if pd.isna(lga_name): continue
                
                lga_id = self._find_lga_id(str(lga_name))
                if not lga_id:
                    continue # Skip unknown LGAs
                
                # Parse date
                date_val = row.get(date_col)
                report_date = self._parse_date(date_val)
                if not report_date:
                    continue

                outcome = str(row.get(outcome_col, "")).lower()
                is_death = "dead" in outcome or "died" in outcome
                
                valid_rows.append({
                    "lga_id": lga_id,
                    "report_date": report_date,
                    "is_death": is_death
                })
            except Exception:
                continue

        if not valid_rows:
             return {"records_imported": 0, "records_failed": len(df), "errors": ["No valid rows extracted"]}

        # Aggregate
        agg_df = pd.DataFrame(valid_rows)
        summary = agg_df.groupby(['lga_id', 'report_date']).agg(
            new_cases=('lga_id', 'count'),
            deaths=('is_death', 'sum')
        ).reset_index()

        # Insert Aggregated Data
        for _, row in summary.iterrows():
            try:
                existing = self.db.query(CaseReport).filter(
                    CaseReport.lga_id == row['lga_id'],
                    CaseReport.report_date == row['report_date']
                ).first()

                if existing:
                    existing.new_cases = int(row['new_cases'])
                    existing.deaths = int(row['deaths'])
                else:
                    report = CaseReport(
                        lga_id=int(row['lga_id']),
                        report_date=row['report_date'],
                        new_cases=int(row['new_cases']),
                        deaths=int(row['deaths']),
                        source="line_list_upload",
                        source_file=source_file
                    )
                    self.db.add(report)
                
                records_imported += 1
            except Exception as e:
                errors.append(str(e))
                records_failed += 1

        self.db.commit()
        
        return {
            "records_imported": records_imported,
            "records_failed": len(df) - len(valid_rows), # Rough estimate
            "errors": errors[:5]
        }

    def import_cholera_excel(self, filepath: str) -> Dict[str, Any]:
        """
        Import the specific cholera Excel file provided.
        Handles the structure of 'Copy of Cholera Data for CRS 2021.xlsx'
        """
        try:
            # Read all sheets
            xl = pd.ExcelFile(filepath)
            total_imported = 0
            total_failed = 0
            all_errors = []

            for sheet_name in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sheet_name)

                if df.empty:
                    continue

                # Check if it's a line list (has 'Date of Onset')
                is_line_list = False
                for col in df.columns:
                    if "Date of Onset" in str(col):
                        is_line_list = True
                        break
                
                if is_line_list:
                    result = self.import_line_list_data(df, source_file=filepath)
                else:
                    # Try import as aggregated case data
                    result = self.import_case_data(df, source_file=filepath)
                
                total_imported += result["records_imported"]
                total_failed += result["records_failed"]
                all_errors.extend(result.get("errors", []))

            return {
                "records_imported": total_imported,
                "records_failed": total_failed,
                "errors": all_errors[:20]
            }

        except Exception as e:
            logger.error(f"Error importing Excel file: {e}")
            return {
                "records_imported": 0,
                "records_failed": 0,
                "errors": [str(e)]
            }
