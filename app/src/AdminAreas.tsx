import React from 'react';

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

  return null;
}
