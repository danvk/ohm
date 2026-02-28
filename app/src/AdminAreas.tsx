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
  year: number;
  onClickFeature: (features: FeatureInfo[]) => void;
  clearSelectionRef?: React.MutableRefObject<(() => void) | null>;
}

function decodePositions(pos: number[]) {
  let x = pos[0];
  let y = pos[1];
  const lng = (x / 4_000_000) * 360 - 180;
  const lat = (y / 2_000_000) * 180 - 90;
  const coords = [[lng, lat]];
  for (let i = 2; i < pos.length; i += 2) {
    x += pos[i];
    y += pos[i + 1];
    const lng = (x / 4_000_000) * 360 - 180;
    const lat = (y / 2_000_000) * 180 - 90;
    coords.push([lng, lat]);
  }
  return coords;
}

export function AdminAreas(props: AdminAreasProps) {
  const { year, onClickFeature } = props;
  const admin2ForYear = React.useMemo(() => {
    const yearStr = String(year).padStart(4, '0');
    const out: typeof relations = {};
    for (const [id, relation] of Object.entries(relations)) {
      const { tags } = relation;
      if (
        tags['admin_level'] != '2' ||
        ('start_date' in tags && yearStr < tags['start_date']) ||
        ('end_date' in tags && yearStr >= tags['end_date'])
      ) {
        continue;
      }
      out[id] = relation;
    }
    return out;
  }, [year]);

  // admin2ForYear contains an ID -> Relation mapping with a list of way IDs for each
  //   relation. Together, these form a polygon.
  // The global "ways" variable contains a mapping from way ID -> coordinate string
  // The decodePositions function can be used to decode these to lng/lats.

  const geojson = React.useMemo<FeatureCollection<MultiPolygon>>(() => {
    const features: Feature<MultiPolygon>[] = [];
    for (const [id, relation] of Object.entries(admin2ForYear)) {
      const rings: Position[][] = [];

      for (const ring of relation.ways) {
        let currentRing: Position[] = [];
        for (const wayId of ring) {
          const encoded = ways[Math.abs(wayId)];
          if (!encoded) {
            throw new Error(`Missing way ${wayId}`);
          }
          const coords = decodePositions(encoded);
          if (wayId < 0) {
            currentRing = currentRing.concat(coords.reverse());
          } else {
            currentRing = currentRing.concat(coords);
          }
        }
        rings.push(currentRing);
      }
      if (rings.length > 0) {
        features.push({
          type: 'Feature',
          id,
          geometry: {
            type: 'MultiPolygon',
            coordinates: rings.map((r) => [r]), // no holes
          },
          properties: relation.tags,
        });
      }
    }
    return { type: 'FeatureCollection', features };
  }, [admin2ForYear]);

  const map = useMap();
  const selectedIds = React.useRef<Set<string | number>>(new Set());

  const clearSelection = React.useCallback(() => {
    if (!map) return;
    for (const id of selectedIds.current) {
      map.setFeatureState({ source: 'admin2', id }, { selected: false });
    }
    selectedIds.current.clear();
  }, [map]);

  React.useEffect(() => {
    if (props.clearSelectionRef) {
      props.clearSelectionRef.current = clearSelection;
    }
  }, [clearSelection, props.clearSelectionRef]);

  const handleOnClick = React.useCallback(
    (e: maplibregl.MapLayerMouseEvent) => {
      if (!map) return;
      const SOURCE_ID = 'admin2';
      // Clear previous selection
      clearSelection();

      const features = map.queryRenderedFeatures(e.point, {
        layers: ['admin2-fill'],
      });
      for (const f of features) {
        if (f.id !== undefined) {
          map.setFeatureState(
            { source: SOURCE_ID, id: f.id },
            { selected: true },
          );
          selectedIds.current.add(f.id);
        }
      }
      onClickFeature(
        features.map((f) => ({
          id: f.id ?? '?',
          tags: (f.properties ?? {}) as Record<string, string>,
        })),
      );
    },
    [map, onClickFeature],
  );

  React.useEffect(() => {
    if (!map) return;

    const SOURCE_ID = 'admin2';
    const FILL_LAYER_ID = 'admin2-fill';
    const LINE_LAYER_ID = 'admin2-line';

    if (!map.getSource(SOURCE_ID)) {
      map.addSource(SOURCE_ID, { type: 'geojson', data: geojson });
      map.addLayer({
        id: FILL_LAYER_ID,
        type: 'fill',
        source: SOURCE_ID,
        paint: {
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
        },
      });
      map.addLayer({
        id: LINE_LAYER_ID,
        type: 'line',
        source: SOURCE_ID,
        paint: {
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
        },
      });
      map.on('click', FILL_LAYER_ID, handleOnClick);
      map.on('click', LINE_LAYER_ID, handleOnClick);
    } else {
      (map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource).setData(geojson);
    }

    return () => {
      if (map.getLayer(FILL_LAYER_ID)) map.removeLayer(FILL_LAYER_ID);
      if (map.getLayer(LINE_LAYER_ID)) map.removeLayer(LINE_LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      map.off('click', FILL_LAYER_ID, handleOnClick);
      map.off('click', LINE_LAYER_ID, handleOnClick);
    };
  }, [map, geojson]);

  return null;
}
