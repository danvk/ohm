/** Extract the numeric year from a date string (YYYY, YYYY-MM, or YYYY-MM-DD). */
export function yearFromDateStr(dateStr: string): number {
  // TODO: use dates.ts for this
  if (dateStr.startsWith('-')) {
    return -yearFromDateStr(dateStr.slice(1));
  }
  return parseInt(dateStr.split('-')[0]);
}

/** Extract the month (1-12) from a date string, or 0 if the string is year-only. */
export function monthFromDateStr(dateStr: string): number {
  const s = dateStr.replace(/^-/, '');
  const parts = s.split('-');
  return parts.length >= 2 ? parseInt(parts[1]) : 0;
}

/** Regex for a valid date string: YYYY, YYYY-MM, or YYYY-MM-DD (with optional leading minus). */
export const DATE_STR_REGEX = /^-?\d{1,4}(-\d{2}(-\d{2})?)?$/;

/** Format a numeric year as a zero-padded 4-digit string. */
export function yearToDateStr(year: number): string {
  if (year < 0) return '-' + String(-year).padStart(4, '0');
  return String(year).padStart(4, '0');
}

/**
 * Convert a date string to a total-months integer (year * 12 + (month - 1)).
 * Year-only strings map to the first month of that year.
 */
export function dateStrToMonths(dateStr: string): number {
  const year = yearFromDateStr(dateStr);
  const month = monthFromDateStr(dateStr);
  return year * 12 + (month > 0 ? month - 1 : 0);
}

/** Convert a total-months integer back to a "YYYY-MM" date string. */
export function monthsToDateStr(totalMonths: number): string {
  const year = Math.floor(totalMonths / 12);
  const month = (((totalMonths % 12) + 12) % 12) + 1;
  return `${yearToDateStr(year)}-${String(month).padStart(2, '0')}`;
}
