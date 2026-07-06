import { useState } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import toast from 'react-hot-toast';
import { useRiskScores, useDashboard, useLgaAnalytics, apiService } from '../../hooks/useApi';
import { useAppStore } from '../../store/appStore';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

type ReportType = 'overview' | 'lga' | 'environmental' | 'trends';
type TimePeriod = '7d' | '30d' | '90d';

const RISK_COLORS = {
  red: '#ef4444',
  yellow: '#eab308',
  green: '#22c55e',
};

function ReportHeader({ title, subtitle, onExport }: { title: string; subtitle: string; onExport?: () => void }) {
  return (
    <div className="flex justify-between items-start mb-6">
      <div>
        <h3 className="text-lg font-bold text-[#111518]">{title}</h3>
        <p className="text-[#637588] text-sm mt-1">{subtitle}</p>
      </div>
      {onExport && (
        <button
          onClick={onExport}
          className="flex items-center gap-2 px-3 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>download</span>
          Export PDF
        </button>
      )}
    </div>
  );
}

function OverviewReport() {
  const { data: dashboard } = useDashboard();
  const { data: riskScores } = useRiskScores();

  const riskDistribution = [
    { name: 'High Risk', value: dashboard?.lgas_high_risk || 0, color: RISK_COLORS.red },
    { name: 'Medium Risk', value: dashboard?.lgas_medium_risk || 0, color: RISK_COLORS.yellow },
    { name: 'Low Risk', value: dashboard?.lgas_low_risk || 0, color: RISK_COLORS.green },
  ];

  const topRiskLGAs = riskScores
    ?.sort((a, b) => b.score - a.score)
    .slice(0, 5) || [];

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
          <p className="text-[#637588] text-xs font-medium mb-1">Total LGAs</p>
          <p className="text-2xl font-bold text-[#111518]">{dashboard?.total_lgas || 18}</p>
        </div>
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
          <p className="text-[#637588] text-xs font-medium mb-1">Cases (30d)</p>
          <p className="text-2xl font-bold text-alert-orange">{dashboard?.total_cases || 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
          <p className="text-[#637588] text-xs font-medium mb-1">Deaths (30d)</p>
          <p className="text-2xl font-bold text-red-600">{dashboard?.total_deaths || 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
          <p className="text-[#637588] text-xs font-medium mb-1">Avg Rainfall</p>
          <p className="text-2xl font-bold text-primary">{dashboard?.avg_rainfall_7day?.toFixed(0) || 0}mm</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Distribution Pie Chart */}
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
          <h4 className="font-bold text-[#111518] mb-4">Risk Level Distribution</h4>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {riskDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Risk LGAs Table */}
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
          <h4 className="font-bold text-[#111518] mb-4">Top 5 At-Risk LGAs</h4>
          <div className="space-y-3">
            {topRiskLGAs.map((lga, idx) => (
              <div key={lga.lga_id} className="flex items-center gap-3">
                <span className="text-sm font-bold text-[#637588] w-6">{idx + 1}</span>
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-[#111518]">{lga.lga_name}</span>
                    <span className={`text-sm font-bold ${
                      lga.level === 'red' ? 'text-red-500' :
                      lga.level === 'yellow' ? 'text-yellow-500' : 'text-green-500'
                    }`}>
                      {(lga.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-2 bg-[#e6e8eb] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        lga.level === 'red' ? 'bg-red-500' :
                        lga.level === 'yellow' ? 'bg-yellow-400' : 'bg-green-500'
                      }`}
                      style={{ width: `${lga.score * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function LGAReport() {
  const { selectedLGAId, selectedLGA } = useAppStore();
  const [period, setPeriod] = useState<TimePeriod>('30d');
  const days = period === '7d' ? 7 : period === '30d' ? 30 : 90;
  const { data: analytics, isLoading } = useLgaAnalytics(selectedLGAId, days);

  if (!selectedLGAId) {
    return (
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-8 text-center">
        <span className="material-symbols-outlined text-[#637588] mb-3" style={{ fontSize: '48px' }}>location_on</span>
        <h4 className="font-bold text-[#111518] mb-2">No LGA Selected</h4>
        <p className="text-[#637588] text-sm">Click on an LGA on the map to view detailed reports</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* LGA Header */}
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <div className="flex justify-between items-start">
          <div>
            <h4 className="text-xl font-bold text-[#111518]">{selectedLGA?.name || analytics?.lga_name}</h4>
            <p className="text-[#637588] text-sm">Population: {selectedLGA?.population?.toLocaleString() || 'N/A'}</p>
          </div>
          <div className="flex gap-2">
            {(['7d', '30d', '90d'] as TimePeriod[]).map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  period === p ? 'bg-primary text-white' : 'bg-[#f0f2f5] text-[#637588] hover:bg-[#e6e8eb]'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
          <p className="text-[#637588] text-xs font-medium mb-1">Total Cases</p>
          <p className="text-2xl font-bold text-[#111518]">{analytics?.total_cases || 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
          <p className="text-[#637588] text-xs font-medium mb-1">Deaths</p>
          <p className="text-2xl font-bold text-alert-orange">{analytics?.total_deaths || 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
          <p className="text-[#637588] text-xs font-medium mb-1">CFR</p>
          <p className="text-2xl font-bold text-[#111518]">
            {analytics && analytics.total_cases > 0
              ? ((analytics.total_deaths / analytics.total_cases) * 100).toFixed(1)
              : 0}%
          </p>
        </div>
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
          <p className="text-[#637588] text-xs font-medium mb-1">Avg Risk</p>
          <p className={`text-2xl font-bold ${
            analytics?.current_risk_level === 'red' ? 'text-red-500' :
            analytics?.current_risk_level === 'yellow' ? 'text-yellow-500' : 'text-green-500'
          }`}>
            {((analytics?.avg_risk_score || 0) * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Cases Chart */}
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <h4 className="font-bold text-[#111518] mb-4">Cases & Deaths Over Time</h4>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={analytics?.cases_time_series || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="value" name="Cases" stroke="#1392ec" fill="#1392ec" fillOpacity={0.2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Risk Score Trend */}
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <h4 className="font-bold text-[#111518] mb-4">Risk Score Trend</h4>
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={analytics?.risk_time_series || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
              <YAxis tick={{ fontSize: 12 }} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
              <Tooltip formatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
              <Line type="monotone" dataKey="value" name="Risk Score" stroke="#fa6238" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function EnvironmentalReport() {
  const { data: riskScores } = useRiskScores();

  const rainfallData = riskScores?.map(score => ({
    name: score.lga_name,
    rainfall: score.rainfall_mm || 0,
    flood: (score.flood_score || 0) * 100,
  })).slice(0, 10) || [];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <h4 className="font-bold text-[#111518] mb-4">Rainfall by LGA (Latest)</h4>
        <div className="h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rainfallData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
              <Tooltip />
              <Legend />
              <Bar dataKey="rainfall" name="Rainfall (mm)" fill="#1392ec" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <h4 className="font-bold text-[#111518] mb-4">Flood Risk Score by LGA</h4>
        <div className="h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rainfallData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
              <XAxis type="number" tick={{ fontSize: 12 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
              <Tooltip formatter={(v: number) => `${v.toFixed(0)}%`} />
              <Bar dataKey="flood" name="Flood Risk" fill="#fa6238" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

type SurveillanceScope = 'national' | 'state' | 'lga';
type SurveillancePeriod = 'weekly' | 'monthly';

interface SurveillanceReport {
  period: string;
  scope: string;
  from: string;
  to: string;
  totals: { cases: number; deaths: number; cfr: number };
  previous?: { cases: number };
  hotspots_by_cases?: Array<{ lga_id?: number; lga_name?: string; cases?: number; deaths?: number; risk_level?: string }>;
  hotspots_by_risk?: Array<{ lga_id?: number; lga_name?: string; score?: number; risk_level?: string; cases?: number }>;
  risk_distribution?: Record<string, number>;
}

const SURVEILLANCE_RISK_COLORS: Record<string, string> = {
  red: '#ef4444',
  yellow: '#eab308',
  green: '#22c55e',
  High: '#ef4444',
  Medium: '#eab308',
  Low: '#22c55e',
};

function SurveillanceReportPanel() {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
  const [period, setPeriod] = useState<SurveillancePeriod>('weekly');
  const [scope, setScope] = useState<SurveillanceScope>('national');
  const [stateFilter, setStateFilter] = useState('');
  const [lgaId, setLgaId] = useState('');
  const [from, setFrom] = useState<Date | null>(null);
  const [to, setTo] = useState<Date | null>(null);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<SurveillanceReport | null>(null);

  const buildParams = () => {
    const params: { period: string; from: string; to: string; state?: string; lga_id?: number } = {
      period,
      from: from ? from.toISOString().slice(0, 10) : '',
      to: to ? to.toISOString().slice(0, 10) : '',
    };
    if (scope === 'state' && stateFilter) params.state = stateFilter;
    if (scope === 'lga' && lgaId) params.lga_id = Number(lgaId);
    return params;
  };

  const handlePreview = async () => {
    if (!from || !to) {
      toast.error('Please select a date range');
      return;
    }
    setLoading(true);
    try {
      const data = await apiService.getSurveillanceReport(buildParams());
      setReport(data);
      toast.success('Surveillance report generated');
    } catch {
      toast.error('Failed to generate surveillance report');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (format: 'pdf' | 'csv') => {
    if (!from || !to) {
      toast.error('Please select a date range');
      return;
    }
    const p = buildParams();
    const params = new URLSearchParams({ period: p.period, from: p.from, to: p.to });
    if (p.state) params.set('state', p.state);
    if (p.lga_id !== undefined) params.set('lga_id', String(p.lga_id));
    params.set('format', format);
    window.open(`${API_BASE}/reports/surveillance/export?${params.toString()}`);
  };

  const fmtDate = (d: string) =>
    d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A';

  const prevCases = report?.previous?.cases;
  const casesDelta = report && prevCases !== undefined ? report.totals.cases - prevCases : null;

  const riskDistData = report?.risk_distribution
    ? Object.entries(report.risk_distribution).map(([name, value]) => ({
        name,
        value,
        color: SURVEILLANCE_RISK_COLORS[name] || '#637588',
      }))
    : [];

  const topHotspots = report?.hotspots_by_cases?.slice(0, 5) || [];

  return (
    <div className="bg-white rounded-xl border border-[#e6e8eb] p-6 space-y-6">
      <div>
        <h3 className="text-lg font-bold text-[#111518]">Surveillance Report</h3>
        <p className="text-[#637588] text-sm mt-1">Generate a cholera surveillance report for a date range and scope.</p>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-xs font-medium text-[#637588] mb-1">Period</label>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as SurveillancePeriod)}
            className="w-full border border-[#e6e8eb] rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-[#637588] mb-1">Scope</label>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as SurveillanceScope)}
            className="w-full border border-[#e6e8eb] rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="national">National</option>
            <option value="state">State</option>
            <option value="lga">LGA</option>
          </select>
        </div>
        {scope === 'state' && (
          <div>
            <label className="block text-xs font-medium text-[#637588] mb-1">State</label>
            <input
              type="text"
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              placeholder="e.g. Lagos"
              className="w-full border border-[#e6e8eb] rounded-lg px-3 py-2 text-sm"
            />
          </div>
        )}
        {scope === 'lga' && (
          <div>
            <label className="block text-xs font-medium text-[#637588] mb-1">LGA ID</label>
            <input
              type="number"
              value={lgaId}
              onChange={(e) => setLgaId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full border border-[#e6e8eb] rounded-lg px-3 py-2 text-sm"
            />
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-[#637588] mb-1">From</label>
          <DatePicker
            selected={from}
            onChange={(d: Date | null) => setFrom(d)}
            selectsStart
            startDate={from}
            endDate={to}
            dateFormat="yyyy-MM-dd"
            className="w-full border border-[#e6e8eb] rounded-lg px-3 py-2 text-sm"
            placeholderText="Start date"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-[#637588] mb-1">To</label>
          <DatePicker
            selected={to}
            onChange={(d: Date | null) => setTo(d)}
            selectsEnd
            startDate={from}
            endDate={to}
            minDate={from || undefined}
            dateFormat="yyyy-MM-dd"
            className="w-full border border-[#e6e8eb] rounded-lg px-3 py-2 text-sm"
            placeholderText="End date"
          />
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handlePreview}
          disabled={loading}
          className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Preview'}
        </button>
        <button
          onClick={() => handleDownload('pdf')}
          className="flex items-center gap-2 px-4 py-2 bg-[#f0f2f5] text-[#111518] rounded-lg text-sm font-medium hover:bg-[#e6e8eb] transition-colors"
        >
          <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>picture_as_pdf</span>
          Download PDF
        </button>
        <button
          onClick={() => handleDownload('csv')}
          className="flex items-center gap-2 px-4 py-2 bg-[#f0f2f5] text-[#111518] rounded-lg text-sm font-medium hover:bg-[#e6e8eb] transition-colors"
        >
          <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>table_chart</span>
          Download CSV
        </button>
      </div>

      {/* Report output */}
      {report && (
        <div className="space-y-6 pt-4 border-t border-[#e6e8eb]">
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[#637588]">
            <span>Period: <span className="font-medium text-[#111518]">{report.period}</span></span>
            <span>Scope: <span className="font-medium text-[#111518]">{report.scope}</span></span>
            <span>From: <span className="font-medium text-[#111518]">{fmtDate(report.from)}</span></span>
            <span>To: <span className="font-medium text-[#111518]">{fmtDate(report.to)}</span></span>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-[#f0f2f5] rounded-lg p-4">
              <p className="text-[#637588] text-xs font-medium mb-1">Total Cases</p>
              <p className="text-2xl font-bold text-[#111518]">{report.totals.cases}</p>
              {casesDelta !== null && (
                <p className={`text-xs mt-1 ${casesDelta > 0 ? 'text-red-500' : casesDelta < 0 ? 'text-green-500' : 'text-[#637588]'}`}>
                  {casesDelta > 0 ? '+' : ''}{casesDelta} vs prev
                </p>
              )}
            </div>
            <div className="bg-[#f0f2f5] rounded-lg p-4">
              <p className="text-[#637588] text-xs font-medium mb-1">Deaths</p>
              <p className="text-2xl font-bold text-red-600">{report.totals.deaths}</p>
            </div>
            <div className="bg-[#f0f2f5] rounded-lg p-4">
              <p className="text-[#637588] text-xs font-medium mb-1">CFR</p>
              <p className="text-2xl font-bold text-[#111518]">{(report.totals.cfr * 100).toFixed(1)}%</p>
            </div>
            <div className="bg-[#f0f2f5] rounded-lg p-4">
              <p className="text-[#637588] text-xs font-medium mb-1">Previous Cases</p>
              <p className="text-2xl font-bold text-[#111518]">{prevCases ?? 'N/A'}</p>
            </div>
          </div>

          {/* Risk distribution */}
          {riskDistData.length > 0 && (
            <div className="bg-[#f0f2f5] rounded-lg p-4">
              <h4 className="font-bold text-[#111518] mb-3">Risk-Level Distribution</h4>
              <div className="space-y-2">
                {riskDistData.map((entry) => (
                  <div key={entry.name} className="flex items-center gap-3">
                    <span className="text-sm text-[#637588] w-24">{entry.name}</span>
                    <div className="flex-1 h-3 bg-white rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${Math.min(100, (entry.value / Math.max(...riskDistData.map((d: { value: number }) => d.value), 1)) * 100)}%`, backgroundColor: entry.color }}
                      />
                    </div>
                    <span className="text-sm font-medium text-[#111518] w-8 text-right">{entry.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top hotspots */}
          {topHotspots.length > 0 && (
            <div className="bg-[#f0f2f5] rounded-lg p-4">
              <h4 className="font-bold text-[#111518] mb-3">Top Hotspots by Cases</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[#637588] border-b border-[#e6e8eb]">
                      <th className="py-2 pr-4">#</th>
                      <th className="py-2 pr-4">LGA</th>
                      <th className="py-2 pr-4">Cases</th>
                      <th className="py-2 pr-4">Deaths</th>
                      <th className="py-2">Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topHotspots.map((h, idx) => (
                      <tr key={h.lga_id ?? idx} className="border-b border-[#e6e8eb] last:border-0">
                        <td className="py-2 pr-4 text-[#637588]">{idx + 1}</td>
                        <td className="py-2 pr-4 font-medium text-[#111518]">{h.lga_name || 'Unknown'}</td>
                        <td className="py-2 pr-4 text-[#111518]">{h.cases ?? 0}</td>
                        <td className="py-2 pr-4 text-red-600">{h.deaths ?? 0}</td>
                        <td className="py-2">
                          <span
                            className="px-2 py-0.5 rounded text-xs font-medium"
                            style={{
                              color: SURVEILLANCE_RISK_COLORS[h.risk_level || ''] || '#637588',
                              backgroundColor: `${SURVEILLANCE_RISK_COLORS[h.risk_level || ''] || '#637588'}1a`,
                            }}
                          >
                            {h.risk_level || 'N/A'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TrendsReport() {
  // Mock trend data - in real app would come from API
  const weeklyTrend = [
    { week: 'Week 1', cases: 45, deaths: 2 },
    { week: 'Week 2', cases: 62, deaths: 3 },
    { week: 'Week 3', cases: 89, deaths: 4 },
    { week: 'Week 4', cases: 124, deaths: 5 },
    { week: 'Week 5', cases: 156, deaths: 7 },
    { week: 'Week 6', cases: 142, deaths: 6 },
    { week: 'Week 7', cases: 118, deaths: 4 },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <h4 className="font-bold text-[#111518] mb-4">Weekly Case Trend (Last 7 Weeks)</h4>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={weeklyTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
              <XAxis dataKey="week" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="cases" name="Cases" stroke="#1392ec" fill="#1392ec" fillOpacity={0.3} />
              <Area type="monotone" dataKey="deaths" name="Deaths" stroke="#fa6238" fill="#fa6238" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <h4 className="font-bold text-[#111518] mb-4">Epidemic Curve Analysis</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[#f0f2f5] rounded-lg p-4">
            <p className="text-[#637588] text-xs font-medium mb-1">Peak Week</p>
            <p className="text-xl font-bold text-[#111518]">Week 5</p>
            <p className="text-sm text-alert-orange">156 cases</p>
          </div>
          <div className="bg-[#f0f2f5] rounded-lg p-4">
            <p className="text-[#637588] text-xs font-medium mb-1">Current Trend</p>
            <p className="text-xl font-bold text-env-green">Declining</p>
            <p className="text-sm text-[#637588]">-24% from peak</p>
          </div>
          <div className="bg-[#f0f2f5] rounded-lg p-4">
            <p className="text-[#637588] text-xs font-medium mb-1">Avg CFR</p>
            <p className="text-xl font-bold text-[#111518]">4.1%</p>
            <p className="text-sm text-[#637588]">Below threshold</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReportsView() {
  const [activeReport, setActiveReport] = useState<ReportType>('overview');

  const reportTabs: { id: ReportType; label: string; icon: string }[] = [
    { id: 'overview', label: 'Overview', icon: 'dashboard' },
    { id: 'lga', label: 'LGA Report', icon: 'location_on' },
    { id: 'environmental', label: 'Environmental', icon: 'water_drop' },
    { id: 'trends', label: 'Trends', icon: 'trending_up' },
  ];

  const handleExport = () => {
    // In real app, would generate PDF
    alert('PDF export would be triggered here');
  };

  return (
    <div className="space-y-6">
      {/* Report Type Selector */}
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-2 flex gap-2 overflow-x-auto">
        {reportTabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveReport(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              activeReport === tab.id
                ? 'bg-primary text-white'
                : 'text-[#637588] hover:bg-[#f0f2f5]'
            }`}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Report Header */}
      <ReportHeader
        title={reportTabs.find(t => t.id === activeReport)?.label || 'Report'}
        subtitle={`Generated on ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`}
        onExport={handleExport}
      />

      {/* Report Content */}
      {activeReport === 'overview' && <OverviewReport />}
      {activeReport === 'lga' && <LGAReport />}
      {activeReport === 'environmental' && <EnvironmentalReport />}
      {activeReport === 'trends' && <TrendsReport />}

      {/* Surveillance Report Panel */}
      <div className="pt-6 border-t border-[#e6e8eb]">
        <SurveillanceReportPanel />
      </div>
    </div>
  );
}
