# Analytics Views Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two new view tabs (Off-Role Picks, Learning Profile scatter chart), enrich three existing tables with cross-joined slope fields, and split the single help modal into a User Guide and a Methodology reference.

**Architecture:** All new data is already in the JSON — no backend changes. Cross-joins happen via `Map` lookups in `App.tsx` and column factory functions. New components follow the exact patterns of `SlopeIterationsView.tsx` (table) and `MasteryCurveView.tsx` (chart). The dual modal split repurposes `HelpModal.tsx` as `MethodologyModal.tsx` and adds a new `UserGuideModal.tsx`.

**Tech Stack:** React 18, TypeScript, MUI v5, Recharts, @tanstack/react-table v8, Vite

**Build verification command (run after every task):** `cd web && npm run build`

---

### Task 1: Extend ViewMode + VIEW_CONFIGS

**Files:**
- Modify: `web/src/types/analysis.ts`
- Modify: `web/src/utils/columns.tsx`

**Context:** `ViewMode` is a union type. `VIEW_CONFIGS` is `Record<ViewMode, ViewConfig>` — TypeScript will error if any `ViewMode` value is missing from the record. Both must be updated together.

**Step 1: Add new values to ViewMode**

In `web/src/types/analysis.ts`, find the `ViewMode` export (line 150) and add two entries:

```ts
export type ViewMode =
  | 'easiest_to_learn'
  | 'best_to_master'
  | 'mastery_curve'
  | 'all_stats'
  | 'pabu_easiest_to_learn'
  | 'pabu_best_to_master'
  | 'pabu_mastery_curve'
  | 'slope_iterations'
  | 'off_role'
  | 'learning_profile'
```

**Step 2: Add VIEW_CONFIGS entries**

In `web/src/utils/columns.tsx`, find `VIEW_CONFIGS` (line 167) and add two entries inside the record:

```ts
  off_role: {
    label: 'Off-Role Picks',
    defaultSort: { id: 'initial_wr', desc: true },
  },
  learning_profile: {
    label: 'Learning Profile',
    defaultSort: { id: 'champion', desc: false },
  },
```

**Step 3: Build**

```bash
cd web && npm run build
```

Expected: build succeeds (TypeScript will catch any Record completeness errors).

**Step 4: Commit**

```bash
git add web/src/types/analysis.ts web/src/utils/columns.tsx
git commit -m "feat: add off_role and learning_profile to ViewMode"
```

---

### Task 2: Create shared tier utilities

**Files:**
- Create: `web/src/utils/tiers.ts`

**Context:** `SlopeIterationsView.tsx` currently defines `SLOPE_TIER_COLORS` (hex strings for charts) and `SLOPE_TIER_COLOR` (MUI chip color variants) locally. `ChampionTable.tsx` will need the MUI chip variant maps for the new `slope_tier` and `growth_type` columns. Extract them to a shared file so there's no duplication.

**Step 1: Create the file**

```ts
// web/src/utils/tiers.ts

type ChipColor = 'success' | 'warning' | 'error' | 'default' | 'info'

export const SLOPE_TIER_CHIP_COLOR: Record<string, ChipColor> = {
  'Easy Pickup':      'success',
  'Mild Pickup':      'info',
  'Hard Pickup':      'warning',
  'Very Hard Pickup': 'error',
}

export const SLOPE_TIER_LINE_COLOR: Record<string, string> = {
  'Easy Pickup':      '#66BB6A',
  'Mild Pickup':      '#FFA726',
  'Hard Pickup':      '#EF6C00',
  'Very Hard Pickup': '#EF5350',
}

export const GROWTH_TYPE_CHIP_COLOR: Record<string, ChipColor> = {
  'Plateau':   'default',
  'Gradual':   'info',
  'Continual': 'success',
}
```

**Step 2: Update SlopeIterationsView to import from shared file**

In `web/src/components/SlopeIterationsView.tsx`:

Remove the local definitions of `SLOPE_TIER_COLORS` (hex map used in sparklines) and `SLOPE_TIER_COLOR` (chip variant map). Replace with imports:

```ts
import { SLOPE_TIER_CHIP_COLOR, SLOPE_TIER_LINE_COLOR, GROWTH_TYPE_CHIP_COLOR } from '../utils/tiers'
```

Then update all references:
- `SLOPE_TIER_COLORS[slopeTier ?? '']` → `SLOPE_TIER_LINE_COLOR[slopeTier ?? '']`
- `SLOPE_TIER_COLOR[tier] ?? 'default'` → `SLOPE_TIER_CHIP_COLOR[tier] ?? 'default'`
- `GROWTH_TYPE_COLOR[gt] ?? 'default'` → `GROWTH_TYPE_CHIP_COLOR[gt] ?? 'default'`

**Step 3: Build**

```bash
cd web && npm run build
```

Expected: identical behavior, no new errors.

**Step 4: Commit**

```bash
git add web/src/utils/tiers.ts web/src/components/SlopeIterationsView.tsx
git commit -m "refactor: extract slope/growth tier color maps to shared utils/tiers.ts"
```

---

### Task 3: Enrich column factories + ChampionTable

**Files:**
- Modify: `web/src/utils/columns.tsx`
- Modify: `web/src/components/ChampionTable.tsx`

**Context:** `getEasiestToLearnCols()` and `getBestToMasterCols()` currently take no arguments. We add an optional `slopeMap` parameter. When present, extra columns are appended. `ChampionTable` gains a `slopeMap` prop and passes it through. `renderCell` gains handlers for the new colIds.

**Step 1: Update getEasiestToLearnCols in columns.tsx**

Add the import at the top of `columns.tsx`:
```ts
import type { SlopeIterationStat } from '../types/analysis'
import { SLOPE_TIER_CHIP_COLOR } from './tiers'
import Chip from '@mui/material/Chip'
```

Replace `getEasiestToLearnCols()` with:

