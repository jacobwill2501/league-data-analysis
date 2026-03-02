import { describe, it, expect } from 'vitest'
import {
  SLOPE_TIER_ORDER,
  LEARNING_TIER_ORDER,
  MASTERY_TIER_ORDER,
  GROWTH_TYPE_ORDER,
  GAMES_TO_50_STATUS_ORDER,
} from '../tiers'
import { makeTierSortingFn } from '../format'

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Minimal Row stub compatible with makeTierSortingFn */
function makeRow(value: string | null): { getValue: (id: string) => string | null } {
  return { getValue: (_id: string) => value }
}

function sortByTier(values: (string | null)[], orderMap: Record<string, number>): (string | null)[] {
  const fn = makeTierSortingFn<Record<string, unknown>>(orderMap)
  return [...values].sort((a, b) =>
    fn(makeRow(a) as never, makeRow(b) as never, 'col')
  )
}

// ── Order map completeness ────────────────────────────────────────────────────

describe('SLOPE_TIER_ORDER', () => {
  it('contains all expected tiers', () => {
    expect(SLOPE_TIER_ORDER).toHaveProperty('Easy Pickup')
    expect(SLOPE_TIER_ORDER).toHaveProperty('Mild Pickup')
    expect(SLOPE_TIER_ORDER).toHaveProperty('Hard Pickup')
    expect(SLOPE_TIER_ORDER).toHaveProperty('Very Hard Pickup')
  })

  it('has correct ascending rank order', () => {
    expect(SLOPE_TIER_ORDER['Easy Pickup']).toBeLessThan(SLOPE_TIER_ORDER['Mild Pickup'])
    expect(SLOPE_TIER_ORDER['Mild Pickup']).toBeLessThan(SLOPE_TIER_ORDER['Hard Pickup'])
    expect(SLOPE_TIER_ORDER['Hard Pickup']).toBeLessThan(SLOPE_TIER_ORDER['Very Hard Pickup'])
  })
})

describe('LEARNING_TIER_ORDER', () => {
  it('contains all expected tiers', () => {
    expect(LEARNING_TIER_ORDER).toHaveProperty('Safe Blind Pick')
    expect(LEARNING_TIER_ORDER).toHaveProperty('Low Risk')
    expect(LEARNING_TIER_ORDER).toHaveProperty('Moderate')
    expect(LEARNING_TIER_ORDER).toHaveProperty('High Risk')
    expect(LEARNING_TIER_ORDER).toHaveProperty('Avoid')
  })

  it('has correct ascending rank order', () => {
    expect(LEARNING_TIER_ORDER['Safe Blind Pick']).toBeLessThan(LEARNING_TIER_ORDER['Low Risk'])
    expect(LEARNING_TIER_ORDER['Low Risk']).toBeLessThan(LEARNING_TIER_ORDER['Moderate'])
    expect(LEARNING_TIER_ORDER['Moderate']).toBeLessThan(LEARNING_TIER_ORDER['High Risk'])
    expect(LEARNING_TIER_ORDER['High Risk']).toBeLessThan(LEARNING_TIER_ORDER['Avoid'])
  })
})

describe('MASTERY_TIER_ORDER', () => {
  it('contains all expected tiers', () => {
    expect(MASTERY_TIER_ORDER).toHaveProperty('Exceptional Payoff')
    expect(MASTERY_TIER_ORDER).toHaveProperty('High Payoff')
    expect(MASTERY_TIER_ORDER).toHaveProperty('Moderate Payoff')
    expect(MASTERY_TIER_ORDER).toHaveProperty('Low Payoff')
    expect(MASTERY_TIER_ORDER).toHaveProperty('Not Worth Mastering')
  })

  it('has correct ascending rank order', () => {
    expect(MASTERY_TIER_ORDER['Exceptional Payoff']).toBeLessThan(MASTERY_TIER_ORDER['High Payoff'])
    expect(MASTERY_TIER_ORDER['High Payoff']).toBeLessThan(MASTERY_TIER_ORDER['Moderate Payoff'])
    expect(MASTERY_TIER_ORDER['Moderate Payoff']).toBeLessThan(MASTERY_TIER_ORDER['Low Payoff'])
    expect(MASTERY_TIER_ORDER['Low Payoff']).toBeLessThan(MASTERY_TIER_ORDER['Not Worth Mastering'])
  })
})

describe('GROWTH_TYPE_ORDER', () => {
  it('contains all expected types', () => {
    expect(GROWTH_TYPE_ORDER).toHaveProperty('Continual')
    expect(GROWTH_TYPE_ORDER).toHaveProperty('Gradual')
    expect(GROWTH_TYPE_ORDER).toHaveProperty('Plateau')
  })

  it('has correct ascending rank order', () => {
    expect(GROWTH_TYPE_ORDER['Continual']).toBeLessThan(GROWTH_TYPE_ORDER['Gradual'])
    expect(GROWTH_TYPE_ORDER['Gradual']).toBeLessThan(GROWTH_TYPE_ORDER['Plateau'])
  })
})

