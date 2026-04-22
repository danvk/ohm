// There are two variants of the boundary viewer:
// the main one for OpenHistoricalMap, and a variant for WorldHistoryMaps (WHM).
export const IS_WHM = window.location.href.includes('whm');

// TODO: expose this as an environment variable.
const SERVER = '//localhost:8081/';

export const BASE_URL = IS_WHM
  ? `${SERVER}/whm-boundary/`
  : `${SERVER}/boundary/`;
