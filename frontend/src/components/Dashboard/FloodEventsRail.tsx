import { useFloodEvents } from '../../hooks/useApi';
import { useDateRangeStore } from '../../store/dateRangeStore';

export function FloodEventsRail() {
  const { start, end } = useDateRangeStore();
  const { data: events, isLoading } = useFloodEvents({
    start_date: start ?? undefined,
    end_date: end ?? undefined,
    limit: 5,
  });
  const top = events ?? [];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <h3 className="font-semibold text-sm mb-2">🌊 Recent flood events</h3>
      {isLoading && <div className="text-xs text-gray-400">Loading…</div>}
      {!isLoading && top.length === 0 && <div className="text-xs text-gray-400">No flood events in window</div>}
      <ul className="space-y-1">
        {top.map((e) => (
          <li key={e.id} className="text-xs flex justify-between">
            <span>{e.lga_name ?? 'Unknown LGA'}</span>
            <span className="text-gray-500">
              {e.duration_days ?? 0}d · {Math.round(e.area_km2 ?? 0)}km²
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
