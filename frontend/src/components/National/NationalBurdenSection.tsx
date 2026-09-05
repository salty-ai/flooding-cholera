import { useMemo, useState } from 'react';
import {
  useNationalSummary,
  useStateBoundaries,
  useStateChoropleth,
} from '../../hooks/useApi';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { NationalBurdenChart } from './NationalBurdenChart';
import { NationalKpiCards } from './NationalKpiCards';
import { BurdenLegend, StateChoroplethMap } from './StateChoroplethMap';
import { StateDrilldownPanel } from './StateDrilldownPanel';

function YearSelector({
  years,
  selected,
  onSelect,
}: {
  years: number[];
  selected: number | null;
  onSelect: (year: number) => void;
}) {
  if (years.length === 0) return null;
  return (
    <div
      className="flex flex-wrap items-center gap-1"
      role="group"
      aria-label="Select epidemiological year"
    >
      {years.map((year) => {
        const active = year === selected;
        return (
          <button
            key={year}
            type="button"
            onClick={() => onSelect(year)}
            aria-pressed={active}
            className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
              active
                ? 'border-[#111518] bg-[#111518] text-white'
                : 'border-[#e6e8eb] bg-white text-[#111518] hover:bg-gray-50'
            }`}
          >
            {year}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Verified national tier: state-level NCDC situation-report extraction.
 *
 * Everything here comes from /api/states — no figure is hard-coded in the UI
 * except the labels themselves. The only static numbers in the system are the
 * official NCDC year-end totals, which live in the backend constants file with
 * their citation and arrive through the API alongside the dataset-derived sums.
 */
export function NationalBurdenSection() {
  const [requestedYear, setRequestedYear] = useState<number | null>(null);
  const [selectedState, setSelectedState] = useState<string | null>(null);

  const { data: choropleth, isLoading: choroLoading, isError: choroError } =
    useStateChoropleth(requestedYear);
  const { data: national, isLoading: summaryLoading } = useNationalSummary();
  const { data: boundaries, isLoading: boundariesLoading, isError: boundariesError } =
    useStateBoundaries();

  const year = choropleth?.year ?? requestedYear ?? null;
  const yearsAvailable = choropleth?.years_available ?? national?.years_available ?? [];
  const rows = choropleth?.states ?? [];

  const yearSummary = useMemo(
    () => national?.years.find((y) => y.year === year),
    [national, year],
  );

  const handleSelectYear = (next: number) => {
    setRequestedYear(next);
    setSelectedState(null);
  };

  const totalStates = boundaries?.features.length ?? 0;

  return (
    <section
      className="flex flex-col gap-4 rounded-xl border border-[#e6e8eb] bg-white p-4"
      aria-label="National cholera burden, verified state-level data"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-[#111518]">National burden — verified state tier</h2>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-gray-500">
            {national?.evidence_label ?? choropleth?.evidence_label ?? 'Loading provenance…'}
          </p>
        </div>
        <YearSelector years={yearsAvailable} selected={year} onSelect={handleSelectYear} />
      </div>

      <NationalKpiCards summary={yearSummary} />
      {yearSummary && (
        <p className="-mt-1 text-[11px] leading-snug text-gray-400">{yearSummary.coverage_note}</p>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <div className="flex flex-col gap-3 rounded-xl border border-[#e6e8eb] xl:col-span-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#e6e8eb] p-3">
            <h3 className="text-sm font-bold text-[#111518]">
              Suspected cases by state{year ? ` — ${year} year-end snapshot` : ''}
            </h3>
            <span className="text-[11px] text-gray-400">
              {rows.length} of {totalStates || 37} states reporting
            </span>
          </div>
          <div className="relative min-h-[320px] flex-1 sm:min-h-[400px]">
            {(choroLoading || boundariesLoading) && (
              <div className="flex h-full min-h-[320px] items-center justify-center text-xs text-gray-400">
                Loading verified state data…
              </div>
            )}
            {(choroError || boundariesError) && !choroLoading && !boundariesLoading && (
              <div className="flex h-full min-h-[320px] items-center justify-center px-4 text-center text-xs text-red-600">
                Could not load the state map. The verified state dataset may not be seeded yet.
              </div>
            )}
            {!choroLoading && !boundariesLoading && boundaries && (
              <ErrorBoundary>
                <StateChoroplethMap
                  boundaries={boundaries}
                  rows={rows}
                  year={year}
                  selectedState={selectedState}
                  onSelectState={setSelectedState}
                />
              </ErrorBoundary>
            )}
          </div>
          <div className="border-t border-[#e6e8eb] p-3">
            <BurdenLegend rows={rows} totalStates={totalStates || 37} />
          </div>
        </div>

        <div className="flex flex-col rounded-xl border border-[#e6e8eb] xl:col-span-2">
          <div className="border-b border-[#e6e8eb] p-3">
            <h3 className="text-sm font-bold text-[#111518]">Year-by-year burden</h3>
            <p className="mt-0.5 text-[11px] text-gray-400">
              Bars and the deaths line are dataset-derived; diamonds are NCDC's official year-end
              totals where published.
            </p>
          </div>
          <div className="p-3">
            {summaryLoading ? (
              <div className="flex h-[260px] items-center justify-center text-xs text-gray-400">
                Loading…
              </div>
            ) : (
              <NationalBurdenChart
                years={national?.years ?? []}
                selectedYear={year}
                onSelectYear={handleSelectYear}
              />
            )}
          </div>
        </div>
      </div>

      {selectedState && (
        <StateDrilldownPanel
          state={selectedState}
          year={year}
          onClose={() => setSelectedState(null)}
        />
      )}
      {!selectedState && rows.length > 0 && (
        <p className="text-[11px] text-gray-400">
          Select a state on the map to see every situation report it was extracted from, with links
          to the source PDFs.
        </p>
      )}
    </section>
  );
}

export default NationalBurdenSection;