```tsx
export function getEasiestToLearnCols(
  slopeMap?: Map<string, SlopeIterationStat>
): ColumnDef<ChampionStat>[] {
  const enriched: ColumnDef<ChampionStat>[] = slopeMap
    ? [
        {
          id: 'slope_tier',
          header: () => (
            <MuiTooltip title="How steep is the early win-rate curve? Easy Pickup = competent quickly. Very Hard Pickup = steep penalty before you learn the basics.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Pickup</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.slope_tier ?? null,
          cell: info => info.getValue<string | null>() ?? '—',
          enableSorting: true,
        },
        {
          id: 'initial_wr',
          header: () => (
            <MuiTooltip title="Win rate in the 5–25 games bracket. Your floor — the worst you should expect to perform before you've learned the basics.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Floor WR</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.initial_wr ?? null,
          cell: info => fmtPct(info.getValue<number | null>()),
          enableSorting: true,
        },
      ]
    : []

  return [
    championCol,
    laneCol,
    ...enriched,
    { id: 'status', header: 'Status', accessorKey: 'games_to_50_status', cell: info => info.getValue<string | null>() ?? '—', enableSorting: true },
    estGamesChampCol,
    { id: 'mastery_threshold', header: 'Mastery Threshold', accessorKey: 'mastery_threshold', cell: info => fmtThreshold(info.getValue<number | null>()), enableSorting: true },
    {
      id: 'starting_winrate',
      header: () => (
        <MuiTooltip title="Win rate in the lowest mastery interval (0–1,000 points) — approximates performance in a player's first 1–2 games on this champion">
          <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Starting WR</span>
        </MuiTooltip>
      ),
      accessorKey: 'starting_winrate',
      cell: info => fmtPct(info.getValue<number | null>()),
      enableSorting: true,
    },
  ]
}
```

**Step 2: Update getBestToMasterCols in columns.tsx**

Add `fmtGames` is already imported. Also need a helper:

