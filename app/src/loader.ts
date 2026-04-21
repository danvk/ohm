import type { Relation, RawRelation, RelationsFile, Node } from './ohm-data';
import {
  toDecimalEarliest,
  toDecimalLatest,
  toDecimalExclusiveEnd,
} from './date.ts';

const BASE_URL = '//ohmdash.pages.dev/boundary/';
// const BASE_URL = '//localhost:8081/boundary/';

export interface AppData {
  relations: Relation[];
  ways: Record<string, number[]>;
  nodes: Record<string, Node>;
}

interface LevelData {
  relations: Relation[];
  ways: Record<string, number[]>;
  nodes: Record<string, Node>;
}

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

function decodeRelation(r: RawRelation, relFile: RelationsFile): Relation {
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

/** Per-level cache: level string → in-flight or resolved Promise. */
const levelCache = new Map<string, Promise<LevelData>>();

function loadLevel(level: string): Promise<LevelData> {
  if (!levelCache.has(level)) {
    const promise = Promise.all([
      fetch(`${BASE_URL}relations${level}.b64.json`).then(
        (r) => r.json() as Promise<RelationsFile>,
      ),
      fetch(`${BASE_URL}ways${level}.json`).then(
        (r) => r.json() as Promise<Record<string, number[]>>,
      ),
      fetch(`${BASE_URL}nodes${level}.json`).then(
        (r) => r.json() as Promise<Record<string, Node>>,
      ),
    ]).then(([relFile, ways, nodes]) => ({
      relations: relFile.relations.map((r) => decodeRelation(r, relFile)),
      ways,
      nodes,
    }));
    levelCache.set(level, promise);
  }
  return levelCache.get(level)!;
}

function computeEffectiveDates(relations: Relation[]): void {
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

export async function loadDataForLevels(
  adminLevels: Set<string>,
): Promise<AppData> {
  const levels = [...adminLevels];

  const fetches = levels.map((level) => loadLevel(level));

  const results = await Promise.all(fetches);

  const relations: Relation[] = [];
  const ways: Record<string, number[]> = {};
  const nodes: Record<string, Node> = {};

  for (const levelData of results) {
    relations.push(...levelData.relations);
    Object.assign(ways, levelData.ways);
    Object.assign(nodes, levelData.nodes);
  }

  computeEffectiveDates(relations);

  console.log(
    'Loaded',
    relations.length,
    'relations,',
    Object.keys(ways).length,
    'ways, and',
    Object.keys(nodes).length,
    `nodes for levels: ${levels.join(', ')}.`,
  );

  return { relations, ways, nodes };
}
