/// <reference types="vite/client" />
// There are two variants of the boundary viewer:
// the main one for OpenHistoricalMap, and a variant for WorldHistoryMaps (WHM).
export const IS_WHM = window.location.href.includes('whm');

// TODO: expose this as an environment variable.
const OHM_SERVER: string =
  import.meta.env['VITE_BOUNDARY_SERVER'] ?? '//s3.amazonaws.com/planet.openhistoricalmap.org/planet-stats'; // '//localhost:8081';
const WHM_SERVER: string =
  import.meta.env['VITE_BOUNDARY_SERVER'] ?? '//ohmdash.pages.dev'; // '//localhost:8081';

export const BASE_URL = IS_WHM
  ? `${WHM_SERVER}/whm-boundary/`
  : `${OHM_SERVER}/boundary/`;