```ts
function fmtSlope(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${val.toFixed(1)}pp`
}
```

Replace `getBestToMasterCols()` with:

```tsx
export function getBestToMasterCols(
  slopeMap?: Map<string, SlopeIterationStat>
): ColumnDef<ChampionStat>[] {
  const enriched: ColumnDef<ChampionStat>[] = slopeMap
    ? [
        {
          id: 'growth_type',
          header: () => (
            <MuiTooltip title="Does the champion keep rewarding mastery past the competency plateau? Continual = yes. Plateau = WR levels off after ~competency.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Growth</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.growth_type ?? null,
          cell: info => info.getValue<string | null>() ?? '—',
          enableSorting: true,
        },
        {
          id: 'late_slope',
          header: () => (
            <MuiTooltip title="Win rate gain across the last 3 mastery brackets (100k+ points). Positive = champion rewards deep mastery. Drives the Growth tier.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Late Slope</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.late_slope ?? null,
          cell: info => fmtSlope(info.getValue<number | null>()),
          enableSorting: true,
        },
        {
          id: 'inflection_games',
          header: () => (
            <MuiTooltip title="Estimated games until win rate reaches within 0.5pp of peak. Lower = you hit your ceiling faster.">
              <span style={{ cursor: 'help', borderBottom: '1px dotted currentColor' }}>Games to Plateau</span>
            </MuiTooltip>
          ),
          accessorFn: (row: ChampionStat) => slopeMap.get(row.champion)?.inflection_games ?? null,
          cell: info => {
            const v = info.getValue<number | null>()
            return v == null ? '—' : fmtGames(v)
          },
          sortingFn: nullLastSortingFn,
          enableSorting: true,
        },
      ]
    : []

  return [
    championCol,
    laneCol,
    masteryTierCol,
    { id: 'mastery_score', header: 'Mastery Score', accessorKey: 'mastery_score', cell: i => fmtScore(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_wr', header: 'High WR', accessorKey: 'high_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'medium_wr', header: 'Medium WR', accessorKey: 'medium_wr', cell: i => fmtPct(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_ratio', header: 'High Ratio', accessorKey: 'high_ratio', cell: i => fmtRatio(i.getValue<number | null>()), enableSorting: true },
    { id: 'delta', header: 'High Δ', accessorKey: 'delta', cell: i => fmtDelta(i.getValue<number | null>()), enableSorting: true },
    { id: 'high_games', header: 'High Games', accessorKey: 'high_games', cell: i => fmtGames(i.getValue<number | null>()), enableSorting: true },
    ...enriched,
  ]
}
```

**Step 3: Update ChampionTable to accept + pass slopeMap**

In `web/src/components/ChampionTable.tsx`:

Add import:
```ts
import type { SlopeIterationStat } from '../types/analysis'
import { SLOPE_TIER_CHIP_COLOR, GROWTH_TYPE_CHIP_COLOR } from '../utils/tiers'
```

Add new colId handlers to `renderCell` (add before the final `return formattedNode`):

```tsx
  if (colId === 'slope_tier') {
    const str = rawValue as string | null
    return str ? (
      <Chip
        label={str}
        color={SLOPE_TIER_CHIP_COLOR[str] ?? 'default'}
        size="small"
        variant="outlined"
        sx={{ fontSize: 11 }}
      />
    ) : <>—</>
  }

  if (colId === 'growth_type') {
    const str = rawValue as string | null
    return str ? (
      <Chip
        label={str}
        color={GROWTH_TYPE_CHIP_COLOR[str] ?? 'default'}
        size="small"
        variant="outlined"
        sx={{ fontSize: 11 }}
      />
    ) : <>—</>
  }

  if (colId === 'initial_wr') {
    const raw = rawValue as number | null
    const pct = raw != null ? raw * 100 : null
    const color =
      pct == null ? 'text.primary'
      : pct < 48  ? 'error.main'
      : pct > 52  ? 'success.main'
      : 'text.primary'
    return (
      <Typography variant="body2" component="span" color={color} fontFamily="monospace">
        {formattedNode}
      </Typography>
    )
  }

  if (colId === 'late_slope') {
    const raw = rawValue as number | null
    const color =
      raw == null ? 'text.primary'
      : raw > 0   ? 'success.main'
      : raw < -1  ? 'error.main'
      : 'text.primary'
    return (
      <Typography variant="body2" component="span" color={color} fontFamily="monospace">
        {formattedNode}
      </Typography>
    )
  }

  if (colId === 'inflection_games') {
    return (
      <Typography variant="body2" component="span" fontFamily="monospace">
        {formattedNode}
      </Typography>
    )
  }
```

Update `ChampionTableProps` and `ChampionTable`:

```tsx
interface ChampionTableProps {
  data: ChampionStat[]
  view: Exclude<ViewMode, 'mastery_curve' | 'pabu_mastery_curve' | 'off_role' | 'learning_profile'>
  slopeMap?: Map<string, SlopeIterationStat>
}

export function ChampionTable({ data, view, slopeMap }: ChampionTableProps) {
  const cols =
    view === 'easiest_to_learn'        ? getEasiestToLearnCols(slopeMap)
    : view === 'pabu_easiest_to_learn' ? getPabuEasiestToLearnCols()
    : view === 'best_to_master' || view === 'pabu_best_to_master' ? getBestToMasterCols(slopeMap)
    : getAllStatsCols()

  return <SortableTable data={data} columns={cols as ColumnDef<ChampionStat>[]} view={view} />
}
```

**Step 4: Build**

```bash
cd web && npm run build
```

Expected: succeeds. The new columns will be wired up in App.tsx in a later task.

**Step 5: Commit**

```bash
git add web/src/utils/columns.tsx web/src/components/ChampionTable.tsx
git commit -m "feat: enrich easiest_to_learn + best_to_master columns with slope data"
```

---

### Task 4: Enrich SlopeIterationsView with Est. Games to 50%

**Files:**
- Modify: `web/src/components/SlopeIterationsView.tsx`

**Context:** `SlopeIterationsView` already has all slope fields. We add one new column: `estimated_games` from the `games_to_50` data, looked up via a `g50Map` prop.

**Step 1: Add g50Map prop**

In `web/src/components/SlopeIterationsView.tsx`, add to the `Props` interface:

```ts
import type { GameTo50Entry, LaneCurve, MasteryChampionCurve, SlopeIterationStat, SlopeIterationStatByLane } from '../types/analysis'

interface Props {
  data: SlopeIterationStat[]
  masteryChampionCurves?: Record<string, MasteryChampionCurve>
  dataByLane?: SlopeIterationStatByLane[]
  masteryChampionCurvesByLane?: Record<string, Record<string, LaneCurve>> | null
  onChampionClick?: (champion: string, lane: string | null) => void
  g50Map?: Map<string, GameTo50Entry>
}
```

Update the function signature to destructure `g50Map`.

**Step 2: Add the new column definition**

Inside the `columns` useMemo (add after `valid_intervals`, before the closing `]`):

```ts
    {
      id: 'estimated_games',
      header: () => (
        <Tooltip title="Estimated games until win rate crosses 50%. From the Easiest to Learn analysis." placement="top" arrow>
          <span>Est. Games to 50%</span>
        </Tooltip>
      ),
      enableSorting: true,
      sortingFn: nullLastSortingFn,
      accessorFn: (row: SlopeIterationStat) => {
        const entry = g50Map?.get(row.champion)
        return entry?.estimated_games ?? null
      },
      cell: ({ row }) => {
        const entry = g50Map?.get(row.original.champion)
        if (!entry) return <span style={{ color: '#666' }}>—</span>
        const games = entry.estimated_games
        const status = entry.status
        const statusColors: Record<string, string> = {
          'always above 50%': '#66BB6A',
          'never reaches 50%': '#EF5350',
          'crosses 50%': '#90CAF9',
          'low data': '#888',
        }
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {games != null && (
              <Typography variant="body2" fontFamily="monospace">
                {games.toLocaleString()}
              </Typography>
            )}
            {status && (
              <Chip
                label={status}
                size="small"
                variant="outlined"
                sx={{ fontSize: 10, color: statusColors[status] ?? 'text.secondary', borderColor: statusColors[status] ?? 'divider' }}
              />
            )}
          </Box>
        )
      },
    },
```

Also add `g50Map` to the `useMemo` dependency array for columns.

**Step 3: Build**

```bash
cd web && npm run build
```

**Step 4: Commit**

```bash
git add web/src/components/SlopeIterationsView.tsx
git commit -m "feat: add Est. Games to 50% column to SlopeIterationsView"
```

---

### Task 5: Create OffRoleView component

**Files:**
- Create: `web/src/components/OffRoleView.tsx`

**Context:** A new table view sourced from `SlopeIterationStat[]` sorted by `initial_wr` desc. Shows the six columns from the design: Champion, Lane, Pickup, Floor WR, Est. Games to 50%, Peak WR. Lane toggle if lane data is available.

**Step 1: Create the file**

```tsx
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
import { fmtLane, fmtPct } from '../utils/format'
import { SLOPE_TIER_CHIP_COLOR } from '../utils/tiers'

type ChipColor = 'success' | 'warning' | 'error' | 'default' | 'info'

const STATUS_COLORS: Record<string, string> = {
  'always above 50%': '#66BB6A',
  'never reaches 50%': '#EF5350',
  'crosses 50%': '#90CAF9',
  'low data': '#888',
}

function wrColor(val: number | null): string {
  if (val === null || val === undefined) return 'text.primary'
  const pct = val * 100
  if (pct < 48) return 'error.main'
  if (pct > 52) return 'success.main'
  return 'text.primary'
}

const nullLastSortingFn = <T extends object>(
  rowA: import('@tanstack/react-table').Row<T>,
  rowB: import('@tanstack/react-table').Row<T>,
  columnId: string,
): number => {
  const a = rowA.getValue<number | null>(columnId) ?? Infinity
  const b = rowB.getValue<number | null>(columnId) ?? Infinity
  return a - b
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
      header: () => (
        <Tooltip title="How steep is the early learning curve? Easy Pickup = competent within a few games." placement="top" arrow>
          <span>Pickup</span>
        </Tooltip>
      ),
      accessorKey: 'slope_tier',
      enableSorting: true,
      cell: info => {
        const tier = info.getValue<string | null>()
        return tier ? (
          <Chip
            label={tier}
            color={SLOPE_TIER_CHIP_COLOR[tier] ?? 'default' as ChipColor}
            size="small"
            variant="outlined"
            sx={{ fontSize: 11 }}
          />
        ) : <>—</>
      },
    },
    {
      id: 'initial_wr',
      header: () => (
        <Tooltip title="Win rate in the 5–25 games bracket. Your floor — the worst you should expect to perform before learning the basics." placement="top" arrow>
          <span>Floor WR</span>
        </Tooltip>
      ),
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
      header: () => (
        <Tooltip title="Estimated games until win rate crosses 50%." placement="top" arrow>
          <span>Est. Games to 50%</span>
        </Tooltip>
      ),
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
                sx={{ fontSize: 10, color: STATUS_COLORS[entry.status] ?? 'text.secondary', borderColor: STATUS_COLORS[entry.status] ?? 'divider' }}
              />
            )}
          </Box>
        )
      },
    },
    {
      id: 'peak_wr',
      header: () => (
        <Tooltip title="Highest observed win rate across all mastery brackets. Your ceiling if you invest." placement="top" arrow>
          <span>Peak WR</span>
        </Tooltip>
      ),
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
```

**Step 2: Build**

```bash
cd web && npm run build
```

**Step 3: Commit**

```bash
git add web/src/components/OffRoleView.tsx
git commit -m "feat: add OffRoleView component for off-role champion recommendations"
```

---

### Task 6: Create LearningProfileChart component

**Files:**
- Create: `web/src/components/LearningProfileChart.tsx`

**Context:** A Recharts `ScatterChart` with X = `inflection_games` and Y = `(peak_wr - initial_wr) * 100` (pp). Champions are grouped by `slope_tier` so each tier gets its own `<Scatter>` element with the correct color. Quadrant reference lines divide the chart at median X and 3pp Y. Clicking a dot navigates to the mastery curve.

**Step 1: Create the file**

```tsx
// web/src/components/LearningProfileChart.tsx
import { useMemo, useState } from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import type { SlopeIterationStat } from '../types/analysis'
import { SLOPE_TIER_LINE_COLOR } from '../utils/tiers'

interface ProfileDatum {
  x: number           // inflection_games
  y: number           // (peak_wr - initial_wr) * 100 in pp
  champion: string
  slope_tier: string | null
  medium_games: number
  initial_wr: number
  peak_wr: number
  growth_type: string | null
}

interface Props {
  data: SlopeIterationStat[]
  mediumGamesMap: Map<string, number>
  onChampionClick?: (champion: string, lane: string | null) => void
}

const TIER_ORDER = ['Easy Pickup', 'Mild Pickup', 'Hard Pickup', 'Very Hard Pickup']
const FALLBACK_COLOR = '#90CAF9'

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ProfileDatum }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <Box sx={{
      bgcolor: 'background.paper',
      border: '1px solid',
      borderColor: 'divider',
      p: 1.5,
      borderRadius: 1,
      minWidth: 180,
    }}>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>{d.champion}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ fontSize: 11 }}>
        {d.slope_tier ?? '—'} · {d.growth_type ?? '—'}
      </Typography>
      <Typography variant="body2" fontFamily="monospace" sx={{ mt: 0.5 }}>
        Games to plateau: {d.x.toLocaleString()}
      </Typography>
      <Typography variant="body2" fontFamily="monospace">
        WR gain: +{d.y.toFixed(1)}pp
      </Typography>
      <Typography variant="body2" fontFamily="monospace" color="text.secondary" sx={{ fontSize: 11 }}>
        Floor WR: {(d.initial_wr * 100).toFixed(1)}% → Peak: {(d.peak_wr * 100).toFixed(1)}%
      </Typography>
    </Box>
  )
}

