import { describe, expect, it } from 'vitest';
import { yearFromDateStr, yearToDateStr, DATE_STR_REGEX } from './date-utils';

describe('yearFromDateStr', () => {
  it('parses year-only strings', () => {
    expect(yearFromDateStr('1100')).toBe(1100);
    expect(yearFromDateStr('2024')).toBe(2024);
    expect(yearFromDateStr('0800')).toBe(800);
  });

  it('parses year-month strings', () => {
    expect(yearFromDateStr('1984-07')).toBe(1984);
    expect(yearFromDateStr('0044-03')).toBe(44);
  });

  it('parses year-month-day strings', () => {
    expect(yearFromDateStr('2000-12-31')).toBe(2000);
    expect(yearFromDateStr('1066-10-14')).toBe(1066);
  });

  it('handles BCE (negative) dates', () => {
    expect(yearFromDateStr('-0044')).toBe(-44);
    expect(yearFromDateStr('-3000')).toBe(-3000);
    expect(yearFromDateStr('-0044-03-15')).toBe(-44);
  });
});

describe('yearToDateStr', () => {
  it('formats positive years with 4-digit zero-padding', () => {
    expect(yearToDateStr(1100)).toBe('1100');
    expect(yearToDateStr(44)).toBe('0044');
    expect(yearToDateStr(1)).toBe('0001');
    expect(yearToDateStr(2024)).toBe('2024');
  });

  it('formats negative years with leading minus and 4-digit zero-padding', () => {
    expect(yearToDateStr(-44)).toBe('-0044');
    expect(yearToDateStr(-3000)).toBe('-3000');
    expect(yearToDateStr(-1)).toBe('-0001');
  });

  it('formats year 0', () => {
    expect(yearToDateStr(0)).toBe('0000');
  });
});

describe('yearFromDateStr / yearToDateStr round-trip', () => {
  it('round-trips year-only strings', () => {
    for (const year of [1, 44, 800, 1100, 2024]) {
      expect(yearFromDateStr(yearToDateStr(year))).toBe(year);
    }
  });

  it('round-trips BCE year strings', () => {
    for (const year of [-1, -44, -3000, -6000]) {
      expect(yearFromDateStr(yearToDateStr(year))).toBe(year);
    }
  });
});

describe('DATE_STR_REGEX', () => {
  it('accepts valid date strings', () => {
    expect(DATE_STR_REGEX.test('1100')).toBe(true);
    expect(DATE_STR_REGEX.test('1984-07')).toBe(true);
    expect(DATE_STR_REGEX.test('2000-12-31')).toBe(true);
    expect(DATE_STR_REGEX.test('-0044')).toBe(true);
    expect(DATE_STR_REGEX.test('-0044-03-15')).toBe(true);
    expect(DATE_STR_REGEX.test('0')).toBe(true);
  });

  it('rejects invalid strings', () => {
    expect(DATE_STR_REGEX.test('')).toBe(false);
    expect(DATE_STR_REGEX.test('abc')).toBe(false);
    expect(DATE_STR_REGEX.test('12345')).toBe(false); // 5-digit year not allowed
    expect(DATE_STR_REGEX.test('1984-7')).toBe(false); // month must be 2 digits
    expect(DATE_STR_REGEX.test('1984-07-1')).toBe(false); // day must be 2 digits
  });
});
