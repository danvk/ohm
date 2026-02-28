import React from 'react';
import { MapLibreMap, type MapView } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';
import { AdminAreas } from './AdminAreas';
import { FeaturePanel, type FeatureInfo } from './FeaturePanel';
import { TimeSlider } from './TimeSlider';
import { parseHash, serializeHash } from './useUrlState';

export default function App() {
  const initial = React.useMemo(() => parseHash(window.location.hash), []);

  // year is the only piece of URL state that drives React re-renders.
  // Viewport (zoom/lat/lng) is kept in a ref so map moves don't cause re-renders
  // and don't feed back into setCenter.
  const [year, setYear] = React.useState(initial.year);
  const viewportRef = React.useRef<MapView>({
    zoom: initial.zoom,
    lat: initial.lat,
    lng: initial.lng,
  });

  // When an external hash change arrives, we need to imperatively move the map.
  // Use a counter so MapLibreMap sees a new object reference each time.
  const [externalView, setExternalView] = React.useState<
    (MapView & { seq: number }) | undefined
  >(undefined);

  const [selectedFeatures, setSelectedFeatures] = React.useState<FeatureInfo[]>(
    [],
  );
  const selectedIds = React.useMemo(
    () => new Set(selectedFeatures.map((f) => f.id)),
    [selectedFeatures],
  );

  const lastWrittenHash = React.useRef<string>('');

  const writeHash = React.useCallback((nextYear: number, view?: MapView) => {
    const { zoom, lat, lng } = view ?? viewportRef.current;
    const hash = serializeHash({ zoom, lat, lng, year: nextYear });
    lastWrittenHash.current = hash;
    window.location.hash = hash;
  }, []);

  const handleYearChange = React.useCallback(
    (nextYear: number) => {
      setYear(nextYear);
      writeHash(nextYear);
    },
    [writeHash],
  );

  const handleMapMove = React.useCallback(
    (view: MapView) => {
      viewportRef.current = view;
      writeHash(year, view);
    },
    [year, writeHash],
  );

  // Respond to external hash edits (user typing in the URL bar).
  React.useEffect(() => {
    const handler = () => {
      if (window.location.hash === lastWrittenHash.current) return;
      const parsed = parseHash(window.location.hash);
      setYear(parsed.year);
      viewportRef.current = parsed;
      setExternalView((prev) => ({ ...parsed, seq: (prev?.seq ?? 0) + 1 }));
    };
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  return (
    <>
      <TimeSlider
        year={year}
        minYear={0}
        maxYear={2030}
        onChange={handleYearChange}
      />
      <MapLibreMap
        containerId="map"
        containerClassName="maplibregl-map"
        center={[initial.lng, initial.lat]}
        zoom={initial.zoom}
        {...(externalView && { externalView })}
        onMapMove={handleMapMove}
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
        onSetYear={handleYearChange}
      />
    </>
  );
}
