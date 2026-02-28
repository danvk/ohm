import React from 'react';
import { MapLibreMap } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';
import { AdminAreas } from './AdminAreas';
import { FeaturePanel, type FeatureInfo } from './FeaturePanel';
import { TimeSlider } from './TimeSlider';

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

  return (
    <>
      <TimeSlider year={year} minYear={0} maxYear={2030} onChange={setYear} />
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
        onSetYear={setYear}
      />
    </>
  );
}
