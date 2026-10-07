import type { DashboardSummary } from '../../types';

interface KpiProps {
  title: string;
  value: string | number;
  subtitle?: string;
}

function Kpi({ title, value, subtitle }: KpiProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500">{title}</div>
      <div className="text-xl font-semibold text-gray-900">{value}</div>
      {subtitle && <div className="text-xs text-gray-400">{subtitle}</div>}
    </div>
  );
}

const LEVEL_LABEL: Record<string, string> = {
  green: 'Low',
  yellow: 'Medium',
  red: 'High',
};

/**
 * Environmental and alerting tier, at LGA resolution.
 *
 * The case-count KPI that used to lead this row was dropped: the nationwide
 * LGA-month case panel was rejected by the manuscript and purged, so it would
 * read "0 confirmed cases in selected window" — a false negative rather than
 * an absence of data. National case burden is reported by the verified
 * state-tier section above, which is the only case evidence in the platform.
 */
export function DashboardKpiRow({ summary }: { summary: DashboardSummary | undefined }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline gap-2">
        <h3 className="text-sm font-bold text-[#111518]">Environmental &amp; alerting tier</h3>
        <span className="text-[11px] text-gray-400">LGA resolution · selected window</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi title="Active alerts" value={summary?.active_alerts_count ?? 0} subtitle="real alerts" />
        <Kpi
          title="Alert level"
          value={summary ? LEVEL_LABEL[summary.alert_level] ?? '—' : '—'}
          subtitle={`${summary?.lgas_high_risk ?? 0} high-risk LGAs`}
        />
        <Kpi title="Rainfall 7d" value={`${summary?.avg_rainfall_7day ?? 0} mm`} subtitle="latest available" />
        <Kpi title="Flood events" value={summary?.flood_events_count ?? 0} subtitle="in window" />
      </div>
    </div>
  );
}
