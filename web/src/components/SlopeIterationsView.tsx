import React, { useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
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
import Tooltip from '@mui/material/Tooltip'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import ToggleButton from '@mui/material/ToggleButton'
import { LineChart, Line, ReferenceLine, YAxis, Tooltip as RechartsTooltip } from 'recharts'
import type { LaneCurve, MasteryChampionCurve, SlopeIterationStat, SlopeIterationStatByLane } from '../types/analysis'
import { ChampionIcon } from './ChampionIcon'
import { fmtLane, fmtPct } from '../utils/format'

type ChipColor = 'success' | 'warning' | 'error' | 'default' | 'info'

const SLOPE_TIER_COLORS: Record<string, string> = {
  'Easy Pickup':     '#66BB6A',
  'Mild Pickup':     '#FFA726',
  'Hard Pickup':     '#EF6C00',
  'Very Hard Pickup': '#EF5350',
}

function SlopeSparkline({
  champion,
  slopeTier,
  masteryChampionCurves,
  curveOverride,
  onClick,
}: {
  champion: string
  slopeTier: string | null
  masteryChampionCurves: Record<string, MasteryChampionCurve>
  curveOverride?: { intervals: MasteryChampionCurve['intervals'] } | null
  onClick?: () => void
}) {
  const [tooltipState, setTooltipState] = useState<{ x: number; y: number; d: { label: string; rawWr: number; games: number } } | null>(null)

  const curve = curveOverride ?? masteryChampionCurves[champion]
  if (!curve) return <span style={{ color: '#666' }}>—</span>

  const rawData = curve.intervals
    .filter(i => i.games >= 30 && i.min >= 3500)
    .map((i, idx) => ({
      idx,
      wr: +(i.win_rate * 100).toFixed(1),
      rawWr: +(i.win_rate * 100).toFixed(2),
      games: i.games,
      label: i.label,
    }))

  if (rawData.length < 2) return <span style={{ color: '#666' }}>—</span>

  const W = 3
  const chartData = rawData.map((d, i, arr) => {
    const lo = Math.max(0, i - Math.floor(W / 2))
    const hi = Math.min(arr.length - 1, i + Math.floor(W / 2))
    const avg = arr.slice(lo, hi + 1).reduce((s, x) => s + x.wr, 0) / (hi - lo + 1)
    return { ...d, wr: +avg.toFixed(2) }
  })

  const wrs = chartData.map(d => d.wr)
  const minWr = Math.min(...wrs)
  const maxWr = Math.max(...wrs)
  const pad = Math.max(0.5, (maxWr - minWr) * 0.2)
  const domain: [number, number] = [
    +Math.min(minWr - pad, 50).toFixed(1),
    +Math.max(maxWr + pad, 50).toFixed(1),
  ]

  const lineColor = SLOPE_TIER_COLORS[slopeTier ?? ''] ?? '#90CAF9'

  return (
    <>
      <Box
        onClick={onClick}
        sx={{ cursor: onClick ? 'pointer' : 'default', display: 'inline-block' }}
        title={onClick ? 'Click to open Mastery Curve' : undefined}
      >
        <LineChart
          width={120}
          height={44}
          data={chartData}
          margin={{ top: 6, right: 4, bottom: 6, left: 4 }}
          onMouseMove={(state, event) => {
            const idx = state.activeIndex
            if (idx !== undefined && idx !== null && chartData[idx as number]) {
              const d = chartData[idx as number]
              const e = event as React.MouseEvent
              setTooltipState({ x: e.clientX, y: e.clientY, d })
            } else {
              setTooltipState(null)
            }
          }}
          onMouseLeave={() => setTooltipState(null)}
        >
          <YAxis domain={domain} hide />
          <ReferenceLine y={50} stroke="#555" strokeDasharray="2 2" strokeWidth={1} />
          <RechartsTooltip content={() => null} />
          <Line
            type="monotone"
            dataKey="wr"
            dot={false}
            activeDot={{ r: 3, fill: lineColor, strokeWidth: 0 }}
            strokeWidth={1.5}
            stroke={lineColor}
            isAnimationActive={false}
          />
        </LineChart>
      </Box>
      {tooltipState && createPortal(
        <div style={{
          position: 'fixed',
          left: tooltipState.x + 12,
          top: tooltipState.y - 72,
          zIndex: 99999,
          background: '#1e1e1e',
          border: '1px solid #444',
          borderRadius: 4,
          padding: '4px 8px',
          fontSize: 11,
          lineHeight: 1.6,
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
        }}>
          <div style={{ fontWeight: 600 }}>{tooltipState.d.label}</div>
          <div>WR: {tooltipState.d.rawWr}%</div>
          <div style={{ color: '#aaa' }}>{tooltipState.d.games.toLocaleString()} games</div>
        </div>,
        document.body
      )}
    </>
  )
}

const SLOPE_TIER_COLOR: Record<string, ChipColor> = {
  'Easy Pickup':     'success',
  'Mild Pickup':     'info',
  'Hard Pickup':     'warning',
  'Very Hard Pickup': 'error',
}

const GROWTH_TYPE_COLOR: Record<string, ChipColor> = {
  'Plateau':   'default',
  'Gradual':   'info',
  'Continual': 'success',
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
  dataByLane?: SlopeIterationStatByLane[]
  masteryChampionCurvesByLane?: Record<string, Record<string, LaneCurve>> | null
  onChampionClick?: (champion: string, lane: string | null) => void
}

export function SlopeIterationsView({ data, masteryChampionCurves, dataByLane, masteryChampionCurvesByLane, onChampionClick }: Props) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'slope_tier', desc: false },
  ])
  const [laneSel, setLaneSel] = useState<string>('ALL')

  const availableLanes = useMemo(
    () => [...new Set((dataByLane ?? []).map(r => r.lane))].sort(),
    [dataByLane]
  )

  const activeData: SlopeIterationStat[] = useMemo(() => {
    if (laneSel !== 'ALL' && dataByLane) {
      return dataByLane.filter(r => r.lane === laneSel)
    }
    return data
  }, [laneSel, dataByLane, data])

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
      header: 'Pickup',
      accessorKey: 'slope_tier',
      enableSorting: true,
      cell: info => info.getValue<string | null>() ?? '—',
    },
    {
      id: 'growth_type',
      header: 'Growth',
      accessorKey: 'growth_type',
      enableSorting: true,
      cell: info => info.getValue<string | null>() ?? '—',
    },
    {
      id: 'curve',
      header: 'Curve',
      enableSorting: false,
      cell: ({ row }) => {
        if (!masteryChampionCurves) return null
        const rowLane = (row.original as SlopeIterationStatByLane).lane ?? null
        const curveOverride = rowLane && masteryChampionCurvesByLane?.[row.original.champion]?.[rowLane]
          ? masteryChampionCurvesByLane[row.original.champion][rowLane]
          : null
        return (
          <SlopeSparkline
            champion={row.original.champion}
            slopeTier={row.original.slope_tier}
            masteryChampionCurves={masteryChampionCurves}
            curveOverride={curveOverride}
            onClick={onChampionClick
              ? () => onChampionClick(row.original.champion, rowLane)
              : undefined}
          />
        )
      },
    },
    {
      id: 'early_slope',
      header: 'Early Slope',
      accessorKey: 'early_slope',
      enableSorting: true,
      sortingFn: nullLastSortingFn,
      cell: info => fmtSlope(info.getValue<number | null>()),
    },
    {
      id: 'late_slope',
      header: 'Late Slope',
      accessorKey: 'late_slope',
      enableSorting: true,
      sortingFn: nullLastSortingFn,
      cell: info => fmtSlope(info.getValue<number | null>()),
    },
    {
      id: 'total_slope',
      header: 'Total Slope',
      accessorKey: 'total_slope',
      enableSorting: true,
      cell: info => fmtSlope(info.getValue<number | null>()),
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
  ], [masteryChampionCurves, masteryChampionCurvesByLane, onChampionClick])

  const table = useReactTable({
    data: activeData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const COLUMN_TOOLTIPS: Record<string, string> = {
    slope_tier:         'Early-mastery difficulty. Based on win rate gain in the first 3 mastery brackets. A faded chip with "?" means the 95% confidence interval spans a tier boundary — treat the tier as approximate.',
    growth_type:        'Whether the champion keeps improving at high mastery. Plateau = WR levels off after competency. Gradual = slow continued gains. Continual = still growing significantly at 200+ games.',
    curve:              'Win rate progression across game brackets (5+ games only — matches the range used for all slope metrics). Color matches Pickup tier. Dashed line = 50% WR.',
    early_slope:        'Win rate gain across the first 3 mastery brackets (~5k–50k points). Drives the Pickup tier. When filtered to a specific role, slope uses games in that role only — but the mastery axis still represents total champion mastery (not role-specific). A 95% CI is computed from sample sizes — near a tier boundary, the chip shows a faded "?" indicator.',
    late_slope:         'Win rate gain across the last 3 mastery brackets (100k to end of available data). Positive = champion rewards deep mastery investment. Drives the Growth tier label.',
    total_slope:        'Total win rate gain from starting mastery to peak mastery (percentage points). Smoothed to reduce noise from low-sample brackets.',

    initial_wr:         'Win rate in the 5–25 games bracket — your baseline performance with minimal experience.',
    peak_wr:            'Highest observed win rate across all mastery brackets for this champion.',
    valid_intervals:    'Number of mastery brackets with sufficient data (≥ 200 games) used in this analysis.',
  }

  return (
    <>
    {availableLanes.length > 1 && (
      <Box sx={{ px: 2, pt: 1.5, pb: 0.5, borderBottom: '1px solid', borderColor: 'divider' }}>
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
        {laneSel !== 'ALL' && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
            Mastery axis = total champion mastery, not {fmtLane(laneSel)}-specific.
          </Typography>
        )}
      </Box>
    )}
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
                  const es = cell.row.original.early_slope
                  const ci = cell.row.original.early_slope_ci
                  const BOUNDARIES = [2, 5, 8]
                  const isUncertain = ci != null && es != null &&
                    BOUNDARIES.some(b => es - ci < b && es + ci > b)

                  // Estimate games per early bracket needed to narrow CI below the boundary gap.
                  // Formula: n ≥ 1.96² × 2 × 0.5 × 0.5 × 100² / distance² = 19208 / distance²
                  // Uses p=0.5 (worst case) and equal n in both boundary intervals.
                  let gamesNeededText = ''
                  if (isUncertain && es != null) {
                    const nearestBoundary = BOUNDARIES.reduce((prev, curr) =>
                      Math.abs(curr - es) < Math.abs(prev - es) ? curr : prev
                    )
                    const distance = Math.abs(es - nearestBoundary)
                    if (distance >= 0.05) {
                      const n = Math.ceil(19208 / (distance * distance))
                      gamesNeededText = ` (~${n.toLocaleString()} games per early bracket needed for confident assignment)`
                    }
                  }

                  return (
                    <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                      {tier ? (
                        <Tooltip
                          title={isUncertain ? `Tier boundary uncertain — 95% CI: ±${ci?.toFixed(1)}pp${gamesNeededText}` : ''}
                          placement="top"
                          arrow
                          disableHoverListener={!isUncertain}
                        >
                          <Chip
                            label={isUncertain ? `${tier} ?` : tier}
                            color={SLOPE_TIER_COLOR[tier] ?? 'default'}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: 11, opacity: isUncertain ? 0.6 : 1 }}
                          />
                        </Tooltip>
                      ) : <>—</>}
                    </TableCell>
                  )
                }

                if (colId === 'growth_type') {
                  const gt = rawValue as string | null
                  return (
                    <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                      {gt ? (
                        <Chip
                          label={gt}
                          color={GROWTH_TYPE_COLOR[gt] ?? 'default'}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: 11 }}
                        />
                      ) : <>—</>}
                    </TableCell>
                  )
                }

                if (colId === 'total_slope' || colId === 'early_slope' || colId === 'late_slope') {
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

                if (['valid_intervals'].includes(colId)) {
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
    </>
  )
}
