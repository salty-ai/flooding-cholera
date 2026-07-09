import { useAlerts } from '../../hooks/useApi';
import { useNavigate } from 'react-router-dom';

export function ActiveAlertsRail() {
  const { data: alerts, isLoading } = useAlerts({ is_acknowledged: false });
  const navigate = useNavigate();
  const top = (alerts ?? []).slice(0, 5);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">🚨 Active alerts</h3>
        <button className="text-xs text-blue-600" onClick={() => navigate('/alerts')}>View all</button>
      </div>
      {isLoading && <div className="text-xs text-gray-400">Loading…</div>}
      {!isLoading && top.length === 0 && <div className="text-xs text-gray-400">No active alerts</div>}
      <ul className="space-y-1">
        {top.map((a) => (
          <li key={a.id} className="text-xs flex justify-between">
            <span>{a.title ?? a.type}</span>
            <span className={a.severity === 'critical' ? 'text-red-600' : 'text-yellow-600'}>
              {a.severity}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