export function LearningProfileChart({ data, mediumGamesMap, onChampionClick }: Props) {
  const [hoveredChamp, setHoveredChamp] = useState<string | null>(null)

  const profileData = useMemo((): ProfileDatum[] => {
    return data
      .filter(s => s.inflection_games != null && s.peak_wr != null && s.initial_wr != null)
      .map(s => ({
        x: s.inflection_games!,
        y: +((s.peak_wr! - s.initial_wr!) * 100).toFixed(2),
        champion: s.champion,
        slope_tier: s.slope_tier,
        medium_games: mediumGamesMap.get(s.champion) ?? 0,
        initial_wr: s.initial_wr!,
        peak_wr: s.peak_wr!,
        growth_type: s.growth_type,
      }))
  }, [data, mediumGamesMap])

  // Median X for quadrant divider
  const medianX = useMemo(() => {
    const xs = profileData.map(d => d.x).sort((a, b) => a - b)
    if (xs.length === 0) return 100
    const mid = Math.floor(xs.length / 2)
    return xs.length % 2 === 0 ? (xs[mid - 1] + xs[mid]) / 2 : xs[mid]
  }, [profileData])

  const QUADRANT_Y = 3 // pp threshold for "meaningful WR gain"

  // Group by slope_tier for separate Scatter elements (each gets a single color)
  const byTier = useMemo(() => {
    const map = new Map<string, ProfileDatum[]>()
    for (const d of profileData) {
      const key = d.slope_tier ?? 'Unknown'
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(d)
    }
    return map
  }, [profileData])

  const tiers = [...byTier.keys()].sort(
    (a, b) => TIER_ORDER.indexOf(a) - TIER_ORDER.indexOf(b)
  )

  const CustomDot = (props: { cx?: number; cy?: number; payload?: ProfileDatum }) => {
    const { cx, cy, payload } = props
    if (cx == null || cy == null || !payload) return null
    // Scale dot radius 3–8 based on medium_games (log scale feels better)
    const maxGames = Math.max(...profileData.map(d => d.medium_games), 1)
    const r = 3 + 5 * (Math.log1p(payload.medium_games) / Math.log1p(maxGames))
    const isHovered = hoveredChamp === payload.champion
    return (
      <circle
        cx={cx}
        cy={cy}
        r={isHovered ? r + 2 : r}
        fill={SLOPE_TIER_LINE_COLOR[payload.slope_tier ?? ''] ?? FALLBACK_COLOR}
        fillOpacity={0.8}
        stroke={isHovered ? '#fff' : 'none'}
        strokeWidth={1.5}
        style={{ cursor: onChampionClick ? 'pointer' : 'default' }}
        onMouseEnter={() => setHoveredChamp(payload.champion)}
        onMouseLeave={() => setHoveredChamp(null)}
        onClick={() => onChampionClick?.(payload.champion, null)}
      />
    )
  }

  const QUADRANT_LABELS = [
    { x1: 0, x2: medianX, y1: QUADRANT_Y, y2: 25, label: 'Pick up & commit', position: 'insideTopLeft' as const },
    { x1: medianX, x2: 9999, y1: QUADRANT_Y, y2: 25, label: 'Deep investment', position: 'insideTopRight' as const },
    { x1: 0, x2: medianX, y1: -5, y2: QUADRANT_Y, label: 'Off-role safe', position: 'insideBottomLeft' as const },
    { x1: medianX, x2: 9999, y1: -5, y2: QUADRANT_Y, label: 'Avoid', position: 'insideBottomRight' as const },
  ]

  if (profileData.length === 0) {
    return (
      <Box sx={{ py: 10, textAlign: 'center' }}>
        <Typography color="text.secondary">Not enough data to render chart.</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ p: { xs: 1, sm: 2 }, width: '100%' }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        <strong>X:</strong> Games until win rate plateaus (lower = faster to learn) &nbsp;·&nbsp;
        <strong>Y:</strong> Total WR gain floor→peak (higher = more mastery reward) &nbsp;·&nbsp;
        Dot size = sample size
      </Typography>
      <ResponsiveContainer width="100%" height={520}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="x"
            type="number"
            name="Games to Plateau"
            label={{ value: 'Games to Plateau', position: 'insideBottom', offset: -10 }}
            tickFormatter={v => v.toLocaleString()}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="WR Gain (pp)"
            label={{ value: 'WR Gain (pp)', angle: -90, position: 'insideLeft', offset: 10 }}
          />
          <RechartsTooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
          <Legend verticalAlign="top" />

          {/* Quadrant backgrounds */}
          {QUADRANT_LABELS.map(q => (
            <ReferenceArea
              key={q.label}
              x1={q.x1}
              x2={q.x2}
              y1={q.y1}
              y2={q.y2}
              fill="transparent"
              label={{
                value: q.label,
                position: q.position,
                style: { fontSize: 11, fill: '#888', fontStyle: 'italic' },
              }}
            />
          ))}

          {/* Quadrant dividers */}
          <ReferenceLine
            x={medianX}
            stroke="#555"
            strokeDasharray="6 3"
            label={{ value: `median (${Math.round(medianX)} games)`, position: 'insideTopRight', style: { fontSize: 10, fill: '#666' } }}
          />
          <ReferenceLine
            y={QUADRANT_Y}
            stroke="#555"
            strokeDasharray="6 3"
            label={{ value: `${QUADRANT_Y}pp`, position: 'insideTopLeft', style: { fontSize: 10, fill: '#666' } }}
          />

          {/* One Scatter per slope tier */}
          {tiers.map(tier => (
            <Scatter
              key={tier}
              name={tier}
              data={byTier.get(tier)}
              fill={SLOPE_TIER_LINE_COLOR[tier] ?? FALLBACK_COLOR}
              shape={<CustomDot />}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </Box>
  )
}
```

**Step 2: Build**

```bash
cd web && npm run build
```

**Step 3: Commit**

```bash
git add web/src/components/LearningProfileChart.tsx
git commit -m "feat: add LearningProfileChart scatter chart for Q4/Q5 analysis"
```

---

### Task 7: Create UserGuideModal

**Files:**
- Create: `web/src/components/UserGuideModal.tsx`

**Context:** Practical, goal-first content explaining how to use the site to answer the 5 analytical questions. Mirrors the structure of `HelpModal.tsx` (same MUI Dialog pattern, same `Section`/`P` helpers).

**Step 1: Create the file**

```tsx
// web/src/components/UserGuideModal.tsx
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'

interface Props {
  open: boolean
  onClose: () => void
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom fontWeight="bold">
        {title}
      </Typography>
      {children}
    </Box>
  )
}

function P({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="body2" sx={{ mb: 1, display: 'block' }}>
      {children}
    </Typography>
  )
}

function Goal({ question, answer }: { question: string; answer: React.ReactNode }) {
  return (
    <Box sx={{ mb: 2, pl: 1.5, borderLeft: '3px solid', borderColor: 'primary.main' }}>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
        {question}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {answer}
      </Typography>
    </Box>
  )
}

export function UserGuideModal({ open, onClose }: Props) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth scroll="paper">
      <DialogTitle>User Guide</DialogTitle>

      <DialogContent dividers>
        <Section title="What This Dashboard Shows">
          <P>
            This dashboard analyzes how champion mastery affects win rate in Emerald+ ranked solo
            queue. The core question: <em>does playing more games on a champion actually make you
            better?</em> — and if so, how quickly, and by how much?
          </P>
          <P>
            All views are interactive — click column headers to sort, use the lane filter to isolate
            a role, and search by champion name.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Finding the Right Champion for Your Goal">
          <Goal
            question="What champions are the easiest to learn?"
            answer={
              <>
                Go to <strong>Easiest to Learn</strong>. Sort by <strong>Floor WR</strong> descending
                to find champions where even first-time players perform reasonably well. Look for a
                green <strong>Easy Pickup</strong> chip — these have the flattest early learning
                curve. The <strong>Est. Games</strong> column shows how quickly you'll cross 50% WR.
              </>
            }
          />
          <Goal
            question="Which champions reward consistent play and mastery investment?"
            answer={
              <>
                Go to <strong>Best to Master</strong>. Sort by <strong>Mastery Score</strong> (default).
                Look for a <strong>Continual</strong> growth chip — these champions keep improving
                at high mastery. The <strong>Late Slope</strong> column shows WR gain in the 100k+
                bracket. <strong>Games to Plateau</strong> tells you how long until you hit your ceiling.
              </>
            }
          />
          <Goal
            question="What should I play when off-roled with few games to invest?"
            answer={
              <>
                Go to <strong>Off-Role Picks</strong>. This is sorted by <strong>Floor WR</strong>
                by default — champions where you perform best with minimal experience. Filter by your
                off-role lane. Prioritize champions with a green <strong>Easy Pickup</strong> chip
                and a low <strong>Est. Games to 50%</strong>.
              </>
            }
          />
          <Goal
            question="How many games do I need before I start to matter?"
            answer={
              <>
                Check <strong>Slope Iterations</strong> and sort by <strong>Inflection Games</strong>
                (ascending). This is the estimated number of games until you reach near-peak performance.
                For a visual overview, open <strong>Learning Profile</strong> — the X axis shows
                games to plateau across all champions. Champions on the left side plateau quickly.
              </>
            }
          />
          <Goal
            question="When should I stop grinding one champion and diversify?"
            answer={
              <>
                Open <strong>Learning Profile</strong>. The Y axis shows total WR gain from floor
                to peak. Champions in the bottom half have a low ceiling — once you've hit it
                (check <strong>Games to Plateau</strong> in Slope Iterations), your time is better
                spent elsewhere. Champions with a <strong>Plateau</strong> growth chip have already
                leveled off.
              </>
            }
          />
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Understanding the Learning Profile Chart">
          <P>
            The <strong>Learning Profile</strong> chart plots every champion on two axes:
          </P>
          <P>
            <strong>X axis (Games to Plateau):</strong> How many games until your win rate stops
            improving. Lower = faster to unlock the champion's potential.
          </P>
          <P>
            <strong>Y axis (WR Gain pp):</strong> The total win-rate gain from your worst games to
            your best games (floor → peak). Higher = mastery matters more on this champion.
          </P>
          <P>
            The four quadrants each tell a different story:
          </P>
          <Box sx={{ pl: 2, mb: 1 }}>
            <P><strong>Top-left (Pick up &amp; commit):</strong> Fast to learn, high ceiling. Best all-round investment.</P>
            <P><strong>Top-right (Deep investment):</strong> Takes many games, but keeps rewarding mastery.</P>
            <P><strong>Bottom-left (Off-role safe):</strong> Competent quickly, won't improve much — ideal for off-role.</P>
            <P><strong>Bottom-right (Avoid):</strong> Slow plateau, low gain — not worth the time unless you enjoy the champion.</P>
          </Box>
          <P>
            Dot size reflects sample size — larger dots = more data = more confidence in the result.
            Click any dot to open the Mastery Curve for that champion.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="ELO Filter">
          <P>
            Use the <strong>Emerald+ / Diamond+ / Diamond 2+</strong> toggle in the header to filter
            the dataset. Emerald+ has the most data (best statistical power). Diamond 2+ is the
            smallest, highest-elo sample — useful for checking whether patterns hold at the top of
            the ladder.
          </P>
          <P>
            Higher filters will show more "low data" cells for rare champions, since fewer players
            have accumulated high mastery on niche picks at those ranks.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Lane Filter">
          <P>
            The lane filter restricts all tables to champions played in that role. For flex picks
            (champions played across multiple roles), the per-lane stats reflect only games played
            in the selected role.
          </P>
          <P>
            <strong>Note:</strong> The mastery axis in per-lane views always reflects{' '}
            <em>total champion mastery</em>, not role-specific mastery. Riot's API does not provide
            per-role mastery breakpoints. This means a Lux main who mostly plays Support will appear
            with the same mastery axis whether you're in the Support or Mid filter.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Reading the Tables">
          <P>
            <strong>Color coding:</strong> Win rate cells turn green when {'>'}52% and red when {'<'}48%.
          </P>
          <P>
            <strong>Sorting:</strong> Click any column header once to sort ascending, again for
            descending. Each view has a sensible default sort.
          </P>
          <P>
            <strong>"low data":</strong> Fewer than 100 games exist in that bucket. Scores that
            depend on low-data cells are omitted from rankings.
          </P>
          <P>
            <strong>Confidence intervals:</strong> Hover over Low WR, Medium WR, or High WR cells
            in the All Stats view to see the 95% Wilson confidence interval. Wider CI = smaller
            sample size = less certainty.
          </P>
          <P>
            <strong>Include rare picks:</strong> Uncheck this to show champions with very low play
            rates. These have small samples and can produce unreliable statistics.
          </P>
        </Section>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  )
}
```

**Step 2: Build**

```bash
cd web && npm run build
```

**Step 3: Commit**

```bash
git add web/src/components/UserGuideModal.tsx
git commit -m "feat: add UserGuideModal with goal-oriented usage guidance"
```

---

### Task 8: Rename HelpModal → MethodologyModal and update content

**Files:**
- Create: `web/src/components/MethodologyModal.tsx` (copy + rename)
- Delete: `web/src/components/HelpModal.tsx` (after updating all imports)

**Context:** The existing `HelpModal.tsx` content stays nearly identical — it's already the technical reference. We rename the export and file, then add new entries for Off-Role Picks and Learning Profile.

**Step 1: Create MethodologyModal.tsx**

Copy the entire contents of `web/src/components/HelpModal.tsx` into `web/src/components/MethodologyModal.tsx`. Make these changes:

1. Change `export function HelpModal` → `export function MethodologyModal`
2. Change `interface Props` name stays the same (it's local)
3. Change `<DialogTitle>About This Study</DialogTitle>` → `<DialogTitle>Technical Methodology</DialogTitle>`
4. In the **Views** section, add entries for the two new views before the closing `</Section>`:

```tsx
          <P>
            <strong>Off-Role Picks</strong> — Champions ranked by floor win rate (WR in the 5–25
            games bracket). Use this view to find champions that perform decently even with minimal
            experience — ideal when you're off-roled and can't invest many games. Filter by your
            off-role lane. The <strong>Est. Games to 50%</strong> column joins data from the
            Easiest to Learn analysis.
          </P>
          <P>
            <strong>Learning Profile</strong> — A scatter chart plotting all champions on two axes:
            X = games until win rate plateaus (inflection games), Y = total win-rate gain from floor
            to peak (pp). Four labeled quadrants help identify champions worth investing in vs.
            those better suited to off-role play or avoidance. Dot size scales with sample size.
            Click a dot to open the Mastery Curve for that champion.
          </P>
