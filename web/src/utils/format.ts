export function fmtPct(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return (val * 100).toFixed(2) + '%'
}

export function fmtRatio(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return val.toFixed(2)
}

export function fmtDelta(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  const sign = val >= 0 ? '+' : ''
  return sign + val.toFixed(2) + '%'
}

export function fmtScore(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return val.toFixed(2)
}

export function fmtGames(val: number | null | undefined): string {
  if (val === null || val === undefined) return 'N/A'
  return val.toLocaleString()
}

export function fmtThreshold(val: number | null | undefined): string {
  if (val === null || val === undefined) return 'N/A'
  return val.toLocaleString() + ' pts'
}

/** Returns Tailwind classes for win-rate color coding */
export function wrColor(val: number | null | undefined): string {
  if (val === null || val === undefined) return ''
  const pct = val * 100
  if (pct < 48) return 'text-red-600 dark:text-red-400'
  if (pct > 52) return 'text-emerald-600 dark:text-emerald-400'
  return 'text-gray-600 dark:text-gray-300'
}

const LANE_DISPLAY: Record<string, string> = {
  TOP: 'Top',
  JUNGLE: 'Jungle',
  MIDDLE: 'Mid',
  BOTTOM: 'Bot',
  UTILITY: 'Support',
}

export function fmtLane(lane: string | null | undefined): string {
  if (!lane) return '—'
  return LANE_DISPLAY[lane] ?? lane
}
