import { useDashboard } from '../../hooks/useApi';
import type { RiskLevel } from '../../types';
import RiskLevelFilter from '../Filters/RiskLevelFilter';

const RISK_COLORS: Record<RiskLevel | 'unknown', string> = {
  green: '#22c55e',
  yellow: '#eab308',
  red: '#ef4444',
  unknown: '#6b7280',
};

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  icon?: React.ReactNode;
}

function StatCard({ title, value, subtitle, color = '#3b82f6', icon }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{title}</p>
          <p className="text-2xl font-bold" style={{ color }}>
            {value}
          </p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
    </div>
  );
}

export default function RiskPanel() {
  const { data: summary, isLoading: loading, error } = useDashboard();

  if (loading) {
    return (
      <div className="space-y-4" role="status" aria-label="Loading dashboard">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="bg-white rounded-lg shadow p-4" role="alert">
        <p className="text-red-500 text-sm">
          {error instanceof Error ? error.message : 'Unable to load dashboard data'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Dashboard Overview</h2>

      {/* Risk level summary */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">LGA Risk Levels</h3>
        <div className="flex gap-2" role="list" aria-label="Risk level distribution">
          <div
            className="flex-1 text-center py-2 rounded-lg"
            style={{ backgroundColor: `${RISK_COLORS.red}15` }}
            role="listitem"
          >
            <p className="text-2xl font-bold" style={{ color: RISK_COLORS.red }}>
              {summary.lgas_high_risk}
            </p>
            <p className="text-xs text-gray-600">High</p>
          </div>
          <div
            className="flex-1 text-center py-2 rounded-lg"
            style={{ backgroundColor: `${RISK_COLORS.yellow}15` }}
            role="listitem"
          >
            <p className="text-2xl font-bold" style={{ color: RISK_COLORS.yellow }}>
              {summary.lgas_medium_risk}
            </p>
            <p className="text-xs text-gray-600">Medium</p>
          </div>
          <div
            className="flex-1 text-center py-2 rounded-lg"
            style={{ backgroundColor: `${RISK_COLORS.green}15` }}
            role="listitem"
          >
            <p className="text-2xl font-bold" style={{ color: RISK_COLORS.green }}>
              {summary.lgas_low_risk}
            </p>
            <p className="text-xs text-gray-600">Low</p>
          </div>
        </div>
      </div>

      {/* Risk Level Filter */}
      <RiskLevelFilter
        highRiskCount={summary.lgas_high_risk}
        mediumRiskCount={summary.lgas_medium_risk}
        lowRiskCount={summary.lgas_low_risk}
      />

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          title="Total LGAs"
          value={summary.total_lgas}
          subtitle="Federal Republic of Nigeria (774 LGAs)"
          color="#3b82f6"
        />
        <StatCard
          title="Cases (30d)"
          value={summary.total_cases}
          subtitle={`${summary.total_deaths} deaths`}
          color="#ef4444"
        />
        <StatCard
          title="Avg Rainfall"
          value={`${summary.avg_rainfall_7day.toFixed(1)}mm`}
          subtitle="Last 7 days"
          color="#0ea5e9"
        />
        <StatCard
          title="Last Updated"
          value={summary.last_updated ? new Date(summary.last_updated).toLocaleDateString() : '—'}
          subtitle="Data refresh"
          color="#6b7280"
        />
      </div>

      {/* Alert if high risk LGAs */}
      {summary.lgas_high_risk > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4" role="alert">
          <div className="flex items-start gap-3">
            <div className="text-red-500" aria-hidden="true">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div>
              <h4 className="text-sm font-medium text-red-800">
                High Risk Alert
              </h4>
              <p className="text-sm text-red-600 mt-1">
                {summary.lgas_high_risk} LGA{summary.lgas_high_risk > 1 ? 's' : ''} currently
                at high cholera risk level. Click on the map to view details.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
