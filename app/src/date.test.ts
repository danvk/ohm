// This is an AI port of https://github.com/OpenHistoricalMap/DateFunctions-plpgsql/blob/90d8d0f0daea4c8c5aa62edf440f26e9eb0ab950/tests.sql

import { describe, expect, it } from 'vitest';
import {
  decimalDateToIsoDate,
  howManyDaysInMonth,
  howManyDaysInYear,
  isDateInRange,
  isLeapYear,
  isoDateToDecimalDate,
  isValidMonth,
  isValidMonthDay,
  padDate,
  splitDateString,
  yday,
} from './date';

describe('isDateInRange', () => {
  it('should handle basic ranges', () => {
    expect(isDateInRange('1980', '1981', '1989')).toBe(false);
    expect(isDateInRange('1985', '1981', '1989')).toBe(true);
    expect(isDateInRange('1981', '1981', '1989')).toBe(true);
    expect(isDateInRange('1989', '1981', '1989')).toBe(false);
    expect(isDateInRange('1990', '1981', '1989')).toBe(false);
  });

  it('should handle open-ended ranges', () => {
    expect(isDateInRange('1981', null, '2000')).toBe(true);
    expect(isDateInRange('1981', null, '1982')).toBe(true);
    expect(isDateInRange('1981', null, '1981')).toBe(false);
    expect(isDateInRange('1981', '1980', null)).toBe(true);
    expect(isDateInRange('1981', '1981', null)).toBe(true);
    expect(isDateInRange('1981', '1982', null)).toBe(false);
  });

  it('should handle zero-padded dates', () => {
    expect(isDateInRange('1981', '0802', '905')).toBe(false);
    expect(isDateInRange('802', '0802', '905')).toBe(true);
    expect(isDateInRange('900', '0802', '905')).toBe(true);
    expect(isDateInRange('905', '0802', '905')).toBe(false);
    expect(isDateInRange('0905', '0802', '905')).toBe(false);
  });

  it('should handle months', () => {
    expect(isDateInRange('1984-07-12', '1984-01', '1984-12')).toBe(true);
    expect(isDateInRange('1984-07', '1984-01', '1984-12')).toBe(true);
    expect(isDateInRange('1984-07', '1984-01', '1984-07')).toBe(false);
    expect(isDateInRange('1984-07', '1984-07', '1984-08')).toBe(true);
  });

  it('should handle negative dates', () => {
    expect(isDateInRange('1234', '-123', '1234')).toBe(false);
    expect(isDateInRange('-123', '-123', '1234')).toBe(true);
    expect(isDateInRange('-124', '-123', '1234')).toBe(false);
    expect(isDateInRange('-122', '-123', '1234')).toBe(true);
  });
});

describe('isLeapYear', () => {
  it('handles BCE leap years', () => {
    expect(isLeapYear(-1)).toBe(true); // BCE leap years: -1, -5, ...
    expect(isLeapYear(-4)).toBe(false);
    expect(isLeapYear(1900)).toBe(false); // not on centuries unless also div-by-400
    expect(isLeapYear(-1901)).toBe(false);
    expect(isLeapYear(1684)).toBe(true);
    expect(isLeapYear(-1684)).toBe(false);
    expect(isLeapYear(-2001)).toBe(true); // BCE, but div-by-400 equivalent
  });
});

describe('howManyDaysInYear', () => {
  it('returns 366 for leap years, 365 otherwise', () => {
    expect(howManyDaysInYear(1684)).toBe(366);
    expect(howManyDaysInYear(-1684)).toBe(365);
    expect(howManyDaysInYear(-1685)).toBe(366);
  });
});

describe('howManyDaysInMonth', () => {
  it('handles February in leap and non-leap years', () => {
    expect(howManyDaysInMonth(1684, 2)).toBe(29);
    expect(howManyDaysInMonth(1685, 2)).toBe(28);
    expect(howManyDaysInMonth(-1684, 2)).toBe(28);
    expect(howManyDaysInMonth(-1685, 2)).toBe(29);
  });
});

describe('isValidMonth', () => {
  it('accepts 1-12, rejects others', () => {
    expect(isValidMonth(1)).toBe(true);
    expect(isValidMonth(7)).toBe(true);
    expect(isValidMonth(12)).toBe(true);
    expect(isValidMonth(19)).toBe(false);
    expect(isValidMonth(-2)).toBe(false);
    expect(isValidMonth(0)).toBe(false);
  });
});

