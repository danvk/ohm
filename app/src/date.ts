export function isDateInRange(
  date: string,
  startDate: string | undefined | null,
  endDate: string | undefined | null,
): boolean {
  if (startDate && date < startDate) {
    return false;
  }
  if (endDate && date >= endDate) {
    return false;
  }
  return true;
}
