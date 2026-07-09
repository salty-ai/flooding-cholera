import { useCorrelation } from '../../hooks/useApi';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

// Maps the backend /analytics/correlation response, which returns a `lags`
// array of { lag, pearson_r, p_value, n, insufficient_data } (lag in months),
// NOT a by_year coefficient series. Plots Pearson r per lag month.
export function CorrelationChart() {
  const currentYear = new Date().getFullYear();
  const { data, isLoading } = useCorrelation({ from_year: currentYear - 2, to_year: currentYear });

  const rows = (data?.lags ?? []).map((r: any) => ({
    lag: r.lag === 0 ? '0 (same)' : `+${r.lag}m`,
    coefficient: typeof r.pearson_r === 'number' ? Number(r.pearson_r.toFixed(2)) : 0,
    insufficient: !!r.insufficient_data,
    n: r.n ?? 0,
  }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <h3 className="font-semibold text-sm mb-2">📈 Flood ↔ Cholera correlation</h3>
      <div className="text-[10px] text-gray-400 mb-1">Pearson r by flood→cases lag (months)</div>
      {isLoading && <div className="text-xs text-gray-400">Loading…</div>}
      {!isLoading && rows.length === 0 && <div className="text-xs text-gray-400">No correlation data</div>}
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="lag" tick={{ fontSize: 10 }} />
          <YAxis domain={[-1, 1]} tick={{ fontSize: 10 }} />
          <Tooltip
            contentStyle={{ fontSize: '11px', borderRadius: '8px', border: '1px solid #e5e7eb' }}
            formatter={(value: number, _name, props) => [
              value,
              props?.payload?.insufficient ? `${value} (insufficient, n=${props?.payload?.n ?? 0})` : `r (n=${props?.payload?.n ?? 0})`,
            ]}
          />
          <Bar dataKey="coefficient" fill="#6b3ed6">
            {rows.map((r: { insufficient: boolean }, i: number) => (
              <Cell key={i} fill={r.insufficient ? '#d1d5db' : '#6b3ed6'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
