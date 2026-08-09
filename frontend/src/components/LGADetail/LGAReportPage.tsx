import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { useLgaAnalytics, useLgas } from '../../hooks/useApi';
import type { RiskLevel, TimeSeriesPoint, LGA } from '../../types';
import LGASearchBar from '../Search/LGASearchBar';

const RISK_COLORS: Record<RiskLevel, { bg: string; text: string; border: string; label: string; hex: string }> = {
  red: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300', label: 'High Risk', hex: '#ef4444' },
  yellow: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300', label: 'Medium Risk', hex: '#eab308' },
  green: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300', label: 'Low Risk', hex: '#22c55e' },
  unknown: { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-300', label: 'Unknown', hex: '#6b7280' },
};

interface StatCardProps {
  title: string;
  value: string | number;
  icon: string;
  iconColor: string;
  subtitle?: string;
  trend?: { value: number; positive: boolean };
}

function StatCard({ title, value, icon, iconColor, subtitle, trend }: StatCardProps) {
  const bgColor = iconColor === 'primary' ? 'bg-primary/10 text-primary'
    : iconColor === 'orange' ? 'bg-orange-100 text-orange-600'
    : iconColor === 'red' ? 'bg-red-100 text-red-600'
    : iconColor === 'blue' ? 'bg-blue-100 text-blue-600'
    : 'bg-green-100 text-green-600';

  return (
    <div className="rounded-xl border border-[#e6e8eb] bg-white p-5 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <p className="text-[#637588] text-sm font-medium">{title}</p>
        <span className={`material-symbols-outlined ${bgColor} p-2 rounded-lg`} style={{ fontSize: '20px' }}>
          {icon}
        </span>
      </div>
      <p className="text-3xl font-bold tracking-tight text-[#111518]">{value}</p>
      <div className="flex items-center gap-2 mt-1">
        {subtitle && <p className="text-[#637588] text-xs">{subtitle}</p>}
        {trend && (
          <span className={`text-xs font-medium flex items-center gap-0.5 ${trend.positive ? 'text-green-600' : 'text-red-600'}`}>
            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>
              {trend.positive ? 'trending_down' : 'trending_up'}
            </span>
            {Math.abs(trend.value)}%
          </span>
        )}
      </div>
    </div>
  );
}

function InfrastructureBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between text-sm">
        <span className="text-[#637588] font-medium">{label}</span>
        <span className="text-[#111518] font-bold">{value.toFixed(1)}%</span>
      </div>
      <div className="h-3 w-full bg-[#e6e8eb] rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700`}
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

  return Array.from(dateMap.values())
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .map(item => ({
      ...item,
      formattedDate: formatDate(item.date),
    }));
}

function prepareWeeklyData(casesData: TimeSeriesPoint[]) {
  // Group by week
  const weekMap = new Map<string, number>();
  
  casesData.forEach(point => {
    const date = new Date(point.date);
    const weekStart = new Date(date);
    weekStart.setDate(date.getDate() - date.getDay());
    const weekKey = weekStart.toISOString().split('T')[0];
    weekMap.set(weekKey, (weekMap.get(weekKey) || 0) + point.value);
  });

  return Array.from(weekMap.entries())
    .map(([week, cases]) => ({
      week: formatDate(week),
      cases,
    }))
    .slice(-12); // Last 12 weeks
}

export default function LGAReportPage() {
  const { lgaId } = useParams<{ lgaId: string }>();
  const navigate = useNavigate();
  const id = lgaId ? parseInt(lgaId, 10) : null;
  
  const { data: lgasData } = useLgas();
  const { data: analytics, isLoading, error } = useLgaAnalytics(id, 90);
  
  const lgas = lgasData?.lgas || [];
  const selectedLGA: LGA | undefined = lgas.find((l) => l.id === id);

  // Scroll to top on LGA change
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [lgaId]);

  if (!id) {
    return (
      <div className="min-h-screen bg-[#f6f7f8] p-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-16">
            <span className="material-symbols-outlined text-[#637588] mb-4" style={{ fontSize: '64px' }}>
              location_searching
            </span>
            <h1 className="text-2xl font-bold text-[#111518] mb-2">Search for an LGA</h1>
            <p className="text-[#637588] mb-8">
              Enter an LGA name to view its detailed cholera surveillance report
            </p>
            <div className="max-w-md mx-auto">
              <LGASearchBar placeholder="Search LGA name..." />
            </div>
          </div>
        </div>
      </div>
    );
  }

  const riskLevel = analytics?.current_risk_level || 'unknown';
  const riskStyle = RISK_COLORS[riskLevel];
  
  const combinedChartData = analytics
    ? prepareChartData(analytics.cases_time_series, analytics.rainfall_time_series)
    : [];

  const weeklyData = analytics
    ? prepareWeeklyData(analytics.cases_time_series)
    : [];

  const riskTrendData = analytics
    ? analytics.risk_time_series
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
        .map(item => ({
          ...item,
          formattedDate: formatDate(item.date),
          risk: item.value * 100,
        }))
    : [];

  // CFR calculation
  const cfr = analytics && analytics.total_cases > 0 
    ? ((analytics.total_deaths / analytics.total_cases) * 100).toFixed(1)
    : '0.0';

  // Pie chart data for risk distribution over time
  const riskDistribution = [
    { name: 'High Risk Days', value: riskTrendData.filter(d => d.risk >= 70).length, color: RISK_COLORS.red.hex },
    { name: 'Medium Risk Days', value: riskTrendData.filter(d => d.risk >= 40 && d.risk < 70).length, color: RISK_COLORS.yellow.hex },
    { name: 'Low Risk Days', value: riskTrendData.filter(d => d.risk < 40).length, color: RISK_COLORS.green.hex },
  ].filter(d => d.value > 0);

  return (
    <div className="min-h-screen bg-[#f6f7f8]">
      {/* Header */}
      <header className="bg-white border-b border-[#e6e8eb] sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            {/* Back button and title */}
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(-1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <span className="material-symbols-outlined text-[#637588]" style={{ fontSize: '22px' }}>
                  arrow_back
                </span>
              </button>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-xl font-bold text-[#111518]">
                    {analytics?.lga_name || selectedLGA?.name || 'Loading...'}
                  </h1>
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${riskStyle.bg} ${riskStyle.text} ${riskStyle.border} border`}>
                    {riskStyle.label}
                  </span>
                </div>
                <p className="text-sm text-[#637588]">
                  LGA Surveillance Report • Last 90 days
                </p>
              </div>
            </div>

            {/* Search bar */}
            <div className="flex-1 max-w-md">
              <LGASearchBar placeholder="Search for another LGA..." />
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#637588] hover:bg-gray-100 rounded-lg transition-colors">
                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>download</span>
                Export PDF
              </button>
              <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors">
                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>share</span>
                Share
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-24">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
              <p className="mt-4 text-[#637588]">Loading report data...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-24">
            <div className="text-center text-red-600">
              <span className="material-symbols-outlined" style={{ fontSize: '48px' }}>error</span>
              <p className="mt-4 text-lg font-medium">Failed to load report</p>
              <p className="text-sm text-[#637588]">Please try again later</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                title="Total Cases"
                value={analytics?.total_cases || 0}
                icon="coronavirus"
                iconColor="orange"
                subtitle="Last 90 days"
              />
              <StatCard
                title="Total Deaths"
                value={analytics?.total_deaths || 0}
                icon="skull"
                iconColor="red"
                subtitle={`CFR: ${cfr}%`}
              />
              <StatCard
                title="Avg Risk Score"
                value={`${((analytics?.avg_risk_score || 0) * 100).toFixed(0)}%`}
                icon="speed"
                iconColor="primary"
                subtitle="Composite score"
              />
              <StatCard
                title="Population"
                value={selectedLGA?.population?.toLocaleString() || 'N/A'}
                icon="group"
                iconColor="blue"
                subtitle={selectedLGA?.area_sq_km ? `${selectedLGA.area_sq_km.toLocaleString()} km²` : undefined}
              />
            </div>

            {/* Charts Row 1 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Cases vs Rainfall */}
              {combinedChartData.length > 0 && (
                <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
                  <h3 className="text-lg font-bold text-[#111518] mb-1">Cases vs Rainfall Correlation</h3>
                  <p className="text-sm text-[#637588] mb-6">Daily comparison over time</p>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={combinedChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorCasesPage" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="colorRainfallPage" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
                        <XAxis 
                          dataKey="formattedDate" 
                          tick={{ fontSize: 11, fill: '#637588' }}
                          tickLine={false}
                          axisLine={{ stroke: '#e6e8eb' }}
                        />
                        <YAxis 
                          yAxisId="left"
                          tick={{ fontSize: 11, fill: '#637588' }}
                          tickLine={false}
                          axisLine={false}
                        />
                        <YAxis 
                          yAxisId="right"
                          orientation="right"
                          tick={{ fontSize: 11, fill: '#637588' }}
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
                        <Legend iconType="circle" iconSize={8} />
                        <Area
                          yAxisId="left"
                          type="monotone"
                          dataKey="cases"
                          name="Cases"
                          stroke="#f97316"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#colorCasesPage)"
                        />
                        <Area
                          yAxisId="right"
                          type="monotone"
                          dataKey="rainfall"
                          name="Rainfall (mm)"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#colorRainfallPage)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Risk Score Trend */}
              {riskTrendData.length > 0 && (
                <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
                  <h3 className="text-lg font-bold text-[#111518] mb-1">Risk Score Trend</h3>
                  <p className="text-sm text-[#637588] mb-6">Daily risk assessment</p>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={riskTrendData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
                        <XAxis 
                          dataKey="formattedDate" 
                          tick={{ fontSize: 11, fill: '#637588' }}
                          tickLine={false}
                          axisLine={{ stroke: '#e6e8eb' }}
                        />
                        <YAxis 
                          domain={[0, 100]}
                          tick={{ fontSize: 11, fill: '#637588' }}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(v) => `${v}%`}
                        />
                        <Tooltip 
                          formatter={(value: number) => [`${value.toFixed(1)}%`, 'Risk Score']}
                          contentStyle={{ 
                            backgroundColor: 'white', 
                            border: '1px solid #e6e8eb',
                            borderRadius: '8px',
                            fontSize: '12px'
                          }}
                        />
                        {/* Reference lines for risk thresholds */}
                        <Line
                          type="monotone"
                          dataKey="risk"
                          name="Risk Score"
                          stroke="#8b5cf6"
                          strokeWidth={2}
                          dot={false}
                          activeDot={{ r: 5, fill: '#8b5cf6' }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>

            {/* Charts Row 2 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Weekly Cases Bar Chart */}
              {weeklyData.length > 0 && (
                <div className="bg-white rounded-xl border border-[#e6e8eb] p-6 lg:col-span-2">
                  <h3 className="text-lg font-bold text-[#111518] mb-1">Weekly Case Distribution</h3>
                  <p className="text-sm text-[#637588] mb-6">Cases aggregated by week</p>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={weeklyData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" vertical={false} />
                        <XAxis 
                          dataKey="week" 
                          tick={{ fontSize: 11, fill: '#637588' }}
                          tickLine={false}
                          axisLine={{ stroke: '#e6e8eb' }}
                        />
                        <YAxis 
                          tick={{ fontSize: 11, fill: '#637588' }}
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
                        <Bar 
                          dataKey="cases" 
                          name="Cases" 
                          fill="#f97316" 
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Risk Distribution Pie */}
              {riskDistribution.length > 0 && (
                <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
                  <h3 className="text-lg font-bold text-[#111518] mb-1">Risk Level Distribution</h3>
                  <p className="text-sm text-[#637588] mb-6">Days by risk category</p>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={riskDistribution}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {riskDistribution.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip 
                          formatter={(value: number) => [`${value} days`, '']}
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
                          formatter={(value) => <span className="text-xs text-[#637588]">{value}</span>}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>

            {/* Infrastructure & LGA Info */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Infrastructure Coverage */}
              {(selectedLGA?.water_coverage_pct !== undefined || selectedLGA?.sanitation_coverage_pct !== undefined) && (
                <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
                  <h3 className="text-lg font-bold text-[#111518] mb-1">Infrastructure Coverage</h3>
                  <p className="text-sm text-[#637588] mb-6">Water and sanitation access indicators</p>
                  <div className="flex flex-col gap-6">
                    {selectedLGA?.water_coverage_pct !== undefined && (
                      <InfrastructureBar
                        label="Water Access"
                        value={selectedLGA.water_coverage_pct}
                        color="bg-blue-500"
                      />
                    )}
                    {selectedLGA?.sanitation_coverage_pct !== undefined && (
                      <InfrastructureBar
                        label="Sanitation Coverage"
                        value={selectedLGA.sanitation_coverage_pct}
                        color="bg-green-500"
                      />
                    )}
                    {selectedLGA?.health_facilities_count !== undefined && (
                      <div className="flex items-center justify-between p-4 bg-[#f6f7f8] rounded-lg">
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined text-primary" style={{ fontSize: '24px' }}>
                            local_hospital
                          </span>
                          <span className="text-sm font-medium text-[#637588]">Health Facilities</span>
                        </div>
                        <span className="text-2xl font-bold text-[#111518]">
                          {selectedLGA.health_facilities_count}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* LGA Details */}
              {selectedLGA && (
                <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
                  <h3 className="text-lg font-bold text-[#111518] mb-1">LGA Information</h3>
                  <p className="text-sm text-[#637588] mb-6">Administrative details</p>
                  <div className="grid grid-cols-2 gap-4">
                    {selectedLGA.code && (
                      <div className="p-4 bg-[#f6f7f8] rounded-lg">
                        <p className="text-xs text-[#637588] mb-1">LGA Code</p>
                        <p className="text-lg font-bold text-[#111518]">{selectedLGA.code}</p>
                      </div>
                    )}
                    {selectedLGA.headquarters && (
                      <div className="p-4 bg-[#f6f7f8] rounded-lg">
                        <p className="text-xs text-[#637588] mb-1">Headquarters</p>
                        <p className="text-lg font-bold text-[#111518]">{selectedLGA.headquarters}</p>
                      </div>
                    )}
                    {selectedLGA.area_sq_km && (
                      <div className="p-4 bg-[#f6f7f8] rounded-lg">
                        <p className="text-xs text-[#637588] mb-1">Area</p>
                        <p className="text-lg font-bold text-[#111518]">{selectedLGA.area_sq_km.toLocaleString()} km²</p>
                      </div>
                    )}
                    {selectedLGA.population && (
                      <div className="p-4 bg-[#f6f7f8] rounded-lg">
                        <p className="text-xs text-[#637588] mb-1">Population Density</p>
                        <p className="text-lg font-bold text-[#111518]">
                          {selectedLGA.area_sq_km 
                            ? Math.round(selectedLGA.population / selectedLGA.area_sq_km).toLocaleString()
                            : 'N/A'
                          }
                          <span className="text-sm font-normal text-[#637588]"> /km²</span>
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="text-center py-6 text-sm text-[#637588]">
              <p>Report generated on {new Date().toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              })}</p>
              <p className="mt-1">Nigeria EO-enabled Environmental Health Surveillance Hub (774 LGAs)</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
