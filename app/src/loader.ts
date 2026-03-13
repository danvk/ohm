export interface AppData {
  relations: Relation[];
  ways: Record<string, number[]>;
  nodes: Record<string, Node>;
}

export async function loadData(): Promise<AppData> {
  const [relations, ways, nodes] = await Promise.all([
    fetch('relations.json').then((r) => r.json() as Promise<Relation[]>),
    fetch('ways.json').then(
      (r) => r.json() as Promise<Record<string, number[]>>,
    ),
    fetch('nodes.json').then((r) => r.json() as Promise<Record<string, Node>>),
  ]);

  console.log(
    'Loaded',
    relations.length,
    'relations,',
    Object.keys(ways).length,
    'ways, and',
    Object.keys(nodes).length,
    'nodes.',
  );

  return { relations, ways, nodes };
}
