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
import GitHubIcon from '@mui/icons-material/GitHub'
import type { PaletteMode } from '@mui/material'
import type { EloFilter } from '../types/analysis'
import { HelpModal } from './HelpModal'

function fmtCompact(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M'
  if (n >= 1_000) return Math.round(n / 1_000) + 'K'
  return String(n)
}

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
  summary?: { total_matches: number; total_unique_players: number } | null
  generatedAt?: string | null
}

export function Header({ elo, onEloChange, mode, onModeToggle, summary, generatedAt }: Props) {
  const [helpOpen, setHelpOpen] = useState(false)

  return (
    <>
      <AppBar position="sticky" color="default" elevation={1}>
        <Toolbar variant="dense" sx={{ gap: 2, flexWrap: 'wrap' }}>
          <Typography variant="h6" fontWeight="bold" sx={{ flexShrink: 0 }}>
            Champion Mastery Analysis
          </Typography>

          {summary && (
            <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
              {fmtCompact(summary.total_matches)} matches
              {' · '}
              {fmtCompact(summary.total_unique_players)} players
              {generatedAt && ` · Updated ${new Date(generatedAt).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}`}
            </Typography>
          )}

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

          <Tooltip title="View source on GitHub">
            <IconButton
              component="a"
              href="https://github.com/jacobwill2501/league-data-analysis"
              target="_blank"
              rel="noopener noreferrer"
              size="small"
            >
              <GitHubIcon />
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
