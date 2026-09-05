import { useState } from 'react';
import { useStateRecords } from '../../hooks/useApi';
import type { StateCholeraRecord } from '../../types';

const CONFIDENCE_STYLE: Record<string, string> = {
  high: 'bg-[#e8f3ec] text-[#166534]',
  reassembled: 'bg-[#fdf2e3] text-[#8a5200]',
};

function ConfidenceBadge({ confidence }: { confidence: string | null }) {
  const label = confidence ?? 'unknown';
  const style = CONFIDENCE_STYLE[label] ?? 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${style}`}>
      {label}
    </span>
  );
}

function RecordRow({ record }: { record: StateCholeraRecord }) {
  return (
    <tr className="border-b border-[#f1f3f4] last:border-0 align-top">
      <td className="whitespace-nowrap py-2 pr-3">
        <span className="font-medium text-[#111518]">wk {record.epi_week}</span>
        <span className="block text-[10px] text-gray-400">{record.month ?? '—'}</span>
      </td>
      <td className="whitespace-nowrap py-2 pr-3 text-[#111518]">
        {record.suspected_cases !== null ? record.suspected_cases.toLocaleString() : '—'}
      </td>
      <td className="whitespace-nowrap py-2 pr-3 text-[#111518]">
        {record.deaths !== null ? record.deaths.toLocaleString() : '—'}
      </td>
      <td className="whitespace-nowrap py-2 pr-3 text-[#111518]">
        {record.cfr !== null ? `${record.cfr.toFixed(1)}%` : '—'}
      </td>
      <td className="whitespace-nowrap py-2 pr-3">
        <ConfidenceBadge confidence={record.confidence} />
      </td>
      <td className="whitespace-nowrap py-2 pr-3 text-[11px] text-gray-500">
        {record.extraction_method ?? '—'}
      </td>
      <td className="whitespace-nowrap py-2 pr-3">
        {record.monotonic_ok ? (
          <span className="text-[11px] text-gray-400">ok</span>
        ) : (
          <span
            className="flex items-center gap-1 text-[11px] font-medium text-[#8a5200]"
            title="Cumulative total decreases within the year — extraction artefact, excluded from aggregates"
          >
            <span className="material-symbols-outlined text-[14px] leading-none">warning</span>
            check
          </span>
        )}
      </td>
      <td className="whitespace-nowrap py-2">
        {record.source_url ? (
          <a
            href={record.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] font-medium text-[#2a78d6] hover:underline"
          >
            Source PDF
          </a>
        ) : (
          <span className="text-[11px] text-gray-400">—</span>
        )}
      </td>
    </tr>
  );
}

interface StateDrilldownPanelProps {
  state: string;
  year: number | null;
  onClose: () => void;
}

export function StateDrilldownPanel({ state, year, onClose }: StateDrilldownPanelProps) {
  const [allYears, setAllYears] = useState(false);
  const effectiveYear = allYears ? null : year;
  const { data, isLoading, isError } = useStateRecords(state, effectiveYear);

  const records = data?.records ?? [];
  const quarantined = records.filter((r) => !r.monotonic_ok).length;

  return (
    <div className="rounded-xl border border-[#e6e8eb] bg-white">
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[#e6e8eb] p-4">
        <div>
          <h4 className="text-sm font-bold text-[#111518]">
            {data?.state ?? state} — verified situation-report records
          </h4>
          <p className="mt-0.5 text-xs text-gray-500">
            {allYears ? 'All years' : `Epi year ${year ?? '—'}`} · {records.length} record
            {records.length === 1 ? '' : 's'}
            {quarantined > 0 && ` · ${quarantined} flagged non-monotonic`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setAllYears((v) => !v)}
            className="rounded-lg border border-[#e6e8eb] px-2.5 py-1 text-xs font-medium text-[#111518] hover:bg-gray-50"
          >
            {allYears ? `Only ${year ?? 'selected year'}` : 'All years'}
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close state drill-down"
            className="rounded-lg border border-[#e6e8eb] px-2.5 py-1 text-xs font-medium text-[#111518] hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>

      <div className="p-4">
        {isLoading && <div className="text-xs text-gray-400">Loading records…</div>}
        {isError && (
          <div className="text-xs text-red-600">Could not load records for {state}.</div>
        )}
        {!isLoading && !isError && records.length === 0 && (
          <div className="text-xs text-gray-500">
            No situation report was parsed for {data?.state ?? state}
            {allYears ? '' : ` in ${year ?? 'this year'}`}. This is an absence of extracted
            evidence, not a report of zero cases.
          </div>
        )}
        {records.length > 0 && (
          <div className="max-h-[320px] overflow-auto">
            <table className="w-full min-w-[640px] text-left text-xs">
              <thead className="sticky top-0 bg-white text-gray-500">
                <tr className="border-b border-[#e6e8eb]">
                  <th className="py-2 pr-3 font-medium">Epi week</th>
                  <th className="py-2 pr-3 font-medium">Cases</th>
                  <th className="py-2 pr-3 font-medium">Deaths</th>
                  <th className="py-2 pr-3 font-medium">CFR</th>
                  <th className="py-2 pr-3 font-medium">Confidence</th>
                  <th className="py-2 pr-3 font-medium">Extraction</th>
                  <th className="py-2 pr-3 font-medium">Monotonic</th>
                  <th className="py-2 font-medium">Provenance</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <RecordRow key={`${record.year}-${record.epi_week}`} record={record} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        {records.length > 0 && (
          <p className="mt-3 text-[11px] text-gray-400">{data?.note}</p>
        )}
      </div>
    </div>
  );
}
