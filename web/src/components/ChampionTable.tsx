import { useState, useEffect } from 'react'
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
import type { ChampionStat, ViewMode } from '../types/analysis'
import { ChampionIcon } from './ChampionIcon'
import { fmtLane } from '../utils/format'
import {
  getEasiestToLearnCols,
  getBestToMasterCols,
  getAllStatsCols,
  getPabuEasiestToLearnCols,
  VIEW_CONFIGS,
} from '../utils/columns'

// ── Tier chip colors ──────────────────────────────────────────────────────────

type ChipColor = 'success' | 'warning' | 'error' | 'default' | 'info'

const LEARNING_TIER_COLOR: Record<string, ChipColor> = {
  'Safe Blind Pick': 'success',
  'Low Risk': 'success',
  'Moderate': 'warning',
  'High Risk': 'warning',
  'Avoid': 'error',
}

const MASTERY_TIER_COLOR: Record<string, ChipColor> = {
  'Exceptional Payoff': 'success',
  'High Payoff': 'success',
  'Moderate Payoff': 'warning',
  'Low Payoff': 'warning',
  'Not Worth Mastering': 'error',
}

const DIFFICULTY_COLOR: Record<string, ChipColor> = {
  'Instantly Viable': 'success',
  'Extremely Hard to Learn': 'error',
  'Never Viable': 'default',
}

const STATUS_COLOR: Record<string, ChipColor> = {
  'always above 50%': 'success',
  'crosses 50%': 'info',
  'never reaches 50%': 'error',
  'low data': 'default',
}

function TierChip({ label, colorMap }: { label: string; colorMap: Record<string, ChipColor> }) {
  return (
    <Chip
      label={label}
      color={colorMap[label] ?? 'default'}
      size="small"
      variant="outlined"
      sx={{ fontSize: 11 }}
    />
  )
}

// ── Champion cell ─────────────────────────────────────────────────────────────

function ChampionCell({ name }: { name: string }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
      <ChampionIcon name={name} />
      <Typography variant="body2" fontWeight={500} noWrap>
        {name}
      </Typography>
    </Box>
  )
}

// ── Generic sortable table ────────────────────────────────────────────────────

interface TableProps<T extends object> {
  data: T[]
  columns: ColumnDef<T>[]
  view: ViewMode
}

/**
 * Render a table cell.
 * - rawValue: the raw JS value from cell.getValue() (number, string, null, etc.)
 * - formattedNode: the React node returned by flexRender (already formatted string
 *   like "48.57%"). Never call String() on this — it may be a React element.
 */
function renderCell(colId: string, rawValue: unknown, formattedNode: React.ReactNode, row?: ChampionStat) {
  // Champion (icon + name) — rawValue is the champion name string
  if (colId === 'champion') {
    return <ChampionCell name={rawValue as string} />
  }

  // Lane display — rawValue is the raw lane key e.g. "TOP"
  if (colId === 'lane') {
    return <Typography variant="body2">{fmtLane(rawValue as string | null)}</Typography>
  }

  // Win-rate cells — colour from raw 0–1 value, display pre-formatted node
  if (['low_wr', 'medium_wr', 'high_wr', 'starting_winrate'].includes(colId)) {
    const raw = rawValue as number | null
    const pct = raw != null ? raw * 100 : null
    const color =
      pct == null  ? 'text.primary'
      : pct < 48   ? 'error.main'
      : pct > 52   ? 'success.main'
      : 'text.primary'

    const ciLower = colId === 'low_wr'    ? row?.low_wr_ci_lower
                  : colId === 'medium_wr' ? row?.medium_wr_ci_lower
                  : colId === 'high_wr'   ? row?.high_wr_ci_lower
                  : null
    const ciUpper = colId === 'low_wr'    ? row?.low_wr_ci_upper
                  : colId === 'medium_wr' ? row?.medium_wr_ci_upper
                  : colId === 'high_wr'   ? row?.high_wr_ci_upper
                  : null
    const ciTitle = ciLower != null && ciUpper != null
      ? `95% CI: [${(ciLower * 100).toFixed(1)}%, ${(ciUpper * 100).toFixed(1)}%]`
      : ''

    const inner = (
      <Typography variant="body2" component="span" color={color} fontFamily="monospace">
        {formattedNode}
      </Typography>
    )
    return ciTitle
      ? <Tooltip title={ciTitle} arrow placement="top"><span>{inner}</span></Tooltip>
      : inner
  }

  // Delta cells — colour from sign of raw value
  if (['low_delta', 'delta'].includes(colId)) {
    const raw = rawValue as number | null
    const color =
      raw == null  ? 'text.primary'
      : raw > 0    ? 'success.main'
      : raw < 0    ? 'error.main'
      : 'text.primary'
    return (
      <Typography variant="body2" component="span" color={color} fontFamily="monospace">
        {formattedNode}
      </Typography>
    )
  }

  // Tier / badge columns — rawValue is the raw tier string (or null)
  if (colId === 'learning_tier') {
    const str = rawValue as string | null
    return str ? <TierChip label={str} colorMap={LEARNING_TIER_COLOR} /> : <>—</>
  }
  if (colId === 'mastery_tier') {
    const str = rawValue as string | null
    return str ? <TierChip label={str} colorMap={MASTERY_TIER_COLOR} /> : <>—</>
  }
  if (colId === 'difficulty') {
    const str = rawValue as string | null
    return str ? <TierChip label={str} colorMap={DIFFICULTY_COLOR} /> : <>—</>
  }
  if (colId === 'status') {
    const str = rawValue as string | null
    return str ? <TierChip label={str} colorMap={STATUS_COLOR} /> : <>—</>
  }

  // Numeric mono columns — display pre-formatted node in monospace
  if (['low_ratio', 'high_ratio', 'low_games', 'medium_games', 'high_games',
       'learning_score', 'mastery_score', 'investment_score',
       'estimated_games', 'mastery_threshold'].includes(colId)) {
    return (
      <Typography variant="body2" component="span" fontFamily="monospace">
        {formattedNode}
      </Typography>
    )
  }

  // Default — return formattedNode directly (already a valid React node)
  return formattedNode
}

function SortableTable<T extends object>({ data, columns, view }: TableProps<T>) {
  const defaultSort = VIEW_CONFIGS[view].defaultSort
  const [sorting, setSorting] = useState<SortingState>([defaultSort])

  useEffect(() => {
    setSorting([VIEW_CONFIGS[view].defaultSort])
  }, [view])

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
              {row.getVisibleCells().map(cell => (
                <TableCell key={cell.id} sx={{ whiteSpace: 'nowrap' }}>
                  {renderCell(
                    cell.column.id,
                    cell.getValue(),
                    // formatted string from the column's cell function
                    flexRender(cell.column.columnDef.cell, cell.getContext()),
                    row.original as ChampionStat,
                  )}
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
  )
}

// ── Public typed wrappers ─────────────────────────────────────────────────────

interface ChampionTableProps {
  data: ChampionStat[]
  view: Exclude<ViewMode, 'mastery_curve' | 'pabu_mastery_curve'>
}

export function ChampionTable({ data, view }: ChampionTableProps) {
  const cols =
    view === 'easiest_to_learn'      ? getEasiestToLearnCols()
    : view === 'pabu_easiest_to_learn' ? getPabuEasiestToLearnCols()
    : view === 'best_to_master' || view === 'pabu_best_to_master' ? getBestToMasterCols()
    : getAllStatsCols()

  return <SortableTable data={data} columns={cols as ColumnDef<ChampionStat>[]} view={view} />
}
