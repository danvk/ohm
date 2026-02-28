declare module '*.css' {
  const content: Record<string, string>;
  export default content;
}

interface Relation {
  id: string;
  tags: Record<string, string>;
  ways: number[][];
}
let relations: Relation[];

let ways: Record<string, number[]>;
let dataReady: Promise<void>;
