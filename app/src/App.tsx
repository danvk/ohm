import React from 'react';
import { MapLibreMap, type MapView } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';
import { AdminAreas } from './AdminAreas';
import { FeaturePanel, type FeatureInfo } from './FeaturePanel';
import { TimeSlider } from './TimeSlider';
import { DEFAULT_YEAR, parseHash, serializeHash } from './useUrlState';
import Logo from './ohm_logo.svg';
import { yearFromDateStr } from './date-utils';

export default function App() {
  const initial = React.useMemo(() => parseHash(window.location.hash), []);

  // year is the only piece of URL state that drives React re-renders.
  // Viewport (zoom/lat/lng) is kept in a ref so map moves don't cause re-renders
  // and don't feed back into setCenter.
  const [year, setYear] = React.useState<string>(initial.year);
  const yearRef = React.useRef<string>(initial.year);
  React.useEffect(() => {
    yearRef.current = year;
  });
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

  const lastWrittenHash = React.useRef('');

  const writeHash = React.useCallback(
    (nextYear: string, ids: number[], view?: MapView) => {
      const { zoom, lat, lng } = view ?? viewportRef.current;
      const hash = serializeHash({ zoom, lat, lng, year: nextYear, ids });
      lastWrittenHash.current = hash;
      window.location.hash = hash;
    },
    [],
  );

  const currentIdsRef = React.useRef<number[]>(initial.ids);

  const handleDateChange = React.useCallback(
    (nextDate: string) => {
      setYear(nextDate);
      writeHash(nextDate, currentIdsRef.current);
    },
    [writeHash],
  );
  const handleYearChange = React.useCallback((nextYear: number) => {
    const nextYearStr = String(nextYear).padStart(4, '0');
    handleDateChange(nextYearStr);
  }, []);

  const handleMapMove = React.useCallback(
    (view: MapView) => {
      viewportRef.current = view;
      writeHash(yearRef.current, currentIdsRef.current, view);
    },
    [writeHash],
  );

  // Derive FeatureInfo[] from a list of numeric relation IDs.
  const resolveFeatureInfos = React.useCallback(
    (ids: number[]): FeatureInfo[] => {
      return ids.flatMap((id) => {
        const relation = relations.find((r) => Number(r.id) === id);
        if (!relation) return [];
        return [
          {
            id: relation.id,
            tags: relation.tags,
            chronology: relation.chronology,
          },
        ];
      });
    },
    [],
  );

  const handleClickFeature = React.useCallback(
    (features: FeatureInfo[]) => {
      const ids = features.map((f) => Number(f.id));
      currentIdsRef.current = ids;
      setSelectedFeatures(features);
      writeHash(yearRef.current, ids);
    },
    [writeHash],
  );

  // Build a map from relation ID (number) to Relation for O(1) lookup.
  // relations is a global loaded asynchronously; we access it at call time.
  const handleSelectRelation = React.useCallback(
    (relationId: number) => {
      const relation = relations.find((r) => Number(r.id) === relationId);
      if (!relation) return;
      const startDateStr = relation.tags['start_date'];
      const nextYear =
        startDateStr ?? String(yearFromDateStr(year)).padStart(4, '0');
      const ids = [relationId];
      currentIdsRef.current = ids;
      setYear(nextYear);
      writeHash(nextYear, ids);
      setSelectedFeatures([
        {
          id: relation.id,
          tags: relation.tags,
          chronology: relation.chronology,
        },
      ]);
    },
    [year, writeHash],
  );

  // Hydrate selectedFeatures from URL ids on initial load (after data is ready).
  // Also update the year to the feature's start_date if no explicit date was in the URL.
  React.useEffect(() => {
    if (initial.ids.length === 0) return;
    dataReady.then(() => {
      const features = resolveFeatureInfos(initial.ids);
      setSelectedFeatures(features);
      const currentHash = window.location.hash;
      const parsedYear = parseHash(currentHash).year;
      const hasExplicitDate = parsedYear !== DEFAULT_YEAR;
      if (!hasExplicitDate && features.length > 0) {
        const firstId = initial.ids[0];
        const relation = relations.find((r) => Number(r.id) === firstId);
        const startDate = relation?.tags['start_date'];
        if (startDate) {
          setYear(startDate);
          writeHash(startDate, initial.ids);
        }
      }
    });
  }, [initial.ids, resolveFeatureInfos, writeHash]);

  // Respond to external hash edits (user typing in the URL bar).
  React.useEffect(() => {
    const handler = () => {
      if (window.location.hash === lastWrittenHash.current) return;
      const parsed = parseHash(window.location.hash);
      setYear(parsed.year);
      viewportRef.current = parsed;
      setExternalView((prev) => ({ ...parsed, seq: (prev?.seq ?? 0) + 1 }));
      currentIdsRef.current = parsed.ids;
      dataReady.then(() => {
        const features = resolveFeatureInfos(parsed.ids);
        setSelectedFeatures(features);
      });
    };
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, [resolveFeatureInfos]);

  return (
    <>
      <div className="title">
        <img src={Logo} width={30} height={30} className="logo" />
        <h3>Boundary Viewer</h3>
        <a href="https://github.com/danvk/ohm/tree/main/app" target="_blank">
          About
        </a>
      </div>
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
          onClickFeature={handleClickFeature}
        />
      </MapLibreMap>
      <FeaturePanel
        features={selectedFeatures}
        onClose={() => {
          currentIdsRef.current = [];
          setSelectedFeatures([]);
          writeHash(yearRef.current, []);
        }}
        onSetDate={handleDateChange}
        onSelectRelation={handleSelectRelation}
      />
    </>
  );
}
