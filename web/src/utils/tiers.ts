// web/src/utils/tiers.ts

type ChipColor = 'success' | 'warning' | 'error' | 'default' | 'info'

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
