import { useState } from 'react'
import AppBar from '@mui/material/AppBar'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import ToggleButton from '@mui/material/ToggleButton'
import IconButton from '@mui/material/IconButton'
import Tooltip from '@mui/material/Tooltip'
import Brightness4Icon from '@mui/icons-material/Brightness4'
import Brightness7Icon from '@mui/icons-material/Brightness7'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import type { PaletteMode } from '@mui/material'
import type { EloFilter } from '../types/analysis'
import { HelpModal } from './HelpModal'

const ELO_OPTIONS: { value: EloFilter; label: string }[] = [
  { value: 'emerald_plus', label: 'Emerald+' },
  { value: 'diamond_plus', label: 'Diamond+' },
  { value: 'diamond2_plus', label: 'Diamond 2+' },
]

interface Props {
  elo: EloFilter
  onEloChange: (elo: EloFilter) => void
  mode: PaletteMode
  onModeToggle: () => void
}

export function Header({ elo, onEloChange, mode, onModeToggle }: Props) {
  const [helpOpen, setHelpOpen] = useState(false)

  return (
    <>
      <AppBar position="sticky" color="default" elevation={1}>
        <Toolbar variant="dense" sx={{ gap: 2, flexWrap: 'wrap' }}>
          <Typography variant="h6" fontWeight="bold" sx={{ flexShrink: 0 }}>
            Champion Mastery Analysis
          </Typography>

          <ToggleButtonGroup
            value={elo}
            exclusive
            size="small"
            onChange={(_, val) => val && onEloChange(val as EloFilter)}
            sx={{ ml: 'auto' }}
          >
            {ELO_OPTIONS.map(opt => (
              <ToggleButton key={opt.value} value={opt.value} sx={{ px: 1.5 }}>
                {opt.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          <Tooltip title="Help & methodology">
            <IconButton onClick={() => setHelpOpen(true)} size="small">
              <HelpOutlineIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title={mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
            <IconButton onClick={onModeToggle} size="small">
              {mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <HelpModal open={helpOpen} onClose={() => setHelpOpen(false)} />
    </>
  )
}
