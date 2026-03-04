declare module '*.css' {
  const content: Record<string, string>;
  export default content;
}
declare module '*.svg' {
  export default {};
}

interface Chronology {
  id: number;
  name: string;
  prev?: number;
  next?: number;
}
interface Relation {
  id: string;
  tags: Record<string, string>;
  /** Polygons: ways[i] is a polygon, ways[i][0] is the outer ring,
   *  ways[i][1..] are inner rings (holes). Each ring is an ordered list
   *  of signed way IDs (negative = reversed). */
  ways: number[][][];
  chronology: Chronology[];
}
let relations: Relation[];

let ways: Record<string, number[]>;
let dataReady: Promise<void>;
