import React, { useCallback } from 'react';
import { MapLibreMap } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';
import { AdminAreas } from './AdminAreas';

const DEFAULT_CENTER: [number, number] = [0, 20];

export default function App() {
  const [year, setYear] = React.useState(1100);

  return (
    <>
      <div id="time-slider">
        {year}
        <input
          id="year"
          type="range"
          min={0}
          max={2030}
          value={year}
          onChange={(e) => setYear(e.currentTarget.valueAsNumber)}
        />
      </div>
      <MapLibreMap
        containerId="map"
        containerClassName="maplibregl-map"
        center={DEFAULT_CENTER}
        zoom={1.5}
      >
        <ZoomControl />
        <AdminAreas year={year} />
      </MapLibreMap>
    </>
  );
}
