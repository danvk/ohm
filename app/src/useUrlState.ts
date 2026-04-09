/**
 * URL search-parameter state: `?map=zoom/lat/lng&date=year`
 */

import { createParser } from 'nuqs';

// nuqs parsers — custom serialization to preserve the existing URL format.
// nuqs's renderQueryString intentionally leaves / and , unencoded, so pretty URLs are preserved.

export const mapViewParser = createParser({
  parse(value: string) {
    const parts = value.split('/');
    if (parts.length !== 3) return null;
    const [zoom, lat, lng] = parts.map(parseFloat);
    if (!isFinite(zoom) || !isFinite(lat) || !isFinite(lng)) return null;
    return { zoom, lat, lng };
  },
  serialize({ zoom, lat, lng }: { zoom: number; lat: number; lng: number }) {
    return `${zoom.toFixed(2)}/${lat.toFixed(4)}/${lng.toFixed(4)}`;
  },
});

export const dateParser = createParser({
  parse(v: string) {
    return /^-?\d{1,4}(-\d{2}(-\d{2})?)?$/.test(v) ? v : null;
  },
  serialize(v: string) {
    return v;
  },
});

export const idsParser = createParser({
  parse(v: string) {
    const parsed = v.split(',').map(Number).filter(isFinite);
    return parsed.length > 0 ? parsed : null;
  },
  serialize(v: number[]) {
    return v.join(',');
  },
});

export const rangeParser = createParser<{ min: number; max: number }>({
  parse(v: string) {
    const parts = v.split(',');
    if (parts.length !== 2) return null;
    const min = parseInt(parts[0], 10);
    const max = parseInt(parts[1], 10);
    if (!isFinite(min) || !isFinite(max) || min >= max) return null;
    return { min, max };
  },
  serialize({ min, max }) {
    return `${min},${max}`;
  },
});

export const levelsParser = createParser({
  parse(v: string) {
    const parsed = v.split(',').filter((l) => /^\d+$/.test(l));
    return parsed.length > 0 ? new Set(parsed) : null;
  },
  serialize(v: Set<string>) {
    return [...v].sort().join(',');
  },
  eq(a: Set<string>, b: Set<string>) {
    return [...a].sort().join() === [...b].sort().join();
  },
});

export interface UrlState {
  zoom: number;
  lat: number;
  lng: number;
  year: string;
  ids: number[];
  /** Serialized as a sorted comma-separated string, e.g. "2" or "1,2,4". Absent means not specified in URL. */
  adminLevels: Set<string> | null;
}

export const DEFAULT_YEAR = '1100';

export const DEFAULT_STATE: UrlState = {
  zoom: 1.5,
  lat: 20,
  lng: 0,
  year: DEFAULT_YEAR,
  ids: [],
  adminLevels: null,
};

export function parseSearchParams(params: URLSearchParams): UrlState {
  const state = { ...DEFAULT_STATE };

  const map = params.get('map');
  if (map) {
    const parts = map.split('/');
    if (parts.length === 3) {
      const zoom = parseFloat(parts[0]);
      const lat = parseFloat(parts[1]);
      const lng = parseFloat(parts[2]);
      if (isFinite(zoom)) state.zoom = zoom;
      if (isFinite(lat)) state.lat = lat;
      if (isFinite(lng)) state.lng = lng;
    }
  }

  const date = params.get('date');
  if (date && /^-?\d{1,4}(-\d{2}(-\d{2})?)?$/.test(date)) {
    state.year = date;
  }

  const ids = params.get('ids');
  if (ids) {
    const parsed = ids.split(',').map(Number).filter(isFinite);
    if (parsed.length > 0) state.ids = parsed;
  }

  const levels = params.get('levels');
  if (levels !== null) {
    const parsed = levels.split(',').filter((l) => /^\d+$/.test(l));
    state.adminLevels = new Set(parsed);
  }

  return state;
}

/** Returns a raw, unencoded query string (no leading `?`). Commas and slashes are
 * intentionally left unencoded for readability, e.g. `map=1.50/20.0000/0.0000&levels=2,4`.
 */
export function buildSearch(state: UrlState): string {
  const { zoom, lat, lng, year, ids, adminLevels } = state;
  const parts: string[] = [
    `map=${zoom.toFixed(2)}/${lat.toFixed(4)}/${lng.toFixed(4)}`,
    `date=${year}`,
  ];
  if (ids && ids.length > 0) {
    parts.push(`ids=${ids.join(',')}`);
  }
  if (adminLevels) {
    parts.push(`levels=${[...adminLevels].sort().join(',')}`);
  }
  return parts.join('&');
}
