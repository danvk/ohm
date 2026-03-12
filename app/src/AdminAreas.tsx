import React from 'react';
import type {
  Feature,
  FeatureCollection,
  MultiPolygon,
  Position,
} from 'geojson';
import maplibregl from 'maplibre-gl';
import { useMap } from './MapLibreMap';
import type { FeatureInfo } from './FeaturePanel';

export interface AdminAreasProps {
  year: string;
  selectedIds: Set<string | number>;
  onClickFeature: (features: FeatureInfo[]) => void;
}

const SOURCE_ID = 'admin2';
const FILL_LAYER_ID = 'admin2-fill';
const LINE_LAYER_ID = 'admin2-line';

type FillPaintStyle = Exclude<
  maplibregl.FillLayerSpecification['paint'],
  undefined
>;

const PAINT_STYLE: FillPaintStyle = {
  'fill-color': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    '#ff8c00',
    '#6080c0',
  ],
  'fill-opacity': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    0.7,
    0.5,
  ],
};

type LinePaintStyle = Exclude<
  maplibregl.LineLayerSpecification['paint'],
  undefined
>;
const LINE_STYLE: LinePaintStyle = {
  'line-color': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    '#cc5500',
    '#3050a0',
  ],
  'line-width': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    2,
    1,
  ],
};

function decodePositions(pos: number[]) {
  let x = pos[0];
  let y = pos[1];
  const lng = (x / 4_000_000) * 360 - 180;
  const lat = (y / 2_000_000) * 180 - 90;
  const coords = new Array<Position>(pos.length / 2);
  coords[0] = [lng, lat];
  for (let i = 2; i < pos.length; i += 2) {
    x += pos[i];
    y += pos[i + 1];
    const lng = (x / 4_000_000) * 360 - 180;
    const lat = (y / 2_000_000) * 180 - 90;
    coords[i / 2] = [lng, lat];
  }
  return coords;
}

function decodeRing(signedWayIds: number[]): Position[] {
  const segments: Position[][] = [];
  for (const wayId of signedWayIds) {
    const encoded = ways[Math.abs(wayId)];
    if (!encoded) {
      throw new Error(`Missing way ${wayId}`);
    }
    const coords = decodePositions(encoded);
    segments.push(wayId < 0 ? coords.reverse() : coords);
  }
  return segments.flat();
}

function buildFeature(id: string, relation: Relation): Feature<MultiPolygon> {
  // relation.ways is a list of polygons; each polygon is [outerRing, ...holeRings]
  const polygons: Position[][][] = relation.ways.map((polygon) =>
    polygon.map((ring) => decodeRing(ring)),
  );
  return {
    type: 'Feature',
    id,
    geometry: {
      type: 'MultiPolygon',
      coordinates: polygons,
    },
    properties: relation.tags,
  };
}

export function AdminAreas(props: AdminAreasProps) {
  const { year, onClickFeature } = props;

  // Cache built Feature objects by relation ID so that features whose
  // [start_date, end_date) interval spans the current *and* previous year
  // don't need to be recomputed.
  const featureCache = React.useRef<Map<string, Feature<MultiPolygon>>>(
    new Map(),
  );

  // Build a map from relation ID (as string) to the full Relation object for O(1) lookup.
  const relationById = React.useMemo(
    () => new Map<string, Relation>(relations.map((r) => [String(r.id), r])),
    [],
  );

  const geojson = React.useMemo<FeatureCollection<MultiPolygon>>(() => {
    const features: Feature<MultiPolygon>[] = [];
    const nextCache = new Map<string, Feature<MultiPolygon>>();

    for (const relation of relations) {
      const { id, tags } = relation;
      if (
        tags['admin_level'] != '2' ||
        ('start_date' in tags && year < tags['start_date']) ||
        ('end_date' in tags && year >= tags['end_date'])
      ) {
        continue;
      }
      // Reuse cached feature if available, otherwise build and cache it.
      let feature = featureCache.current.get(id);
      if (!feature) {
        feature = buildFeature(id, relation);
      }
      nextCache.set(id, feature);
      features.push(feature);
    }

    featureCache.current = nextCache;
    return { type: 'FeatureCollection', features };
  }, [year]);

  const map = useMap();

  // Sync selectedIds prop → MapLibre feature state
  const prevSelectedIds = React.useRef<Set<string | number>>(new Set());
  React.useEffect(() => {
    if (!map) return;
    for (const id of prevSelectedIds.current) {
      if (!props.selectedIds.has(id)) {
        map.setFeatureState({ source: SOURCE_ID, id }, { selected: false });
      }
    }
    for (const id of props.selectedIds) {
      map.setFeatureState({ source: SOURCE_ID, id }, { selected: true });
    }
    prevSelectedIds.current = new Set(props.selectedIds);
  }, [map, props.selectedIds]);

  // Keep a stable ref to onClickFeature so click handlers registered once
  // always call the latest version without needing to be re-registered.
  const onClickFeatureRef = React.useRef(onClickFeature);
  React.useEffect(() => {
    onClickFeatureRef.current = onClickFeature;
  }, [onClickFeature]);

  // Effect 1: add source, layers, and click handlers once per map instance.
  React.useEffect(() => {
    if (!map) return;

    const EMPTY: FeatureCollection<MultiPolygon> = {
      type: 'FeatureCollection',
      features: [],
    };
    map.addSource(SOURCE_ID, { type: 'geojson', data: EMPTY });
    map.addLayer({
      id: FILL_LAYER_ID,
      type: 'fill',
      source: SOURCE_ID,
      paint: PAINT_STYLE,
    });
    map.addLayer({
      id: LINE_LAYER_ID,
      type: 'line',
      source: SOURCE_ID,
      paint: LINE_STYLE,
    });

    const handleLayerClick = (e: maplibregl.MapLayerMouseEvent) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [FILL_LAYER_ID],
      });
      onClickFeatureRef.current(
        features.map((f) => {
          const id = f.id ?? '?';
          const relation = relationById.get(String(id));
          return {
            id,
            tags: (f.properties ?? {}) as Record<string, string>,
            ...(relation?.chronology && { chronology: relation.chronology }),
          };
        }),
      );
    };
    const handleMapClick = (e: maplibregl.MapMouseEvent) => {
      const hits = map.queryRenderedFeatures(e.point, {
        layers: [FILL_LAYER_ID],
      });
      if (hits.length === 0) {
        onClickFeatureRef.current([]);
      }
    };

    map.on('click', FILL_LAYER_ID, handleLayerClick);
    map.on('click', LINE_LAYER_ID, handleLayerClick);
    map.on('click', handleMapClick);

    return () => {
      if (map.getLayer(FILL_LAYER_ID)) map.removeLayer(FILL_LAYER_ID);
      if (map.getLayer(LINE_LAYER_ID)) map.removeLayer(LINE_LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      map.off('click', FILL_LAYER_ID, handleLayerClick);
      map.off('click', LINE_LAYER_ID, handleLayerClick);
      map.off('click', handleMapClick);
    };
  }, [map]);

  // Effect 2: push updated geojson data whenever it changes, then re-apply
  // feature state. MapLibre clears feature state when setData is called, so we
  // must restore selectedIds after every data reload.
  React.useEffect(() => {
    if (!map) return;
    const source = map.getSource(SOURCE_ID) as
      | maplibregl.GeoJSONSource
      | undefined;
    if (!source) return;
    source.setData(geojson);
    // Re-apply selected state after the data reload wipes it.
    for (const id of props.selectedIds) {
      map.setFeatureState({ source: SOURCE_ID, id }, { selected: true });
    }
  }, [map, geojson, props.selectedIds]);

  return null;
}
