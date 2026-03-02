// web/src/utils/tiers.ts

export type ChipColor = 'success' | 'warning' | 'error' | 'default' | 'info'

export const SLOPE_TIER_CHIP_COLOR: Record<string, ChipColor> = {
  'Easy Pickup':      'success',
  'Mild Pickup':      'info',
  'Hard Pickup':      'warning',
  'Very Hard Pickup': 'error',
}

export const SLOPE_TIER_LINE_COLOR: Record<string, string> = {
  'Easy Pickup':      '#66BB6A',
  'Mild Pickup':      '#FFA726',
  'Hard Pickup':      '#EF6C00',
  'Very Hard Pickup': '#EF5350',
}

export const GROWTH_TYPE_CHIP_COLOR: Record<string, ChipColor> = {
  'Plateau':   'default',
  'Gradual':   'info',
  'Continual': 'success',
}

export const GAMES_TO_50_STATUS_COLORS: Record<string, string> = {
  'always above 50%': '#66BB6A',
  'never reaches 50%': '#EF5350',
  'crosses 50%': '#90CAF9',
  'low data': '#888',
}

// ── Tier sort order maps (ascending = best/easiest first) ─────────────────────

export const SLOPE_TIER_ORDER: Record<string, number> = {
  'Easy Pickup':      0,
  'Mild Pickup':      1,
  'Hard Pickup':      2,
  'Very Hard Pickup': 3,
}

export const LEARNING_TIER_ORDER: Record<string, number> = {
  'Safe Blind Pick': 0,
  'Low Risk':        1,
  'Moderate':        2,
  'High Risk':       3,
  'Avoid':           4,
}

export const MASTERY_TIER_ORDER: Record<string, number> = {
  'Exceptional Payoff': 0,
  'High Payoff':        1,
  'Moderate Payoff':    2,
  'Low Payoff':         3,
  'Not Worth Mastering': 4,
}

export const GROWTH_TYPE_ORDER: Record<string, number> = {
  'Continual': 0,
  'Gradual':   1,
  'Plateau':   2,
}

export const GAMES_TO_50_STATUS_ORDER: Record<string, number> = {
  'always above 50%':  0,
  'crosses 50%':       1,
  'never reaches 50%': 2,
  'low data':          3,
}
