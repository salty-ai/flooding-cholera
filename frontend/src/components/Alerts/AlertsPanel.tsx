import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow, parseISO, isValid } from 'date-fns';
import { useAlerts, apiService } from '../../hooks/useApi';
import { useAppStore } from '../../store/appStore';
import { useAuthStore } from '../../store/authStore';
import { showToast } from '../common/Toast';
import AlertRulesPanel from './AlertRulesPanel';
import type { Alert, AlertSeverity } from '../../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

// Safely format date distance, handling invalid dates
function safeFormatDistanceToNow(dateString: string): string {
  try {
    const date = parseISO(dateString);
    if (!isValid(date)) {
      return 'recently';
    }
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return 'recently';
  }
}

const SEVERITY_CONFIG: Record<AlertSeverity, { bg: string; border: string; icon: string; iconBg: string; text: string }> = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: 'warning',
    iconBg: 'bg-red-100 text-red-600',
    text: 'text-red-800',
  },
  warning: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    icon: 'error',
    iconBg: 'bg-yellow-100 text-yellow-600',
    text: 'text-yellow-800',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: 'info',
    iconBg: 'bg-blue-100 text-blue-600',
    text: 'text-blue-800',
  },
};

interface AlertCardProps {
  alert: Alert;
  onLGAClick?: (lgaId: number) => void;
  onAcknowledge?: (alertId: string) => void;
  acknowledging?: boolean;
}

