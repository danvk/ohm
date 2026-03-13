import type maplibregl from 'maplibre-gl';

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
