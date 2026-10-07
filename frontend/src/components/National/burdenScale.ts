/**
 * Quantile colour scale for the national state choropleth.
 *
 * Sequential encoding (one hue, light -> dark) because the quantity is a
 * magnitude, not a category or a polarity. Quantile bins rather than equal
 * intervals: state burdens are heavily skewed, so equal intervals would put
 * almost every state in the lightest bin.
 */

/** Blue sequential ramp, light -> dark. */
export const BURDEN_RAMP = ['#cde2fb', '#9ec5f4', '#5598e7', '#2a78d6', '#184f95'];

/** States with no parsed situation report for the selected year. */
export const NO_DATA_COLOR = '#d6d8dc';

export interface BurdenScale {
  /** Upper bound of every bin except the last. */
  breaks: number[];
  colors: string[];
  colorFor: (value: number | null | undefined) => string;
  /** Human-readable range per bin, e.g. "1 – 96". */
  binLabels: string[];
}

function quantile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const index = (sorted.length - 1) * p;
  const low = Math.floor(index);
  const high = Math.ceil(index);
  if (low === high) return sorted[low];
  return sorted[low] + (sorted[high] - sorted[low]) * (index - low);
}

function formatBound(value: number): string {
  return Math.round(value).toLocaleString();
}

/**
 * Build a quantile scale over `values`. Duplicate breaks are collapsed, so a
 * distribution with many tied values yields fewer, honest bins rather than
 * several bins covering the same number.
 */
export function buildBurdenScale(values: number[]): BurdenScale {
  const clean = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);

  if (clean.length === 0) {
    return {
      breaks: [],
      colors: [BURDEN_RAMP[BURDEN_RAMP.length - 1]],
      colorFor: () => NO_DATA_COLOR,
      binLabels: [],
    };
  }

  const candidates = [0.2, 0.4, 0.6, 0.8].map((p) => quantile(clean, p));
  const breaks: number[] = [];
  for (const b of candidates) {
    const rounded = Math.round(b);
    if (breaks.length === 0 || rounded > breaks[breaks.length - 1]) breaks.push(rounded);
  }

  const colors = BURDEN_RAMP.slice(BURDEN_RAMP.length - (breaks.length + 1));
  const min = clean[0];
  const max = clean[clean.length - 1];

  const binLabels = colors.map((_, i) => {
    const lower = i === 0 ? min : breaks[i - 1] + 1;
    const upper = i === colors.length - 1 ? max : breaks[i];
    return lower >= upper ? formatBound(upper) : `${formatBound(lower)} – ${formatBound(upper)}`;
  });

  const colorFor = (value: number | null | undefined): string => {
    if (value === null || value === undefined || !Number.isFinite(value)) return NO_DATA_COLOR;
    for (let i = 0; i < breaks.length; i += 1) {
      if (value <= breaks[i]) return colors[i];
    }
    return colors[colors.length - 1];
  };

  return { breaks, colors, colorFor, binLabels };
}
