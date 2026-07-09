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

export function DashboardKpiRow({ summary }: { summary: DashboardSummary | undefined }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      <Kpi title="Confirmed cases" value={summary?.total_cases ?? 0} subtitle="in selected window" />
      <Kpi title="Active alerts" value={summary?.active_alerts_count ?? 0} subtitle="real alerts" />
      <Kpi
        title="Alert level"
        value={summary ? LEVEL_LABEL[summary.alert_level] ?? '—' : '—'}
        subtitle={`${summary?.lgas_high_risk ?? 0} high-risk LGAs`}
      />
      <Kpi title="Rainfall 7d" value={`${summary?.avg_rainfall_7day ?? 0} mm`} subtitle="latest available" />
      <Kpi title="Flood events" value={summary?.flood_events_count ?? 0} subtitle="in window" />
    </div>
  );
}
