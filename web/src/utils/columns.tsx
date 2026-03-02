import { type ColumnDef } from '@tanstack/react-table'
import MuiTooltip from '@mui/material/Tooltip'
import type { ChampionStat, ViewMode, SlopeIterationStat } from '../types/analysis'
import { fmtPct, fmtRatio, fmtDelta, fmtScore, fmtLane, fmtGames, fmtThreshold, nullLastSortingFn } from './format'

// ── Shared champion columns ───────────────────────────────────────────────────

const championCol: ColumnDef<ChampionStat> = {
  id: 'champion',
  header: 'Champion',
  accessorKey: 'champion',
  enableSorting: true,
}

const laneCol: ColumnDef<ChampionStat> = {
  id: 'lane',
  header: 'Lane',
  accessorKey: 'most_common_lane',
  cell: info => fmtLane(info.getValue<string | null>()),
  enableSorting: true,
}

const learningTierCol: ColumnDef<ChampionStat> = {
  id: 'learning_tier',
  header: 'Learning Tier',
  accessorKey: 'learning_tier',
  cell: info => info.getValue<string | null>() ?? '—',
  enableSorting: true,
}

const masteryTierCol: ColumnDef<ChampionStat> = {
  id: 'mastery_tier',
  header: 'Mastery Tier',
  accessorKey: 'mastery_tier',
  cell: info => info.getValue<string | null>() ?? '—',
  enableSorting: true,
}

const estGamesChampCol: ColumnDef<ChampionStat> = {
  id: 'estimated_games',
  header: 'Est. Games',
  accessorKey: 'estimated_games',
  cell: info => {
    const v = info.getValue<number | null>()
    return v === null || v === undefined ? 'N/A' : fmtGames(v)
  },
  sortingFn: nullLastSortingFn,
  enableSorting: true,
}

// ── Standard view columns ─────────────────────────────────────────────────────

