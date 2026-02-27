import React from 'react';
import type { Feature, FeatureCollection, Polygon } from 'geojson';
import maplibregl from 'maplibre-gl';
import { useMap } from './MapLibreMap';

export interface AdminAreasProps {
  year: number;
}

// The first two entries are quantized [lng, lat].
// The remaining entries are delta encoded.
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
      let ring: number[][] = [];
      for (const wayId of relation.ways) {
        const encoded = ways[wayId];
        if (encoded) {
          ring = ring.concat(decodePositions(encoded));
        }
      }
      if (ring.length > 0) {
        ring.push(ring[0]);
        features.push({
          type: 'Feature',
          id,
          geometry: { type: 'Polygon', coordinates: [ring] },
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