function AlertCard({ alert, onLGAClick, onAcknowledge, acknowledging }: AlertCardProps) {
  const config = SEVERITY_CONFIG[alert.severity];
  const numericId = Number(alert.id);

  return (
    <div
      className={`${config.bg} ${config.border} border rounded-xl p-4 transition-all hover:shadow-md`}
      role="alert"
      aria-live={alert.severity === 'critical' ? 'assertive' : 'polite'}
    >
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-lg ${config.iconBg} flex items-center justify-center flex-shrink-0`}>
          <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>{config.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className={`text-sm font-semibold ${config.text}`}>{alert.title}</h4>
            <div className="flex items-center gap-2 flex-shrink-0">
              {alert.read && (
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-[#e6e8eb] text-[#637588]">
                  acknowledged
                </span>
              )}
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                alert.severity === 'critical' ? 'bg-red-200 text-red-800' :
                alert.severity === 'warning' ? 'bg-yellow-200 text-yellow-800' : 'bg-blue-200 text-blue-800'
              }`}>
                {alert.severity}
              </span>
            </div>
          </div>
          <p className={`text-sm ${config.text} opacity-80 mt-1`}>{alert.message}</p>
          <div className="flex items-center gap-3 mt-3">
            <span className="text-xs text-[#637588]">
              {safeFormatDistanceToNow(alert.created_at)}
            </span>
            {alert.lga_name && (
              <span className="text-xs text-[#637588] flex items-center gap-1">
                <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>location_on</span>
                {alert.lga_name}
              </span>
            )}
            {alert.lga_id && onLGAClick && (
              <button
                onClick={() => onLGAClick(alert.lga_id!)}
                className="text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1"
                aria-label={`View ${alert.lga_name} on map`}
              >
                <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>map</span>
                View on map
              </button>
            )}
            {!alert.read && onAcknowledge && !Number.isNaN(numericId) && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                disabled={acknowledging}
                className="text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1 disabled:opacity-50"
                aria-label={`Acknowledge alert ${alert.title}`}
              >
                <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>check_circle</span>
                {acknowledging ? 'Acknowledging...' : 'Acknowledge'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

type FilterType = 'all' | AlertSeverity;
type AckFilterType = 'all' | 'unacknowledged' | 'acknowledged';

interface AlertFilters {
  severity?: string;
  is_acknowledged?: boolean;
  lga_id?: number;
}

export default function AlertsPanel() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [severityFilter, setSeverityFilter] = useState<FilterType>('all');
  const [ackFilter, setAckFilter] = useState<AckFilterType>('all');
  const [lgaIdInput, setLgaIdInput] = useState('');
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  const filters: AlertFilters = {};
  if (severityFilter !== 'all') filters.severity = severityFilter;
  if (ackFilter === 'unacknowledged') filters.is_acknowledged = false;
  if (ackFilter === 'acknowledged') filters.is_acknowledged = true;
  const lgaIdNum = lgaIdInput.trim() ? Number(lgaIdInput) : NaN;
  if (!Number.isNaN(lgaIdNum)) filters.lga_id = lgaIdNum;

  const { data: alerts, isLoading, error, refetch } = useAlerts(filters);
  const { setSelectedLGAId } = useAppStore();
  const [filter, setFilter] = useState<FilterType>('all');

  const filteredAlerts = filter === 'all'
    ? alerts
    : alerts?.filter(a => a.severity === filter);

  const criticalCount = alerts?.filter((a) => a.severity === 'critical').length || 0;
  const warningCount = alerts?.filter((a) => a.severity === 'warning').length || 0;
  const infoCount = alerts?.filter((a) => a.severity === 'info').length || 0;

  const handleLGAClick = (lgaId: number) => {
    setSelectedLGAId(lgaId);
  };

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: string) =>
      apiService.acknowledgeAlert(Number(alertId), { user_id: user?.id ?? null }),
    onMutate: (alertId) => setAcknowledgingId(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      showToast.success('Alert acknowledged');
    },
    onError: () => showToast.error('Failed to acknowledge alert'),
    onSettled: () => setAcknowledgingId(null),
  });

  const handleAcknowledge = (alertId: string) => {
    acknowledgeMutation.mutate(alertId);
  };

  const handleExport = () => {
    window.open(`${API_BASE}/alerts/export`);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-[#f0f2f5] rounded w-1/3"></div>
            <div className="grid grid-cols-3 gap-4">
              <div className="h-20 bg-[#f0f2f5] rounded-xl"></div>
              <div className="h-20 bg-[#f0f2f5] rounded-xl"></div>
              <div className="h-20 bg-[#f0f2f5] rounded-xl"></div>
            </div>
            <div className="h-24 bg-[#f0f2f5] rounded-xl"></div>
            <div className="h-24 bg-[#f0f2f5] rounded-xl"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-8 text-center">
        <span className="material-symbols-outlined text-red-400 mb-3" style={{ fontSize: '48px' }}>error</span>
        <p className="text-sm font-medium text-red-600">Failed to load alerts</p>
        <button
          onClick={() => refetch()}
          className="mt-3 text-sm text-primary hover:text-primary/80 font-medium flex items-center gap-1 mx-auto"
        >
          <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>refresh</span>
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-[#111518]">Alerts & Notifications</h2>
          <p className="text-sm text-[#637588] mt-1">Monitor risk alerts and outbreak notifications</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-2 bg-[#f0f2f5] text-[#637588] rounded-lg text-sm font-medium hover:bg-[#e6e8eb] transition-colors"
            aria-label="Export alerts as CSV"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>download</span>
            Export CSV
          </button>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-3 py-2 bg-[#f0f2f5] text-[#637588] rounded-lg text-sm font-medium hover:bg-[#e6e8eb] transition-colors"
            aria-label="Refresh alerts"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>refresh</span>
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col">
            <label className="text-xs font-medium text-[#637588] mb-1">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as FilterType)}
              className="px-3 py-2 text-sm border border-[#e6e8eb] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            >
              <option value="all">All severities</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-medium text-[#637588] mb-1">Status</label>
            <select
              value={ackFilter}
              onChange={(e) => setAckFilter(e.target.value as AckFilterType)}
              className="px-3 py-2 text-sm border border-[#e6e8eb] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            >
              <option value="all">All</option>
              <option value="unacknowledged">Unacknowledged</option>
              <option value="acknowledged">Acknowledged</option>
            </select>
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-medium text-[#637588] mb-1">LGA ID</label>
            <input
              type="number"
              min={1}
              value={lgaIdInput}
              onChange={(e) => setLgaIdInput(e.target.value)}
              placeholder="e.g. 12"
              className="px-3 py-2 text-sm border border-[#e6e8eb] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary w-32"
            />
          </div>
          {(severityFilter !== 'all' || ackFilter !== 'all' || lgaIdInput.trim() !== '') && (
            <button
              onClick={() => {
                setSeverityFilter('all');
                setAckFilter('all');
                setLgaIdInput('');
              }}
              className="px-3 py-2 text-sm text-primary hover:text-primary/80 font-medium"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
            <span className="material-symbols-outlined text-red-600" style={{ fontSize: '24px' }}>warning</span>
          </div>
          <div>
            <p className="text-2xl font-bold text-red-600">{criticalCount}</p>
            <p className="text-sm text-[#637588]">Critical Alerts</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-yellow-100 flex items-center justify-center">
            <span className="material-symbols-outlined text-yellow-600" style={{ fontSize: '24px' }}>error</span>
          </div>
          <div>
            <p className="text-2xl font-bold text-yellow-600">{warningCount}</p>
            <p className="text-sm text-[#637588]">Warnings</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-[#e6e8eb] p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
            <span className="material-symbols-outlined text-blue-600" style={{ fontSize: '24px' }}>info</span>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-600">{infoCount}</p>
            <p className="text-sm text-[#637588]">Informational</p>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-2 flex gap-2 overflow-x-auto">
        {(['all', 'critical', 'warning', 'info'] as FilterType[]).map(type => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              filter === type
                ? 'bg-primary text-white'
                : 'text-[#637588] hover:bg-[#f0f2f5]'
            }`}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              {type === 'all' ? 'notifications' : SEVERITY_CONFIG[type as AlertSeverity].icon}
            </span>
            {type === 'all' ? 'All Alerts' : type.charAt(0).toUpperCase() + type.slice(1)}
            {type !== 'all' && (
              <span className={`px-1.5 py-0.5 rounded text-xs ${
                filter === type ? 'bg-white/20' : 'bg-[#e6e8eb]'
              }`}>
                {type === 'critical' ? criticalCount : type === 'warning' ? warningCount : infoCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Alerts List */}
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-[#111518]">
            {filter === 'all' ? 'All Alerts' : `${filter.charAt(0).toUpperCase() + filter.slice(1)} Alerts`}
          </h3>
          <span className="text-sm text-[#637588]">{filteredAlerts?.length || 0} total</span>
        </div>

        {!filteredAlerts || filteredAlerts.length === 0 ? (
          <div className="text-center py-12">
            <span className="material-symbols-outlined text-[#637588] mb-3" style={{ fontSize: '48px' }}>
              check_circle
            </span>
            <p className="text-sm font-medium text-[#111518]">No active alerts</p>
            <p className="text-xs text-[#637588] mt-1">All areas are within normal risk levels</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onLGAClick={handleLGAClick}
                onAcknowledge={handleAcknowledge}
                acknowledging={acknowledgingId === alert.id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Alert Rules Management */}
      <AlertRulesPanel />
    </div>
  );
}