```

5. In the **Slope Iterations** section, add a note about the new column:

```tsx
          <P>
            <strong>Est. Games to 50%</strong> — Cross-joined from the Easiest to Learn analysis.
            Estimates how many games a player needs to cross 50% win rate on the champion. Champions
            already above 50% at low mastery show "always above 50%".
          </P>
```

**Step 2: Delete HelpModal.tsx**

```bash
rm web/src/components/HelpModal.tsx
```

**Step 3: Build**

```bash
cd web && npm run build
```

TypeScript will error on any remaining imports of `HelpModal`. Fix them now (Header.tsx will be updated in the next task).

**Step 4: Commit**

```bash
git add web/src/components/MethodologyModal.tsx
git rm web/src/components/HelpModal.tsx
git commit -m "feat: rename HelpModal to MethodologyModal and add new view entries"
```

---

### Task 9: Update Header with dual modal buttons

**Files:**
- Modify: `web/src/components/Header.tsx`

**Context:** Replace the single `HelpOutlineIcon` button with two buttons: `MenuBookIcon` (User Guide) and `ScienceIcon` (Methodology). Both icons are in `@mui/icons-material` which is already installed.

**Step 1: Update imports**

Replace:
```ts
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import { HelpModal } from './HelpModal'
```

With:
```ts
import MenuBookIcon from '@mui/icons-material/MenuBook'
import ScienceIcon from '@mui/icons-material/Science'
import { UserGuideModal } from './UserGuideModal'
import { MethodologyModal } from './MethodologyModal'
```

**Step 2: Update state**

Replace `const [helpOpen, setHelpOpen] = useState(false)` with:

```ts
const [guideOpen, setGuideOpen] = useState(false)
const [methodologyOpen, setMethodologyOpen] = useState(false)
```

**Step 3: Replace the single button with two buttons**

Replace the block:
```tsx
          <Tooltip title="Help & methodology">
            <IconButton onClick={() => setHelpOpen(true)} size="small">
              <HelpOutlineIcon />
            </IconButton>
          </Tooltip>
