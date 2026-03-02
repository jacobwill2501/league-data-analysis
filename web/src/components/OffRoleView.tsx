// web/src/components/OffRoleView.tsx
import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import Table from '@mui/material/Table'
import TableHead from '@mui/material/TableHead'
import TableBody from '@mui/material/TableBody'
import TableRow from '@mui/material/TableRow'
import TableCell from '@mui/material/TableCell'
import TableSortLabel from '@mui/material/TableSortLabel'
import TableContainer from '@mui/material/TableContainer'
import Paper from '@mui/material/Paper'
import Chip from '@mui/material/Chip'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Tooltip from '@mui/material/Tooltip'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import ToggleButton from '@mui/material/ToggleButton'
import type { GameTo50Entry, SlopeIterationStat, SlopeIterationStatByLane } from '../types/analysis'
import { ChampionIcon } from './ChampionIcon'
import { fmtLane, fmtPct, nullLastSortingFn, makeTierSortingFn } from '../utils/format'
import { ChipColor, SLOPE_TIER_CHIP_COLOR, GAMES_TO_50_STATUS_COLORS, SLOPE_TIER_ORDER } from '../utils/tiers'

function wrColor(val: number | null): string {
  if (val === null || val === undefined) return 'text.primary'
  const pct = val * 100
  if (pct < 48) return 'error.main'
  if (pct > 52) return 'success.main'
  return 'text.primary'
}

const COLUMN_TOOLTIPS: Record<string, string> = {
  slope_tier:       'How steep is the early learning curve? Easy Pickup = competent within a few games. Very Hard Pickup = steep penalty before basics are learned.',
  initial_wr:       'Win rate in the 5–25 games bracket. Your floor — the worst you should expect before learning the basics.',
  estimated_games:  'Estimated games until win rate crosses 50%. From the Easiest to Learn analysis.',
  peak_wr:          'Highest observed win rate across all mastery brackets. Your ceiling if you invest deeply.',
}

interface Props {
  data: SlopeIterationStat[]
  dataByLane?: SlopeIterationStatByLane[]
  g50Map?: Map<string, GameTo50Entry>
}

