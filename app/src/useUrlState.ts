/**
 * URL hash state: `#map=zoom/lat/lng&date=year`
 * Matches the OHM URL format.
 */

export interface UrlState {
  zoom: number;
  lat: number;
  lng: number;
  year: number;
}

const DEFAULT_STATE: UrlState = {
  zoom: 1.5,
  lat: 20,
  lng: 0,
  year: 1100,
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
  if (date) {
    const year = parseInt(date, 10);
    if (isFinite(year)) state.year = year;
  }

  return state;
}

export function serializeHash(state: UrlState): string {
  const { zoom, lat, lng, year } = state;
  const mapStr = `${zoom.toFixed(2)}/${lat.toFixed(4)}/${lng.toFixed(4)}`;
  return `#map=${mapStr}&date=${year}`;
}
