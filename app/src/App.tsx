import React from 'react';
import { useQueryState, useQueryStates, throttle } from 'nuqs';
import { MapLibreMap, type MapView } from './MapLibreMap';
import { ZoomControl } from './ZoomControl';
import { AdminAreas } from './AdminAreas';
import { AdminLevelFilter } from './AdminLevelFilter';
import { FeaturePanel, type FeatureInfo } from './FeaturePanel';
import { TimeControl } from './TimeControl';
import {
  DEFAULT_YEAR,
  DEFAULT_STATE,
  mapViewParser,
  dateParser,
  idsParser,
  levelsParser,
  rangeParser,
} from './useUrlState';
import Logo from './ohm_logo.svg';
import { yearFromDateStr, yearToDateStr } from './date-utils';
import type { AppData } from './loader.ts';
import { loadDataForLevels } from './loader.ts';
import { MAX_YEAR, MIN_YEAR } from './slider/slider-utils.ts';

export default function App() {
  // Map viewport — 500ms throttle (can fire 60fps during pan/zoom)
  const [mapView, setMapView] = useQueryState(
    'map',
    mapViewParser
      .withDefault({
        zoom: DEFAULT_STATE.zoom,
        lat: DEFAULT_STATE.lat,
        lng: DEFAULT_STATE.lng,
      })
      .withOptions({ history: 'replace', limitUrlUpdates: throttle(500) }),
  );

  // Date — 300ms throttle (can fire rapidly while dragging the time slider)
  const [date, setDate] = useQueryState(
    'date',
    dateParser
      .withDefault(DEFAULT_YEAR)
      .withOptions({ history: 'replace', limitUrlUpdates: throttle(300) }),
  );

  // ids and levels — immediate (single-click actions, no drag)
  const [{ ids, levels }, setUrlParams] = useQueryStates(
    {
      ids: idsParser.withDefault([]),
      levels: levelsParser, // null default (absent from URL)
    },
    { history: 'replace' },
  );

  const urlIds = ids;
  const adminLevels = levels ?? new Set(['2']);

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

  // Range mode: `range=min,max` in URL means range mode is active.
  // null means single-slider mode (parameter absent from URL).
  const [urlRange, setUrlRange] = useQueryState(
    'range',
    rangeParser.withOptions({
      history: 'replace',
      limitUrlUpdates: throttle(300),
    }),
  );

  const isRange = urlRange !== null;
  const minYear = urlRange?.min ?? 1500;
  const maxYear = urlRange?.max ?? 1900;

  // Preserve the last range when switching to single mode, so switching back restores it.
  const lastRangeRef = React.useRef({ min: minYear, max: maxYear });
  if (isRange) {
    lastRangeRef.current = { min: minYear, max: maxYear };
  }

  // Viewport (zoom/lat/lng) is kept in a ref so map moves don't cause re-renders
  // and don't feed back into setCenter.
  const viewportRef = React.useRef<MapView>({
    zoom: mapView.zoom,
    lat: mapView.lat,
    lng: mapView.lng,
  });

  // When URL-driven viewport changes arrive (e.g. user edits address bar),
  // we need to imperatively move the map. Use a counter so MapLibreMap sees
  // a new object reference each time.
  const [externalView, setExternalView] = React.useState<
    (MapView & { seq: number }) | undefined
  >(undefined);

  // Detect external navigation (user editing the address bar) by comparing
  // the current mapView from nuqs to what we last explicitly set.
  const lastSetMapViewRef = React.useRef<typeof mapView | null>(null);
  React.useEffect(() => {
    const last = lastSetMapViewRef.current;
    if (!last) return;
    const isDifferent =
      Math.abs(mapView.zoom - last.zoom) > 0.01 ||
      Math.abs(mapView.lat - last.lat) > 0.0001 ||
      Math.abs(mapView.lng - last.lng) > 0.0001;
    if (isDifferent) {
      setExternalView((prev) => ({
        zoom: mapView.zoom,
        lat: mapView.lat,
        lng: mapView.lng,
        seq: (prev?.seq ?? 0) + 1,
      }));
      viewportRef.current = {
        zoom: mapView.zoom,
        lat: mapView.lat,
        lng: mapView.lng,
      };
    }
  }, [mapView]);

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
            ...(relation.chronology && { chronology: relation.chronology }),
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

  const handleYearChange = React.useCallback(
    (nextYear: number) => {
      setDate(yearToDateStr(nextYear));
    },
    [setDate],
  );

  const handleMapMove = React.useCallback(
    (view: MapView) => {
      viewportRef.current = view;
      lastSetMapViewRef.current = view;
      setMapView(view);
    },
    [setMapView],
  );

  const handleClickFeature = React.useCallback(
    (features: FeatureInfo[]) => {
      const newIds = features.map((f) => Number(f.id));
      setUrlParams({ ids: newIds });
    },
    [setUrlParams],
  );

  const handleSelectRelation = React.useCallback(
    (relationId: number) => {
      const relation = relations.find((r) => Number(r.id) === relationId);
      if (!relation) return;
      const startDateStr = relation.tags['start_date'];
      const nextDate = startDateStr ?? yearToDateStr(yearFromDateStr(date));
      setDate(nextDate);
      setUrlParams({ ids: [relationId] });
    },
    [relations, date, setDate, setUrlParams],
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
    if (!levels) {
      const inferredLevels = new Set(
        features.map((f) => f.tags['admin_level']).filter(Boolean),
      );
      if (inferredLevels.size > 0) nextLevels = inferredLevels;
    }

    const hasExplicitDate = date !== DEFAULT_YEAR;
    if (!hasExplicitDate && features.length > 0) {
      const relation = relations.find((r) => Number(r.id) === urlIds[0]);
      const startDate = relation?.tags['start_date'];
      if (startDate) {
        setDate(startDate);
        if (nextLevels) setUrlParams({ levels: nextLevels });
        return;
      }
    }
    if (nextLevels) {
      setUrlParams({ levels: nextLevels });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleChangeRange = React.useCallback(
    (newMinYear: number, newMaxYear: number) => {
      setUrlRange({ min: newMinYear, max: newMaxYear });
      const currentYear = yearFromDateStr(date);
      if (currentYear < newMinYear) {
        setDate(yearToDateStr(newMinYear));
      } else if (currentYear > newMaxYear) {
        setDate(yearToDateStr(newMaxYear));
      }
    },
    [date, setDate, setUrlRange],
  );

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )
        return;
      if (e.key !== 'n' && e.key !== 'p') return;
      const currentYear = yearFromDateStr(date);
      const newYear = e.key === 'n' ? currentYear + 1 : currentYear - 1;
      const clampedYear = Math.max(MIN_YEAR, Math.min(MAX_YEAR, newYear));
      if (isRange) {
        if (clampedYear > maxYear)
          setUrlRange({ min: minYear, max: clampedYear });
        else if (clampedYear < minYear)
          setUrlRange({ min: clampedYear, max: maxYear });
      }
      handleYearChange(clampedYear);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [date, isRange, minYear, maxYear, handleYearChange, setUrlRange]);

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
      <TimeControl
        year={date}
        minYear={minYear}
        maxYear={maxYear}
        onChange={setDate}
        onChangeRange={handleChangeRange}
        isRange={isRange}
        onChangeIsRange={(newIsRange) => {
          if (!newIsRange) {
            setUrlRange(null);
            return;
          }
          const currentYear = yearFromDateStr(date);
          let { min, max } = lastRangeRef.current;
          if (currentYear < min || currentYear > max) {
            min = Math.round((currentYear - 200) / 100) * 100;
            max = Math.round((currentYear + 200) / 100) * 100;
            if (min === max) max += 100;
            min = Math.max(min, MIN_YEAR);
            max = Math.min(max, MAX_YEAR);
            if (min >= max) min = max - 100;
          }
          setUrlRange({ min, max });
        }}
      />
      <MapLibreMap
        containerId="map"
        containerClassName={'maplibregl-map' + (isRange ? ' dual' : ' single')}
        center={[mapView.lng, mapView.lat]}
        zoom={mapView.zoom}
        {...(externalView && { externalView })}
        onMapMove={handleMapMove}
      >
        <ZoomControl />
        <AdminLevelFilter
          adminLevels={adminLevels}
          onChange={(newLevels) => {
            setUrlParams({ levels: newLevels });
          }}
        />
        <AdminAreas
          data={data ?? { relations: [], ways: {}, nodes: {} }}
          year={date}
          adminLevels={adminLevels}
          selectedIds={selectedIds}
          onClickFeature={handleClickFeature}
        />
      </MapLibreMap>
      <FeaturePanel
        features={selectedFeatures}
        onClose={() => {
          setUrlParams({ ids: [] });
        }}
        onSetDate={setDate}
        onSelectRelation={handleSelectRelation}
      />
    </>
  );
}
