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
  // Dynamic fields (present in dynamic_champion_stats rows)
  dynamic_status?: string | null
  mastery_threshold?: number | null
  estimated_games?: number | null
  difficulty_label?: string | null
}

export interface GameTo50Entry {
  champion_name: string
  lane: string | null
  mastery_threshold: number | null
  estimated_games: number | null
  starting_winrate: number | null
  status: string
}

export interface AnalysisData {
  filter: string
  filter_description: string
  champion_stats: Record<string, Omit<ChampionStat, 'champion'>>
  dynamic_champion_stats: Record<string, Omit<ChampionStat, 'champion'>>
  games_to_50_winrate: GameTo50Entry[]
  dynamic_easiest_to_learn: ChampionStat[]
  dynamic_best_to_master: ChampionStat[]
  dynamic_best_investment: ChampionStat[]
  easiest_to_learn: ChampionStat[]
  best_to_master: ChampionStat[]
  best_investment: ChampionStat[]
}

export type EloFilter = 'emerald_plus' | 'diamond_plus' | 'diamond2_plus'

export type ViewMode =
  | 'easiest_to_learn'
  | 'best_to_master'
  | 'best_investment'
  | 'all_stats'
  | 'dynamic_easiest'
  | 'dynamic_master'
  | 'dynamic_investment'
  | 'games_to_50'
