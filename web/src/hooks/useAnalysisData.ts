import { useEffect, useRef, useState } from 'react'
import type { AnalysisData, ChampionStat, EloFilter, GameTo50Entry, MasteryChampionCurve } from '../types/analysis'

export interface ParsedData {
  champions: ChampionStat[]
  biasChampions: ChampionStat[]
  biasEasiest: ChampionStat[]
  biasMaster: ChampionStat[]
  biasInvestment: ChampionStat[]
  gameTo50: GameTo50Entry[]
  easiestToLearn: ChampionStat[]
  bestToMaster: ChampionStat[]
  bestInvestment: ChampionStat[]
  masteryChampionCurves: Record<string, MasteryChampionCurve>
}

const BASE_URL = import.meta.env.BASE_URL

function parseData(raw: AnalysisData): ParsedData {
  const champions: ChampionStat[] = Object.entries(raw.champion_stats).map(
    ([name, stat]) => ({ champion: name, ...stat })
  )
  const biasChampions: ChampionStat[] = Object.entries(raw.bias_champion_stats ?? {}).map(
    ([name, stat]) => ({ champion: name, ...stat })
  )
  return {
    champions,
    biasChampions,
    biasEasiest: raw.bias_easiest_to_learn ?? [],
    biasMaster: raw.bias_best_to_master ?? [],
    biasInvestment: raw.bias_best_investment ?? [],
    gameTo50: raw.games_to_50_winrate ?? [],
    easiestToLearn: raw.easiest_to_learn ?? [],
    bestToMaster: raw.best_to_master ?? [],
    bestInvestment: raw.best_investment ?? [],
    masteryChampionCurves: raw.mastery_curves ?? {},
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
