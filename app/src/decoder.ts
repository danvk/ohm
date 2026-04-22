/** See "Data encoding" in app/README.md for an explanation of the encoding. */

import {
  toDecimalEarliest,
  toDecimalExclusiveEnd,
  toDecimalLatest,
} from './date';
import type { RawRelation, Relation, RelationsFile } from './ohm-data';

function decodeTags(
  flat: (number | string)[],
  tagPairs: [string, string][],
  tagKeys: string[],
  tagVals: string[],
): Record<string, string> {
  const tags: Record<string, string> = {};
  let i = 0;
  while (i < flat.length) {
    const x = flat[i++];
    if (typeof x === 'number' && x < 0) {
      const [k, v] = tagPairs[-(x + 1)];
      tags[k] = v;
    } else {
      const k = tagKeys[x as number];
      const raw = flat[i++];
      tags[k] = typeof raw === 'string' ? raw : tagVals[raw as number];
    }
  }
  return tags;
}

export function decodeRelation(
  r: RawRelation,
  relFile: RelationsFile,
): Relation {
  return {
    ...r,
    tags: decodeTags(
      r.tags,
      relFile.tagPairs,
      relFile.tagKeys,
      relFile.tagVals,
    ),
  };
}

/** Add decDates to relations using start_date, end_date and chronologies. */
export function computeEffectiveDates(relations: Relation[]): void {
  const byId = new Map(relations.map((r) => [String(r.id), r]));

  for (const r of relations) {
    const sd = r.tags['start_date'];
    const ed = r.tags['end_date'];
    r.startDecDate = sd ? (toDecimalEarliest(sd) ?? undefined) : undefined;
    r.endDecDate = ed ? (toDecimalExclusiveEnd(ed) ?? undefined) : undefined;
  }

  // Chronology-informed adjustment: when a feature's end_date matches the
  // start_date of the next feature in a chronology, split the interval at
  // the midpoint so neither feature overlaps the other.
  for (const r of relations) {
    const endDate = r.tags['end_date'];
    if (!endDate) continue;
    for (const chrono of r.chronology ?? []) {
      if (chrono.next === undefined) continue;
      const next = byId.get(String(chrono.next));
      if (!next || next.tags['start_date'] !== endDate) continue;
      const earliest = toDecimalEarliest(endDate);
      const latest = toDecimalLatest(endDate);
      if (earliest === null || latest === null) continue;
      const midpoint = (earliest + latest) / 2;
      r.endDecDate = midpoint;
      next.startDecDate = midpoint;
    }
  }
}
