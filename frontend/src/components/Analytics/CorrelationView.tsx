// frontend/src/components/Analytics/CorrelationView.tsx
import { useMemo, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from "recharts";
import { apiService } from "../../hooks/useApi";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

interface LagRow { lag: number; pearson_r: number | null; p_value: number | null; n: number; insufficient_data: boolean; }
interface SeriesPt { year: number; month: number; }
interface Report {
  lags: LagRow[];
  flood_series: (SeriesPt & { count: number; area: number })[];
  case_series: (SeriesPt & { cases: number })[];
  caveat: string;
}

export default function CorrelationView() {
  const [scope, setScope] = useState<"national" | "lga" | "state">("national");
  const [lgaId, setLgaId] = useState<number | "">("");
  const [state, setState] = useState("");
  const [from, setFrom] = useState(2020);
  const [to, setTo] = useState(2025);
  const [data, setData] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const params: any = { from_year: from, to_year: to };
      if (scope === "lga" && lgaId) params.lga_id = lgaId;
      if (scope === "state" && state) params.state = state;
      const data = await apiService.getCorrelation(params);
      setData(data);
    } finally {
      setLoading(false);
    }
  }

  const lagData = useMemo(
    () => (data?.lags || []).map((l) => ({ lag: `+${l.lag}mo`, r: l.pearson_r ?? 0, n: l.n, insufficient: l.insufficient_data })),
    [data]
  );
  const overlay = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, number>();
    data.flood_series.forEach((f) => map.set(`${f.year}-${f.month}`, f.count));
    return data.case_series.map((c) => ({
      month: `${c.year}-${String(c.month).padStart(2, "0")}`,
      cases: c.cases,
      floods: map.get(`${c.year}-${c.month}`) ?? 0,
    }));
  }, [data]);

  function exportCsv() {
    const params = new URLSearchParams({ from_year: String(from), to_year: String(to), format: "csv" });
    if (scope === "lga" && lgaId) params.set("lga_id", String(lgaId));
    if (scope === "state" && state) params.set("state", state);
    window.open(`${API_BASE}/analytics/correlation/export?${params}`);
  }

  return (
    <div style={{ padding: 24 }}>
      <h2>Flood ↔ Cholera Time-Lag Correlation</h2>
      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <select value={scope} onChange={(e) => setScope(e.target.value as any)}>
          <option value="national">National</option>
          <option value="state">State</option>
          <option value="lga">LGA</option>
        </select>
        {scope === "lga" && <input placeholder="LGA id" value={lgaId} onChange={(e) => setLgaId(Number(e.target.value))} />}
        {scope === "state" && <input placeholder="State name" value={state} onChange={(e) => setState(e.target.value)} />}
        <input type="number" value={from} onChange={(e) => setFrom(Number(e.target.value))} />
        <input type="number" value={to} onChange={(e) => setTo(Number(e.target.value))} />
        <button onClick={load} disabled={loading}>{loading ? "Loading…" : "Run"}</button>
        <button onClick={exportCsv}>Export CSV</button>
      </div>
      {data && (
        <>
          <p style={{ color: "#b00", fontStyle: "italic" }}>{data.caveat}</p>
          <h3>Pearson r by lag (months)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={lagData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="lag" />
              <YAxis domain={[-1, 1]} />
              <Tooltip />
              <Bar dataKey="r" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
          <h3>Flood events vs cholera cases (monthly)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={overlay}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis yAxisId="l" />
              <YAxis yAxisId="r" orientation="right" />
              <Tooltip />
              <Legend />
              <Line yAxisId="l" dataKey="cases" stroke="#dc2626" name="Cases" dot={false} />
              <Line yAxisId="r" dataKey="floods" stroke="#2563eb" name="Flood events" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