```

With:
```tsx
          <Tooltip title="User Guide">
            <IconButton onClick={() => setGuideOpen(true)} size="small">
              <MenuBookIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Technical Methodology">
            <IconButton onClick={() => setMethodologyOpen(true)} size="small">
              <ScienceIcon />
            </IconButton>
          </Tooltip>
```

**Step 4: Replace the modal render**

Replace:
```tsx
      <HelpModal open={helpOpen} onClose={() => setHelpOpen(false)} />
```

With:
```tsx
      <UserGuideModal open={guideOpen} onClose={() => setGuideOpen(false)} />
      <MethodologyModal open={methodologyOpen} onClose={() => setMethodologyOpen(false)} />
```

**Step 5: Build**

```bash
cd web && npm run build
```

**Step 6: Commit**

```bash
git add web/src/components/Header.tsx
git commit -m "feat: split help button into User Guide + Methodology modals"
```

---

### Task 10: Update TableControls with new view options

**Files:**
- Modify: `web/src/components/TableControls.tsx`

**Context:** `VIEW_OPTIONS` drives the main toggle button group. Add `off_role` to the main group and `learning_profile` to the main group (it's a chart view like `mastery_curve`). Also add `off_role` to the rare picks filter condition.

**Step 1: Add to VIEW_OPTIONS**

In `VIEW_OPTIONS`, add after `slope_iterations`:

```ts
const VIEW_OPTIONS: { value: ViewMode; label: string }[] = [
  { value: 'easiest_to_learn', label: 'Easiest to Learn' },
  { value: 'best_to_master',   label: 'Best to Master' },
  { value: 'off_role',         label: 'Off-Role Picks' },
  { value: 'slope_iterations', label: 'Slope Iterations' },
  { value: 'learning_profile', label: 'Learning Profile' },
  { value: 'mastery_curve',    label: 'Mastery Curve' },
  { value: 'all_stats',        label: 'All Stats' },
]
```

**Step 2: Add off_role to the rare picks filter condition**

Find the condition (line 131):
```ts
      {(view === 'easiest_to_learn' || view === 'best_to_master'
        || view === 'pabu_easiest_to_learn' || view === 'pabu_best_to_master'
        || view === 'slope_iterations')
```

Add `|| view === 'off_role'` to the condition.

**Step 3: Build**

```bash
cd web && npm run build
```

**Step 4: Commit**

```bash
git add web/src/components/TableControls.tsx
git commit -m "feat: add Off-Role Picks and Learning Profile to TableControls view selector"
```

---

### Task 11: Wire everything up in App.tsx

**Files:**
- Modify: `web/src/App.tsx`

**Context:** This is the final wiring task. We add `slopeMap` + `g50Map` + `mediumGamesMap` memos, extend the `VALID_VIEWS` list, add routing for `off_role` and `learning_profile`, add `filteredOffRole` and `learningProfileData` memos, and pass new props to existing components.

**Step 1: Add new imports**

Add to imports:
```ts
import { OffRoleView } from './components/OffRoleView'
import { LearningProfileChart } from './components/LearningProfileChart'
import type { GameTo50Entry } from './types/analysis'
```

**Step 2: Extend VALID_VIEWS**

In both the `useState` initializer and the `onPopState` handler, update the `VALID_VIEWS` arrays to include `'off_role'` and `'learning_profile'`.

**Step 3: Add lookup maps as memos**

After the `useAnalysisData` call, add:

```tsx
  const slopeMap = useMemo(
    () => new Map(data?.slopeIterations.map(s => [s.champion, s]) ?? []),
    [data]
  )

  const g50Map = useMemo(
    () => new Map<string, GameTo50Entry>(data?.gameTo50.map(e => [e.champion_name, e]) ?? []),
    [data]
  )

  const mediumGamesMap = useMemo(
    () => new Map(data?.champions.map(c => [c.champion, c.medium_games]) ?? []),
    [data]
  )
```

Note: `mediumGamesMap` is already computed inline inside `filteredSlope` — replace that inline definition with a reference to this shared memo.

**Step 4: Add filteredOffRole memo**

Add after `filteredSlope`:

```tsx
  const filteredOffRole = useMemo(() => {
    if (view !== 'off_role' || !data) return []

    const rarePickThreshold = (data.summary?.total_unique_players ?? 0) * 0.005

    let rows = hideRarePicks
      ? data.slopeIterations.filter(r => (mediumGamesMap.get(r.champion) ?? 0) >= rarePickThreshold)
      : data.slopeIterations

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(r => r.champion.toLowerCase().includes(q))
    }

    if (lane !== 'ALL') {
      rows = rows.filter(r => getLaneDisplay(r.most_common_lane) === lane)
    }

    return rows
  }, [data, view, search, lane, hideRarePicks, mediumGamesMap])
