import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type Row,
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
import { LineChart, Line, ReferenceLine } from 'recharts'
import type { MasteryChampionCurve, SlopeIterationStat } from '../types/analysis'
import { ChampionIcon } from './ChampionIcon'
import { fmtLane, fmtPct, fmtThreshold } from '../utils/format'

type ChipColor = 'success' | 'warning' | 'error' | 'default' | 'info'

const SLOPE_TIER_COLORS: Record<string, string> = {
  'Flat Curve':     '#66BB6A',
  'Gentle Slope':   '#FFA726',
  'Moderate Slope': '#EF6C00',
  'Steep Curve':    '#EF5350',
}

function SlopeSparkline({
  champion,
  slopeTier,
  masteryChampionCurves,
}: {
  champion: string
  slopeTier: string | null
  masteryChampionCurves: Record<string, MasteryChampionCurve>
}) {
  const curve = masteryChampionCurves[champion]
  if (!curve) return <span style={{ color: '#666' }}>—</span>

  const chartData = curve.intervals
    .filter(i => i.games >= 30)
    .map((i, idx) => ({ idx, wr: +(i.win_rate * 100).toFixed(1) }))

  if (chartData.length < 2) return <span style={{ color: '#666' }}>—</span>

  const lineColor = SLOPE_TIER_COLORS[slopeTier ?? ''] ?? '#90CAF9'

  return (
    <LineChart
      width={120}
      height={44}
      data={chartData}
      margin={{ top: 6, right: 4, bottom: 6, left: 4 }}
    >
      <ReferenceLine y={50} stroke="#555" strokeDasharray="2 2" strokeWidth={1} />
      <Line
        type="monotone"
        dataKey="wr"
        dot={false}
        strokeWidth={1.5}
        stroke={lineColor}
        isAnimationActive={false}
      />
    </LineChart>
  )
}

const SLOPE_TIER_COLOR: Record<string, ChipColor> = {
  'Flat Curve':     'success',
  'Gentle Slope':   'info',
  'Moderate Slope': 'warning',
  'Steep Curve':    'error',
}

