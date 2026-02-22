import Box from '@mui/material/Box'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import type { ViewMode } from '../types/analysis'
import { VIEW_CONFIGS } from '../utils/columns'

const VIEW_GROUPS = [
  {
    label: 'Standard',
    views: ['easiest_to_learn', 'best_to_master', 'best_investment', 'all_stats', 'mastery_curve'] as ViewMode[],
  },
  {
    label: 'Bias (per-champion thresholds)',
    views: ['bias_easiest', 'bias_master', 'bias_investment', 'games_to_50'] as ViewMode[],
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
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 1.5,
        px: 2,
        py: 1.5,
        borderBottom: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      {/* View selector */}
      <FormControl size="small" sx={{ minWidth: 220 }}>
        <InputLabel>View</InputLabel>
        <Select
          value={view}
          label="View"
          onChange={e => onViewChange(e.target.value as ViewMode)}
        >
          {VIEW_GROUPS.map(group => [
            <MenuItem key={`hdr-${group.label}`} disabled divider sx={{ fontWeight: 600, fontSize: 12, opacity: 1 }}>
              {group.label}
            </MenuItem>,
            ...group.views.map(v => (
              <MenuItem key={v} value={v} sx={{ pl: 3 }}>
                {VIEW_CONFIGS[v].label}
              </MenuItem>
            )),
          ])}
        </Select>
      </FormControl>

      {/* Search */}
      <TextField
        size="small"
        label="Search champion"
        value={search}
        onChange={e => onSearchChange(e.target.value)}
        sx={{ width: 160 }}
      />

      {/* Lane filter */}
      <FormControl size="small" sx={{ minWidth: 110 }}>
        <InputLabel>Lane</InputLabel>
        <Select value={lane} label="Lane" onChange={e => onLaneChange(e.target.value)}>
          {LANE_OPTIONS.map(l => (
            <MenuItem key={l} value={l}>
              {l === 'ALL' ? 'All Lanes' : l}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Tier filter (contextual) */}
      {tierOptions.length > 0 && (
        <FormControl size="small" sx={{ minWidth: 190 }}>
          <InputLabel>Tier</InputLabel>
          <Select
            value={tierFilter}
            label="Tier"
            onChange={e => onTierFilterChange(e.target.value)}
          >
            <MenuItem value="">All Tiers</MenuItem>
            {tierOptions.map(t => (
              <MenuItem key={t} value={t}>
                {t}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
        Showing {rowCount.toLocaleString()} of {totalCount.toLocaleString()}
      </Typography>
    </Box>
  )
}