```

**Step 5: Add learningProfileData memo**

```tsx
  const learningProfileData = useMemo(() => {
    if (!data) return []

    const rarePickThreshold = (data.summary?.total_unique_players ?? 0) * 0.005

    let rows = hideRarePicks
      ? data.slopeIterations.filter(r => (mediumGamesMap.get(r.champion) ?? 0) >= rarePickThreshold)
      : data.slopeIterations

    if (lane !== 'ALL') {
      // Use per-lane data if available when a specific lane is selected
      const laneRows = data.slopeIterationsByLane.filter(r => getLaneDisplay(r.most_common_lane) === lane)
      rows = hideRarePicks
        ? laneRows.filter(r => (mediumGamesMap.get(r.champion) ?? 0) >= rarePickThreshold)
        : laneRows
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(r => r.champion.toLowerCase().includes(q))
    }

    return rows
  }, [data, hideRarePicks, lane, search, mediumGamesMap])
```

**Step 6: Update view type guards**

Add:
```tsx
  const isOffRole = view === 'off_role'
  const isLearningProfile = view === 'learning_profile'
```

Update `rowCount` and `totalCount`:
```tsx
  const rowCount =
    isMasteryCurve    ? 0
    : isSlopeView     ? filteredSlope.length
    : isOffRole       ? filteredOffRole.length
    : isLearningProfile ? learningProfileData.length
    : filteredChampions.length

  const totalCount =
    isMasteryCurve    ? 0
    : isSlopeView     ? (data?.slopeIterations.length ?? 0)
    : isOffRole       ? (data?.slopeIterations.length ?? 0)
    : isLearningProfile ? (data?.slopeIterations.length ?? 0)
    : sourceRows.length
