export interface Chronology {
  id: number;
  name: string;
  prev?: number;
  next?: number;
}

export interface Relation {
  id: string;
  tags: Record<string, string>;
  /** Polygons: ways[i] is a polygon, ways[i][0] is the outer ring,
   *  ways[i][1..] are inner rings (holes). Each ring is a base64-encoded
   *  varint byte stream of delta+zigzag encoded signed way IDs. */
  ways: string[][];
  /** Nodes that are direct members of this relation */
  nodes: number[];
  chronology: Chronology[];
}

/** A relation as stored in the JSON file before tag decoding. */
export interface RawRelation extends Omit<Relation, 'tags'> {
  /** Flat encoded tag array. Negative int n = pair index -(n+1) in tagPairs.
   *  Non-negative int k followed by string|int = key tagKeys[k] + value. */
  tags: (number | string)[];
}

/** Top-level structure of a relationsN.json file. */
export interface RelationsFile {
  tagPairs: [string, string][];
  tagKeys: string[];
  tagVals: string[];
  relations: RawRelation[];
}

export interface Node {
  loc: [number, number];
  tags: Record<string, string>;
}
