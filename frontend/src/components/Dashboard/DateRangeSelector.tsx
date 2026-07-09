import { useState } from 'react';
import { useDateRangeStore } from '../../store/dateRangeStore';

const PRESETS: { label: string; days: number }[] = [
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
  { label: '12m', days: 365 },
];

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function DateRangeSelector({ maxDataDate }: { maxDataDate: string | null }) {
  const { start, end, setRange } = useDateRangeStore();
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  // Anchor for presets: the latest-available data date, else today.
  const anchor = maxDataDate ? new Date(maxDataDate) : new Date();

  const applyPreset = (days: number) => {
    const e = new Date(anchor);
    const s = new Date(anchor);
    s.setDate(s.getDate() - days);
    setRange(iso(s), iso(e));
  };

  const applyCustom = () => {
    if (customStart && customEnd) setRange(customStart, customEnd);
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-gray-500">Date range:</span>
      {PRESETS.map((p) => (
        <button
          key={p.label}
          onClick={() => applyPreset(p.days)}
          className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-100"
        >
          {p.label}
        </button>
      ))}
      <input type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)} className="border border-gray-300 rounded px-1 py-0.5" />
      <span>–</span>
      <input type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} className="border border-gray-300 rounded px-1 py-0.5" />
      <button onClick={applyCustom} className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-100">Apply</button>
      <button onClick={() => setRange(null, null)} className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-100">Latest</button>
      {maxDataDate && (
        <span className="ml-2 text-gray-400">Data through: {maxDataDate}</span>
      )}
      {(start || end) && (
        <span className="text-gray-400">
          ({start ?? '…'} → {end ?? '…'})
        </span>
      )}
    </div>
  );
}
