import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import { renderToString } from 'react-dom/server';
import L from 'leaflet';
import type { Layer, PathOptions } from 'leaflet';
import type { StateChoroplethRow } from '../../types';
import { buildBurdenScale, NO_DATA_COLOR, type BurdenScale } from './burdenScale';

const NIGERIA_CENTER: [number, number] = [9.1, 8.7];
const NIGERIA_ZOOM = 5;

interface StateTooltipProps {
  name: string;
  row: StateChoroplethRow | undefined;
  year: number | null;
}

function StateTooltip({ name, row, year }: StateTooltipProps) {
  return (
    <div className="px-3 py-2 text-xs">
      <div className="font-bold text-[#111518]">{name}</div>
      {row ? (
        <>
          <div className="mt-1 text-[#111518]">
            {(row.suspected_cases ?? 0).toLocaleString()} suspected cases
          </div>
          <div className="text-[#111518]">{(row.deaths ?? 0).toLocaleString()} deaths</div>
          <div className="text-gray-500">
            CFR {row.cfr !== null ? `${row.cfr.toFixed(1)}%` : '—'}
          </div>
          <div className="mt-1 text-gray-500">
            Snapshot: {year} epi-week {row.epi_week}
          </div>
          <div className="text-gray-400">Click for source reports</div>
        </>
      ) : (
        <div className="mt-1 text-gray-500">No situation report parsed for {year}</div>
      )}
    </div>
  );
}

/**
 * Frame the country and keep the canvas in step with its container.
 *
 * Leaflet measures its container once at mount; inside a responsive grid that
 * measurement is taken before the final layout, which leaves a dead strip down
 * the side of the map. A ResizeObserver plus an initial fitBounds fixes both.
 */
function MapFrame({ boundaries }: { boundaries: GeoJSON.FeatureCollection }) {
  const map = useMap();

  useEffect(() => {
    const frame = () => {
      // Size first, then frame: fitBounds derives zoom from the container size.
      map.invalidateSize();
      const bounds = L.geoJSON(boundaries).getBounds();
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [8, 8] });
    };

    frame();
    const observer = new ResizeObserver(frame);
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map, boundaries]);

  return null;
}

interface StateChoroplethMapProps {
  boundaries: GeoJSON.FeatureCollection;
  rows: StateChoroplethRow[];
  year: number | null;
  selectedState: string | null;
  onSelectState: (state: string) => void;
}

/** Match a boundary feature to a data row by pcode, falling back to adm1 name. */
function rowKeyFor(props: Record<string, unknown> | null): { pcode: string; name: string } {
  return {
    pcode: String(props?.adm1_pcode ?? ''),
    name: String(props?.adm1_name ?? 'Unknown state'),
  };
}

export function StateChoroplethMap({
  boundaries,
  rows,
  year,
  selectedState,
  onSelectState,
}: StateChoroplethMapProps) {
  const byPcode = useMemo(() => {
    const map = new Map<string, StateChoroplethRow>();
    rows.forEach((r) => {
      if (r.adm1_pcode) map.set(r.adm1_pcode, r);
      if (r.adm1_name) map.set(r.adm1_name, r);
    });
    return map;
  }, [rows]);

  const scale: BurdenScale = useMemo(
    () => buildBurdenScale(rows.map((r) => r.suspected_cases ?? 0)),
    [rows],
  );

  const lookup = (props: Record<string, unknown> | null): StateChoroplethRow | undefined => {
    const { pcode, name } = rowKeyFor(props);
    return byPcode.get(pcode) ?? byPcode.get(name);
  };

  const style = (feature?: GeoJSON.Feature): PathOptions => {
    const props = (feature?.properties ?? null) as Record<string, unknown> | null;
    const row = lookup(props);
    const isSelected =
      !!selectedState &&
      (row?.state === selectedState || String(props?.adm1_name ?? '') === selectedState);
    return {
      fillColor: row ? scale.colorFor(row.suspected_cases) : NO_DATA_COLOR,
      fillOpacity: row ? 0.85 : 0.55,
      color: isSelected ? '#111518' : '#ffffff',
      weight: isSelected ? 2.5 : 1,
      opacity: 1,
    };
  };

  const onEachFeature = (feature: GeoJSON.Feature, layer: Layer) => {
    const props = (feature.properties ?? null) as Record<string, unknown> | null;
    const { name } = rowKeyFor(props);
    const row = lookup(props);

    layer.bindTooltip(
      renderToString(<StateTooltip name={name} row={row} year={year} />),
      { sticky: true, className: 'lga-tooltip-container', direction: 'top', offset: [0, -8] },
    );

    layer.on({
      click: () => onSelectState(row?.state ?? name),
      keydown: (e) => {
        const key = (e as unknown as { originalEvent?: KeyboardEvent }).originalEvent?.key;
        if (key === 'Enter' || key === ' ') onSelectState(row?.state ?? name);
      },
    });
  };

  return (
    <MapContainer
      center={NIGERIA_CENTER}
      zoom={NIGERIA_ZOOM}
      scrollWheelZoom={false}
      className="h-full w-full"
      style={{ height: '100%', width: '100%' }}
      aria-label={`Suspected cholera cases by state, ${year ?? 'no year'}`}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <GeoJSON
        key={`${year}-${rows.length}-${selectedState ?? 'none'}`}
        data={boundaries}
        style={style}
        onEachFeature={onEachFeature}
      />
      <MapFrame boundaries={boundaries} />
    </MapContainer>
  );
}

interface BurdenLegendProps {
  rows: StateChoroplethRow[];
  totalStates: number;
}

export function BurdenLegend({ rows, totalStates }: BurdenLegendProps) {
  const scale = useMemo(
    () => buildBurdenScale(rows.map((r) => r.suspected_cases ?? 0)),
    [rows],
  );
  const noReport = Math.max(totalStates - rows.length, 0);

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-[#111518]">
      <span className="text-gray-500">Suspected cases</span>
      {scale.colors.map((color, i) => (
        <span key={color} className="flex items-center gap-1.5">
          <span
            className="size-3 rounded-sm border border-white"
            style={{ backgroundColor: color }}
            aria-hidden="true"
          />
          {scale.binLabels[i]}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span
          className="size-3 rounded-sm border border-white"
          style={{ backgroundColor: NO_DATA_COLOR }}
          aria-hidden="true"
        />
        No report ({noReport})
      </span>
    </div>
  );
}
