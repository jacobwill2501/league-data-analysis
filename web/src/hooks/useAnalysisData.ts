import { useEffect, useRef, useState } from 'react'
import type { AnalysisData, ChampionStat, EloFilter, GameTo50Entry, MasteryChampionCurve } from '../types/analysis'

export interface ParsedData {
  champions: ChampionStat[]
  gameTo50: GameTo50Entry[]
  easiestToLearn: ChampionStat[]
  bestToMaster: ChampionStat[]
  masteryChampionCurves: Record<string, MasteryChampionCurve>
  summary: { total_matches: number; total_unique_players: number } | null
  generatedAt: string | null
  overallWinRate: number | null
  pabuEasiestToLearn: ChampionStat[]
  pabuBestToMaster: ChampionStat[]
}

const BASE_URL = import.meta.env.BASE_URL

function parseData(raw: AnalysisData): ParsedData {
  const champions: ChampionStat[] = Object.entries(raw.champion_stats).map(
    ([name, stat]) => ({ champion: name, ...stat })
  )
  const gameTo50: GameTo50Entry[] = raw.games_to_50_winrate ?? []

  // Lookup map for backward compatibility with old JSON that lacks merged g50 fields
  const g50Map = new Map<string, GameTo50Entry>(gameTo50.map(e => [e.champion_name, e]))

  // Fill missing games_to_50 fields on easiest_to_learn rows (old JSON format)
  const easiestToLearn: ChampionStat[] = (raw.easiest_to_learn ?? []).map(row => {
    if (row.games_to_50_status !== undefined) return row
    const g50 = g50Map.get(row.champion)
    return {
      ...row,
      games_to_50_status: g50?.status ?? null,
      estimated_games: g50?.estimated_games ?? null,
      mastery_threshold: g50?.mastery_threshold ?? null,
      starting_winrate: g50?.starting_winrate ?? null,
    }
  })

  // Fall back to champion_stats keys when mastery_curves is absent (old JSON format)
  const masteryChampionCurves: Record<string, MasteryChampionCurve> =
    raw.mastery_curves && Object.keys(raw.mastery_curves).length > 0
      ? raw.mastery_curves
      : Object.fromEntries(
          Object.entries(raw.champion_stats ?? {}).map(([name, stat]) => [
            name,
            { lane: stat.most_common_lane ?? null, intervals: [] },
          ])
        )

  return {
    champions,
    gameTo50,
    easiestToLearn,
    bestToMaster: raw.best_to_master ?? [],
    masteryChampionCurves,
    summary: raw.summary
      ? { total_matches: raw.summary.total_matches, total_unique_players: raw.summary.total_unique_players }
      : null,
    generatedAt: raw.generated_at ?? null,
    overallWinRate: raw.summary?.overall_win_rate ?? null,
    pabuEasiestToLearn: raw.pabu_easiest_to_learn ?? [],
    pabuBestToMaster: raw.pabu_best_to_master ?? [],
  }
}

export function useAnalysisData(elo: EloFilter) {
  const [data, setData] = useState<ParsedData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const cache = useRef<Partial<Record<EloFilter, ParsedData>>>({})

  useEffect(() => {
    if (cache.current[elo]) {
      setData(cache.current[elo]!)
      setLoading(false)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)

    const controller = new AbortController()
    const url = `${BASE_URL}data/${elo}_results.json`
    fetch(url, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`)
        return res.json() as Promise<AnalysisData>
      })
      .then(raw => {
        const parsed = parseData(raw)
        cache.current[elo] = parsed
        setData(parsed)
        setLoading(false)
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') return
        setError(String(err))
        setLoading(false)
      })

    return () => controller.abort()
  }, [elo])

  return { data, loading, error }
}
