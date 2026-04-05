/** Extract the numeric year from a date string (YYYY, YYYY-MM, or YYYY-MM-DD). */
export function yearFromDateStr(dateStr: string): number {
  // TODO: use dates.ts for this
  if (dateStr.startsWith('-')) {
    return -yearFromDateStr(dateStr.slice(1));
  }
  return parseInt(dateStr.split('-')[0]);
}
