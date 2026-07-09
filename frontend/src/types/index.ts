export interface LGA {
  id: number;
  name: string;
  code: string;
  population?: number;
  area_sq_km?: number;
  headquarters?: string;
  centroid_lat?: number;
  centroid_lon?: number;
  water_coverage_pct?: number;
  sanitation_coverage_pct?: number;
  health_facilities_count?: number;
  created_at: string;
  updated_at: string;
}

export interface LGAWithGeometry extends LGA {
  geometry?: GeoJSONGeometry;
}

export interface GeoJSONGeometry {
  type: string;
  coordinates: number[][][] | number[][][][];
}

export interface GeoJSONFeature {
  type: 'Feature';
  id?: number;
  properties: LGAProperties;
  geometry: GeoJSONGeometry;
}

export interface LGAProperties {
  id: number;
  name: string;
  code: string;
  population?: number;
  centroid_lat?: number;
  centroid_lon?: number;
  risk_score?: number;
  risk_level: RiskLevel;
  recent_cases?: number;
  recent_deaths?: number;
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

export type RiskLevel = 'green' | 'yellow' | 'red' | 'unknown';

export interface RiskScore {
  id: number;
  lga_id: number;
  lga_name?: string;
  score_date: string;
  score: number;
  level: RiskLevel;
  flood_score?: number;
  rainfall_score?: number;
  case_score?: number;
  vulnerability_score?: number;
  flood_event_score?: number;
  recent_flood_events?: number;
  algorithm_version?: string;
  recent_cases?: number;
  recent_deaths?: number;
  rainfall_mm?: number;
  calculated_at: string;
}

export interface CaseReport {
  id: number;
  lga_id: number;
  date: string;
  new_cases: number;
  deaths: number;
  suspected_cases?: number;
  confirmed_cases?: number;
  cfr?: number;
}

export interface EnvironmentalData {
  lga_id: number;
  lga_name: string;
  observation_date: string;
  rainfall_mm?: number;
  rainfall_7day_mm?: number;
  ndwi?: number;
  flood_extent_pct?: number;
  flood_observed: boolean;
  lst_day?: number;
  data_source?: string;
}

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

export interface LGAAnalytics {
  lga_id: number;
  lga_name: string;
  cases_time_series: TimeSeriesPoint[];
  deaths_time_series: TimeSeriesPoint[];
  rainfall_time_series: TimeSeriesPoint[];
  risk_time_series: TimeSeriesPoint[];
  total_cases: number;
  total_deaths: number;
  avg_risk_score: number;
  current_risk_level: RiskLevel;
}

export interface DashboardSummary {
  total_lgas: number;
  total_cases: number;
  total_deaths: number;
  lgas_high_risk: number;
  lgas_medium_risk: number;
  lgas_low_risk: number;
  avg_rainfall_7day: number;
  last_updated: string | null;
  active_alerts_count: number;
  alert_level: 'green' | 'yellow' | 'red';
  flood_events_count: number;
  applied_window_start: string | null;
  applied_window_end: string | null;
  max_data_date: string | null;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  records_imported: number;
  records_failed: number;
  errors: string[];
}

export interface SatelliteStatus {
  nasa_gpm_available: boolean;
  google_earth_engine_available: boolean;
  last_fetch: string | null;
  next_scheduled_fetch: string | null;
  data_coverage_days: number;
}

export interface SatelliteData {
  lga_id: number;
  lga_name: string;
  observation_date: string;
  rainfall_mm: number | null;
  rainfall_7day_mm: number | null;
  ndwi: number | null;
  ndvi: number | null;
  flood_extent_pct: number | null;
  flood_observed: boolean;
  lst_day: number | null;
  data_source: string;
}

export type AlertType = 'high_risk' | 'case_spike' | 'flood_warning' | 'rainfall_alert' | 'risk_change';
export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface Alert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  lga_id?: number;
  lga_name?: string;
  created_at: string;
  read: boolean;
}

export interface DateRange {
  startDate: Date | null;
  endDate: Date | null;
}

export type RefreshInterval = 0 | 5 | 15 | 30; // minutes, 0 = disabled

export interface FilterState {
  showHighRisk: boolean;
  showMediumRisk: boolean;
  showLowRisk: boolean;
  dateRange: DateRange;
}

export interface WeeklySummary {
  weeks: number;
  start_date: string;
  end_date: string;
  weekly_data: Array<{
    week: string;
    cases: number;
    deaths: number;
    flood_extent: number;
    rainfall: number;
  }>;
}
