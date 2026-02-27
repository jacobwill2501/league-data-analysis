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
  { value: 'mastery_curve',    label: 'Mastery Curve' },
  { value: 'all_stats',        label: 'All Stats' },
]

const BETA_VIEW_OPTIONS: { value: ViewMode; label: string }[] = [
  { value: 'pabu_easiest_to_learn', label: 'Pabu: Easiest to Learn β' },
  { value: 'pabu_best_to_master',   label: 'Pabu: Best to Master β' },
  { value: 'pabu_mastery_curve',    label: 'Pabu: Mastery Curve β' },
  { value: 'slope_iterations',      label: 'Slope Iterations β' },
]

const BETA_VIEW_VALUES: ViewMode[] = BETA_VIEW_OPTIONS.map(o => o.value)

const LANE_OPTIONS = ['ALL', 'Top', 'Jungle', 'Mid', 'Bot', 'Support']

interface Props {
  view: ViewMode
  onViewChange: (v: ViewMode) => void
  search: string
  onSearchChange: (s: string) => void
  lane: string
  onLaneChange: (l: string) => void
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
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <ToggleButtonGroup
          value={BETA_VIEW_VALUES.includes(view) ? false : view}
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

        <FormControl size="small" sx={{ minWidth: 160 }}>
          <Select
            displayEmpty
            value={BETA_VIEW_VALUES.includes(view) ? view : ''}
            renderValue={val => {
              if (!val) return <em style={{ fontStyle: 'italic', opacity: 0.7 }}>Beta Views</em>
              return BETA_VIEW_OPTIONS.find(o => o.value === val)?.label ?? String(val)
            }}
            onChange={e => {
              const val = e.target.value as ViewMode
              if (val) onViewChange(val)
            }}
          >
            {BETA_VIEW_OPTIONS.map(opt => (
              <MenuItem key={opt.value} value={opt.value} sx={{ fontStyle: 'italic' }}>
                {opt.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

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

      <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
        Showing {rowCount.toLocaleString()} of {totalCount.toLocaleString()}
      </Typography>
    </Box>
  )
}
