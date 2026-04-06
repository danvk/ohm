import React from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { MapLibreMap, type MapView } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';
import { AdminAreas } from './AdminAreas';
import { AdminLevelFilter } from './AdminLevelFilter';
import { FeaturePanel, type FeatureInfo } from './FeaturePanel';
import { TimeSlider } from './TimeSlider';
import {
  DEFAULT_YEAR,
  DEFAULT_STATE,
  parseSearchParams,
  buildSearch,
} from './useUrlState';
import Logo from './ohm_logo.svg';
import { yearFromDateStr } from './date-utils';
import type { AppData } from './loader.ts';
import { loadDataForLevels } from './loader.ts';

export default function App() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Parse current URL state. This is the single source of truth.
  const urlState = React.useMemo(
    () => parseSearchParams(searchParams),
    [searchParams],
  );

  const year = urlState.year;
  const adminLevels = urlState.adminLevels ?? new Set(['2']);

  // Data loading: fetch only the files needed for the selected admin levels.
  const [data, setData] = React.useState<AppData | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    loadDataForLevels(adminLevels).then((newData) => {
      if (!cancelled) {
        setData(newData);
        setIsLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
    // adminLevels is a Set; stringify for stable comparison
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [[...adminLevels].sort().join(',')]);

  const relations = data?.relations ?? [];
  const urlIds = urlState.ids;

  // Viewport (zoom/lat/lng) is kept in a ref so map moves don't cause re-renders
  // and don't feed back into setCenter.
  const viewportRef = React.useRef<MapView>({
    zoom: urlState.zoom,
    lat: urlState.lat,
    lng: urlState.lng,
  });

  // When URL-driven viewport changes arrive (e.g. user edits address bar),
  // we need to imperatively move the map. Use a counter so MapLibreMap sees
  // a new object reference each time.
  const [externalView, setExternalView] = React.useState<
    (MapView & { seq: number }) | undefined
  >(undefined);

  // Track the previous raw search string to detect external navigation.
  // We store and compare the raw window.location.search (with unencoded chars)
  // rather than searchParams.toString() (which re-encodes).
  const lastWrittenSearch = React.useRef('');

  // Detect external navigation (user editing the address bar) by comparing
  // current location.search to what we last wrote.
  const prevSearchRef = React.useRef(window.location.search);
  React.useEffect(() => {
    const current = window.location.search;
    if (
      current !== lastWrittenSearch.current &&
      current !== prevSearchRef.current
    ) {
      // External navigation: sync viewport imperatively.
      setExternalView((prev) => ({
        zoom: urlState.zoom,
        lat: urlState.lat,
        lng: urlState.lng,
        seq: (prev?.seq ?? 0) + 1,
      }));
      viewportRef.current = {
        zoom: urlState.zoom,
        lat: urlState.lat,
        lng: urlState.lng,
      };
    }
    prevSearchRef.current = current;
  }, [searchParams, urlState.zoom, urlState.lat, urlState.lng]);

  const updateUrl = React.useCallback(
    (nextYear: string, ids: number[], view?: MapView, levels?: Set<string>) => {
      const { zoom, lat, lng } = view ?? viewportRef.current;
      const search = buildSearch({
        zoom,
        lat,
        lng,
        year: nextYear,
        ids,
        adminLevels: levels ?? urlState.adminLevels,
      });
      lastWrittenSearch.current = `?${search}`;
      navigate({ search: `?${search}` }, { replace: true });
    },
    [navigate, urlState.adminLevels],
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
    [relations],
  );

  const selectedFeatures = React.useMemo(
    () => resolveFeatureInfos(urlIds),
    [urlIds, resolveFeatureInfos],
  );
  const selectedIds = React.useMemo(
    () => new Set(selectedFeatures.map((f) => f.id)),
    [selectedFeatures],
  );

  const handleDateChange = React.useCallback(
    (nextDate: string) => {
      updateUrl(nextDate, urlIds);
    },
    [updateUrl, urlIds],
  );

  const handleYearChange = React.useCallback(
    (nextYear: number) => {
      handleDateChange(String(nextYear).padStart(4, '0'));
    },
    [handleDateChange],
  );

  const handleMapMove = React.useCallback(
    (view: MapView) => {
      viewportRef.current = view;
      updateUrl(year, urlIds, view);
    },
    [updateUrl, year, urlIds],
  );

  const handleClickFeature = React.useCallback(
    (features: FeatureInfo[]) => {
      const ids = features.map((f) => Number(f.id));
      updateUrl(year, ids);
    },
    [updateUrl, year],
  );

  const handleSelectRelation = React.useCallback(
    (relationId: number) => {
      const relation = relations.find((r) => Number(r.id) === relationId);
      if (!relation) return;
      const startDateStr = relation.tags['start_date'];
      const nextYear =
        startDateStr ?? String(yearFromDateStr(year)).padStart(4, '0');
      updateUrl(nextYear, [relationId]);
    },
    [relations, year, updateUrl],
  );

  // On initial load: if ids are present but no explicit date, set date to the
  // first feature's start_date. Also infer admin levels from feature tags if
  // not set in URL.
  const initializedRef = React.useRef(false);
  React.useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    if (urlIds.length === 0) return;
    const features = resolveFeatureInfos(urlIds);

    let nextLevels: Set<string> | undefined;
    if (!urlState.adminLevels) {
      const levels = new Set(
        features.map((f) => f.tags['admin_level']).filter(Boolean),
      );
      if (levels.size > 0) nextLevels = levels;
    }

    const hasExplicitDate = urlState.year !== DEFAULT_YEAR;
    if (!hasExplicitDate && features.length > 0) {
      const relation = relations.find((r) => Number(r.id) === urlIds[0]);
      const startDate = relation?.tags['start_date'];
      if (startDate) {
        updateUrl(startDate, urlIds, undefined, nextLevels);
        return;
      }
    }
    if (nextLevels) {
      updateUrl(urlState.year, urlIds, undefined, nextLevels);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Keep initialCenter/Zoom stable across re-renders so MapLibreMap doesn't re-mount.
  const initialViewRef = React.useRef({
    zoom: DEFAULT_STATE.zoom,
    lat: DEFAULT_STATE.lat,
    lng: DEFAULT_STATE.lng,
  });
  React.useEffect(() => {
    // Capture real initial viewport from first URL parse (runs once before any updateUrl).
    if (!initializedRef.current) {
      initialViewRef.current = {
        zoom: urlState.zoom,
        lat: urlState.lat,
        lng: urlState.lng,
      };
    }
  });

  return (
    <>
      {isLoading && <div className="loading">Loading…</div>}
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
        center={[urlState.lng, urlState.lat]}
        zoom={urlState.zoom}
        {...(externalView && { externalView })}
        onMapMove={handleMapMove}
      >
        <ZoomControl />
        <AdminLevelFilter
          adminLevels={adminLevels}
          onChange={(levels) => {
            updateUrl(year, urlIds, undefined, levels);
          }}
        />
        <AdminAreas
          data={data ?? { relations: [], ways: {}, nodes: {} }}
          year={year}
          adminLevels={adminLevels}
          selectedIds={selectedIds}
          onClickFeature={handleClickFeature}
        />
      </MapLibreMap>
      <FeaturePanel
        features={selectedFeatures}
        onClose={() => {
          updateUrl(year, []);
        }}
        onSetDate={handleDateChange}
        onSelectRelation={handleSelectRelation}
      />
    </>
  );
}
