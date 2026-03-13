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
   *  ways[i][1..] are inner rings (holes). Each ring is an ordered list
   *  of signed way IDs (negative = reversed). */
  ways: number[][][];
  /** Nodes that are direct members of this relation */
  nodes: number[];
  chronology: Chronology[];
}

export interface Node {
  loc: [number, number];
  tags: Record<string, string>;
}
