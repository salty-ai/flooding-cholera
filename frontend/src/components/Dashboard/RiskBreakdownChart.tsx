import { useRiskScores } from '../../hooks/useApi';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';

export function RiskBreakdownChart() {
  const { data: scores, isLoading } = useRiskScores();
  const top = (scores ?? [])
    .slice()
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 8)
    .map((s) => ({
      name: s.lga_name ?? `LGA ${s.lga_id}`,
      case_score: Math.round((s.case_score ?? 0) * 100),
      flood_score: Math.round((s.flood_score ?? 0) * 100),
      flood_event_score: Math.round((s.flood_event_score ?? 0) * 100),
      vulnerability_score: Math.round((s.vulnerability_score ?? 0) * 100),
      total_score: Math.round((s.score ?? 0) * 100),
    }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <h3 className="font-bold text-[#111518] text-xs sm:text-sm mb-1">📊 Top Risk LGAs — Multi-Factor Vulnerability</h3>
      <p className="text-[10px] sm:text-xs text-gray-500 mb-3">Composite risk breakdown (Epidemiological, Flood, Infrastructure)</p>
      {isLoading && <div className="text-xs text-gray-400 py-6 text-center">Loading risk scores...</div>}
      {!isLoading && top.length === 0 && <div className="text-xs text-gray-400 py-6 text-center">No risk scores available</div>}
      <div className="h-[220px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={top}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
            <Tooltip contentStyle={{ fontSize: '11px', borderRadius: '8px', border: '1px solid #e5e7eb' }} />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            <Bar dataKey="case_score" name="Case Severity" stackId="a" fill="#1392ec" />
            <Bar dataKey="flood_score" name="Satellite Flood" stackId="a" fill="#fa6238" />
            <Bar dataKey="flood_event_score" name="Disaster Impact" stackId="a" fill="#6b3ed6" />
            <Bar dataKey="vulnerability_score" name="Infrastructure Gap" stackId="a" fill="#10b981" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
