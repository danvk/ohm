import { describe, expect, it } from 'vitest';
import {
  SLIDER_MAX,
  MIN_YEAR,
  MAX_YEAR,
  yearToSlider,
  sliderToYear,
  snapYear,
  snapYearByPixels,
} from './slider-utils';

describe('yearToSlider', () => {
  it('maps segment boundaries exactly', () => {
    expect(yearToSlider(-6000)).toBe(0);
    expect(yearToSlider(-3000)).toBe(1000);
    expect(yearToSlider(-1000)).toBe(2000);
    expect(yearToSlider(0)).toBe(3000);
    expect(yearToSlider(MAX_YEAR)).toBe(SLIDER_MAX);
  });

  it('is monotonically increasing', () => {
    const years = [
      -6000, -4000, -3000, -2000, -1000, -500, 0, 500, 1000, 1500, 1900, 2000,
      2026,
    ];
    for (let i = 1; i < years.length; i++) {
      expect(yearToSlider(years[i])).toBeGreaterThan(
        yearToSlider(years[i - 1]),
      );
    }
  });

  it('stays within [0, SLIDER_MAX]', () => {
    for (const year of [MIN_YEAR, -3000, -1000, 0, 1000, MAX_YEAR]) {
      const v = yearToSlider(year);
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(SLIDER_MAX);
    }
  });

  it('compresses ancient history relative to modern times', () => {
    // The sqrt scale means the first 1000 years CE take more slider space than all of 0-1000 CE
    const ancientRange = yearToSlider(-3000) - yearToSlider(-6000); // 3000 years in BCE
    const modernRange = yearToSlider(2026) - yearToSlider(1000); // 1026 years of CE
    expect(modernRange).toBeGreaterThan(ancientRange);
  });
});

describe('sliderToYear', () => {
  it('maps segment boundaries exactly', () => {
    expect(sliderToYear(0)).toBe(-6000);
    expect(sliderToYear(1000)).toBe(-3000);
    expect(sliderToYear(2000)).toBe(-1000);
    expect(sliderToYear(3000)).toBe(0);
    expect(sliderToYear(SLIDER_MAX)).toBe(MAX_YEAR);
  });

  it('is monotonically increasing', () => {
    const positions = [
      0,
      500,
      1000,
      1500,
      2000,
      2500,
      3000,
      5000,
      7000,
      9000,
      SLIDER_MAX,
    ];
    for (let i = 1; i < positions.length; i++) {
      expect(sliderToYear(positions[i])).toBeGreaterThan(
        sliderToYear(positions[i - 1]),
      );
    }
  });

  it('stays within [MIN_YEAR, MAX_YEAR]', () => {
    for (const pos of [0, 1000, 2000, 3000, 5000, SLIDER_MAX]) {
      const y = sliderToYear(pos);
      expect(y).toBeGreaterThanOrEqual(MIN_YEAR);
      expect(y).toBeLessThanOrEqual(MAX_YEAR);
    }
  });
});

describe('yearToSlider / sliderToYear round-trips', () => {
  it('year → slider → year is within rounding tolerance', () => {
    // Resolution per segment: ~3yr (ancient), ~2yr (middle), ~1yr (late BCE), sub-year (CE sqrt)
    const cases: [number, number][] = [
      [-6000, 0],
      [-5000, 3],
      [-4000, 3],
      [-3000, 0],
      [-2500, 2],
      [-2000, 2],
      [-1500, 2],
      [-1000, 0],
      [-800, 1],
      [-500, 1],
      [-100, 1],
      [0, 0],
      [500, 1],
      [1000, 1],
      [1500, 1],
      [1900, 1],
      [2000, 1],
      [2026, 0],
    ];
    for (const [year, tolerance] of cases) {
      const roundTrip = sliderToYear(yearToSlider(year));
      expect(Math.abs(roundTrip - year)).toBeLessThanOrEqual(tolerance);
    }
  });

  it('slider → year → slider is exact at segment boundaries', () => {
    for (const pos of [0, 1000, 2000, 3000, SLIDER_MAX]) {
      expect(yearToSlider(sliderToYear(pos))).toBe(pos);
    }
  });

  it('slider → year → slider: sliderToYear(yearToSlider(y)) is close to y', () => {
    // Equivalently: converting a slider pos to a year and back gives the same year.
    // This is a cleaner invariant than checking slider units, since the sqrt segment
    // has many slider units per year near recent times, making slider-unit tolerance segment-dependent.
    const positions = [
      0,
      500,
      1000,
      1500,
      2000,
      2500,
      3000,
      4000,
      6000,
      8000,
      9000,
      SLIDER_MAX,
    ];
    for (const pos of positions) {
      const year = sliderToYear(pos);
      const roundTripYear = sliderToYear(yearToSlider(year));
      expect(Math.abs(roundTripYear - year)).toBeLessThanOrEqual(3);
    }
  });
});

describe('snapYear', () => {
  it('snaps years >= 1900 to nearest 50 when close', () => {
    // 1950 is a "nice" year; values close to it should snap
    expect(snapYear(yearToSlider(1950), 1950)).toBe(1950);
    expect(snapYear(yearToSlider(1948), 1948)).toBe(1950);
    expect(snapYear(yearToSlider(1952), 1952)).toBe(1950);
  });

  it('does not snap years >= 1900 when far from a 50-boundary', () => {
    // 1925 is equidistant between 1900 and 1950 — may or may not snap, but 1930 should not snap to 1950
    const result = snapYear(yearToSlider(1930), 1930);
    // Should stay near 1930, not jump to 1950
    expect(Math.abs(result - 1930)).toBeLessThan(20);
  });

  it('rounds years in [-1000, 1900) to nearest 10', () => {
    expect(snapYear(yearToSlider(1453), 1453)).toBe(1450);
    expect(snapYear(yearToSlider(776), 776)).toBe(780);
    expect(snapYear(yearToSlider(-44), -44)).toBe(-40);
  });

  it('rounds years in [-3000, -1000) to nearest 50', () => {
    expect(snapYear(yearToSlider(-1234), -1234)).toBe(-1250);
    expect(snapYear(yearToSlider(-2001), -2001)).toBe(-2000);
  });

  it('rounds years < -3000 to nearest 100', () => {
    expect(snapYear(yearToSlider(-4321), -4321)).toBe(-4300);
    expect(snapYear(yearToSlider(-5550), -5550)).toBe(-5500); // JS Math.round(-55.5) = -55
  });
});

describe('snapYearByPixels', () => {
  const SLIDER_WIDTH = 1000; // hypothetical 1000px wide slider

  it('rounds years in [-1000, 1900) to nearest 10', () => {
    expect(snapYearByPixels(1453, SLIDER_WIDTH)).toBe(1450);
    expect(snapYearByPixels(-44, SLIDER_WIDTH)).toBe(-40);
  });

  it('rounds years in [-3000, -1000) to nearest 50', () => {
    expect(snapYearByPixels(-1234, SLIDER_WIDTH)).toBe(-1250);
  });

  it('rounds years < -3000 to nearest 100', () => {
    expect(snapYearByPixels(-4321, SLIDER_WIDTH)).toBe(-4300);
  });

  it('snaps years >= 1900 to nearest 50 when close in pixels', () => {
    // 1950 exactly should always snap to itself
    expect(snapYearByPixels(1950, SLIDER_WIDTH)).toBe(1950);
  });
});
