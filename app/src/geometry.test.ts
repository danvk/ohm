import { describe, expect, it } from 'vitest';
import { signedArea } from './geometry';

describe('signedArea', () => {
  it('returns positive area for a counter-clockwise ring', () => {
    // Unit square, CCW: (0,0) → (1,0) → (1,1) → (0,1) → (0,0)
    const ring = [
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
      [0, 0],
    ];
    expect(signedArea(ring)).toBeGreaterThan(0);
  });

  it('returns negative area for a clockwise ring', () => {
    // Unit square, CW: (0,0) → (0,1) → (1,1) → (1,0) → (0,0)
    const ring = [
      [0, 0],
      [0, 1],
      [1, 1],
      [1, 0],
      [0, 0],
    ];
    expect(signedArea(ring)).toBeLessThan(0);
  });

  it('returns the correct magnitude for a known area', () => {
    // Unit square has area 1; shoelace returns 2*area
    const ring = [
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
      [0, 0],
    ];
    expect(signedArea(ring)).toBe(2);
  });

  it('returns 0 for a degenerate (collinear) ring', () => {
    const ring = [
      [0, 0],
      [1, 0],
      [2, 0],
      [0, 0],
    ];
    expect(signedArea(ring)).toBe(0);
  });
});
