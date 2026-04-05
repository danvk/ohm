import { describe, expect, it } from 'vitest';
import { isDateInRange } from './date';

describe('isDateInRange', () => {
  it('should handle basic ranges', () => {
    expect(isDateInRange('1980', '1981', '1989')).toBe(false);
    expect(isDateInRange('1985', '1981', '1989')).toBe(true);
    expect(isDateInRange('1981', '1981', '1989')).toBe(true);
    expect(isDateInRange('1989', '1981', '1989')).toBe(false);
    expect(isDateInRange('1990', '1981', '1989')).toBe(false);
  });
});