export function OffRoleView({ data, dataByLane, g50Map }: Props) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'initial_wr', desc: true },
  ])
  const [laneSel, setLaneSel] = useState<string>('ALL')

  const availableLanes = useMemo(
    () => [...new Set((dataByLane ?? []).map(r => r.lane))].sort(),
    [dataByLane]
  )

  const activeData: SlopeIterationStat[] = useMemo(() => {
    const rows = (laneSel !== 'ALL' && dataByLane)
      ? dataByLane.filter(r => r.lane === laneSel)
      : data
    return rows.filter(r => r.initial_wr != null)
  }, [laneSel, dataByLane, data])

  const columns = useMemo((): ColumnDef<SlopeIterationStat>[] => [
    {
      id: 'champion',
      header: 'Champion',
      accessorKey: 'champion',
      enableSorting: true,
      cell: ({ row }) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
          <ChampionIcon name={row.original.champion} />
          <Typography variant="body2" fontWeight={500} noWrap>
            {row.original.champion}
          </Typography>
        </Box>
      ),
    },
    {
      id: 'lane',
      header: 'Lane',
      accessorKey: 'most_common_lane',
      enableSorting: true,
      cell: info => fmtLane(info.getValue<string | null>()),
    },
    {
      id: 'slope_tier',
      header: 'Pickup',
      accessorKey: 'slope_tier',
      enableSorting: true,
      sortingFn: makeTierSortingFn(SLOPE_TIER_ORDER),
      cell: info => {
        const tier = info.getValue<string | null>()
        return tier ? (
          <Chip
            label={tier}
            color={(SLOPE_TIER_CHIP_COLOR[tier] ?? 'default') as ChipColor}
            size="small"
            variant="outlined"
            sx={{ fontSize: 11 }}
          />
        ) : <>—</>
      },
    },
    {
      id: 'initial_wr',
      header: 'Floor WR',
      accessorKey: 'initial_wr',
      enableSorting: true,
      cell: info => {
        const v = info.getValue<number | null>()
        return (
          <Typography variant="body2" component="span" color={wrColor(v)} fontFamily="monospace">
            {fmtPct(v)}
          </Typography>
        )
      },
    },
    {
      id: 'estimated_games',
      header: 'Est. Games to 50%',
      enableSorting: true,
      sortingFn: nullLastSortingFn,
      accessorFn: (row: SlopeIterationStat) => g50Map?.get(row.champion)?.estimated_games ?? null,
      cell: ({ row }) => {
        const entry = g50Map?.get(row.original.champion)
        if (!entry) return <span style={{ color: '#666' }}>—</span>
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {entry.estimated_games != null && (
              <Typography variant="body2" fontFamily="monospace">
                {entry.estimated_games.toLocaleString()}
              </Typography>
            )}
            {entry.status && (
              <Chip
                label={entry.status}
                size="small"
                variant="outlined"
                sx={{ fontSize: 10, color: GAMES_TO_50_STATUS_COLORS[entry.status] ?? 'text.secondary', borderColor: GAMES_TO_50_STATUS_COLORS[entry.status] ?? 'divider' }}
              />
            )}
          </Box>
        )
      },
    },
    {
      id: 'peak_wr',
      header: 'Peak WR',
      accessorKey: 'peak_wr',
      enableSorting: true,
      cell: info => {
        const v = info.getValue<number | null>()
        return (
          <Typography variant="body2" component="span" color={wrColor(v)} fontFamily="monospace">
            {fmtPct(v)}
          </Typography>
        )
      },
    },
  ], [g50Map])

  const table = useReactTable({
    data: activeData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <>
      {availableLanes.length > 1 && (
        <Box sx={{ px: { xs: 1, sm: 2 }, pt: 1.5, pb: 0.5, borderBottom: '1px solid', borderColor: 'divider' }}>
          <ToggleButtonGroup
            value={laneSel}
            exclusive
            size="small"
            onChange={(_, v) => v && setLaneSel(v)}
          >
            <ToggleButton value="ALL">All Lanes</ToggleButton>
            {availableLanes.map(l => (
              <ToggleButton key={l} value={l}>{fmtLane(l)}</ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>
      )}

      <Box sx={{ overflowX: 'auto', width: '100%' }}>
        <TableContainer component={Paper} elevation={0} sx={{ borderRadius: 0 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              {table.getHeaderGroups().map(hg => (
                <TableRow key={hg.id}>
                  <TableCell sx={{ width: 48, color: 'text.secondary', fontWeight: 600 }}>#</TableCell>
                  {hg.headers.map(header => {
                    const tooltip = COLUMN_TOOLTIPS[header.id]
                    const label = flexRender(header.column.columnDef.header, header.getContext())
                    const wrappedLabel = tooltip ? (
                      <Tooltip title={tooltip} placement="top" arrow>
                        <span>{label}</span>
                      </Tooltip>
                    ) : label

                    return (
                      <TableCell
                        key={header.id}
                        sortDirection={header.column.getIsSorted() || false}
                        sx={{ whiteSpace: 'nowrap', fontWeight: 600 }}
                      >
                        {header.column.getCanSort() ? (
                          <TableSortLabel
                            active={!!header.column.getIsSorted()}
                            direction={header.column.getIsSorted() || 'asc'}
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {wrappedLabel}
                          </TableSortLabel>
                        ) : (
                          wrappedLabel
                        )}
                      </TableCell>
                    )
                  })}
                </TableRow>
              ))}
            </TableHead>

            <TableBody>
              {table.getRowModel().rows.map((row, idx) => (
                <TableRow
                  key={row.id}
                  hover
                  sx={{ '&:nth-of-type(even)': { bgcolor: 'action.hover' } }}
                >
                  <TableCell sx={{ color: 'text.disabled', textAlign: 'right' }}>
                    {idx + 1}
                  </TableCell>
                  {row.getVisibleCells().map(cell => (
                    <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {table.getRowModel().rows.length === 0 && (
            <Box sx={{ py: 10, textAlign: 'center' }}>
              <Typography color="text.secondary">No champions match the current filters.</Typography>
            </Box>
          )}
        </TableContainer>
      </Box>
    </>
  )
}
