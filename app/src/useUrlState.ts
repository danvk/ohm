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
}

const DEFAULT_STATE: UrlState = {
  zoom: 1.5,
  lat: 20,
  lng: 0,
  year: '1100',
  ids: [],
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

  return state;
}

export function serializeHash(state: UrlState): string {
  const { zoom, lat, lng, year, ids } = state;
  const mapStr = `${zoom.toFixed(2)}/${lat.toFixed(4)}/${lng.toFixed(4)}`;
  let hash = `#map=${mapStr}&date=${year}`;
  if (ids && ids.length > 0) {
    hash += `&ids=${ids.join(',')}`;
  }
  return hash;
}
