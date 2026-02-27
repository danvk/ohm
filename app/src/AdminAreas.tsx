import React from 'react';
import type { Feature, FeatureCollection, Polygon } from 'geojson';
import maplibregl from 'maplibre-gl';
import { useMap } from './MapLibreMap';

export interface AdminAreasProps {
  year: number;
}

// The first two entries are quantized [lng, lat].
// The remaining entries are delta encoded.
function lastEncodedPoint(pos: number[]): [number, number] {
  let x = pos[0]!;
  let y = pos[1]!;
  for (let i = 2; i < pos.length; i += 2) {
    x += pos[i]!;
    y += pos[i + 1]!;
  }
  return [x, y];
}

function isWayClosed(pos: number[]): boolean {
  if (pos.length < 4) return false;
  const [lastX, lastY] = lastEncodedPoint(pos);
  return lastX === pos[0] && lastY === pos[1];
}

/** Shoelace formula: positive area = counter-clockwise = right-hand rule. */
function signedArea(ring: number[][]): number {
  let area = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[i + 1];
    area += x1 * y2 - x2 * y1;
  }
  return area;
}

function ensureRightHandRule(ring: number[][]): number[][] {
  // Right-hand rule: exterior rings counter-clockwise (positive signed area).
  const area = signedArea(ring);
  return area > 0 ? ring : ring.slice().reverse();
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
  const { year } = props;
  const admin2ForYear = React.useMemo(() => {
    const yearStr = String(year).padStart(4, '0');
    const out: typeof relations = {};
    for (const [id, relation] of Object.entries(relations)) {
      if (id != '2851762') {
        continue; // Iceland
      }
      const { tags } = relation;
      if (
        tags['admin_level'] != '2' ||
        ('start_date' in tags && yearStr < tags['start_date']) ||
        ('end_date' in tags && yearStr > tags['end_date'])
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

  const geojson = React.useMemo<FeatureCollection<Polygon>>(() => {
    const features: Feature<Polygon>[] = [];
    for (const [id, relation] of Object.entries(admin2ForYear)) {
      const rings: number[][][] = [];
      let currentRing: number[][] = [];

      for (const wayId of relation.ways) {
        const encoded = ways[wayId];
        if (!encoded) continue;

        // Check if closed in encoded space to avoid floating-point rounding issues.
        const isClosed = isWayClosed(encoded);

        const coords = decodePositions(encoded);

        if (isClosed) {
          // Close off any open ring accumulated so far.
          if (currentRing.length > 0) {
            currentRing.push(currentRing[0]!);
            rings.push(ensureRightHandRule(currentRing));
            currentRing = [];
          }
          // Add this self-contained closed ring.
          rings.push(ensureRightHandRule(coords));
        } else {
          // Open way — concatenate into the current ring.
          currentRing = currentRing.concat(coords);
        }
      }

      // Close off any remaining open ring.
      if (currentRing.length > 0) {
        currentRing.push(currentRing[0]!);
        rings.push(ensureRightHandRule(currentRing));
      }

      if (rings.length > 0) {
        features.push({
          type: 'Feature',
          id,
          geometry: { type: 'Polygon', coordinates: rings },
          properties: relation.tags,
        });
      }
    }
    return { type: 'FeatureCollection', features };
  }, [admin2ForYear]);

  const map = useMap();

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
        paint: { 'fill-color': '#6080c0', 'fill-opacity': 0.5 },
      });
      map.addLayer({
        id: LINE_LAYER_ID,
        type: 'line',
        source: SOURCE_ID,
        paint: { 'line-color': '#3050a0', 'line-width': 1 },
      });
    } else {
      (map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource).setData(geojson);
    }

    return () => {
      if (map.getLayer(FILL_LAYER_ID)) map.removeLayer(FILL_LAYER_ID);
      if (map.getLayer(LINE_LAYER_ID)) map.removeLayer(LINE_LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
    };
  }, [map, geojson]);

  return null;
}
