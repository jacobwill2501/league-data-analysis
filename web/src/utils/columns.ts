import { type ColumnDef } from '@tanstack/react-table'
import type { ChampionStat, GameTo50Entry, ViewMode } from '../types/analysis'
import { fmtPct, fmtRatio, fmtDelta, fmtScore, fmtLane, fmtGames, fmtThreshold } from './format'

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

const difficultyCol: ColumnDef<ChampionStat> = {
  id: 'difficulty',
  header: 'Difficulty',
  accessorKey: 'difficulty_label',
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
  enableSorting: true,
}

// ── Standard view columns ─────────────────────────────────────────────────────

export function getEasiestToLearnCols(): ColumnDef<ChampionStat>[] {
  return [
    championCol,
    laneCol,
    learningTierCol,
    { id: 'learning_score', header: 'Learning Score', accessorKey: 'learning_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_wr', header: 'Low WR', accessorKey: 'low_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'medium_wr', header: 'Medium WR', accessorKey: 'medium_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_ratio', header: 'Low Ratio', accessorKey: 'low_ratio', cell: i => fmtRatio(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_delta', header: 'Low Δ', accessorKey: 'low_delta', cell: i => fmtDelta(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_games', header: 'Low Games', accessorKey: 'low_games', cell: i => fmtGames(i.getValue<number | null>()), enableSorting: true },
  ]
}

export function getBestToMasterCols(): ColumnDef<ChampionStat>[] {
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
  ]
}

export function getBestInvestmentCols(): ColumnDef<ChampionStat>[] {
  return [
    championCol,
    laneCol,
    { id: 'investment_score', header: 'Investment Score', accessorKey: 'investment_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'learning_score', header: 'Learning Score', accessorKey: 'learning_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'mastery_score', header: 'Mastery Score', accessorKey: 'mastery_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    learningTierCol,
    masteryTierCol,
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

// ── Dynamic view columns ──────────────────────────────────────────────────────

export function getDynamicEasiestCols(): ColumnDef<ChampionStat>[] {
  return [
    championCol,
    laneCol,
    difficultyCol,
    estGamesChampCol,
    learningTierCol,
    { id: 'learning_score', header: 'Learning Score', accessorKey: 'learning_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_wr', header: 'Low WR', accessorKey: 'low_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'medium_wr', header: 'Medium WR', accessorKey: 'medium_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_ratio', header: 'Low Ratio', accessorKey: 'low_ratio', cell: i => fmtRatio(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_delta', header: 'Low Δ', accessorKey: 'low_delta', cell: i => fmtDelta(i.getValue<number | null>()), enableSorting: true },
  ]
}

export function getDynamicMasterCols(): ColumnDef<ChampionStat>[] {
  return [
    championCol,
    laneCol,
    difficultyCol,
    estGamesChampCol,
    masteryTierCol,
    { id: 'mastery_score', header: 'Mastery Score', accessorKey: 'mastery_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'medium_wr', header: 'Medium WR', accessorKey: 'medium_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_wr', header: 'High WR', accessorKey: 'high_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_ratio', header: 'High Ratio', accessorKey: 'high_ratio', cell: i => fmtRatio(i.getValue<number | null>()), enableSorting: true },
    { id: 'delta', header: 'High Δ', accessorKey: 'delta', cell: i => fmtDelta(i.getValue<number | null>()), enableSorting: true },
  ]
}

export function getDynamicInvestmentCols(): ColumnDef<ChampionStat>[] {
  return [
    championCol,
    laneCol,
    difficultyCol,
    estGamesChampCol,
    { id: 'investment_score', header: 'Investment Score', accessorKey: 'investment_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'learning_score', header: 'Learning Score', accessorKey: 'learning_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'mastery_score', header: 'Mastery Score', accessorKey: 'mastery_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'low_wr', header: 'Low WR', accessorKey: 'low_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_wr', header: 'High WR', accessorKey: 'high_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
  ]
}

// ── Games to 50% columns ──────────────────────────────────────────────────────

export function getGamesTo50Cols(): ColumnDef<GameTo50Entry>[] {
  return [
    {
      id: 'champion',
      header: 'Champion',
      accessorKey: 'champion_name',
      enableSorting: true,
    },
    {
      id: 'lane',
      header: 'Lane',
      accessorKey: 'lane',
      cell: info => fmtLane(info.getValue<string | null>()),
      enableSorting: true,
    },
    {
      id: 'status',
      header: 'Status',
      accessorKey: 'status',
      enableSorting: true,
    },
    {
      id: 'estimated_games',
      header: 'Est. Games',
      accessorKey: 'estimated_games',
      cell: info => {
        const v = info.getValue<number | null>()
        return v === null || v === undefined ? 'N/A' : fmtGames(v)
      },
      enableSorting: true,
    },
    {
      id: 'mastery_threshold',
      header: 'Mastery Threshold',
      accessorKey: 'mastery_threshold',
      cell: info => fmtThreshold(info.getValue<number | null>()),
      enableSorting: true,
    },
    {
      id: 'starting_winrate',
      header: 'Starting WR',
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
  isDynamic?: boolean
}

export const VIEW_CONFIGS: Record<ViewMode, ViewConfig> = {
  easiest_to_learn: {
    label: 'Easiest to Learn',
    defaultSort: { id: 'learning_score', desc: true },
  },
  best_to_master: {
    label: 'Best to Master',
    defaultSort: { id: 'mastery_score', desc: true },
  },
  best_investment: {
    label: 'Best Investment',
    defaultSort: { id: 'investment_score', desc: true },
  },
  all_stats: {
    label: 'All Stats',
    defaultSort: { id: 'champion', desc: false },
  },
  dynamic_easiest: {
    label: 'Dynamic Easiest to Learn',
    defaultSort: { id: 'learning_score', desc: true },
    isDynamic: true,
  },
  dynamic_master: {
    label: 'Dynamic Best to Master',
    defaultSort: { id: 'mastery_score', desc: true },
    isDynamic: true,
  },
  dynamic_investment: {
    label: 'Dynamic Best Investment',
    defaultSort: { id: 'investment_score', desc: true },
    isDynamic: true,
  },
  games_to_50: {
    label: 'Games to 50% WR',
    defaultSort: { id: 'estimated_games', desc: false },
    isG50: true,
  },
}
