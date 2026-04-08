// The slider's internal range is 0..SLIDER_MAX (integers).
export const SLIDER_MAX = 10000;

// Snap threshold in slider units (0..SLIDER_MAX) for years ≥ 1900.
export const SNAP_THRESHOLD = 60;
// Equivalent pixel threshold for onMouseMove (≈ SNAP_THRESHOLD/SLIDER_MAX * typical slider width).
export const SNAP_PX_THRESHOLD = 6;

// ── General sqrt scale (variable range, used by TimeSlider) ──────────────────

export function yearToSlider(
  year: number,
  minYear: number,
  maxYear: number,
): number {
  const t = (year - minYear) / (maxYear - minYear);
  return Math.round((1 - Math.sqrt(1 - t)) * SLIDER_MAX);
}

export function sliderToYear(
  pos: number,
  minYear: number,
  maxYear: number,
): number {
  const s = pos / SLIDER_MAX;
  const t = 1 - Math.pow(1 - s, 2);
  return Math.round(minYear + t * (maxYear - minYear));
}

// ── Piecewise scale (fixed historical range, used by SqrtTimeSlider + TimeRange) ──
//
// Divides SLIDER_MAX into four segments:
//   [-6000, -3000]  → slider [    0,  1000]  (10%) — linear
//   [-3000, -1000]  → slider [ 1000,  2000]  (10%) — linear
//   [-1000,     0]  → slider [ 2000,  3000]  (10%) — linear
//   [    0,  2026]  → slider [ 3000, 10000]  (70%) — sqrt

export const PIECEWISE_MAX_YEAR = 2026;

export function yearToSliderPiecewise(year: number): number {
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
    const t = Math.min(year, PIECEWISE_MAX_YEAR) / PIECEWISE_MAX_YEAR;
    const s = 1 - Math.sqrt(1 - t);
    return Math.round(3000 + s * 7000);
  }
}

export function sliderToYearPiecewise(pos: number): number {
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
    return Math.round(t * PIECEWISE_MAX_YEAR);
  }
}

/**
 * Snap to a "nice" year for the piecewise scale (rc-slider onChange, slider units).
 * Resolution varies by segment, so snap granularity scales accordingly.
 */
export function snapYearPiecewise(sliderPos: number, year: number): number {
  if (year >= 1900) {
    // High-resolution segment: snap to nearest 50 if close enough
    const nearest = Math.round(year / 50) * 50;
    if (
      Math.abs(sliderPos - yearToSliderPiecewise(nearest)) <= SNAP_THRESHOLD
    ) {
      return nearest;
    }
    return year;
  }
  if (year >= 0) {
    return Math.round(year / 10) * 10;
  }
  if (year >= -1000) {
    // [-1000, 0]: 1 slider unit ≈ 1 year — round to nearest 10
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
export function snapYearByPixelsPiecewise(
  year: number,
  sliderWidthPx: number,
): number {
  if (year >= 1900) {
    const nearest = Math.round(year / 50) * 50;
    const yearPx = (yearToSliderPiecewise(year) / SLIDER_MAX) * sliderWidthPx;
    const nearestPx =
      (yearToSliderPiecewise(nearest) / SLIDER_MAX) * sliderWidthPx;
    if (Math.abs(yearPx - nearestPx) <= SNAP_PX_THRESHOLD) {
      return nearest;
    }
    return year;
  }
  if (year >= 0) return Math.round(year / 10) * 10;
  if (year >= -1000) return Math.round(year / 10) * 10;
  if (year >= -3000) return Math.round(year / 50) * 50;
  return Math.round(year / 100) * 100;
}

/** Marks for the piecewise historical range. */
export function makeHistoricalMarksPiecewise(): Record<number, number> {
  const years = [
    -6000,
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
    PIECEWISE_MAX_YEAR,
  ];
  return Object.fromEntries(years.map((y) => [yearToSliderPiecewise(y), y]));
}

/** Build rc-slider marks for a variable range (used by TimeSlider). */
export function makeHistoricalMarks(
  minYear: number,
  maxYear: number,
): Record<number, number> {
  const years = [
    minYear,
    -4000,
    -3000,
    -2000,
    -1000,
    0,
    500,
    1000,
    1500,
    1800,
    1900,
    2000,
    maxYear,
  ].filter((y) => y >= minYear && y <= maxYear);
  return Object.fromEntries(
    years.map((y) => [yearToSlider(y, minYear, maxYear), y]),
  );
}

/**
 * Snap year to a "nice" value (for rc-slider onChange, which gives slider units):
 *  - year < 1900: always round to nearest multiple of 10
 *  - year ≥ 1900: snap to nearest multiple of 50 if within SNAP_THRESHOLD slider units
 */
export function snapYear(
  sliderPos: number,
  year: number,
  minYear: number,
  maxYear: number,
): number {
  const nearest = Math.round(year / 50) * 50;
  const nearestSliderPos = yearToSlider(nearest, minYear, maxYear);
  if (Math.abs(sliderPos - nearestSliderPos) <= SNAP_THRESHOLD) {
    return nearest;
  }
  if (year < 1900) {
    return Math.round(year / 10) * 10;
  }
  return year;
}

/**
 * Snap year to a "nice" value (for onMouseMove, which works in pixels):
 *  - year < 1900: always round to nearest multiple of 10
 *  - year ≥ 1900: snap to nearest multiple of 50 if within SNAP_PX_THRESHOLD pixels
 */
export function snapYearByPixels(
  year: number,
  sliderWidthPx: number,
  minYear: number,
  maxYear: number,
): number {
  if (year < 1900) {
    return Math.round(year / 10) * 10;
  }
  const nearest = Math.round(year / 50) * 50;
  const yearPx =
    (yearToSlider(year, minYear, maxYear) / SLIDER_MAX) * sliderWidthPx;
  const nearestPx =
    (yearToSlider(nearest, minYear, maxYear) / SLIDER_MAX) * sliderWidthPx;
  if (Math.abs(yearPx - nearestPx) <= SNAP_PX_THRESHOLD) {
    return nearest;
  }
  return year;
}
