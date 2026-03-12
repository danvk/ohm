/**
 * URL hash state: `#map=zoom/lat/lng&date=year`
 * Matches the OHM URL format.
 */

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

const DEFAULT_STATE: UrlState = {
  zoom: 1.5,
  lat: 20,
  lng: 0,
  year: DEFAULT_YEAR,
  ids: [],
  adminLevels: null,
};

export function parseHash(hash: string): UrlState {
  const state = { ...DEFAULT_STATE };
  const params = new URLSearchParams(hash.replace(/^#/, ''));

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
  if (levels) {
    const parsed = levels.split(',').filter((l) => /^\d+$/.test(l));
    if (parsed.length > 0) state.adminLevels = new Set(parsed);
  }

  return state;
}

export function serializeHash(state: UrlState): string {
  const { zoom, lat, lng, year, ids, adminLevels } = state;
  const mapStr = `${zoom.toFixed(2)}/${lat.toFixed(4)}/${lng.toFixed(4)}`;
  let hash = `#map=${mapStr}&date=${year}`;
  if (ids && ids.length > 0) {
    hash += `&ids=${ids.join(',')}`;
  }
  if (adminLevels && adminLevels.size > 0) {
    hash += `&levels=${[...adminLevels].sort().join(',')}`;
  }
  return hash;
}
