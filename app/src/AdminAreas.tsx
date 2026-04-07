import React from 'react';
import type {
  Feature,
  FeatureCollection,
  MultiPoint,
  MultiPolygon,
  Position,
} from 'geojson';
import maplibregl from 'maplibre-gl';
import { useMap } from './MapLibreMap';
import type { FeatureInfo } from './FeaturePanel';
import type { AppData } from './loader.ts';
import type { Relation } from './ohm-data.ts';
import { CIRCLE_STYLE, LINE_STYLE, PAINT_STYLE } from './map-style.ts';
import { isDateInRange } from './date.ts';

export interface AdminAreasProps {
  data: AppData;
  year: string;
  adminLevels: Set<string>;
  selectedIds: Set<string | number>;
  onClickFeature: (features: FeatureInfo[]) => void;
}

const SOURCE_ID = 'admin2';
const FILL_LAYER_ID = 'admin2-fill';
const LINE_LAYER_ID = 'admin2-line';
const CIRCLE_LAYER_ID = 'admin2-circle';

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

function decodeRing(signedWayIds: number[], ways: AppData['ways']): Position[] {
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

function buildFeature(
  id: string,
  relation: Relation,
  ways: AppData['ways'],
  nodes: AppData['nodes'],
): Feature<MultiPolygon | MultiPoint> {
  // if a relation doesn't contain any ways, then it might just have a label.
  if (relation.ways.length === 0 && relation.nodes?.length) {
    const points = relation.nodes.map((nodeId) => nodes[nodeId].loc);

    return {
      type: 'Feature',
      id,
      geometry: {
        type: 'MultiPoint',
        coordinates: points,
      },
      properties: {
        ...relation.tags,
        _relation_node: true,
      },
    };
  } else {
    // relation.ways is a list of polygons; each polygon is [outerRing, ...holeRings]
    const polygons: Position[][][] = relation.ways.map((polygon) =>
      polygon.map((ring) => decodeRing(ring, ways)),
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
}

export function AdminAreas(props: AdminAreasProps) {
  const { data, year, adminLevels, onClickFeature } = props;
  const { relations, ways, nodes } = data;

  // Cache built Feature objects by relation ID so that features whose
  // [start_date, end_date) interval spans the current *and* previous year
  // don't need to be recomputed.
  const featureCache = React.useRef<
    Map<string, Feature<MultiPolygon | MultiPoint>>
  >(new Map());

  // Build a map from relation ID (as string) to the full Relation object for O(1) lookup.
  const relationById = React.useMemo(
    () => new Map<string, Relation>(relations.map((r) => [String(r.id), r])),
    [relations],
  );

  const geojson = React.useMemo<
    FeatureCollection<MultiPolygon | MultiPoint>
  >(() => {
    const features: Feature<MultiPolygon | MultiPoint>[] = [];
    const nextCache = new Map<string, Feature<MultiPolygon | MultiPoint>>();

    for (const relation of relations) {
      const { id, tags } = relation;
      if (
        !adminLevels.has(tags['admin_level'] ?? '') ||
        !isDateInRange(year, tags['start_date'], tags['end_date'])
      ) {
        continue;
      }
      // Reuse cached feature if available, otherwise build and cache it.
      let feature = featureCache.current.get(id);
      if (!feature) {
        feature = buildFeature(id, relation, ways, nodes);
      }
      nextCache.set(id, feature);
      features.push(feature);
    }

    featureCache.current = nextCache;
    return { type: 'FeatureCollection', features };
  }, [year, adminLevels, relations, ways, nodes]);

  const map = useMap();

  // Sync selectedIds prop → MapLibre feature state
  const prevSelectedIds = React.useRef<Set<string | number>>(new Set());
  React.useEffect(() => {
    // Always update prevSelectedIds so deselection works correctly later,
    // even if the source doesn't exist yet (Effect 2 will re-apply selections).
    const prev = prevSelectedIds.current;
    prevSelectedIds.current = new Set(props.selectedIds);
    if (!map || !map.getSource(SOURCE_ID)) return;
    for (const id of prev) {
      if (!props.selectedIds.has(id)) {
        map.setFeatureState({ source: SOURCE_ID, id }, { selected: false });
      }
    }
    for (const id of props.selectedIds) {
      map.setFeatureState({ source: SOURCE_ID, id }, { selected: true });
    }
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
    map.addLayer({
      id: CIRCLE_LAYER_ID,
      type: 'circle',
      source: SOURCE_ID,
      paint: CIRCLE_STYLE,
      filter: ['has', '_relation_node'],
    });

    const handleLayerClick = (e: maplibregl.MapLayerMouseEvent) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [FILL_LAYER_ID, CIRCLE_LAYER_ID],
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
        layers: [FILL_LAYER_ID, CIRCLE_LAYER_ID],
      });
      if (hits.length === 0) {
        onClickFeatureRef.current([]);
      }
    };

    map.on('click', FILL_LAYER_ID, handleLayerClick);
    map.on('click', LINE_LAYER_ID, handleLayerClick);
    map.on('click', CIRCLE_LAYER_ID, handleLayerClick);
    map.on('click', handleMapClick);

    return () => {
      if (map.getLayer(FILL_LAYER_ID)) map.removeLayer(FILL_LAYER_ID);
      if (map.getLayer(LINE_LAYER_ID)) map.removeLayer(LINE_LAYER_ID);
      if (map.getLayer(CIRCLE_LAYER_ID)) map.removeLayer(CIRCLE_LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      map.off('click', FILL_LAYER_ID, handleLayerClick);
      map.off('click', LINE_LAYER_ID, handleLayerClick);
      map.off('click', CIRCLE_LAYER_ID, handleLayerClick);
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
