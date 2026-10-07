import { useMemo, useState } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { NationalYearSummary } from '../../types';

const CASES_COLOR = '#2a78d6';
const DEATHS_COLOR = '#eb6834';
const OFFICIAL_COLOR = '#111518';

interface NationalBurdenChartProps {
  years: NationalYearSummary[];
  selectedYear: number | null;
  onSelectYear: (year: number) => void;
}

interface ChartRow {
  year: number;
  label: string;
  cases: number;
  deaths: number;
  officialCases: number | null;
  statesReporting: number;
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartRow }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-lg border border-[#e6e8eb] bg-white px-3 py-2 text-xs shadow-md">
      <div className="font-bold text-[#111518]">{row.year}</div>
      <div className="mt-1 text-[#111518]">
        {row.cases.toLocaleString()} suspected cases
        <span className="text-gray-500"> (dataset-derived)</span>
      </div>
      <div className="text-[#111518]">
        {row.deaths.toLocaleString()} deaths
        <span className="text-gray-500"> (dataset-derived)</span>
      </div>
      <div className="mt-1 text-gray-500">
        {row.officialCases !== null
          ? `Official NCDC year-end: ${row.officialCases.toLocaleString()} cases`
          : 'No official year-end total recorded'}
      </div>
      <div className="text-gray-500">{row.statesReporting} states reporting</div>
    </div>
  );
}

export function NationalBurdenChart({
  years,
  selectedYear,
  onSelectYear,
}: NationalBurdenChartProps) {
  const [showTable, setShowTable] = useState(false);

  const data: ChartRow[] = useMemo(
    () =>
      [...years]
        .sort((a, b) => a.year - b.year)
        .map((y) => ({
          year: y.year,
          label: String(y.year),
          cases: y.dataset_sum_cases,
          deaths: y.dataset_sum_deaths,
          officialCases: y.official_cases,
          statesReporting: y.states_reporting,
        })),
    [years],
  );

  if (data.length === 0) {
    return (
      <div className="flex h-full min-h-[240px] items-center justify-center text-sm text-gray-400">
        No verified state records loaded.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            onClick={(state) => {
              const label = state?.activeLabel;
              if (label) onSelectYear(Number(label));
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f2" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: '#5c6b73' }}
              axisLine={{ stroke: '#e6e8eb' }}
              tickLine={false}
            />
            <YAxis
              yAxisId="cases"
              tick={{ fontSize: 11, fill: '#5c6b73' }}
              axisLine={false}
              tickLine={false}
              width={54}
              tickFormatter={(v: number) => v.toLocaleString()}
            />
            <YAxis
              yAxisId="deaths"
              orientation="right"
              tick={{ fontSize: 11, fill: '#5c6b73' }}
              axisLine={false}
              tickLine={false}
              width={44}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f5f7f8' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar
              yAxisId="cases"
              dataKey="cases"
              name="Suspected cases (dataset-derived)"
              fill={CASES_COLOR}
              radius={[4, 4, 0, 0]}
              maxBarSize={48}
              opacity={selectedYear === null ? 1 : 0.95}
            />
            <Scatter
              yAxisId="cases"
              dataKey="officialCases"
              name="Official NCDC year-end cases"
              fill={OFFICIAL_COLOR}
              shape="diamond"
              legendType="diamond"
            />
            <Line
              yAxisId="deaths"
              type="monotone"
              dataKey="deaths"
              name="Deaths (dataset-derived, right axis)"
              stroke={DEATHS_COLOR}
              strokeWidth={2}
              dot={{ r: 4, fill: DEATHS_COLOR, stroke: '#ffffff', strokeWidth: 2 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <button
        type="button"
        onClick={() => setShowTable((v) => !v)}
        className="self-start text-xs font-medium text-[#2a78d6] hover:underline"
      >
        {showTable ? 'Hide data table' : 'Show data table'}
      </button>

      {showTable && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] text-left text-xs">
            <thead className="text-gray-500">
              <tr className="border-b border-[#e6e8eb]">
                <th className="py-1.5 pr-3 font-medium">Year</th>
                <th className="py-1.5 pr-3 font-medium">Cases (dataset)</th>
                <th className="py-1.5 pr-3 font-medium">Deaths (dataset)</th>
                <th className="py-1.5 pr-3 font-medium">Official cases</th>
                <th className="py-1.5 font-medium">States</th>
              </tr>
            </thead>
            <tbody className="text-[#111518]">
              {data.map((row) => (
                <tr key={row.year} className="border-b border-[#f1f3f4] last:border-0">
                  <td className="py-1.5 pr-3">{row.year}</td>
                  <td className="py-1.5 pr-3">{row.cases.toLocaleString()}</td>
                  <td className="py-1.5 pr-3">{row.deaths.toLocaleString()}</td>
                  <td className="py-1.5 pr-3">
                    {row.officialCases !== null ? row.officialCases.toLocaleString() : 'not stated'}
                  </td>
                  <td className="py-1.5">{row.statesReporting}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
