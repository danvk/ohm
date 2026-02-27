import React from 'react';
import { MapLibreMap } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';

const DEFAULT_CENTER: [number, number] = [0, 20];

export default function App() {
  return (
    <MapLibreMap
      containerId="map"
      containerClassName="maplibregl-map"
      center={DEFAULT_CENTER}
      zoom={1.5}
    >
      <ZoomControl />
    </MapLibreMap>
  );
}