describe('isValidMonthDay', () => {
  it('validates Feb 29 only in leap years', () => {
    expect(isValidMonthDay(2000, 2, 29)).toBe(true);
    expect(isValidMonthDay(1999, 2, 29)).toBe(false);
  });

  it('rejects out-of-range days and months', () => {
    expect(isValidMonthDay(-1999, 1, 32)).toBe(false);
    expect(isValidMonthDay(-1999, 1, -2)).toBe(false);
    expect(isValidMonthDay(2999, 1, 32)).toBe(false);
    expect(isValidMonthDay(2999, 13, 1)).toBe(false);
    expect(isValidMonthDay(2999, -1, 1)).toBe(false);
  });
});

describe('splitDateString', () => {
  it('parses positive and negative dates', () => {
    expect(splitDateString('2000-12-31')).toEqual([2000, 12, 31]);
    expect(splitDateString('-12000-02-29')).toEqual([-12000, 2, 29]);
  });
});

describe('yday', () => {
  it('computes day-of-year correctly', () => {
    expect(yday(1900, 1, 1)).toBe(1);
    expect(yday(1900, 12, 31)).toBe(365);
    expect(yday(2000, 12, 31)).toBe(366);
    expect(yday(-1700, 1, 1)).toBe(1);
    expect(yday(-1700, 12, 31)).toBe(365);
    expect(yday(-2001, 12, 31)).toBe(366);
    expect(yday(-2000, 12, 31)).toBe(365);
    expect(yday(-1601, 12, 31)).toBe(366);
    expect(yday(-1600, 12, 31)).toBe(365);
  });
});

describe('padDate', () => {
  it('passes through already-full dates and null/empty', () => {
    expect(padDate('', 'start')).toBe('');
    expect(padDate(null, 'end')).toBeNull();
    expect(padDate('218-02-29', 'start')).toBe('218-02-29');
    expect(padDate('44-03-15', 'start')).toBe('44-03-15');
    expect(padDate('-5000-07-02', 'end')).toBe('-5000-07-02');
  });

  it('returns empty string for malformed input', () => {
    expect(padDate('never')).toBe('');
    expect(padDate('before 100 BC')).toBe('');
    expect(padDate('unknown')).toBe('');
  });

  it('pads year-only inputs', () => {
    expect(padDate('+2000', 'start')).toBe('2000-01-01');
    expect(padDate('2000', 'start')).toBe('2000-01-01');
    expect(padDate('-2000', 'start')).toBe('-2000-01-01');
    expect(padDate('-1000000', 'start')).toBe('-1000000-01-01');
    expect(padDate('+2000', 'end')).toBe('2000-12-31');
    expect(padDate('2000', 'end')).toBe('2000-12-31');
    expect(padDate('-2000', 'end')).toBe('-2000-12-31');
    expect(padDate('-1000000', 'end')).toBe('-1000000-12-31');
  });

  it('pads year-month inputs', () => {
    expect(padDate('+44-03')).toBe('44-03-01');
    expect(padDate('-44-03')).toBe('-44-03-01');
    expect(padDate('+2000-07')).toBe('2000-07-01');
    expect(padDate('-2000-07')).toBe('-2000-07-01');
    expect(padDate('+2000-02', 'end')).toBe('2000-02-29');
    expect(padDate('-2001-02', 'end')).toBe('-2001-02-29');
    expect(padDate('+19900-02', 'end')).toBe('19900-02-28');
    expect(padDate('-19900-02', 'end')).toBe('-19900-02-28');
  });
});

