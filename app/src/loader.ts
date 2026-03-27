import type { Relation, Node } from './ohm-data';

export interface AppData {
  relations: Relation[];
  ways: Record<string, number[]>;
  nodes: Record<string, Node>;
}

export async function loadDataForLevels(
  adminLevels: Set<string>,
): Promise<AppData> {
  const levels = [...adminLevels];

  const fetches = levels.flatMap((level) => [
    fetch(`relations${level}.json`).then(
      (r) => r.json() as Promise<Relation[]>,
    ),
    fetch(`ways${level}.json`).then(
      (r) => r.json() as Promise<Record<string, number[]>>,
    ),
    fetch(`nodes${level}.json`).then(
      (r) => r.json() as Promise<Record<string, Node>>,
    ),
  ]);

  const results = await Promise.all(fetches);

  const relations: Relation[] = [];
  const ways: Record<string, number[]> = {};
  const nodes: Record<string, Node> = {};

  for (let i = 0; i < levels.length; i++) {
    const levelRelations = results[i * 3] as Relation[];
    const levelWays = results[i * 3 + 1] as Record<string, number[]>;
    const levelNodes = results[i * 3 + 2] as Record<string, Node>;

    relations.push(...levelRelations);
    Object.assign(ways, levelWays);
    Object.assign(nodes, levelNodes);
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
