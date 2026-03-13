/** Data loader -- run before all other code */
type Globals = typeof window & {
  relations: typeof relations;
  ways: typeof ways;
  nodes: typeof nodes;
  dataReady: typeof dataReady;
};

async function loadData() {
  const relationsR = fetch('relations.json');
  const waysR = fetch('ways.json');
  const nodesR = fetch('nodes.json');

  const [relationsJSON, waysJSON, nodesJSON] = (await Promise.all([
    (await relationsR).json(),
    (await waysR).json(),
    (await nodesR).json(),
  ])) as [typeof relations, typeof ways, typeof nodes];

  console.log(
    'Loaded',
    [...Object.keys(relationsJSON)].length,
    'relations,',
    [...Object.keys(waysJSON)].length,
    'ways, and',
    [...Object.keys(nodesJSON)].length,
  );
  (window as Globals).relations = relationsJSON;
  (window as Globals).ways = waysJSON;
  (window as Globals).nodes = nodesJSON;
}

(window as Globals).dataReady = loadData();
