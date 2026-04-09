// The slider's internal range is 0..SLIDER_MAX (integers).
export const SLIDER_MAX = 10000;

// Snap threshold in slider units (0..SLIDER_MAX) for years ≥ 1900.
const SNAP_THRESHOLD = 60;
// Equivalent pixel threshold for onMouseMove (≈ SNAP_THRESHOLD/SLIDER_MAX * typical slider width).
const SNAP_PX_THRESHOLD = 6;

// ── Piecewise scale (fixed historical range, used by SqrtTimeSlider + TimeRange) ──
//
// Divides SLIDER_MAX into four segments:
//   [-6000, -3000]  → slider [    0,  1000]  (10%) — linear
//   [-3000, -1000]  → slider [ 1000,  2000]  (10%) — linear
//   [-1000,     0]  → slider [ 2000,  3000]  (10%) — linear
//   [    0,  2026]  → slider [ 3000, 10000]  (70%) — sqrt

export const MIN_YEAR = -6000;
export const MAX_YEAR = 2026;

export function yearToSlider(year: number): number {
  if (year <= -3000) {
    // [-6000, -3000] → [0, 1000]
    return Math.round(((year + 6000) / 3000) * 1000);
  } else if (year <= -1000) {
    // [-3000, -1000] → [1000, 2000]
    return Math.round(1000 + ((year + 3000) / 2000) * 1000);
  } else if (year <= 0) {
    // [-1000, 0] → [2000, 3000]
    return Math.round(2000 + ((year + 1000) / 1000) * 1000);
  } else {
    // [0, 2026] → [3000, 10000] sqrt scale
    const t = Math.min(year, MAX_YEAR) / MAX_YEAR;
    const s = 1 - Math.sqrt(1 - t);
    return Math.round(3000 + s * 7000);
  }
}

export function sliderToYear(pos: number): number {
  if (pos <= 1000) {
    // [0, 1000] → [-6000, -3000]
    return Math.round(-6000 + (pos / 1000) * 3000);
  } else if (pos <= 2000) {
    // [1000, 2000] → [-3000, -1000]
    return Math.round(-3000 + ((pos - 1000) / 1000) * 2000);
  } else if (pos <= 3000) {
    // [2000, 3000] → [-1000, 0]
    return Math.round(-1000 + ((pos - 2000) / 1000) * 1000);
  } else {
    // [3000, 10000] → [0, 2026] sqrt scale
    const s = (pos - 3000) / 7000;
    const t = 1 - Math.pow(1 - s, 2);
    return Math.round(t * MAX_YEAR);
  }
}

/**
 * Snap to a "nice" year for the piecewise scale (rc-slider onChange, slider units).
 * Resolution varies by segment, so snap granularity scales accordingly.
 */
export function snapYear(sliderPos: number, year: number): number {
  if (year >= 1900) {
    // High-resolution segment: snap to nearest 50 if close enough
    const nearest = Math.round(year / 50) * 50;
    if (Math.abs(sliderPos - yearToSlider(nearest)) <= SNAP_THRESHOLD) {
      return nearest;
    }
    return year;
  }
  if (year >= -1000) {
    // [-1000, 1900): 1 slider unit ≈ 1 year — round to nearest 10
    return Math.round(year / 10) * 10;
  }
  if (year >= -3000) {
    // [-3000, -1000]: 1 slider unit ≈ 2 years — round to nearest 50
    return Math.round(year / 50) * 50;
  }
  // [-6000, -3000]: 1 slider unit ≈ 3 years — round to nearest 100
  return Math.round(year / 100) * 100;
}

/**
 * Snap to a "nice" year for the piecewise scale (onMouseMove, pixel units).
 */
export function snapYearByPixels(year: number, sliderWidthPx: number): number {
  if (year >= 1900) {
    const nearest = Math.round(year / 50) * 50;
    const yearPx = (yearToSlider(year) / SLIDER_MAX) * sliderWidthPx;
    const nearestPx = (yearToSlider(nearest) / SLIDER_MAX) * sliderWidthPx;
    if (Math.abs(yearPx - nearestPx) <= SNAP_PX_THRESHOLD) {
      return nearest;
    }
    return year;
  }
  if (year >= -1000) return Math.round(year / 10) * 10;
  if (year >= -3000) return Math.round(year / 50) * 50;
  return Math.round(year / 100) * 100;
}

/** Marks for the piecewise historical range. */
export function makeHistoricalMarks(): Record<number, number> {
  const years = [
    MIN_YEAR,
    -3000,
    -1000,
    0,
    500,
    1000,
    1500,
    1700,
    1800,
    1900,
    2000,
    MAX_YEAR,
  ];
  return Object.fromEntries(years.map((y) => [yearToSlider(y), y]));
}
