import { useState } from 'react'
import type { PaletteMode } from '@mui/material'

export function useThemeMode() {
  const [mode, setMode] = useState<PaletteMode>(() => {
    const stored = localStorage.getItem('theme') as PaletteMode | null
    if (stored === 'dark' || stored === 'light') return stored
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  const toggle = () => {
    setMode(m => {
      const next = m === 'dark' ? 'light' : 'dark'
      localStorage.setItem('theme', next)
      return next
    })
  }

  return { mode, toggle }
}
