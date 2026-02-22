import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { useState, useEffect } from 'react'
import type { ChampionStat, GameTo50Entry, ViewMode } from '../types/analysis'
import { ChampionIcon } from './ChampionIcon'
import { fmtLane } from '../utils/format'
import {
  getEasiestToLearnCols,
  getBestToMasterCols,
  getBestInvestmentCols,
  getAllStatsCols,
  getDynamicEasiestCols,
  getDynamicMasterCols,
  getDynamicInvestmentCols,
  getGamesTo50Cols,
  VIEW_CONFIGS,
} from '../utils/columns'

// ── Tier badge ────────────────────────────────────────────────────────────────

const LEARNING_TIER_COLORS: Record<string, string> = {
  'Safe Blind Pick': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
  'Low Risk': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  'Moderate': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  'High Risk': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  'Avoid': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  'Instantly Viable': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
}

const MASTERY_TIER_COLORS: Record<string, string> = {
  'Exceptional Payoff': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
  'High Payoff': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  'Moderate Payoff': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  'Low Payoff': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  'Not Worth Mastering': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

const DIFFICULTY_COLORS: Record<string, string> = {
  'Instantly Viable': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
  'Extremely Hard to Learn': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  'Never Viable': 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
}

const STATUS_COLORS: Record<string, string> = {
  'always above 50%': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
  'crosses 50%': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  'never reaches 50%': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  'low data': 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
}

function Badge({ text, colorMap }: { text: string; colorMap: Record<string, string> }) {
  const cls = colorMap[text] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium whitespace-nowrap ${cls}`}>
      {text}
    </span>
  )
}

// ── WR cell with color ────────────────────────────────────────────────────────

function WrCell({ value }: { value: string }) {
  // parse the pct back to determine color
  const num = parseFloat(value)
  const color = isNaN(num)
    ? ''
    : num < 48
    ? 'text-red-600 dark:text-red-400'
    : num > 52
    ? 'text-emerald-600 dark:text-emerald-400'
    : 'text-gray-700 dark:text-gray-300'
  return <span className={`font-mono text-sm ${color}`}>{value}</span>
}

// ── Cell renderer dispatcher ──────────────────────────────────────────────────

function renderCell(colId: string, value: unknown) {
  const str = String(value ?? '—')

  if (['low_wr', 'medium_wr', 'high_wr', 'starting_winrate'].includes(colId)) {
    return <WrCell value={str} />
  }
  if (colId === 'learning_tier') {
    return str === '—' ? str : <Badge text={str} colorMap={LEARNING_TIER_COLORS} />
  }
  if (colId === 'mastery_tier') {
    return str === '—' ? str : <Badge text={str} colorMap={MASTERY_TIER_COLORS} />
  }
  if (colId === 'difficulty') {
    return str === '—' ? str : <Badge text={str} colorMap={DIFFICULTY_COLORS} />
  }
  if (colId === 'status') {
    return str === '—' ? str : <Badge text={str} colorMap={STATUS_COLORS} />
  }
  if (['low_delta', 'delta'].includes(colId)) {
    const cls = str.startsWith('+')
      ? 'text-emerald-600 dark:text-emerald-400 font-mono text-sm'
      : str.startsWith('-')
      ? 'text-red-600 dark:text-red-400 font-mono text-sm'
      : 'font-mono text-sm'
    return <span className={cls}>{str}</span>
  }
  if (['low_ratio', 'high_ratio'].includes(colId)) {
    return <span className="font-mono text-sm">{str}</span>
  }
  return str
}

// ── Champion cell (icon + name) ───────────────────────────────────────────────

function ChampionCell({ name, lane }: { name: string; lane?: string | null }) {
  return (
    <span className="flex items-center gap-2 min-w-0">
      <ChampionIcon name={name} />
      <span className="truncate font-medium text-gray-900 dark:text-gray-100">{name}</span>
      {lane && (
        <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0 hidden sm:inline">
          {fmtLane(lane)}
        </span>
      )}
    </span>
  )
}

// ── Main table ────────────────────────────────────────────────────────────────

interface Props<T extends object> {
  data: T[]
  columns: ColumnDef<T>[]
  view: ViewMode
  isG50?: boolean
}

function Table<T extends object>({ data, columns, view }: Props<T>) {
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
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-[49px] z-10 bg-gray-100 dark:bg-gray-800">
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id}>
              <th className="px-2 py-2 text-left font-semibold text-gray-600 dark:text-gray-400 w-10 select-none">
                #
              </th>
              {hg.headers.map(header => (
                <th
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  className={[
                    'px-3 py-2 text-left font-semibold text-gray-600 dark:text-gray-400 whitespace-nowrap select-none',
                    header.column.getCanSort() ? 'cursor-pointer hover:text-gray-900 dark:hover:text-gray-100' : '',
                  ].join(' ')}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {header.column.getIsSorted() === 'asc' && ' ↑'}
                  {header.column.getIsSorted() === 'desc' && ' ↓'}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row, idx) => (
            <tr
              key={row.id}
              className={[
                'border-b border-gray-100 dark:border-gray-800 hover:bg-blue-50 dark:hover:bg-gray-800 transition-colors',
                idx % 2 === 0 ? 'bg-white dark:bg-gray-900' : 'bg-gray-50 dark:bg-gray-850',
              ].join(' ')}
            >
              <td className="px-2 py-1.5 text-gray-400 dark:text-gray-600 text-right tabular-nums">
                {idx + 1}
              </td>
              {row.getVisibleCells().map(cell => {
                const colId = cell.column.id
                const rawValue = cell.getValue()

                // Special-case: champion column gets icon
                if (colId === 'champion') {
                  const champName = rawValue as string
                  // For G50 view the champion field accessor is 'champion_name'
                  return (
                    <td key={cell.id} className="px-3 py-1.5 min-w-[160px]">
                      <ChampionCell name={champName} />
                    </td>
                  )
                }

                return (
                  <td
                    key={cell.id}
                    className="px-3 py-1.5 whitespace-nowrap text-gray-700 dark:text-gray-300"
                  >
                    {renderCell(colId, rawValue)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {table.getRowModel().rows.length === 0 && (
        <div className="py-16 text-center text-gray-400 dark:text-gray-600">
          No champions match the current filters.
        </div>
      )}
    </div>
  )
}

// ── Typed wrappers ────────────────────────────────────────────────────────────

interface ChampionTableProps {
  data: ChampionStat[]
  view: Exclude<ViewMode, 'games_to_50'>
}

interface G50TableProps {
  data: GameTo50Entry[]
}

export function ChampionTable({ data, view }: ChampionTableProps) {
  const cols =
    view === 'easiest_to_learn'
      ? getEasiestToLearnCols()
      : view === 'best_to_master'
      ? getBestToMasterCols()
      : view === 'best_investment'
      ? getBestInvestmentCols()
      : view === 'dynamic_easiest'
      ? getDynamicEasiestCols()
      : view === 'dynamic_master'
      ? getDynamicMasterCols()
      : view === 'dynamic_investment'
      ? getDynamicInvestmentCols()
      : getAllStatsCols()

  return <Table data={data} columns={cols as ColumnDef<ChampionStat>[]} view={view} />
}

export function G50Table({ data }: G50TableProps) {
  return (
    <Table
      data={data}
      columns={getGamesTo50Cols() as ColumnDef<GameTo50Entry>[]}
      view="games_to_50"
      isG50
    />
  )
}
