/** Extract the numeric year from a date string (YYYY, YYYY-MM, or YYYY-MM-DD). */
export function yearFromDateStr(dateStr: string): number {
  // TODO: use dates.ts for this
  if (dateStr.startsWith('-')) {
    return -yearFromDateStr(dateStr.slice(1));
  }
  return parseInt(dateStr.split('-')[0]);
}

/** Regex for a valid date string: YYYY, YYYY-MM, or YYYY-MM-DD (with optional leading minus). */
export const DATE_STR_REGEX = /^-?\d{1,4}(-\d{2}(-\d{2})?)?$/;

/** Format a numeric year as a zero-padded 4-digit string. */
export function yearToDateStr(year: number): string {
  if (year < 0) return '-' + String(-year).padStart(4, '0');
  return String(year).padStart(4, '0');
}
