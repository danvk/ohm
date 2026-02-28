import React from 'react';
import { MapLibreMap } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';
import { AdminAreas } from './AdminAreas';
import { FeaturePanel, type FeatureInfo } from './FeaturePanel';

const DEFAULT_CENTER: [number, number] = [0, 20];

export default function App() {
  const [year, setYear] = React.useState(1100);
  const [selectedFeatures, setSelectedFeatures] = React.useState<FeatureInfo[]>(
    [],
  );
  const selectedIds = React.useMemo(
    () => new Set(selectedFeatures.map((f) => f.id)),
    [selectedFeatures],
  );

  const MIN_YEAR = 0;
  const MAX_YEAR = 2030;
  // Fraction 0–1 of thumb position, used to position the label above the thumb
  const thumbFraction = (year - MIN_YEAR) / (MAX_YEAR - MIN_YEAR);

  return (
    <>
      <div id="time-slider">
        <div id="time-slider-track-row">
          <div
            id="time-slider-input-wrap"
            style={{ '--thumb-fraction': thumbFraction } as React.CSSProperties}
          >
            <span id="year-display">{year}</span>
            <input
              id="year"
              type="range"
              min={MIN_YEAR}
              max={MAX_YEAR}
              value={year}
              onChange={(e) => setYear(e.currentTarget.valueAsNumber)}
            />
          </div>
          <span className="time-slider-label time-slider-label-min">
            {MIN_YEAR}
          </span>
          <span className="time-slider-label time-slider-label-max">
            {MAX_YEAR}
          </span>
        </div>
      </div>
      <MapLibreMap
        containerId="map"
        containerClassName="maplibregl-map"
        center={DEFAULT_CENTER}
        zoom={1.5}
      >
        <ZoomControl />
        <AdminAreas
          year={year}
          selectedIds={selectedIds}
          onClickFeature={setSelectedFeatures}
        />
      </MapLibreMap>
      <FeaturePanel
        features={selectedFeatures}
        onClose={() => setSelectedFeatures([])}
      />
    </>
  );
}
