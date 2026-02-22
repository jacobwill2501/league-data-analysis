import { useMemo, useState } from 'react'
import { createTheme, ThemeProvider, CssBaseline } from '@mui/material'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import Alert from '@mui/material/Alert'
import Typography from '@mui/material/Typography'
import type { ChampionStat, EloFilter, GameTo50Entry, ViewMode } from './types/analysis'
import { useAnalysisData } from './hooks/useAnalysisData'
import { useThemeMode } from './hooks/useTheme'
import { Header } from './components/Header'
import { TableControls } from './components/TableControls'
import { ChampionTable, G50Table } from './components/ChampionTable'

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
  const { mode, toggle } = useThemeMode()

  const theme = useMemo(
    () =>
      createTheme({
        palette: { mode },
        components: {
          MuiTableCell: {
            styleOverrides: {
              stickyHeader: ({ theme }) => ({
                backgroundColor: theme.palette.background.paper,
              }),
            },
          },
        },
      }),
    [mode]
  )

  const [elo, setElo] = useState<EloFilter>('emerald_plus')
  const [view, setView] = useState<ViewMode>('easiest_to_learn')
  const [search, setSearch] = useState('')
  const [lane, setLane] = useState('ALL')
  const [tierFilter, setTierFilter] = useState('')

  const { data, loading, error } = useAnalysisData(elo)

  const handleViewChange = (v: ViewMode) => {
    setView(v)
    setTierFilter('')
  }

  const sourceRows = useMemo((): ChampionStat[] => {
    if (!data) return []
    switch (view) {
      case 'easiest_to_learn': return data.easiestToLearn
      case 'best_to_master':   return data.bestToMaster
      case 'best_investment':  return data.bestInvestment
      case 'all_stats':        return data.champions
      case 'dynamic_easiest':  return data.dynamicEasiest
      case 'dynamic_master':   return data.dynamicMaster
      case 'dynamic_investment': return data.dynamicInvestment
      default:                 return data.champions
    }
  }, [data, view])

  const sourceG50 = useMemo((): GameTo50Entry[] => {
    if (!data || view !== 'games_to_50') return []
    return data.gameTo50
  }, [data, view])

  const filteredChampions = useMemo((): ChampionStat[] => {
    if (view === 'games_to_50') return []
    let rows = sourceRows

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(r => r.champion.toLowerCase().includes(q))
    }

    if (lane !== 'ALL') {
      rows = rows.filter(r => getLaneDisplay(r.most_common_lane) === lane)
    }

    const tierField = getTierField(view)
    if (tierField && tierFilter) {
      rows = rows.filter(r => (r[tierField] as string | null) === tierFilter)
    }

    return rows
  }, [sourceRows, search, lane, tierFilter, view])

  const filteredG50 = useMemo((): GameTo50Entry[] => {
    if (view !== 'games_to_50') return []
    let rows = sourceG50

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(r => r.champion_name.toLowerCase().includes(q))
    }

    if (lane !== 'ALL') {
      rows = rows.filter(r => getLaneDisplay(r.lane) === lane)
    }

    return rows
  }, [sourceG50, search, lane, view])

  const isG50 = view === 'games_to_50'
  const rowCount = isG50 ? filteredG50.length : filteredChampions.length
  const totalCount = isG50 ? sourceG50.length : sourceRows.length

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Header elo={elo} onEloChange={setElo} mode={mode} onModeToggle={toggle} />

        <TableControls
          view={view}
          onViewChange={handleViewChange}
          search={search}
          onSearchChange={setSearch}
          lane={lane}
          onLaneChange={setLane}
          tierFilter={tierFilter}
          onTierFilterChange={setTierFilter}
          tierOptions={getTierOptions(view)}
          rowCount={rowCount}
          totalCount={totalCount}
        />

        <Box component="main" sx={{ flex: 1 }}>
          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 15, gap: 2 }}>
              <CircularProgress size={28} />
              <Typography color="text.secondary">Loading data…</Typography>
            </Box>
          )}

          {!loading && error && (
            <Box sx={{ p: 4 }}>
              <Alert severity="error">
                <strong>Failed to load data</strong> — {error}
                <br />
                Make sure the JSON files are in <code>public/data/</code>.
              </Alert>
            </Box>
          )}

          {!loading && !error && data && (
            isG50
              ? <G50Table data={filteredG50} />
              : <ChampionTable
                  data={filteredChampions}
                  view={view as Exclude<ViewMode, 'games_to_50'>}
                />
          )}
        </Box>
      </Box>
    </ThemeProvider>
  )
}
