import type { ViewMode } from '../types/analysis'
import { VIEW_CONFIGS } from '../utils/columns'

const VIEW_GROUPS = [
  {
    label: 'Standard',
    views: ['easiest_to_learn', 'best_to_master', 'best_investment', 'all_stats'] as ViewMode[],
  },
  {
    label: 'Dynamic (per-champion thresholds)',
    views: ['dynamic_easiest', 'dynamic_master', 'dynamic_investment', 'games_to_50'] as ViewMode[],
  },
]

const LANE_OPTIONS = ['ALL', 'Top', 'Jungle', 'Mid', 'Bot', 'Support']

interface Props {
  view: ViewMode
  onViewChange: (v: ViewMode) => void
  search: string
  onSearchChange: (s: string) => void
  lane: string
  onLaneChange: (l: string) => void
  tierFilter: string
  onTierFilterChange: (t: string) => void
  tierOptions: string[]
  rowCount: number
  totalCount: number
}

export function TableControls({
  view,
  onViewChange,
  search,
  onSearchChange,
  lane,
  onLaneChange,
  tierFilter,
  onTierFilterChange,
  tierOptions,
  rowCount,
  totalCount,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      {/* View Selector */}
      <select
        value={view}
        onChange={e => onViewChange(e.target.value as ViewMode)}
        className="select-input"
      >
        {VIEW_GROUPS.map(group => (
          <optgroup key={group.label} label={group.label}>
            {group.views.map(v => (
              <option key={v} value={v}>
                {VIEW_CONFIGS[v].label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>

      {/* Search */}
      <input
        type="search"
        value={search}
        onChange={e => onSearchChange(e.target.value)}
        placeholder="Search champion…"
        className="select-input w-40"
      />

      {/* Lane Filter */}
      <select
        value={lane}
        onChange={e => onLaneChange(e.target.value)}
        className="select-input"
      >
        {LANE_OPTIONS.map(l => (
          <option key={l} value={l}>
            {l === 'ALL' ? 'All Lanes' : l}
          </option>
        ))}
      </select>

      {/* Tier Filter */}
      {tierOptions.length > 0 && (
        <select
          value={tierFilter}
          onChange={e => onTierFilterChange(e.target.value)}
          className="select-input"
        >
          <option value="">All Tiers</option>
          {tierOptions.map(t => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      )}

      <span className="ml-auto text-sm text-gray-500 dark:text-gray-400 shrink-0">
        Showing {rowCount.toLocaleString()} of {totalCount.toLocaleString()}
      </span>
    </div>
  )
}