describe('GAMES_TO_50_STATUS_ORDER', () => {
  it('contains all expected statuses', () => {
    expect(GAMES_TO_50_STATUS_ORDER).toHaveProperty('always above 50%')
    expect(GAMES_TO_50_STATUS_ORDER).toHaveProperty('crosses 50%')
    expect(GAMES_TO_50_STATUS_ORDER).toHaveProperty('never reaches 50%')
    expect(GAMES_TO_50_STATUS_ORDER).toHaveProperty('low data')
  })

  it('has correct ascending rank order', () => {
    expect(GAMES_TO_50_STATUS_ORDER['always above 50%']).toBeLessThan(GAMES_TO_50_STATUS_ORDER['crosses 50%'])
    expect(GAMES_TO_50_STATUS_ORDER['crosses 50%']).toBeLessThan(GAMES_TO_50_STATUS_ORDER['never reaches 50%'])
    expect(GAMES_TO_50_STATUS_ORDER['never reaches 50%']).toBeLessThan(GAMES_TO_50_STATUS_ORDER['low data'])
  })
})

// ── makeTierSortingFn behavior ────────────────────────────────────────────────

describe('makeTierSortingFn', () => {
  it('places Easy Pickup before Hard Pickup (not alphabetically after)', () => {
    const fn = makeTierSortingFn<Record<string, unknown>>(SLOPE_TIER_ORDER)
    const result = fn(makeRow('Easy Pickup') as never, makeRow('Hard Pickup') as never, 'col')
    expect(result).toBeLessThan(0)
  })

  it('places Safe Blind Pick before Avoid (not alphabetically after)', () => {
    const fn = makeTierSortingFn<Record<string, unknown>>(LEARNING_TIER_ORDER)
    const result = fn(makeRow('Safe Blind Pick') as never, makeRow('Avoid') as never, 'col')
    expect(result).toBeLessThan(0)
  })

  it('places Moderate Payoff before Low Payoff (not alphabetically before)', () => {
    const fn = makeTierSortingFn<Record<string, unknown>>(MASTERY_TIER_ORDER)
    const result = fn(makeRow('Moderate Payoff') as never, makeRow('Low Payoff') as never, 'col')
    expect(result).toBeLessThan(0)
  })

  it('places "never reaches 50%" before "low data"', () => {
    const fn = makeTierSortingFn<Record<string, unknown>>(GAMES_TO_50_STATUS_ORDER)
    const result = fn(makeRow('never reaches 50%') as never, makeRow('low data') as never, 'col')
    expect(result).toBeLessThan(0)
  })

  it('sorts nulls last when compared against a real value', () => {
    const fn = makeTierSortingFn<Record<string, unknown>>(SLOPE_TIER_ORDER)
    const nullLast = fn(makeRow(null) as never, makeRow('Easy Pickup') as never, 'col')
    expect(nullLast).toBeGreaterThan(0)
  })

  it('sorts nulls last when real value compared against null', () => {
    const fn = makeTierSortingFn<Record<string, unknown>>(SLOPE_TIER_ORDER)
    const realFirst = fn(makeRow('Easy Pickup') as never, makeRow(null) as never, 'col')
    expect(realFirst).toBeLessThan(0)
  })

  it('returns 0 for two nulls', () => {
    const fn = makeTierSortingFn<Record<string, unknown>>(SLOPE_TIER_ORDER)
    const result = fn(makeRow(null) as never, makeRow(null) as never, 'col')
    expect(result).toBe(0)
  })

  it('produces correct full ascending order for slope tiers', () => {
    const input = ['Very Hard Pickup', 'Easy Pickup', 'Hard Pickup', 'Mild Pickup']
    const sorted = sortByTier(input, SLOPE_TIER_ORDER)
    expect(sorted).toEqual(['Easy Pickup', 'Mild Pickup', 'Hard Pickup', 'Very Hard Pickup'])
  })

  it('produces correct full ascending order for learning tiers', () => {
    const input = ['Avoid', 'Moderate', 'Safe Blind Pick', 'High Risk', 'Low Risk']
    const sorted = sortByTier(input, LEARNING_TIER_ORDER)
    expect(sorted).toEqual(['Safe Blind Pick', 'Low Risk', 'Moderate', 'High Risk', 'Avoid'])
  })

  it('produces correct full ascending order for mastery tiers', () => {
    const input = ['Not Worth Mastering', 'High Payoff', 'Moderate Payoff', 'Exceptional Payoff', 'Low Payoff']
    const sorted = sortByTier(input, MASTERY_TIER_ORDER)
    expect(sorted).toEqual(['Exceptional Payoff', 'High Payoff', 'Moderate Payoff', 'Low Payoff', 'Not Worth Mastering'])
  })

  it('produces correct full ascending order for growth types', () => {
    const input = ['Plateau', 'Continual', 'Gradual']
    const sorted = sortByTier(input, GROWTH_TYPE_ORDER)
    expect(sorted).toEqual(['Continual', 'Gradual', 'Plateau'])
  })

  it('produces correct full ascending order for games_to_50 statuses', () => {
    const input = ['low data', 'crosses 50%', 'never reaches 50%', 'always above 50%']
    const sorted = sortByTier(input, GAMES_TO_50_STATUS_ORDER)
    expect(sorted).toEqual(['always above 50%', 'crosses 50%', 'never reaches 50%', 'low data'])
  })

  it('places nulls after all real values in full sort', () => {
    const input: (string | null)[] = [null, 'Hard Pickup', null, 'Easy Pickup']
    const sorted = sortByTier(input, SLOPE_TIER_ORDER)
    expect(sorted[0]).toBe('Easy Pickup')
    expect(sorted[1]).toBe('Hard Pickup')
    expect(sorted[2]).toBeNull()
    expect(sorted[3]).toBeNull()
  })
})
