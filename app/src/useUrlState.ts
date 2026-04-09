/**
 * URL search-parameter state: `?map=zoom/lat/lng&date=year`
 */

import { createParser } from 'nuqs';
import { MAX_YEAR, MIN_YEAR } from './slider/slider-utils';

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
    if (min < MIN_YEAR || max > MAX_YEAR) return null;
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

export const DEFAULT_YEAR = '1100';

export const DEFAULT_STATE = {
  zoom: 1.5,
  lat: 20,
  lng: 0,
  year: DEFAULT_YEAR,
  ids: [] as number[],
  adminLevels: null as Set<string> | null,
};
