import { useDashboard, useRiskScores, useSatelliteThumbnail } from '../../hooks/useApi';
import { useSatelliteFeedLogic, useChartDataLogic, useRiskChartLogic } from '../../hooks/useDashboardLogic';
import ChoroplethMap from '../Map/ChoroplethMap';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { useMemo } from 'react';
import clsx from 'clsx';
import FloodCholeraChart from './FloodCholeraChart';
import {
  ComposedChart,
  Area,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from 'recharts';

interface KPICardProps {
  title: string;
  value: string | number;
  icon: string;
  iconColor: string;
  trend?: { value: string; isPositive: boolean };
  subtitle?: string;
}

function KPICard({ title, value, icon, iconColor, trend, subtitle }: KPICardProps) {
  const bgColor = iconColor === 'primary' ? 'bg-primary/10 text-primary'
    : iconColor === 'orange' ? 'bg-alert-orange/10 text-alert-orange'
      : 'bg-env-green/10 text-env-green';

  return (
    <div className="rounded-xl border border-[#e6e8eb] bg-white p-5 shadow-sm">
      <div className="flex justify-between items-start mb-2">
        <p className="text-[#637588] text-sm font-medium">{title}</p>
        <span className={`material-symbols-outlined ${bgColor} p-1.5 rounded-lg`} style={{ fontSize: '20px' }}>
          {icon}
        </span>
      </div>
      <p className="text-3xl font-bold tracking-tight mb-1 text-[#111518]">{value}</p>
      {trend && (
        <p className={`text-sm font-medium flex items-center gap-1 ${trend.isPositive ? 'text-env-green' : 'text-alert-orange'}`}>
          <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
            {trend.isPositive ? 'trending_down' : 'trending_up'}
          </span>
          {trend.value}
        </p>
      )}
      {subtitle && !trend && (
        <p className="text-[#637588] text-sm font-medium">{subtitle}</p>
      )}
    </div>
  );
}

function SatelliteThumbnail({ lgaId, name, riskLevel }: { lgaId: number, name: string, riskLevel: 'high' | 'medium' | 'low' }) {
  const { data, isLoading, error } = useSatelliteThumbnail(lgaId);

  const bgColor = clsx({
    'bg-red-500': riskLevel === 'high',
    'bg-yellow-500': riskLevel === 'medium',
    'bg-env-green': riskLevel === 'low',
  });
  const textColor = clsx({
    'text-red-400': riskLevel === 'high',
    'text-yellow-400': riskLevel === 'medium',
    'text-env-green': riskLevel === 'low',
  });

  return (
    <div className="flex flex-col gap-2">
      <div
        className="aspect-video w-full rounded-lg relative overflow-hidden group cursor-pointer bg-slate-50 border border-slate-100"
      >
        {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
                <div className={`animate-spin rounded-full h-8 w-8 border-b-2 ${textColor}`}></div>
            </div>
        ) : error || !data?.url ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-50">
                <div className="flex flex-col items-center gap-2">
                    <span className={`material-symbols-outlined ${textColor} opacity-50`} style={{ fontSize: '32px' }}>
                    satellite_alt
                    </span>
                    <span className="text-[10px] text-slate-400 font-medium">Imagery Unavailable</span>
                </div>
            </div>
        ) : (
            <img src={data.url} alt={`Satellite view of ${name}`} className="w-full h-full object-cover" />
        )}

        <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur px-2 py-1 rounded text-[10px] text-white z-10 font-medium">
          {name}
        </div>
        <div className={`absolute top-2 right-2 size-2.5 rounded-full ${bgColor} animate-pulse z-10 ring-2 ring-white/20`}></div>
      </div>
    </div>
  );
}

