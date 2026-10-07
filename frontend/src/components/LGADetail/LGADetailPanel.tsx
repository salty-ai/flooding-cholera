import { useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Legend,
} from 'recharts';
import { useAppStore } from '../../store/appStore';
import { useLgaAnalytics } from '../../hooks/useApi';
import type { RiskLevel, TimeSeriesPoint } from '../../types';

const RISK_COLORS: Record<RiskLevel, { bg: string; text: string; border: string; label: string }> = {
  red: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300', label: 'High Risk' },
  yellow: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300', label: 'Medium Risk' },
  green: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300', label: 'Low Risk' },
  unknown: { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-300', label: 'Unknown' },
};

interface StatCardProps {
  title: string;
  value: string | number;
  icon: string;
  iconColor: string;
  subtitle?: string;
}

function StatCard({ title, value, icon, iconColor, subtitle }: StatCardProps) {
  const bgColor = iconColor === 'primary' ? 'bg-primary/10 text-primary'
    : iconColor === 'orange' ? 'bg-alert-orange/10 text-alert-orange'
    : iconColor === 'red' ? 'bg-red-100 text-red-600'
    : 'bg-env-green/10 text-env-green';

  return (
    <div className="rounded-lg border border-[#e6e8eb] bg-white p-4">
      <div className="flex justify-between items-start mb-1">
        <p className="text-[#637588] text-xs font-medium">{title}</p>
        <span className={`material-symbols-outlined ${bgColor} p-1 rounded-md`} style={{ fontSize: '16px' }}>
          {icon}
        </span>
      </div>
      <p className="text-xl font-bold tracking-tight text-[#111518]">{value}</p>
      {subtitle && (
        <p className="text-[#637588] text-xs mt-1">{subtitle}</p>
      )}
    </div>
  );
}

interface InfrastructureBarProps {
  label: string;
  value: number;
  color: string;
}

function InfrastructureBar({ label, value, color }: InfrastructureBarProps) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs">
        <span className="text-[#637588] font-medium">{label}</span>
        <span className="text-[#111518] font-bold">{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 w-full bg-[#e6e8eb] rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function prepareChartData(casesData: TimeSeriesPoint[], rainfallData: TimeSeriesPoint[]) {
  // Create a map of dates to values
  const dateMap = new Map<string, { date: string; cases: number; rainfall: number }>();
  
  casesData.forEach(point => {
    const existing = dateMap.get(point.date) || { date: point.date, cases: 0, rainfall: 0 };
    existing.cases = point.value;
    dateMap.set(point.date, existing);
  });
  
  rainfallData.forEach(point => {
    const existing = dateMap.get(point.date) || { date: point.date, cases: 0, rainfall: 0 };
    existing.rainfall = point.value;
    dateMap.set(point.date, existing);
  });

  // Sort by date and return
  return Array.from(dateMap.values())
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .map(item => ({
      ...item,
      formattedDate: formatDate(item.date),
    }));
}

function prepareTrendData(data: TimeSeriesPoint[], label: string) {
  return data
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .map(item => ({
      date: item.date,
      formattedDate: formatDate(item.date),
      [label]: item.value,
    }));
}

export default function LGADetailPanel() {
  const { selectedLGA, selectedLGAId, analyticsDays, setSelectedLGA, setSelectedLGAId, setSelectedLGAAnalytics } = useAppStore();
  const { data: analytics, isLoading, error } = useLgaAnalytics(selectedLGAId, analyticsDays);

  // Sync analytics to store
  useEffect(() => {
    if (analytics) {
      setSelectedLGAAnalytics(analytics);
    }
  }, [analytics, setSelectedLGAAnalytics]);

  // Clear analytics when deselecting
  useEffect(() => {
    if (!selectedLGAId) {
      setSelectedLGAAnalytics(null);
    }
  }, [selectedLGAId, setSelectedLGAAnalytics]);

  const handleClose = () => {
    setSelectedLGA(null);
    setSelectedLGAId(null);
    setSelectedLGAAnalytics(null);
  };

  if (!selectedLGA && !selectedLGAId) {
    return null;
  }

  const riskLevel = analytics?.current_risk_level || 'unknown';
  const riskStyle = RISK_COLORS[riskLevel];

  // Prepare chart data
  const combinedChartData = analytics
    ? prepareChartData(analytics.cases_time_series, analytics.rainfall_time_series)
    : [];

  const riskTrendData = analytics
    ? prepareTrendData(analytics.risk_time_series, 'risk')
    : [];

  return (
    <div className="bg-white border-l border-[#e6e8eb] h-full overflow-y-auto custom-scrollbar">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-[#e6e8eb] p-4 z-10">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-lg font-bold text-[#111518] truncate">
                {analytics?.lga_name || selectedLGA?.name || 'Loading...'}
              </h2>
              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${riskStyle.bg} ${riskStyle.text} ${riskStyle.border} border`}>
                {riskStyle.label}
              </span>
            </div>
            {selectedLGA?.population && (
              <p className="text-sm text-[#637588] mt-1">
                <span className="material-symbols-outlined align-middle mr-1" style={{ fontSize: '14px' }}>group</span>
                Population: {selectedLGA.population.toLocaleString()}
              </p>
            )}
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
            aria-label="Close panel"
          >
            <span className="material-symbols-outlined text-[#637588]" style={{ fontSize: '20px' }}>close</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col gap-5">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-3 text-sm text-[#637588]">Loading analytics...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center text-red-600">
              <span className="material-symbols-outlined" style={{ fontSize: '32px' }}>error</span>
              <p className="mt-2 text-sm">Failed to load analytics</p>
            </div>
          </div>
        ) : (
          <>
            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-3">
              <StatCard
                title="LGA Cases"
                value="—"
                icon="coronavirus"
                iconColor="orange"
                subtitle="Not LGA-resolved · see National Burden (state tier)"
              />
              <StatCard
                title="LGA Deaths"
                value="—"
                icon="skull"
                iconColor="red"
                subtitle="Sentinel pilot LGAs only (Cross River 2021)"
              />
              <StatCard
                title="Avg Risk Score"
                value={`${((analytics?.avg_risk_score || 0) * 100).toFixed(0)}%`}
                icon="trending_up"
                iconColor="primary"
                subtitle="Composite score"
              />
              <StatCard
                title="Health Facilities"
                value={selectedLGA?.health_facilities_count || 'N/A'}
                icon="local_hospital"
                iconColor="green"
                subtitle="Available facilities"
              />
            </div>

            {/* Cases & Rainfall Chart */}
            {combinedChartData.length > 0 && (
              <div className="bg-white rounded-lg border border-[#e6e8eb] p-4">
                <h3 className="text-sm font-bold text-[#111518] mb-1">Cases vs Rainfall</h3>
                <p className="text-xs text-[#637588] mb-4">Correlation over time</p>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={combinedChartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                      <defs>
                        <linearGradient id="colorCases" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#fa6238" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#fa6238" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorRainfall" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#1392ec" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#1392ec" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
                      <XAxis 
                        dataKey="formattedDate" 
                        tick={{ fontSize: 10, fill: '#637588' }}
                        tickLine={false}
                        axisLine={{ stroke: '#e6e8eb' }}
                      />
                      <YAxis 
                        yAxisId="left"
                        tick={{ fontSize: 10, fill: '#637588' }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis 
                        yAxisId="right"
                        orientation="right"
                        tick={{ fontSize: 10, fill: '#637588' }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'white', 
                          border: '1px solid #e6e8eb',
                          borderRadius: '8px',
                          fontSize: '12px'
                        }}
                      />
                      <Legend 
                        iconType="circle"
                        iconSize={8}
                        wrapperStyle={{ fontSize: '11px' }}
                      />
                      <Area
                        yAxisId="left"
                        type="monotone"
                        dataKey="cases"
                        name="Cases"
                        stroke="#fa6238"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorCases)"
                      />
                      <Area
                        yAxisId="right"
                        type="monotone"
                        dataKey="rainfall"
                        name="Rainfall (mm)"
                        stroke="#1392ec"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorRainfall)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Risk Trend Chart */}
            {riskTrendData.length > 0 && (
              <div className="bg-white rounded-lg border border-[#e6e8eb] p-4">
                <h3 className="text-sm font-bold text-[#111518] mb-1">Risk Score Trend</h3>
                <p className="text-xs text-[#637588] mb-4">Risk score over time</p>
                <div className="h-36">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={riskTrendData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
                      <XAxis 
                        dataKey="formattedDate" 
                        tick={{ fontSize: 10, fill: '#637588' }}
                        tickLine={false}
                        axisLine={{ stroke: '#e6e8eb' }}
                      />
                      <YAxis 
                        domain={[0, 1]}
                        tick={{ fontSize: 10, fill: '#637588' }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                      />
                      <Tooltip 
                        formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, 'Risk Score']}
                        contentStyle={{ 
                          backgroundColor: 'white', 
                          border: '1px solid #e6e8eb',
                          borderRadius: '8px',
                          fontSize: '12px'
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="risk"
                        name="Risk Score"
                        stroke="#8b5cf6"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, fill: '#8b5cf6' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Infrastructure Section */}
            {(selectedLGA?.water_coverage_pct !== undefined || selectedLGA?.sanitation_coverage_pct !== undefined) && (
              <div className="bg-white rounded-lg border border-[#e6e8eb] p-4">
                <h3 className="text-sm font-bold text-[#111518] mb-1">Infrastructure Coverage</h3>
                <p className="text-xs text-[#637588] mb-4">Water and sanitation access</p>
                <div className="flex flex-col gap-4">
                  {selectedLGA?.water_coverage_pct !== undefined && (
                    <InfrastructureBar
                      label="Water Access"
                      value={selectedLGA.water_coverage_pct}
                      color="bg-primary"
                    />
                  )}
                  {selectedLGA?.sanitation_coverage_pct !== undefined && (
                    <InfrastructureBar
                      label="Sanitation Coverage"
                      value={selectedLGA.sanitation_coverage_pct}
                      color="bg-env-green"
                    />
                  )}
                </div>
              </div>
            )}

            {/* LGA Details */}
            {selectedLGA && (
              <div className="bg-white rounded-lg border border-[#e6e8eb] p-4">
                <h3 className="text-sm font-bold text-[#111518] mb-3">LGA Information</h3>
                <div className="flex flex-col gap-2 text-sm">
                  {selectedLGA.code && (
                    <div className="flex justify-between">
                      <span className="text-[#637588]">Code</span>
                      <span className="text-[#111518] font-medium">{selectedLGA.code}</span>
                    </div>
                  )}
                  {selectedLGA.headquarters && (
                    <div className="flex justify-between">
                      <span className="text-[#637588]">Headquarters</span>
                      <span className="text-[#111518] font-medium">{selectedLGA.headquarters}</span>
                    </div>
                  )}
                  {selectedLGA.area_sq_km && (
                    <div className="flex justify-between">
                      <span className="text-[#637588]">Area</span>
                      <span className="text-[#111518] font-medium">{selectedLGA.area_sq_km.toLocaleString()} km²</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
