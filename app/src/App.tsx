import React from 'react';
import { MapLibreMap, type MapView } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';
import { AdminAreas } from './AdminAreas';
import { FeaturePanel, type FeatureInfo } from './FeaturePanel';
import { TimeSlider } from './TimeSlider';
import { parseHash, serializeHash } from './useUrlState';

export default function App() {
  const [urlState, setUrlState] = React.useState(() =>
    parseHash(window.location.hash),
  );
  const [year, setYear] = React.useState(urlState.year);
  const mapViewRef = React.useRef<MapView>({
    zoom: urlState.zoom,
    lat: urlState.lat,
    lng: urlState.lng,
  });

  const [selectedFeatures, setSelectedFeatures] = React.useState<FeatureInfo[]>(
    [],
  );
  const selectedIds = React.useMemo(
    () => new Set(selectedFeatures.map((f) => f.id)),
    [selectedFeatures],
  );

  // Write URL (debounced 500ms) whenever year or map view changes.
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const scheduleUrlWrite = React.useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const { zoom, lat, lng } = mapViewRef.current;
      window.location.hash = serializeHash({ zoom, lat, lng, year });
    }, 500);
  }, [year]);

  // Re-schedule whenever year changes.
  React.useEffect(() => {
    scheduleUrlWrite();
  }, [scheduleUrlWrite]);

  const handleMapMove = React.useCallback(
    (view: MapView) => {
      mapViewRef.current = view;
      scheduleUrlWrite();
    },
    [scheduleUrlWrite],
  );

  // When the user edits the URL hash manually, sync state.
  React.useEffect(() => {
    const handler = () => {
      const parsed = parseHash(window.location.hash);
      setUrlState(parsed);
      setYear(parsed.year);
    };
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  return (
    <>
      <TimeSlider year={year} minYear={0} maxYear={2030} onChange={setYear} />
      <MapLibreMap
        containerId="map"
        containerClassName="maplibregl-map"
        center={[urlState.lng, urlState.lat]}
        zoom={urlState.zoom}
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
        onSetYear={setYear}
      />
    </>
  );
}
