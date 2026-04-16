import type { Relation, Node } from './ohm-data';

// const BASE_URL = '//ohmdash.pages.dev/boundary/';
// const BASE_URL = 'http://localhost:8081/whm-boundary/';
const BASE_URL = '//ohmdash.pages.dev/whm-boundary/';

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

/** Per-level cache: level string → in-flight or resolved Promise. */
const levelCache = new Map<string, Promise<LevelData>>();

function loadLevel(level: string): Promise<LevelData> {
  if (!levelCache.has(level)) {
    const promise = Promise.all([
      fetch(`${BASE_URL}relations${level}.json`).then(
        (r) => r.json() as Promise<Relation[]>,
      ),
      fetch(`${BASE_URL}ways${level}.json`).then(
        (r) => r.json() as Promise<Record<string, number[]>>,
      ),
      fetch(`${BASE_URL}nodes${level}.json`).then(
        (r) => r.json() as Promise<Record<string, Node>>,
      ),
    ]).then(([relations, ways, nodes]) => ({ relations, ways, nodes }));
    levelCache.set(level, promise);
  }
  return levelCache.get(level)!;
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