function fmtSlope(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${val.toFixed(1)}pp`
}

export function getEasiestToLearnCols(
  slopeMap?: Map<string, SlopeIterationStat>
): ColumnDef<ChampionStat>[] {
  const enriched: ColumnDef<ChampionStat>[] = slopeMap
    ? [
        {
          id: 'slope_tier',
          header: () => (
            <MuiTooltip title="How steep is the early win-rate curve? Easy Pickup = competent quickly. Very Hard Pickup = steep penalty before you learn the basics.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Pickup</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.slope_tier ?? null,
          cell: info => info.getValue<string | null>() ?? '—',
          enableSorting: true,
        },
        {
          id: 'initial_wr',
          header: () => (
            <MuiTooltip title="Win rate in the 5–25 games bracket. Your floor — the worst you should expect to perform before you've learned the basics.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Floor WR</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.initial_wr ?? null,
          cell: info => fmtPct(info.getValue<number | null>()),
          enableSorting: true,
        },
      ]
    : []

  return [
    championCol,
    laneCol,
    ...enriched,
    { id: 'status', header: 'Status', accessorKey: 'games_to_50_status', cell: info => info.getValue<string | null>() ?? '—', enableSorting: true },
    estGamesChampCol,
    { id: 'mastery_threshold', header: 'Mastery Threshold', accessorKey: 'mastery_threshold', cell: info => fmtThreshold(info.getValue<number | null>()), enableSorting: true },
    {
      id: 'starting_winrate',
      header: () => (
        <MuiTooltip title="Win rate in the lowest mastery interval (0–1,000 points) — approximates performance in a player's first 1–2 games on this champion">
          <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Starting WR</span>
        </MuiTooltip>
      ),
      accessorKey: 'starting_winrate',
      cell: info => fmtPct(info.getValue<number | null>()),
      enableSorting: true,
    },
  ]
}

export function getBestToMasterCols(
  slopeMap?: Map<string, SlopeIterationStat>
): ColumnDef<ChampionStat>[] {
  const enriched: ColumnDef<ChampionStat>[] = slopeMap
    ? [
        {
          id: 'growth_type',
          header: () => (
            <MuiTooltip title="Does the champion keep rewarding mastery past the competency plateau? Continual = yes. Plateau = WR levels off after ~competency.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Growth</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.growth_type ?? null,
          cell: info => info.getValue<string | null>() ?? '—',
          enableSorting: true,
        },
        {
          id: 'late_slope',
          header: () => (
            <MuiTooltip title="Win rate gain across the last 3 mastery brackets (100k+ points). Positive = champion rewards deep mastery. Drives the Growth tier.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Late Slope</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.late_slope ?? null,
          cell: info => fmtSlope(info.getValue<number | null>()),
          enableSorting: true,
        },
        {
          id: 'inflection_games',
          header: () => (
            <MuiTooltip title="Estimated games until win rate reaches within 0.5pp of peak. Lower = you hit your ceiling faster.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Games to Plateau</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.inflection_games ?? null,
          cell: info => {
            const v = info.getValue<number | null>()
            return v == null ? '—' : fmtGames(v)
          },
          sortingFn: nullLastSortingFn,
          enableSorting: true,
        },
      ]
    : []

  return [
    championCol,
    laneCol,
    masteryTierCol,
    { id: 'mastery_score', header: 'Mastery Score', accessorKey: 'mastery_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_wr', header: 'High WR', accessorKey: 'high_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'medium_wr', header: 'Medium WR', accessorKey: 'medium_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_ratio', header: 'High Ratio', accessorKey: 'high_ratio', cell: i => fmtRatio(i.getValue<number | null>()), enableSorting: true },
    { id: 'delta', header: 'High Δ', accessorKey: 'delta', cell: i => fmtDelta(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_games', header: 'High Games', accessorKey: 'high_games', cell: i => fmtGames(i.getValue<number | null>()), enableSorting: true },
    ...enriched,
  ]
}

export function getAllStatsCols(): ColumnDef<ChampionStat>[] {
  return [
    championCol,
    laneCol,
    { id: 'low_wr', header: 'Low WR', accessorKey: 'low_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'medium_wr', header: 'Medium WR', accessorKey: 'medium_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_wr', header: 'High WR', accessorKey: 'high_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_games', header: 'Low Games', accessorKey: 'low_games', cell: i => fmtGames(i.getValue<number | null>()), enableSorting: true },
    { id: 'medium_games', header: 'Med Games', accessorKey: 'medium_games', cell: i => fmtGames(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_games', header: 'High Games', accessorKey: 'high_games', cell: i => fmtGames(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_ratio', header: 'Low Ratio', accessorKey: 'low_ratio', cell: i => fmtRatio(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_ratio', header: 'High Ratio', accessorKey: 'high_ratio', cell: i => fmtRatio(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_delta', header: 'Low Δ', accessorKey: 'low_delta', cell: i => fmtDelta(i.getValue<number | null>()), enableSorting: true },
    { id: 'delta', header: 'High Δ', accessorKey: 'delta', cell: i => fmtDelta(i.getValue<number | null>()), enableSorting: true },
    { id: 'learning_score', header: 'Learn Score', accessorKey: 'learning_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'mastery_score', header: 'Master Score', accessorKey: 'mastery_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'investment_score', header: 'Invest Score', accessorKey: 'investment_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    learningTierCol,
    masteryTierCol,
  ]
}

export function getPabuEasiestToLearnCols(): ColumnDef<ChampionStat>[] {
  const pabuEstGamesCol: ColumnDef<ChampionStat> = {
    id: 'estimated_games',
    header: () => (
      <MuiTooltip title="Est. games until win rate exceeds the elo bracket average (elo-normalized threshold)">
        <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Est. Games</span>
      </MuiTooltip>
    ),
    accessorKey: 'estimated_games',
    cell: info => {
      const v = info.getValue<number | null>()
      return v === null || v === undefined ? 'N/A' : fmtGames(v)
    },
    sortingFn: nullLastSortingFn,
    enableSorting: true,
  }
  return [
    championCol,
    laneCol,
    { id: 'status', header: 'Status', accessorKey: 'games_to_50_status', cell: info => info.getValue<string | null>() ?? '—', enableSorting: true },
    pabuEstGamesCol,
    { id: 'mastery_threshold', header: 'Mastery Threshold', accessorKey: 'mastery_threshold', cell: info => fmtThreshold(info.getValue<number | null>()), enableSorting: true },
    {
      id: 'starting_winrate',
      header: () => (
        <MuiTooltip title="Win rate in the lowest mastery interval (0–1,000 points) — approximates performance in a player's first 1–2 games on this champion">
          <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Starting WR</span>
        </MuiTooltip>
      ),
      accessorKey: 'starting_winrate',
      cell: info => fmtPct(info.getValue<number | null>()),
      enableSorting: true,
    },
  ]
}

// ── View metadata ─────────────────────────────────────────────────────────────

export interface ViewConfig {
  label: string
  defaultSort: { id: string; desc: boolean }
  isG50?: boolean
  isBias?: boolean
  isMasteryCurve?: boolean
  isPabu?: boolean
}

export const VIEW_CONFIGS: Record<ViewMode, ViewConfig> = {
  easiest_to_learn: {
    label: 'Easiest to Learn',
    defaultSort: { id: 'estimated_games', desc: false },
  },
  best_to_master: {
    label: 'Best to Master',
    defaultSort: { id: 'mastery_score', desc: true },
  },
  mastery_curve: {
    label: 'Mastery Curve',
    defaultSort: { id: 'champion', desc: false },
    isMasteryCurve: true,
  },
  all_stats: {
    label: 'All Stats',
    defaultSort: { id: 'champion', desc: false },
  },
  pabu_easiest_to_learn: {
    label: 'Pabu: Easiest to Learn β',
    defaultSort: { id: 'estimated_games', desc: false },
    isPabu: true,
  },
  pabu_best_to_master: {
    label: 'Pabu: Best to Master β',
    defaultSort: { id: 'mastery_score', desc: true },
    isPabu: true,
  },
  pabu_mastery_curve: {
    label: 'Pabu: Mastery Curve β',
    defaultSort: { id: 'champion', desc: false },
    isMasteryCurve: true,
    isPabu: true,
  },
  slope_iterations: {
    label: 'Slope Iterations',
    defaultSort: { id: 'inflection_games', desc: false },
  },
  off_role: {
    label: 'Off-Role Picks',
    defaultSort: { id: 'initial_wr', desc: true },
  },
  learning_profile: {
    label: 'Learning Profile',
    defaultSort: { id: 'champion', desc: false },
  },
}