function fmtSlope(val: number | null): string {
  if (val === null || val === undefined) return '—'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${val.toFixed(1)}pp`
}

function slopeColor(val: number | null): string {
  if (val === null || val === undefined) return 'text.primary'
  if (val < 2) return 'success.main'
  if (val > 8) return 'error.main'
  return 'text.primary'
}

function wrColor(val: number | null): string {
  if (val === null || val === undefined) return 'text.primary'
  const pct = val * 100
  if (pct < 48) return 'error.main'
  if (pct > 52) return 'success.main'
  return 'text.primary'
}

const nullLastSortingFn = <T extends object>(
  rowA: Row<T>,
  rowB: Row<T>,
  columnId: string,
): number => {
  const a = rowA.getValue<number | null>(columnId) ?? Infinity
  const b = rowB.getValue<number | null>(columnId) ?? Infinity
  return a - b
}

interface Props {
  data: SlopeIterationStat[]
  masteryChampionCurves?: Record<string, MasteryChampionCurve>
}

export function SlopeIterationsView({ data, masteryChampionCurves }: Props) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'inflection_games', desc: false },
  ])

  const columns = useMemo((): ColumnDef<SlopeIterationStat>[] => [
    {
      id: 'champion',
      header: 'Champion',
      accessorKey: 'champion',
      enableSorting: true,
      cell: info => info.getValue<string>(),
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
      header: 'Slope Tier',
      accessorKey: 'slope_tier',
      enableSorting: true,
      cell: info => info.getValue<string | null>() ?? '—',
    },
    {
      id: 'curve',
      header: 'Curve',
      enableSorting: false,
      cell: ({ row }) =>
        masteryChampionCurves ? (
          <SlopeSparkline
            champion={row.original.champion}
            slopeTier={row.original.slope_tier}
            masteryChampionCurves={masteryChampionCurves}
          />
        ) : null,
    },
    {
      id: 'total_slope',
      header: 'Total Slope',
      accessorKey: 'total_slope',
      enableSorting: true,
      cell: info => fmtSlope(info.getValue<number | null>()),
    },
    {
      id: 'inflection_games',
      header: 'Games to Competency',
      accessorKey: 'inflection_games',
      enableSorting: true,
      sortingFn: nullLastSortingFn,
      cell: info => {
        const v = info.getValue<number | null>()
        return v === null || v === undefined ? 'N/A' : v.toLocaleString()
      },
    },
    {
      id: 'inflection_mastery',
      header: 'Inflection Mastery',
      accessorKey: 'inflection_mastery',
      enableSorting: true,
      cell: info => fmtThreshold(info.getValue<number | null>()),
    },
    {
      id: 'initial_wr',
      header: 'Starting WR',
      accessorKey: 'initial_wr',
      enableSorting: true,
      cell: info => fmtPct(info.getValue<number | null>()),
    },
    {
      id: 'peak_wr',
      header: 'Peak WR',
      accessorKey: 'peak_wr',
      enableSorting: true,
      cell: info => fmtPct(info.getValue<number | null>()),
    },
    {
      id: 'valid_intervals',
      header: 'Intervals',
      accessorKey: 'valid_intervals',
      enableSorting: true,
      cell: info => {
        const v = info.getValue<number | null>()
        return v === null || v === undefined ? '—' : String(v)
      },
    },
  ], [masteryChampionCurves])

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <TableContainer component={Paper} elevation={0} sx={{ borderRadius: 0 }}>
      <Table size="small" stickyHeader>
        <TableHead>
          {table.getHeaderGroups().map(hg => (
            <TableRow key={hg.id}>
              <TableCell sx={{ width: 48, color: 'text.secondary', fontWeight: 600 }}>#</TableCell>
              {hg.headers.map(header => (
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
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </TableSortLabel>
                  ) : (
                    flexRender(header.column.columnDef.header, header.getContext())
                  )}
                </TableCell>
              ))}
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
              {row.getVisibleCells().map(cell => {
                const colId = cell.column.id
                const rawValue = cell.getValue()
                const formatted = flexRender(cell.column.columnDef.cell, cell.getContext())

                if (colId === 'champion') {
                  return (
                    <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
                        <ChampionIcon name={rawValue as string} />
                        <Typography variant="body2" fontWeight={500} noWrap>
                          {rawValue as string}
                        </Typography>
                      </Box>
                    </TableCell>
                  )
                }

                if (colId === 'slope_tier') {
                  const tier = rawValue as string | null
                  return (
                    <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                      {tier ? (
                        <Chip
                          label={tier}
                          color={SLOPE_TIER_COLOR[tier] ?? 'default'}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: 11 }}
                        />
                      ) : <>—</>}
                    </TableCell>
                  )
                }

                if (colId === 'total_slope') {
                  return (
                    <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                      <Typography
                        variant="body2"
                        component="span"
                        color={slopeColor(rawValue as number | null)}
                        fontFamily="monospace"
                      >
                        {formatted}
                      </Typography>
                    </TableCell>
                  )
                }

                if (colId === 'initial_wr' || colId === 'peak_wr') {
                  return (
                    <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                      <Typography
                        variant="body2"
                        component="span"
                        color={wrColor(rawValue as number | null)}
                        fontFamily="monospace"
                      >
                        {formatted}
                      </Typography>
                    </TableCell>
                  )
                }

                if (['inflection_games', 'inflection_mastery', 'valid_intervals'].includes(colId)) {
                  return (
                    <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                      <Typography variant="body2" component="span" fontFamily="monospace">
                        {formatted}
                      </Typography>
                    </TableCell>
                  )
                }

                return (
                  <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                    {formatted}
                  </TableCell>
                )
              })}
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
  )
}