function SatelliteFeed() {
  const { feedItems, isLoading } = useSatelliteFeedLogic();
  const { data: riskScores } = useRiskScores();

  const displayLgas = useMemo(() => {
    if (!riskScores || riskScores.length === 0) {
      return [];
    }

    return [...riskScores]
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(score => ({
        id: score.lga_id,
        name: score.lga_name || `LGA ${score.lga_id}`,
        level: (score.level === 'red'
          ? 'high'
          : score.level === 'yellow'
            ? 'medium'
            : 'low') as 'high' | 'medium' | 'low',
      }));
  }, [riskScores]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[#e6e8eb] flex flex-col h-full overflow-hidden">
        <div className="p-4 border-b border-[#e6e8eb]">
          <div className="h-4 bg-gray-200 rounded w-1/2 animate-pulse"></div>
        </div>
        <div className="p-4 flex-1 space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="aspect-video w-full rounded-lg bg-gray-100 animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[#e6e8eb] flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-[#e6e8eb] flex justify-between items-center">
        <h3 className="font-bold text-[#111518] text-sm">Environmental Feed</h3>
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/20 text-primary">LIVE</span>
      </div>
      <div className="p-4 flex flex-col gap-4 overflow-y-auto flex-1">
        {feedItems.length > 0 ? (
          feedItems.map((img, idx) => (
            <div key={idx} className="flex flex-col gap-2">
              <div
                className="aspect-video w-full rounded-lg relative overflow-hidden group cursor-pointer"
                style={{
                  background: `linear-gradient(135deg, ${img.color === 'red' ? '#fef2f2' : img.color === 'yellow' ? '#fefce8' : '#f0fdf4'} 0%, ${img.color === 'red' ? '#fee2e2' : img.color === 'yellow' ? '#fef9c3' : '#dcfce7'} 100%)`
                }}
              >
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className={`material-symbols-outlined ${img.color === 'red' ? 'text-red-400' : img.color === 'yellow' ? 'text-yellow-400' : 'text-green-400'}`} style={{ fontSize: '48px' }}>
                    satellite_alt
                  </span>
                </div>
                <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur px-2 py-1 rounded text-[10px] text-white">
                  {img.label} • {img.time}
                </div>
                <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/60 backdrop-blur px-2 py-1 rounded">
                  <span className={`size-2 rounded-full ${img.color === 'red' ? 'bg-red-500' : img.color === 'yellow' ? 'bg-yellow-500' : 'bg-green-500'} animate-pulse`}></span>
                  <span className="text-[10px] text-white">NDWI: {img.ndwi.toFixed(2)}</span>
                </div>
              </div>
            </div>
          ))
        ) : (
          displayLgas.map((lga, idx) => (
            <SatelliteThumbnail
              key={`${lga.id}-${idx}`}
              lgaId={lga.id}
              name={lga.name}
              riskLevel={lga.level}
            />
          ))
        )}
      </div>
    </div>
  );
}

export function CaseRainfallChart() {
  const { chartData } = useChartDataLogic();

  return (
    <div className="bg-white rounded-xl border border-[#e6e8eb] p-6 flex flex-col">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-base font-bold text-[#111518]">Case Rate vs. Precipitation</h3>
          <p className="text-[#637588] text-sm mt-1">Correlation over past 7 days</p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-primary"></span>
            <span className="text-xs text-[#637588]">Rainfall (mm)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-alert-orange"></span>
            <span className="text-xs text-[#637588]">Cases</span>
          </div>
        </div>
      </div>
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 11, fill: '#637588' }}
              axisLine={{ stroke: '#e6e8eb' }}
              tickLine={false}
            />
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 10, fill: '#637588' }}
              axisLine={false}
              tickLine={false}
              label={{ value: 'mm', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#637588' }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 10, fill: '#637588' }}
              axisLine={false}
              tickLine={false}
              label={{ value: 'Cases', angle: 90, position: 'insideRight', fontSize: 10, fill: '#637588' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e6e8eb',
                borderRadius: '8px',
                fontSize: '12px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '11px' }} />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="rainfall"
              name="Rainfall"
              fill="#1392ec30"
              stroke="#1392ec"
              strokeWidth={2}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="cases"
              name="Cases"
              stroke="#fa6238"
              strokeWidth={3}
              dot={{ fill: '#fa6238', strokeWidth: 0, r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function FloodingRiskChart() {
  const { regions, maxRisk, criticalCount, isLoading } = useRiskChartLogic();

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-6"></div>
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex items-center gap-3">
              <div className="h-3 bg-gray-200 rounded w-20"></div>
              <div className="h-3 bg-gray-100 rounded flex-1"></div>
              <div className="h-3 bg-gray-200 rounded w-10"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[#e6e8eb] p-6 flex flex-col">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-base font-bold text-[#111518]">Flooding Risk by LGA</h3>
          <p className="text-[#637588] text-sm mt-1">Current risk based on water levels</p>
        </div>
        <span className={`${maxRisk > 70 ? 'bg-alert-orange/20 text-alert-orange' : maxRisk > 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-env-green'} text-xs font-bold px-2 py-1 rounded`}>
          {criticalCount > 0 ? `${criticalCount} CRITICAL` : 'NORMAL'}
        </span>
      </div>
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={regions} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#e6e8eb" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, 100]}
              tick={{ fontSize: 10, fill: '#637588' }}
              tickFormatter={(value) => `${value}%`}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11, fill: '#637588' }}
              width={90}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e6e8eb',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value: number) => [`${value}%`, 'Risk Score']}
            />
            <Bar dataKey="risk" radius={[0, 4, 4, 0]}>
              {regions.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function DashboardView() {
  const { data: dashboard, isLoading } = useDashboard();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const alertLevel = (dashboard?.lgas_high_risk || 0) > 0 ? 'High' :
    (dashboard?.lgas_medium_risk || 0) > 0 ? 'Medium' : 'Low';

  return (
    <div className="flex flex-col gap-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Confirmed Cases"
          value={dashboard?.total_cases || 0}
          icon="coronavirus"
          iconColor="primary"
          trend={{ value: `${dashboard?.lgas_high_risk || 0} high-risk LGAs`, isPositive: false }}
        />
        <KPICard
          title="Active Outbreaks"
          value={dashboard?.lgas_high_risk || 0}
          icon="warning"
          iconColor="orange"
          trend={{ value: `+${dashboard?.lgas_medium_risk || 0} at-risk`, isPositive: false }}
        />
        <KPICard
          title="Alert Level"
          value={alertLevel}
          icon="notifications_active"
          iconColor="orange"
          subtitle={`${dashboard?.total_lgas || 18} LGAs monitored`}
        />
        <KPICard
          title="Rainfall (7d)"
          value={`${dashboard?.avg_rainfall_7day?.toFixed(0) || 0}mm`}
          icon="water_drop"
          iconColor="green"
          trend={{ value: 'Above threshold', isPositive: false }}
        />
      </div>

      {/* Main Grid: Map & Satellite Feed */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6" style={{ minHeight: '500px' }}>
        {/* Interactive Map */}
        <div className="xl:col-span-9 flex flex-col rounded-xl overflow-hidden border border-[#e6e8eb] bg-white relative">
          {/* Map Header */}
          <div className="p-4 border-b border-[#e6e8eb] flex justify-between items-center bg-white z-10">
            <h3 className="font-bold text-[#111518] text-sm">Geospatial Risk Map</h3>
            <div className="flex gap-4 text-xs">
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-red-500"></span> High
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-yellow-400"></span> Medium
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-green-500"></span> Low
              </span>
            </div>
          </div>
          {/* Map Container */}
          <div className="flex-1 relative min-h-[400px]">
            <ErrorBoundary>
              <ChoroplethMap />
            </ErrorBoundary>
          </div>
        </div>

        {/* Satellite Feed */}
        <div className="xl:col-span-3 h-full min-h-[400px]">
          <SatelliteFeed />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FloodCholeraChart />
        <FloodingRiskChart />
      </div>
    </div>
  );
}

