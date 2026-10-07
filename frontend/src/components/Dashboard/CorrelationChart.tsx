import { useCorrelation } from '../../hooks/useApi';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

export function CorrelationChart() {
  const { data, isLoading } = useCorrelation({ from_year: 2020, to_year: 2025 });

  const rows = (data?.lags ?? []).map((r: { lag: number; pearson_r?: number | null; insufficient_data?: boolean; n?: number }) => ({
    lag: r.lag === 0 ? '0 (same)' : `+${r.lag}m`,
    coefficient: typeof r.pearson_r === 'number' ? Number(r.pearson_r.toFixed(2)) : 0,
    insufficient: !!r.insufficient_data,
    n: r.n ?? 0,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <h3 className="font-bold text-[#111518] text-xs sm:text-sm mb-1">📈 Flood ↔ Cholera Time-Lag Correlation</h3>
      <p className="text-[10px] sm:text-xs text-gray-500 mb-3">Pearson r coefficient across monthly time lags (2020–2025)</p>
      {isLoading && <div className="text-xs text-gray-400 py-6 text-center">Loading correlation calculations...</div>}
      {!isLoading && rows.length === 0 && <div className="text-xs text-gray-400 py-6 text-center">No correlation data available</div>}
      <div className="h-[220px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="lag" tick={{ fontSize: 10 }} />
            <YAxis domain={[-1, 1]} tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{ fontSize: '11px', borderRadius: '8px', border: '1px solid #e5e7eb' }}
              formatter={(value: number, _name, props) => [
                value,
                props?.payload?.insufficient ? `r = ${value} (n=${props?.payload?.n ?? 0})` : `Pearson r = ${value} (n=${props?.payload?.n ?? 0})`,
              ]}
            />
            <Bar dataKey="coefficient" name="Pearson r" fill="#6b3ed6">
              {rows.map((r: { insufficient: boolean }, i: number) => (
                <Cell key={i} fill={r.insufficient ? '#9ca3af' : '#6b3ed6'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
