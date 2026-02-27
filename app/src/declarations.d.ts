declare module '*.css' {
  const content: Record<string, string>;
  export default content;
}

interface Relation {
  tags: Record<string, string>;
  ways: number[];
}
let relations: Record<string, Relation>;

let ways: Record<string, number[]>;
let dataReady: Promise<void>;
