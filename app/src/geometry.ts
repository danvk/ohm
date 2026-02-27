/**
 * Shoelace formula: positive area = counter-clockwise = right-hand rule.
 * Assumes the ring is closed, i.e. ring[0] === ring[ring.length - 1].
 */
export function signedArea(ring: number[][]): number {
  let area = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [x1, y1] = ring[i]!;
    const [x2, y2] = ring[i + 1]!;
    area += x1! * y2! - x2! * y1!;
  }
  return area;
}
