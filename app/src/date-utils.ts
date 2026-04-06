/** Extract the numeric year from a date string (YYYY, YYYY-MM, or YYYY-MM-DD). */
export function yearFromDateStr(dateStr: string): number {
  return parseInt(dateStr.slice(0, 4), 10);
}