```

**Step 7: Update the render switch**

Find the main render block (the nested ternary starting at `isSlopeView`). Replace it with:

```tsx
          {!loading && !error && data && (
            isLearningProfile
              ? <LearningProfileChart
                  data={learningProfileData}
                  mediumGamesMap={mediumGamesMap}
                  onChampionClick={handleNavigateToMasteryCurve}
                />
              : isOffRole
                ? <OffRoleView
                    data={filteredOffRole}
                    dataByLane={data.slopeIterationsByLane}
                    g50Map={g50Map}
                  />
                : isSlopeView
                  ? <SlopeIterationsView
                      data={filteredSlope}
                      masteryChampionCurves={data.masteryChampionCurves}
                      dataByLane={data.slopeIterationsByLane}
                      masteryChampionCurvesByLane={data.masteryChampionCurvesByLane}
                      onChampionClick={handleNavigateToMasteryCurve}
                      g50Map={g50Map}
                    />
                  : isMasteryCurve
                    ? <MasteryCurveView
                        masteryChampionCurves={data.masteryChampionCurves}
                        masteryChampionCurvesByLane={data.masteryChampionCurvesByLane}
                        pabuThreshold={view === 'pabu_mastery_curve' ? data.overallWinRate : undefined}
                      />
                    : <ChampionTable
                        data={filteredChampions}
                        view={view as Exclude<ViewMode, 'mastery_curve' | 'pabu_mastery_curve' | 'off_role' | 'learning_profile' | 'slope_iterations'>}
                        slopeMap={slopeMap}
                      />
          )}
```

**Step 8: Build**

```bash
cd web && npm run build
```

Expected: full clean build. Verify the TypeScript `Exclude<ViewMode, ...>` on `ChampionTable` aligns with the type in ChampionTable.tsx.

**Step 9: Commit**

```bash
git add web/src/App.tsx
git commit -m "feat: wire up off_role and learning_profile views, pass slopeMap/g50Map to components"
```

---

### Task 12: Final verification

**Step 1: Full build**

```bash
cd web && npm run build
```

Expected: clean build, chunk size advisory only (pre-existing, not an error).

**Step 2: Manual smoke check**

Start dev server and verify:

```bash
cd web && npm run dev
```

Check each new feature:
- [ ] Off-Role Picks tab appears in TableControls, shows champions sorted by Floor WR
- [ ] Learning Profile tab shows scatter chart with colored dots + quadrant labels
- [ ] Easiest to Learn shows new Pickup chip and Floor WR columns
- [ ] Best to Master shows Growth chip, Late Slope, Games to Plateau columns
- [ ] Slope Iterations shows Est. Games to 50% column
- [ ] Header has two separate icon buttons (book + flask icons)
- [ ] User Guide modal opens with goal-oriented content
- [ ] Methodology modal opens with the original technical content + new view entries
- [ ] Lane filter, search, and rare picks toggle all work on Off-Role Picks
- [ ] Clicking a dot in Learning Profile navigates to that champion's mastery curve
- [ ] TypeScript build remains clean after smoke check