describe('isoDateToDecimalDate', () => {
  it('converts dates around the BCE/CE boundary', () => {
    expect(isoDateToDecimalDate('-0002-01-01')).toBe(-1.99863);
    expect(isoDateToDecimalDate('-0002-07-02')).toBe(-1.5);
    expect(isoDateToDecimalDate('-0002-12-31')).toBe(-1.00137);
    expect(isoDateToDecimalDate('-0001-01-01')).toBe(-0.99863);
    expect(isoDateToDecimalDate('-0001-07-02')).toBe(-0.5);
    expect(isoDateToDecimalDate('-0001-12-31')).toBe(-0.00137);
    expect(isoDateToDecimalDate('0000-01-01')).toBe(0.00137); // 1 BCE, leap year
    expect(isoDateToDecimalDate('0000-07-02')).toBe(0.50137);
    expect(isoDateToDecimalDate('0000-12-31')).toBe(0.99863);
    expect(isoDateToDecimalDate('0001-01-01')).toBe(1.00137);
    expect(isoDateToDecimalDate('0001-07-02')).toBe(1.5);
    expect(isoDateToDecimalDate('0001-12-31')).toBe(1.99863);
    expect(isoDateToDecimalDate('0002-01-01')).toBe(2.00137);
    expect(isoDateToDecimalDate('0002-07-02')).toBe(2.5);
    expect(isoDateToDecimalDate('0002-12-31')).toBe(2.99863);
  });

  it('handles invalid input', () => {
    expect(isoDateToDecimalDate('1917-04-31', false)).toBeNull();
    expect(isoDateToDecimalDate('1917-04-31', true)).toBe(1917.24795);
    expect(isoDateToDecimalDate('1917-13-32', true)).toBe(1917);
  });

  it('throws on invalid input by default', () => {
    expect(() => isoDateToDecimalDate('1917-04-31')).toThrow();
  });

  it('handles zero-padded dates', () => {
    expect(padDate('802', 'start')).toMatchInlineSnapshot(`"802-01-01"`);
    expect(padDate('0802', 'start')).toMatchInlineSnapshot(`"0802-01-01"`);
    expect(isoDateToDecimalDate('0802-01-01')).toMatchInlineSnapshot(
      `802.00137`,
    );
    expect(isoDateToDecimalDate('802-01-01')).toMatchInlineSnapshot(
      `802.00137`,
    );
  });
});

describe('decimalDateToIsoDate', () => {
  it('converts decimals around the BCE/CE boundary', () => {
    expect(decimalDateToIsoDate(-0.998633)).toBe('-0001-01-01');
    expect(decimalDateToIsoDate(-0.5)).toBe('-0001-07-02');
    expect(decimalDateToIsoDate(-0.001366)).toBe('-0001-12-31');
    expect(decimalDateToIsoDate(0.001367)).toBe('0000-01-01');
    expect(decimalDateToIsoDate(0.5)).toBe('0000-07-01'); // 1 BCE, leap year
    expect(decimalDateToIsoDate(0.998634)).toBe('0000-12-31');
    expect(decimalDateToIsoDate(1.001369)).toBe('0001-01-01');
    expect(decimalDateToIsoDate(1.5)).toBe('0001-07-02');
    expect(decimalDateToIsoDate(1.998631)).toBe('0001-12-31');
    expect(decimalDateToIsoDate(2.001369)).toBe('0002-01-01');
    expect(decimalDateToIsoDate(2.5)).toBe('0002-07-02');
    expect(decimalDateToIsoDate(2.998631)).toBe('0002-12-31');
  });
});

describe('isoDateToDecimalDate / decimalDateToIsoDate round-trip', () => {
  it('round-trips positive dates', () => {
    expect(decimalDateToIsoDate(isoDateToDecimalDate('2000-12-01')!)).toBe(
      '2000-12-01',
    );
    expect(decimalDateToIsoDate(isoDateToDecimalDate('2000-12-31')!)).toBe(
      '2000-12-31',
    );
    expect(decimalDateToIsoDate(isoDateToDecimalDate('2000-02-29')!)).toBe(
      '2000-02-29',
    );
    expect(decimalDateToIsoDate(isoDateToDecimalDate('1999-12-01')!)).toBe(
      '1999-12-01',
    );
    expect(decimalDateToIsoDate(isoDateToDecimalDate('1999-12-31')!)).toBe(
      '1999-12-31',
    );
    expect(decimalDateToIsoDate(isoDateToDecimalDate('10191-06-30')!)).toBe(
      '10191-06-30',
    );
    expect(decimalDateToIsoDate(isoDateToDecimalDate('10191-07-31')!)).toBe(
      '10191-07-31',
    );
  });

  it('round-trips negative dates (with expected ISO 8601 offset)', () => {
    expect(decimalDateToIsoDate(isoDateToDecimalDate('-1999-06-15')!)).toBe(
      '-1999-06-15',
    );
    expect(decimalDateToIsoDate(isoDateToDecimalDate('-10191-06-30')!)).toBe(
      '-10191-06-30',
    );
    expect(decimalDateToIsoDate(isoDateToDecimalDate('-10191-07-31')!)).toBe(
      '-10191-07-31',
    );
  });
});
