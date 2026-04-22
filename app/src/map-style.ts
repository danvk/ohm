import type maplibregl from 'maplibre-gl';
import { IS_WHM } from './config';

export const MINIMAL_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'versatiles-shortbread': {
      type: 'vector',
      url: 'https://vector.openstreetmap.org/shortbread_v1/tilejson.json',
    },
  },
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: {
        'background-color': '#f9f4ee',
      },
    },
    {
      source: 'versatiles-shortbread',
      id: 'water-ocean',
      type: 'fill',
      'source-layer': 'ocean',
      paint: {
        'fill-color': '#beddf3',
        // 'fill-color': 'rgb(196,255,255)',
      },
    },
    {
      source: 'versatiles-shortbread',
      id: 'land',
      type: 'fill',
      'source-layer': 'land',
      paint: {
        'fill-color': '#fafaed',
      },
    },
    {
      source: 'versatiles-shortbread',
      id: 'water-river',
      type: 'line',
      'source-layer': 'water_lines',
      paint: {
        'line-color': '#beddf3',
        'line-width': [
          'interpolate',
          ['linear'],
          ['zoom'],
          9,
          0,
          10,
          3,
          15,
          5,
          17,
          9,
          18,
          20,
          20,
          60,
        ],
      },
      layout: {
        'line-cap': 'round',
        'line-join': 'round',
      },
    },
    {
      source: 'versatiles-shortbread',
      id: 'water-area',
      type: 'fill',
      'source-layer': 'water_polygons',
      paint: {
        'fill-color': '#beddf3',
        'fill-opacity': ['interpolate', ['linear'], ['zoom'], 4, 0, 6, 1],
      },
    },
  ],
};

type FillPaintStyle = Exclude<
  maplibregl.FillLayerSpecification['paint'],
  undefined
>;

const DEFAULT_COLOR = '#6080C0'; // — blue
const PALETTE = [
  DEFAULT_COLOR,
  '#E15759', // — red
  '#4E9F3D', // — green
  '#F28E2B', // — orange
  '#B07AA1', // — purple
  '#76B7B2', // — teal
  '#EDC948', // — yellow
  '#9C755F', // — brown
  '#FF9DA7', // - pink
];
const HIGHLIGHT_COLOR = '#FF00FF'; // '#00E5FF',

// This type assertion is wrong, but this is what MapLibre's types want.
const ID_PALETTE = PALETTE.flatMap((color, i) => [String(i), color]) as [
  string,
  string,
  string,
  string,
];

export const PAINT_STYLE: FillPaintStyle = {
  'fill-color': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    HIGHLIGHT_COLOR,
    // WHM has hand-selected fill colors, but OHM uses an indexed palette
    IS_WHM
      ? ['coalesce', ['get', 'fill'], DEFAULT_COLOR]
      : ['match', ['get', 'color'], ...ID_PALETTE, DEFAULT_COLOR],
  ],
  'fill-opacity': IS_WHM
    ? ['match', ['get', 'group'], 'fntr', 0.25, 0.75]
    : 0.5,
};

type LinePaintStyle = Exclude<
  maplibregl.LineLayerSpecification['paint'],
  undefined
>;
export const LINE_STYLE: LinePaintStyle = {
  'line-color': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    HIGHLIGHT_COLOR,
    IS_WHM
      ? DEFAULT_COLOR
      : ['match', ['get', 'color'], ...ID_PALETTE, DEFAULT_COLOR],
  ],
  'line-width': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    2,
    IS_WHM
      ? ['match', ['get', 'group'], 'fntr', 0, 1]
      : ['match', ['get', 'admin_level'], '2', 1.5, '1', 2, '3', 1.25, 1],
  ],
};

type CirclePaintStyle = Exclude<
  maplibregl.CircleLayerSpecification['paint'],
  undefined
>;
export const CIRCLE_STYLE: CirclePaintStyle = {
  'circle-color': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    '#cc5500',
    '#3050a0',
  ],
  'circle-radius': [
    'interpolate',
    ['linear'],
    ['zoom'],
    2,
    3,
    // At zoom level 5 (or less), the circle radius will be 1 pixel
    4,
    5,
    // At zoom level 10 (or greater), the circle radius will be 5 pixels
    10,
    16,
  ],
  // This increases the click target size, which makes it much easier
  // to tap a dot with your finger on mobile.
  'circle-stroke-width': 4,
  'circle-stroke-opacity': 0.0,
};
