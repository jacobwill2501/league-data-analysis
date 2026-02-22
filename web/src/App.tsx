import { useMemo, useState } from 'react'
import type { ChampionStat, EloFilter, GameTo50Entry, ViewMode } from './types/analysis'
import { useAnalysisData } from './hooks/useAnalysisData'
import { useTheme } from './hooks/useTheme'
import { Header } from './components/Header'
import { TableControls } from './components/TableControls'
import { ChampionTable, G50Table } from './components/ChampionTable'

// Lane values from API → display names
const LANE_MAP: Record<string, string> = {
  TOP: 'Top',
  JUNGLE: 'Jungle',
  MIDDLE: 'Mid',
  BOTTOM: 'Bot',
  UTILITY: 'Support',
}

function getLaneDisplay(lane: string | null | undefined): string {
  if (!lane) return ''
  return LANE_MAP[lane] ?? lane
}

// All unique learning tiers (ordered)
const LEARNING_TIERS = [
  'Safe Blind Pick',
  'Low Risk',
  'Moderate',
  'High Risk',
  'Avoid',
]

const MASTERY_TIERS = [
  'Exceptional Payoff',
  'High Payoff',
  'Moderate Payoff',
  'Low Payoff',
  'Not Worth Mastering',
]

function getTierOptions(view: ViewMode): string[] {
  if (['easiest_to_learn', 'dynamic_easiest'].includes(view)) return LEARNING_TIERS
  if (['best_to_master', 'dynamic_master'].includes(view)) return MASTERY_TIERS
  return []
}

function getTierField(view: ViewMode): keyof ChampionStat | null {
  if (['easiest_to_learn', 'dynamic_easiest'].includes(view)) return 'learning_tier'
  if (['best_to_master', 'dynamic_master'].includes(view)) return 'mastery_tier'
  return null
}

export function App() {
  const { theme, toggle } = useTheme()
  const [elo, setElo] = useState<EloFilter>('emerald_plus')
  const [view, setView] = useState<ViewMode>('easiest_to_learn')
  const [search, setSearch] = useState('')
  const [lane, setLane] = useState('ALL')
  const [tierFilter, setTierFilter] = useState('')

  const { data, loading, error } = useAnalysisData(elo)

  // Reset tier filter when view changes
  const handleViewChange = (v: ViewMode) => {
    setView(v)
    setTierFilter('')
  }

  // Determine which dataset to use based on view
  const sourceRows = useMemo((): ChampionStat[] => {
    if (!data) return []
    switch (view) {
      case 'easiest_to_learn':
        return data.easiestToLearn
      case 'best_to_master':
        return data.bestToMaster
      case 'best_investment':
        return data.bestInvestment
      case 'all_stats':
        return data.champions
      case 'dynamic_easiest':
        return data.dynamicEasiest
      case 'dynamic_master':
        return data.dynamicMaster
      case 'dynamic_investment':
        return data.dynamicInvestment
      default:
        return data.champions
    }
  }, [data, view])

  const sourceG50 = useMemo((): GameTo50Entry[] => {
    if (!data || view !== 'games_to_50') return []
    return data.gameTo50
  }, [data, view])

  // Filtered champion rows
  const filteredChampions = useMemo((): ChampionStat[] => {
    if (view === 'games_to_50') return []
    let rows = sourceRows

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(r => r.champion.toLowerCase().includes(q))
    }

    if (lane !== 'ALL') {
      rows = rows.filter(r => {
        const display = getLaneDisplay(r.most_common_lane)
        return display === lane
      })
    }

    const tierField = getTierField(view)
    if (tierField && tierFilter) {
      rows = rows.filter(r => (r[tierField] as string | null) === tierFilter)
    }

    return rows
  }, [sourceRows, search, lane, tierFilter, view])

  // Filtered G50 rows
  const filteredG50 = useMemo((): GameTo50Entry[] => {
    if (view !== 'games_to_50') return []
    let rows = sourceG50

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(r => r.champion_name.toLowerCase().includes(q))
    }

    if (lane !== 'ALL') {
      rows = rows.filter(r => {
        const display = getLaneDisplay(r.lane)
        return display === lane
      })
    }

    return rows
  }, [sourceG50, search, lane, view])

  const tierOptions = getTierOptions(view)
  const isG50 = view === 'games_to_50'

  const rowCount = isG50 ? filteredG50.length : filteredChampions.length
  const totalCount = isG50 ? sourceG50.length : sourceRows.length

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Header elo={elo} onEloChange={setElo} theme={theme} onThemeToggle={toggle} />

      <TableControls
        view={view}
        onViewChange={handleViewChange}
        search={search}
        onSearchChange={setSearch}
        lane={lane}
        onLaneChange={setLane}
        tierFilter={tierFilter}
        onTierFilterChange={setTierFilter}
        tierOptions={tierOptions}
        rowCount={rowCount}
        totalCount={totalCount}
      />

      <main>
        {loading && (
          <div className="flex items-center justify-center py-24 text-gray-400 dark:text-gray-600">
            <svg className="animate-spin h-8 w-8 mr-3" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Loading data…
          </div>
        )}

        {!loading && error && (
          <div className="flex items-center justify-center py-24">
            <div className="text-center">
              <p className="text-red-500 text-lg font-medium mb-2">Failed to load data</p>
              <p className="text-gray-500 text-sm">{error}</p>
              <p className="text-gray-400 text-sm mt-1">
                Make sure the JSON files are in <code>public/data/</code>
              </p>
            </div>
          </div>
        )}

        {!loading && !error && data && (
          <>
            {isG50 ? (
              <G50Table data={filteredG50} />
            ) : (
              <ChampionTable
                data={filteredChampions}
                view={view as Exclude<ViewMode, 'games_to_50'>}
              />
            )}
          </>
        )}
      </main>
    </div>
  )
}
