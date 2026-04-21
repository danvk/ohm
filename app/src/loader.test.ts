import { describe, expect, it } from 'vitest';
import { computeEffectiveDates } from './loader';
import type { Relation } from './ohm-data';
import {
  isoDateToDecimalDate,
  toDecimalEarliest,
  toDecimalExclusiveEnd,
  toDecimalLatest,
} from './date';

function makeRelation(
  id: string,
  tags: Record<string, string>,
  chronology?: Relation['chronology'],
): Relation {
  return { id, tags, ways: [], nodes: [], chronology };
}

describe('computeEffectiveDates', () => {
  it('sets no dates when tags are absent', () => {
    const r = makeRelation('1', {});
    computeEffectiveDates([r]);
    expect(r.startDecDate).toBeUndefined();
    expect(r.endDecDate).toBeUndefined();
  });

  it('sets startDecDate from start_date (earliest/Jan 1 for year-only)', () => {
    const r = makeRelation('1', { start_date: '1880' });
    computeEffectiveDates([r]);
    expect(r.startDecDate).toBe(toDecimalEarliest('1880'));
    expect(r.startDecDate).toBe(isoDateToDecimalDate('1880-01-01'));
    expect(r.endDecDate).toBeUndefined();
  });

  it('sets endDecDate from end_date (exclusive end, so Dec 31 is included)', () => {
    const r = makeRelation('1', { end_date: '1885' });
    computeEffectiveDates([r]);
    expect(r.endDecDate).toBe(toDecimalExclusiveEnd('1885'));
    expect(r.endDecDate).toBe(isoDateToDecimalDate('1886-01-01'));
    expect(r.startDecDate).toBeUndefined();
  });

  it('sets both dates from both tags', () => {
    const r = makeRelation('1', { start_date: '1880', end_date: '1885' });
    computeEffectiveDates([r]);
    expect(r.startDecDate).toBe(toDecimalEarliest('1880'));
    expect(r.endDecDate).toBe(toDecimalExclusiveEnd('1885'));
  });

  it('leaves dates undefined for unparseable date strings', () => {
    const r = makeRelation('1', { start_date: 'unknown', end_date: 'never' });
    computeEffectiveDates([r]);
    expect(r.startDecDate).toBeUndefined();
    expect(r.endDecDate).toBeUndefined();
  });

  it('does not crash when chronology is absent', () => {
    const r = makeRelation('1', { start_date: '1880', end_date: '1885' });
    expect(() => computeEffectiveDates([r])).not.toThrow();
  });

  describe('chronology-informed adjustment', () => {
    it('splits shared date at midpoint when end_date matches next start_date', () => {
      // A ends in 1885, B starts in 1885, A→B in chronology
      const a = makeRelation('1', { start_date: '1880', end_date: '1885' }, [
        { id: 10, name: 'Empire', next: 2 },
      ]);
      const b = makeRelation('2', { start_date: '1885', end_date: '1890' }, [
        { id: 10, name: 'Empire', prev: 1 },
      ]);
      computeEffectiveDates([a, b]);

      const earliest = toDecimalEarliest('1885')!;
      const latest = toDecimalLatest('1885')!;
      const midpoint = (earliest + latest) / 2;

      expect(a.endDecDate).toBe(midpoint);
      expect(b.startDecDate).toBe(midpoint);
      // A's startDecDate and B's endDecDate are unaffected
      expect(a.startDecDate).toBe(toDecimalEarliest('1880'));
      expect(b.endDecDate).toBe(toDecimalExclusiveEnd('1890'));
    });

    it('midpoint falls in the middle of the shared year', () => {
      const a = makeRelation('1', { end_date: '1885' }, [
        { id: 10, name: 'C', next: 2 },
      ]);
      const b = makeRelation('2', { start_date: '1885' });
      computeEffectiveDates([a, b]);

      // Midpoint should be approximately mid-1885 (≈1885.5)
      expect(a.endDecDate).toBeGreaterThan(isoDateToDecimalDate('1885-01-01')!);
      expect(a.endDecDate).toBeLessThan(isoDateToDecimalDate('1885-12-31')!);
    });

    it('does not adjust when dates differ', () => {
      const a = makeRelation('1', { end_date: '1885' }, [
        { id: 10, name: 'C', next: 2 },
      ]);
      const b = makeRelation('2', { start_date: '1886' });
      computeEffectiveDates([a, b]);

      expect(a.endDecDate).toBe(toDecimalExclusiveEnd('1885'));
      expect(b.startDecDate).toBe(toDecimalEarliest('1886'));
    });

    it('does not adjust when next relation is not found', () => {
      const a = makeRelation('1', { end_date: '1885' }, [
        { id: 10, name: 'C', next: 999 },
      ]);
      computeEffectiveDates([a]);
      expect(a.endDecDate).toBe(toDecimalExclusiveEnd('1885'));
    });

    it('handles month-precision shared date', () => {
      const a = makeRelation('1', { end_date: '1885-07' }, [
        { id: 10, name: 'C', next: 2 },
      ]);
      const b = makeRelation('2', { start_date: '1885-07' });
      computeEffectiveDates([a, b]);

      const earliest = toDecimalEarliest('1885-07')!;
      const latest = toDecimalLatest('1885-07')!;
      const midpoint = (earliest + latest) / 2;

      expect(a.endDecDate).toBe(midpoint);
      expect(b.startDecDate).toBe(midpoint);
    });
  });
});
