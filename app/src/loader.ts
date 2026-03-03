/** Data loader -- run before all other code */
type Globals = typeof window & {
  relations: typeof relations;
  ways: typeof ways;
  dataReady: typeof dataReady;
};

async function loadData() {
  const relationsR = fetch('/relations.json');
  const waysR = fetch('/ways.json');

  const [relationsJSON, waysJSON] = (await Promise.all([
    (await relationsR).json(),
    (await waysR).json(),
  ])) as [typeof relations, typeof ways];

  console.log(
    'Loaded',
    [...Object.keys(relationsJSON)].length,
    'relations and',
    [...Object.keys(waysJSON)].length,
    'ways',
  );
  (window as Globals).relations = relationsJSON;
  (window as Globals).ways = waysJSON;
}

(window as Globals).dataReady = loadData();
