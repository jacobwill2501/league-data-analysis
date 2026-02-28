export interface ChampionStat {
  champion: string
  // Standard bucket stats
  low_wr: number | null
  medium_wr: number | null
  high_wr: number | null
  low_games: number
  medium_games: number
  high_games: number
  low_ratio: number | null
  high_ratio: number | null
  low_delta: number | null
  delta: number | null
  mastery_score: number | null
  learning_score: number | null
  investment_score: number | null
  learning_tier: string | null
  mastery_tier: string | null
  most_common_lane: string | null
  // Bias fields (present in bias_champion_stats rows)
  bias_status?: string | null
  mastery_threshold?: number | null
  estimated_games?: number | null
  difficulty_label?: string | null
  // Games-to-50 merged fields (present in easiest_to_learn rows)
  games_to_50_status?: string | null
  starting_winrate?: number | null
}

export interface GameTo50Entry {
  champion_name: string
  lane: string | null
  mastery_threshold: number | null
  estimated_games: number | null
  starting_winrate: number | null
  status: string
}

export interface MasteryInterval {
  label: string
  min: number
  max: number | null
  win_rate: number
  games: number
  ci_lower?: number | null
  ci_upper?: number | null
}

export interface MasteryChampionCurve {
  lane: string | null
  intervals: MasteryInterval[]
}

export interface AnalysisSummary {
  total_matches: number
  total_unique_players: number
  overall_win_rate: number
}

export interface SlopeIterationStat {
  champion: string
  most_common_lane: string | null
  initial_wr: number | null
  peak_wr: number | null
  total_slope: number | null
  early_slope: number | null
  early_slope_ci?: number | null
  late_slope: number | null
  inflection_mastery: number | null
  inflection_games: number | null
  slope_tier: string | null
  growth_type: string | null
  valid_intervals: number | null
}

export interface AnalysisData {
  filter: string
  filter_description: string
  generated_at?: string
  summary?: AnalysisSummary
  champion_stats: Record<string, Omit<ChampionStat, 'champion'>>
  bias_champion_stats: Record<string, Omit<ChampionStat, 'champion'>>
  games_to_50_winrate: GameTo50Entry[]
  bias_easiest_to_learn: ChampionStat[]
  bias_best_to_master: ChampionStat[]
  bias_best_investment: ChampionStat[]
  easiest_to_learn: ChampionStat[]
  best_to_master: ChampionStat[]
  best_investment: ChampionStat[]
  mastery_curves: Record<string, MasteryChampionCurve>
  // Pabu beta views (optional — absent in older JSONs)
  pabu_champion_stats?: Record<string, Omit<ChampionStat, 'champion'>>
  pabu_games_to_threshold?: GameTo50Entry[]
  pabu_easiest_to_learn?: ChampionStat[]
  pabu_best_to_master?: ChampionStat[]
  slope_iterations?: SlopeIterationStat[]
}

export type EloFilter = 'emerald_plus' | 'diamond_plus' | 'diamond2_plus'

export type ViewMode =
  | 'easiest_to_learn'
  | 'best_to_master'
  | 'mastery_curve'
  | 'all_stats'
  | 'pabu_easiest_to_learn'
  | 'pabu_best_to_master'
  | 'pabu_mastery_curve'
  | 'slope_iterations'
