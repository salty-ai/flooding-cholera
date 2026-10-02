import ChoroplethMap from '../Map/ChoroplethMap';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { useAppStore } from '../../store/appStore';
import { useLgaAnalytics } from '../../hooks/useApi';

export default function MapOnlyView() {
  const { selectedLGAId, selectedLGA } = useAppStore();
  const { data: analytics } = useLgaAnalytics(selectedLGAId, 30);

  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Full Map */}
      <div className="flex-1 rounded-xl overflow-hidden border border-[#e6e8eb] bg-white relative min-h-[400px] sm:min-h-[600px]">
        {/* Map Header */}
        <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-center bg-white/95 backdrop-blur z-10 border-b border-[#e6e8eb]">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-primary" style={{ fontSize: '24px' }}>map</span>
            <div>
              <h3 className="font-bold text-[#111518] text-sm">
                {selectedLGA ? selectedLGA.name : 'Nigeria (774 LGAs)'}
              </h3>
              <p className="text-xs text-[#637588]">
                {selectedLGA ? `Population: ${selectedLGA.population?.toLocaleString() || 'N/A'}` : 'Select an LGA to view details'}
              </p>
            </div>
          </div>
          <div className="flex gap-4 text-xs">
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-red-500"></span> High Risk
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
        <div className="h-full pt-16">
          <ErrorBoundary>
            <ChoroplethMap />
          </ErrorBoundary>
        </div>
      </div>

      {/* Quick Stats Bar (if LGA selected) */}
      {selectedLGA && analytics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
            <p className="text-[#637588] text-xs font-medium mb-1">Total Cases (30d)</p>
            <p className="text-2xl font-bold text-[#111518]">{analytics.total_cases || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
            <p className="text-[#637588] text-xs font-medium mb-1">Deaths</p>
            <p className="text-2xl font-bold text-alert-orange">{analytics.total_deaths || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
            <p className="text-[#637588] text-xs font-medium mb-1">CFR</p>
            <p className="text-2xl font-bold text-[#111518]">
              {analytics.total_cases > 0 ? ((analytics.total_deaths / analytics.total_cases) * 100).toFixed(1) : 0}%
            </p>
          </div>
          <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
            <p className="text-[#637588] text-xs font-medium mb-1">Risk Score</p>
            <p className={`text-2xl font-bold ${
              analytics.current_risk_level === 'red' ? 'text-red-500' :
              analytics.current_risk_level === 'yellow' ? 'text-yellow-500' : 'text-green-500'
            }`}>
              {((analytics.avg_risk_score || 0) * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
