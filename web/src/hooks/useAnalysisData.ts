import { useEffect, useRef, useState } from 'react'
import type { AnalysisData, ChampionStat, EloFilter, GameTo50Entry } from '../types/analysis'

export interface ParsedData {
  champions: ChampionStat[]
  dynamicChampions: ChampionStat[]
  dynamicEasiest: ChampionStat[]
  dynamicMaster: ChampionStat[]
  dynamicInvestment: ChampionStat[]
  gameTo50: GameTo50Entry[]
  easiestToLearn: ChampionStat[]
  bestToMaster: ChampionStat[]
  bestInvestment: ChampionStat[]
}

const BASE_URL = import.meta.env.BASE_URL

function parseData(raw: AnalysisData): ParsedData {
  const champions: ChampionStat[] = Object.entries(raw.champion_stats).map(
    ([name, stat]) => ({ champion: name, ...stat })
  )
  const dynamicChampions: ChampionStat[] = Object.entries(raw.dynamic_champion_stats ?? {}).map(
    ([name, stat]) => ({ champion: name, ...stat })
  )
  return {
    champions,
    dynamicChampions,
    dynamicEasiest: raw.dynamic_easiest_to_learn ?? [],
    dynamicMaster: raw.dynamic_best_to_master ?? [],
    dynamicInvestment: raw.dynamic_best_investment ?? [],
    gameTo50: raw.games_to_50_winrate ?? [],
    easiestToLearn: raw.easiest_to_learn ?? [],
    bestToMaster: raw.best_to_master ?? [],
    bestInvestment: raw.best_investment ?? [],
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

    const url = `${BASE_URL}data/${elo}_results.json`
    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<AnalysisData>
      })
      .then(raw => {
        const parsed = parseData(raw)
        cache.current[elo] = parsed
        setData(parsed)
        setLoading(false)
      })
      .catch(err => {
        setError(String(err))
        setLoading(false)
      })
  }, [elo])

  return { data, loading, error }
}
