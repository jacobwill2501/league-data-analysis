import Box from '@mui/material/Box'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import ToggleButton from '@mui/material/ToggleButton'
import type { ViewMode } from '../types/analysis'

const VIEW_OPTIONS: { value: ViewMode; label: string }[] = [
  { value: 'easiest_to_learn', label: 'Easiest to Learn' },
  { value: 'best_to_master',   label: 'Best to Master' },
  { value: 'all_stats',        label: 'All Stats' },
  { value: 'games_to_50',      label: 'Games to 50% WR' },
  { value: 'mastery_curve',    label: 'Mastery Curve' },
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
      <ToggleButtonGroup
        value={view}
        exclusive
        size="small"
        onChange={(_, val) => val && onViewChange(val as ViewMode)}
      >
        {VIEW_OPTIONS.map(opt => (
          <ToggleButton key={opt.value} value={opt.value} sx={{ px: 1.5 }}>
            {opt.label}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>

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
