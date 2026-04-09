// This is an AI port of https://github.com/OpenHistoricalMap/DateFunctions-plpgsql/blob/90d8d0f0daea4c8c5aa62edf440f26e9eb0ab950/datefunctions.sql

function toDecimal(d: string) {
  const padded = padDate(d, 'start');
  return padded ? isoDateToDecimalDate(padded, false) : null;
}

export function isDateInRange(
  date: string,
  startDate: string | undefined | null,
  endDate: string | undefined | null,
): boolean {
  const decDate = toDecimal(date);
  if (decDate === null) return true;

  if (startDate) {
    const decStart = toDecimal(startDate);
    if (decStart !== null && decDate < decStart) return false;
  }
  if (endDate) {
    const decEnd = toDecimal(endDate);
    if (decEnd !== null && decDate >= decEnd) return false;
  }
  return true;
}

export function isLeapYear(year: number): boolean {
  let y = year;
  if (y <= 0) y += 1;
  return y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
}

export function howManyDaysInYear(year: number): number {
  return isLeapYear(year) ? 366 : 365;
}

export function howManyDaysInMonth(year: number, month: number): number {
  if ([1, 3, 5, 7, 8, 10, 12].includes(month)) return 31;
  if ([4, 6, 9, 11].includes(month)) return 30;
  if (month === 2) return isLeapYear(year) ? 29 : 28;
  return 0;
}

export function isValidMonth(month: number): boolean {
  return month >= 1 && month <= 12;
}

export function isValidMonthDay(
  year: number,
  month: number,
  day: number,
): boolean {
  return (
    isValidMonth(month) && day > 0 && day <= howManyDaysInMonth(year, month)
  );
}

// Return the 1-based day-of-year (yday) for the given date.
export function yday(year: number, month: number, day: number): number {
  if (!isValidMonthDay(year, month, day)) {
    throw new Error(`Not a valid date ${year}, ${month}, ${day}`);
  }
  let dayspassed = 0;
  for (let m = 1; m < month; m++) {
    dayspassed += howManyDaysInMonth(year, m);
  }
  return dayspassed + day;
}

// Split an ISO-8601-shaped date string into [year, month, day].
export function splitDateString(
  datestring: string,
): [number, number, number] | null {
  const match = datestring.match(/^(-?\+?\d+)-(\d\d)-(\d\d)$/);
  if (!match) return null;
  return [
    parseInt(match[1], 10),
    parseInt(match[2], 10),
    parseInt(match[3], 10),
  ];
}

// Convert an ISO-8601-shaped date string to a decimal year.
// tryToFixInvalid: undefined/null = throw on invalid, false = return null, true = best-effort fix
export function isoDateToDecimalDate(
  datestring: string,
  tryToFixInvalid?: boolean | null,
): number | null {
  const parts = splitDateString(datestring);
  if (!parts) {
    if (tryToFixInvalid == null)
      throw new Error(`Cannot parse date: ${datestring}`);
    return null;
  }

  let [yearint, monthint, dayint] = parts;

  if (!isValidMonthDay(yearint, monthint, dayint)) {
    if (tryToFixInvalid == null) {
      throw new Error(`Not a valid date ${yearint}, ${monthint}, ${dayint}`);
    } else if (!tryToFixInvalid) {
      return null;
    } else {
      if (!isValidMonth(monthint)) return yearint;
      dayint = 1;
    }
  }

  // ISO 8601 shift: year 0 = 1 BCE, year -1 = 2 BCE, etc.
  if (yearint <= 0) yearint -= 1;

  const daynumber = yday(yearint, monthint, dayint) - 0.5;
  const daysinyear = howManyDaysInYear(yearint);
  const decibit = daynumber / daysinyear;

  let decimaldate: number;
  if (yearint < 0) {
    decimaldate = 1 + 1 + yearint - (1 - decibit);
  } else {
    decimaldate = yearint + decibit;
  }

  return Math.round(decimaldate * 100000) / 100000;
}

// Convert a decimal year back to an ISO-8601-shaped date string.
export function decimalDateToIsoDate(decimaldate: number): string {
  const truedecdate = decimaldate - 1;
  const ispositive = truedecdate > 0;

  let yearint: number;
  if (ispositive) {
    yearint = Math.floor(truedecdate) + 1;
  } else {
    yearint = -Math.abs(Math.floor(truedecdate));
  }

  const dty = howManyDaysInYear(yearint);
  const fracpart = Math.abs(truedecdate) % 1;
  let targetday: number;
  if (ispositive) {
    targetday = Math.ceil(dty * fracpart);
  } else {
    targetday = dty - Math.floor(dty * fracpart);
  }

  let dayspassed = 0;
  let monthint = 1;
  for (let mi = 1; mi <= 12; mi++) {
    const dtm = howManyDaysInMonth(yearint, mi);
    if (dayspassed + dtm < targetday) {
      dayspassed += dtm;
    } else {
      monthint = mi;
      break;
    }
  }
  const dayint = targetday - dayspassed;

  const monthstring = String(monthint).padStart(2, '0');
  const daystring = String(dayint).padStart(2, '0');
  let yearstring: string;
  if (yearint > 0) {
    yearstring = String(yearint).padStart(4, '0');
  } else if (yearint === -1) {
    // ISO 8601: year 0 = 1 BCE, no minus sign
    yearstring = String(0).padStart(4, '0');
  } else {
    // ISO 8601: shift by 1 and add minus
    yearstring = '-' + String(Math.abs(yearint + 1)).padStart(4, '0');
  }

  return `${yearstring}-${monthstring}-${daystring}`;
}

// Pad a truncated date (year-only or year-month) to a full year-month-day string.
export function padDate(
  datestring: string | null,
  startend: 'start' | 'end' = 'start',
): string | null {
  if (datestring == null) return null;

  // trim leading +
  datestring = datestring.replace(/^\+/, '');

  if (!datestring) return datestring;

  // already a full date
  if (/^-?\d+-\d\d-\d\d$/.test(datestring)) return datestring;

  // year only
  if (/^-?\d+$/.test(datestring)) {
    return startend === 'start' ? `${datestring}-01-01` : `${datestring}-12-31`;
  }

  // year-month
  if (/^-?\d+-\d\d$/.test(datestring)) {
    if (startend === 'start') return `${datestring}-01`;
    const yearstring = datestring.slice(0, datestring.length - 3);
    const monthstring = datestring.slice(datestring.length - 2);
    const lastday = String(
      howManyDaysInMonth(parseInt(yearstring, 10), parseInt(monthstring, 10)),
    ).padStart(2, '0');
    return `${datestring}-${lastday}`;
  }

  return '';
}
