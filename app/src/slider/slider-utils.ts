// Square-root scale: gives more resolution near maxYear without being as extreme
// as a logarithmic scale. sliderPos = sqrt((year - minYear) / (maxYear - minYear)).
// The slider's internal range is 0..SLIDER_MAX (integers).
export const SLIDER_MAX = 10000;

// Snap threshold in slider units (0..SLIDER_MAX) for years ≥ 1900.
export const SNAP_THRESHOLD = 60;
// Equivalent pixel threshold for onMouseMove (≈ SNAP_THRESHOLD/SLIDER_MAX * typical slider width).
export const SNAP_PX_THRESHOLD = 6;

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

/** Build rc-slider marks for the full historical range, filtered to [minYear, maxYear]. */
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
