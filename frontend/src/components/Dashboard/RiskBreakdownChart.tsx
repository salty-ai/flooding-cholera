import { useRiskScores } from '../../hooks/useApi';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';

export function RiskBreakdownChart() {
  const { data: scores, isLoading } = useRiskScores();
  const top = (scores ?? [])
    .slice()
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 5)
    .map((s) => ({
      name: s.lga_name ?? `LGA ${s.lga_id}`,
      case_score: Math.round((s.case_score ?? 0) * 100),
      flood_score: Math.round((s.flood_score ?? 0) * 100),
      flood_event_score: Math.round((s.flood_event_score ?? 0) * 100),
    }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <h3 className="font-semibold text-sm mb-2">📊 Top LGAs — v2.0 risk breakdown</h3>
      {isLoading && <div className="text-xs text-gray-400">Loading…</div>}
      {!isLoading && top.length === 0 && <div className="text-xs text-gray-400">No risk scores</div>}
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={top}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip contentStyle={{ fontSize: '11px', borderRadius: '8px', border: '1px solid #e5e7eb' }} />
          <Legend wrapperStyle={{ fontSize: '10px' }} />
          <Bar dataKey="case_score" stackId="a" fill="#1392ec" />
          <Bar dataKey="flood_score" stackId="a" fill="#fa6238" />
          <Bar dataKey="flood_event_score" stackId="a" fill="#6b3ed6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
