import { useEffect, useMemo, useState } from 'react'
import { createTheme, ThemeProvider, CssBaseline } from '@mui/material'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import Alert from '@mui/material/Alert'
import Typography from '@mui/material/Typography'
import type { ChampionStat, EloFilter, SlopeIterationStat, ViewMode } from './types/analysis'
import { useAnalysisData } from './hooks/useAnalysisData'
import { useThemeMode } from './hooks/useTheme'
import { Header } from './components/Header'
import { TableControls } from './components/TableControls'
import { ChampionTable } from './components/ChampionTable'
import { MasteryCurveView } from './components/MasteryCurveView'
import { SlopeIterationsView } from './components/SlopeIterationsView'

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
  const [view, setView] = useState<ViewMode>(() => {
    const param = new URLSearchParams(window.location.search).get('view')
    const valid: ViewMode[] = [
      'easiest_to_learn', 'best_to_master', 'mastery_curve', 'all_stats',
      'pabu_easiest_to_learn', 'pabu_best_to_master', 'pabu_mastery_curve', 'slope_iterations',
    ]
    return valid.includes(param as ViewMode) ? (param as ViewMode) : 'easiest_to_learn'
  })
  const [search, setSearch] = useState('')
  const [lane, setLane] = useState('ALL')
  const [hideRarePicks, setHideRarePicks] = useState(true)

  // Sync view state when the user presses the browser back/forward button
  useEffect(() => {
    const VALID_VIEWS: ViewMode[] = [
      'easiest_to_learn', 'best_to_master', 'mastery_curve', 'all_stats',
      'pabu_easiest_to_learn', 'pabu_best_to_master', 'pabu_mastery_curve', 'slope_iterations',
    ]
    const onPopState = () => {
      const param = new URLSearchParams(window.location.search).get('view')
      const next = VALID_VIEWS.includes(param as ViewMode) ? (param as ViewMode) : 'easiest_to_learn'
      setView(next)
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const { data, loading, error } = useAnalysisData(elo)

  const sourceRows = useMemo((): ChampionStat[] => {
    if (!data) return []
    switch (view) {
      case 'easiest_to_learn':       return data.easiestToLearn
      case 'best_to_master':         return data.bestToMaster
      case 'all_stats':              return data.champions
      case 'mastery_curve':          return []
      case 'pabu_easiest_to_learn':  return data.pabuEasiestToLearn
      case 'pabu_best_to_master':    return data.pabuBestToMaster
      case 'pabu_mastery_curve':     return []
      default:                       return data.champions
    }
  }, [data, view])

  // Expanded per-lane rows from champion_stats_by_lane — one entry per (champion, lane).
  // Used when a specific lane is selected so flex picks appear in every lane they're played in.
  const laneRows = useMemo((): ChampionStat[] => {
    if (!data?.championStatsByLane) return []
    return Object.entries(data.championStatsByLane).flatMap(([champion, laneMap]) =>
      Object.entries(laneMap).map(([laneKey, stats]) => ({
        champion,
        most_common_lane: laneKey,
        ...stats,
        // Fields not computed per-lane — shown as "—" in table
        games_to_50_status: null,
        starting_winrate: null,
        mastery_threshold: null,
        bias_status: null,
        estimated_games: null,
      } as ChampionStat))
    )
  }, [data])

  const filteredChampions = useMemo((): ChampionStat[] => {
    if (view === 'mastery_curve' || view === 'pabu_mastery_curve' || view === 'slope_iterations') return []

    const isRankedView = view === 'easiest_to_learn' || view === 'best_to_master'
                      || view === 'pabu_easiest_to_learn' || view === 'pabu_best_to_master'
    const rarePickThreshold = (data?.summary?.total_unique_players ?? 0) * 0.005

    // easiest_to_learn/pabu views rely on estimated_games/status/starting_winrate which
    // aren't computed per-lane — always filter the pooled sourceRows for these views.
    const isG50View = view === 'easiest_to_learn' || view === 'pabu_easiest_to_learn'

    const filteredSourceRows = isRankedView && hideRarePicks
      ? sourceRows.filter(r => (r.medium_games ?? 0) >= rarePickThreshold)
      : sourceRows
    const filteredLaneRows = isRankedView && hideRarePicks
      ? laneRows.filter(r => (r.medium_games ?? 0) >= rarePickThreshold)
      : laneRows

    // When a specific lane is selected (and not a g50 view), use per-lane rows so flex
    // picks appear in every lane they're played in (not just their most_common_lane).
    if (lane !== 'ALL' && laneRows.length > 0 && !isG50View) {
      let rows = filteredLaneRows.filter(r => getLaneDisplay(r.most_common_lane) === lane)
      if (search.trim()) {
        const q = search.trim().toLowerCase()
        rows = rows.filter(r => r.champion.toLowerCase().includes(q))
      }
      // Sort appropriately since per-lane rows aren't pre-sorted by the backend
      if (view === 'best_to_master' || view === 'pabu_best_to_master') {
        rows = [...rows].sort((a, b) => (b.mastery_score ?? -Infinity) - (a.mastery_score ?? -Infinity))
      } else {
        rows = [...rows].sort((a, b) => a.champion.localeCompare(b.champion))
      }
      return rows
    }

    // ALL lanes or g50 views: use pooled sourceRows, optionally filtered by lane
    let rows = filteredSourceRows
    if (lane !== 'ALL') {
      rows = rows.filter(r => getLaneDisplay(r.most_common_lane) === lane)
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(r => r.champion.toLowerCase().includes(q))
    }
    return rows
  }, [sourceRows, laneRows, search, lane, view, hideRarePicks, data])

  const filteredSlope = useMemo((): SlopeIterationStat[] => {
    if (view !== 'slope_iterations' || !data) return []
    let rows = data.slopeIterations

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(r => r.champion.toLowerCase().includes(q))
    }

    if (lane !== 'ALL') {
      rows = rows.filter(r => getLaneDisplay(r.most_common_lane) === lane)
    }

    return rows
  }, [data, view, search, lane])

  const handleViewChange = (newView: ViewMode) => {
    setView(newView)
    const params = new URLSearchParams(window.location.search)
    params.set('view', newView)
    window.history.replaceState(null, '', `?${params.toString()}`)
  }

  const handleNavigateToMasteryCurve = (champion: string, lane: string | null) => {
    const params = new URLSearchParams(window.location.search)
    params.set('view', 'mastery_curve')
    params.set('champion', champion)
    if (lane) params.set('lane', lane)
    else params.delete('lane')
    // pushState so the browser back button returns to the previous view
    window.history.pushState(null, '', `?${params.toString()}`)
    setView('mastery_curve')
  }

  const isMasteryCurve = view === 'mastery_curve' || view === 'pabu_mastery_curve'
  const isSlopeView = view === 'slope_iterations'
  const rowCount = isMasteryCurve ? 0 : isSlopeView ? filteredSlope.length : filteredChampions.length
  const totalCount = isMasteryCurve ? 0 : isSlopeView ? (data?.slopeIterations.length ?? 0) : sourceRows.length

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Header
          elo={elo}
          onEloChange={setElo}
          mode={mode}
          onModeToggle={toggle}
          summary={data?.summary ?? null}
          generatedAt={data?.generatedAt ?? null}
        />

        <TableControls
          view={view}
          onViewChange={handleViewChange}
          search={search}
          onSearchChange={setSearch}
          lane={lane}
          onLaneChange={setLane}
          rowCount={rowCount}
          totalCount={totalCount}
          hideRarePicks={hideRarePicks}
          onHideRarePicksChange={setHideRarePicks}
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
            isSlopeView
              ? <SlopeIterationsView
                  data={filteredSlope}
                  masteryChampionCurves={data.masteryChampionCurves}
                  dataByLane={data.slopeIterationsByLane}
                  masteryChampionCurvesByLane={data.masteryChampionCurvesByLane}
                  onChampionClick={handleNavigateToMasteryCurve}
                />
              : isMasteryCurve
                ? <MasteryCurveView
                    masteryChampionCurves={data.masteryChampionCurves}
                    masteryChampionCurvesByLane={data.masteryChampionCurvesByLane}
                    pabuThreshold={view === 'pabu_mastery_curve' ? data.overallWinRate : undefined}
                  />
                : <ChampionTable
                    data={filteredChampions}
                    view={view as Exclude<ViewMode, 'mastery_curve' | 'pabu_mastery_curve' | 'slope_iterations'>}
                  />
          )}
        </Box>
      </Box>
    </ThemeProvider>
  )
}
