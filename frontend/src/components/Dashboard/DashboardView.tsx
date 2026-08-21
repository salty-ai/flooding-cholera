import { useDashboard } from '../../hooks/useApi';
import { useDateRangeStore } from '../../store/dateRangeStore';
import { DateRangeSelector } from './DateRangeSelector';
import { DashboardKpiRow } from './DashboardKpiRow';
import { ActiveAlertsRail } from './ActiveAlertsRail';
import { FloodEventsRail } from './FloodEventsRail';
import { CorrelationChart } from './CorrelationChart';
import { RiskBreakdownChart } from './RiskBreakdownChart';
import ChoroplethMap from '../Map/ChoroplethMap';
import { ErrorBoundary } from '../common/ErrorBoundary';

export default function DashboardView() {
  const { start, end } = useDateRangeStore();
  const { data: dashboard, isLoading } = useDashboard(start, end);

  if (isLoading && !dashboard) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 sm:gap-6">
      <DateRangeSelector maxDataDate={dashboard?.max_data_date ?? null} />
      <DashboardKpiRow summary={dashboard} />

      {/* Main Grid: Map + right rail of alerts/floods */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-6">
        <div className="xl:col-span-2 flex flex-col rounded-xl overflow-hidden border border-[#e6e8eb] bg-white shadow-sm">
          <div className="p-3 sm:p-4 border-b border-[#e6e8eb] flex flex-row justify-between items-center bg-white z-10">
            <h3 className="font-bold text-[#111518] text-xs sm:text-sm">Geospatial Risk Map</h3>
            <div className="flex gap-2 sm:gap-4 text-[10px] sm:text-xs">
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
          <div className="flex-1 relative min-h-[320px] sm:min-h-[450px]">
            <ErrorBoundary>
              <ChoroplethMap />
            </ErrorBoundary>
          </div>
        </div>

        <div className="flex flex-col gap-4 sm:gap-6">
          <ActiveAlertsRail />
          <FloodEventsRail />
        </div>
      </div>

      {/* Bottom charts: real correlation + v2.0 risk breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <CorrelationChart />
        <RiskBreakdownChart />
      </div>
    </div>
  );
}
