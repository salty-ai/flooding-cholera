import type { NationalYearSummary } from '../../types';

interface NationalKpiCardProps {
  title: string;
  value: string;
  citation?: string | null;
  sourceUrl?: string | null;
  /** Smaller, visually subordinate line — the dataset-derived counterpart. */
  derived: string;
}

function NationalKpiCard({ title, value, citation, sourceUrl, derived }: NationalKpiCardProps) {
  return (
    <div className="rounded-xl border border-[#e6e8eb] bg-white p-3">
      <div className="flex items-center gap-1 text-xs text-gray-500">
        <span>{title}</span>
        {citation && (
          <span
            className="material-symbols-outlined cursor-help text-[14px] leading-none text-gray-400"
            title={citation}
            aria-label={citation}
          >
            info
          </span>
        )}
      </div>
      <div className="mt-0.5 text-xl font-semibold text-[#111518]">{value}</div>
      <div className="mt-1 text-[11px] leading-snug text-gray-400">{derived}</div>
      {sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-block text-[11px] font-medium text-[#2a78d6] hover:underline"
        >
          NCDC source
        </a>
      )}
    </div>
  );
}

/**
 * Official NCDC year-end figures on the headline line, the dataset-derived sum
 * underneath in smaller type. The two are never added, averaged or swapped:
 * the official total is measured at epi-week 52, the dataset sum only covers
 * the states and weeks the extraction could parse.
 */
export function NationalKpiCards({ summary }: { summary: NationalYearSummary | undefined }) {
  if (!summary) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {['Suspected cases', 'Deaths', 'Case fatality rate'].map((title) => (
          <div key={title} className="rounded-xl border border-[#e6e8eb] bg-white p-3">
            <div className="text-xs text-gray-500">{title}</div>
            <div className="mt-0.5 text-xl font-semibold text-[#111518]">—</div>
            <div className="mt-1 text-[11px] text-gray-400">No year selected</div>
          </div>
        ))}
      </div>
    );
  }

  const states = summary.states_reporting;
  const plural = states === 1 ? '' : 's';
  // Full provenance lives in the tooltip so the card title stays one short line
  // at 390px — the epi-week matters, but not enough to wrap the headline.
  const citation = summary.official_citation
    ? `${summary.official_citation}${
        summary.official_epi_week ? ` — measured at epi-week ${summary.official_epi_week}` : ''
      }`
    : 'Not stated by NCDC for this year';

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <NationalKpiCard
        title={`Official NCDC suspected cases · ${summary.year}`}
        value={
          summary.official_cases !== null ? summary.official_cases.toLocaleString() : 'Not stated'
        }
        citation={citation}
        sourceUrl={summary.official_source_url}
        derived={`Dataset-derived sum across ${states} reporting state${plural}: ${summary.dataset_sum_cases.toLocaleString()} cases`}
      />
      <NationalKpiCard
        title={`Official NCDC deaths · ${summary.year}`}
        value={
          summary.official_deaths !== null ? summary.official_deaths.toLocaleString() : 'Not stated'
        }
        citation={citation}
        derived={`Dataset-derived sum across ${states} reporting state${plural}: ${summary.dataset_sum_deaths.toLocaleString()} deaths`}
      />
      <NationalKpiCard
        title={`Official NCDC case fatality rate · ${summary.year}`}
        value={summary.official_cfr !== null ? `${summary.official_cfr.toFixed(2)}%` : 'Not stated'}
        citation={citation}
        derived={`Dataset-derived CFR: ${
          summary.dataset_cfr !== null ? `${summary.dataset_cfr.toFixed(2)}%` : '—'
        }`}
      />
    </div>
  );
}
