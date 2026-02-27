import React, { useEffect, useRef } from 'react';
import maplibregl, { StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const MINIMAL_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    maplibre: {
      type: 'vector',
      url: 'https://demotiles.maplibre.org/tiles/tiles.json',
    },
  },
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: { 'background-color': '#e8e8e8' },
    },
    {
      id: 'countries-fill',
      type: 'fill',
      source: 'maplibre',
      'source-layer': 'countries',
      paint: { 'fill-color': '#aaaaaa' },
    },
    {
      id: 'countries-boundary',
      type: 'line',
      source: 'maplibre',
      'source-layer': 'countries',
      paint: {
        'line-color': '#ffffff',
        'line-width': ['interpolate', ['linear'], ['zoom'], 0, 0.5, 6, 2],
      },
    },
  ],
};

export default function App() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (map.current || !mapContainer.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: MINIMAL_STYLE,
      center: [0, 20],
      zoom: 1.5,
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  return <div ref={mapContainer} style={{ width: '100vw', height: '100vh' }} />;
}
