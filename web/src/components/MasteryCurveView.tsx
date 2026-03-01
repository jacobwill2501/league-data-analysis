import { useEffect, useMemo, useRef, useState } from 'react'
import useMediaQuery from '@mui/material/useMediaQuery'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Autocomplete from '@mui/material/Autocomplete'
import TextField from '@mui/material/TextField'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import ToggleButton from '@mui/material/ToggleButton'
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import type { LaneCurve, MasteryChampionCurve, MasteryInterval } from '../types/analysis'
import { useTheme } from '@mui/material/styles'
import { fmtLane } from '../utils/format'

// Use ordinal index as X position so every interval gets equal visual spacing.
// A log scale created a disproportionately large gap between the first two
// intervals because both span 5× the mastery range vs 2× for later intervals.

interface Props {
  masteryChampionCurves: Record<string, MasteryChampionCurve>
  masteryChampionCurvesByLane?: Record<string, Record<string, LaneCurve>> | null
  pabuThreshold?: number | null
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: MasteryInterval & { mid: number } }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', p: 1.5, borderRadius: 1 }}>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>{d.label}</Typography>
      <Typography variant="body2" fontFamily="monospace" color={d.win_rate >= 0.5 ? 'success.main' : 'error.main'}>
        WR: {(d.win_rate * 100).toFixed(2)}%
      </Typography>
      <Typography variant="body2" fontFamily="monospace" color="text.secondary">
        Games: {d.games.toLocaleString()}
      </Typography>
      {d.ci_lower != null && d.ci_upper != null && (
        <Typography variant="body2" fontFamily="monospace" sx={{ color: '#aaa', fontSize: 11 }}>
          95% CI: [{(d.ci_lower * 100).toFixed(1)}%, {(d.ci_upper * 100).toFixed(1)}%]
        </Typography>
      )}
    </Box>
  )
}

export function MasteryCurveView({ masteryChampionCurves, masteryChampionCurvesByLane, pabuThreshold }: Props) {
  const [selectedChamp, setSelectedChamp] = useState<string | null>(() => {
    return new URLSearchParams(window.location.search).get('champion') ?? null
  })
  const [selectedLane, setSelectedLane] = useState<string>(() => {
    return new URLSearchParams(window.location.search).get('lane') ?? 'ALL'
  })
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const isMounted = useRef(false)

  // Reset lane selection when champion changes (user-initiated via autocomplete).
  // Skip the first run so the URL-sourced lane is not overridden on mount.
  useEffect(() => {
    if (!isMounted.current) {
      isMounted.current = true
      return
    }
    setSelectedLane('ALL')
  }, [selectedChamp])

  const championNames = Object.keys(masteryChampionCurves).sort()

  // Sync champion/lane state back to URL so it stays shareable after user changes them
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (selectedChamp) params.set('champion', selectedChamp)
    else params.delete('champion')
    if (selectedLane !== 'ALL') params.set('lane', selectedLane)
    else params.delete('lane')
    window.history.replaceState(null, '', `?${params.toString()}`)
  }, [selectedChamp, selectedLane])

  // Guard against stale URL champion (e.g. typo or old bookmark)
  useEffect(() => {
    if (selectedChamp && championNames.length > 0 && !championNames.includes(selectedChamp)) {
      setSelectedChamp(null)
      setSelectedLane('ALL')
    }
  }, [championNames, selectedChamp])

  const availableLanes = useMemo(() => {
    if (!selectedChamp || !masteryChampionCurvesByLane?.[selectedChamp]) return []
    return Object.keys(masteryChampionCurvesByLane[selectedChamp])
  }, [selectedChamp, masteryChampionCurvesByLane])

  const curveData = useMemo(() => {
    if (!selectedChamp) return null
    if (selectedLane !== 'ALL' && masteryChampionCurvesByLane?.[selectedChamp]?.[selectedLane]) {
      return masteryChampionCurvesByLane[selectedChamp][selectedLane]
    }
    return masteryChampionCurves[selectedChamp] ?? null
  }, [selectedChamp, selectedLane, masteryChampionCurves, masteryChampionCurvesByLane])

  const chartData = curveData ? curveData.intervals.map((iv, idx) => ({
    ...iv,
    mid: idx,
    ci_upper: iv.ci_upper ?? null,
    ci_lower: iv.ci_lower ?? null,
  })) : []

  const yMin = chartData.length
    ? Math.min(...chartData.map(d => d.ci_lower ?? d.win_rate)) - 0.01
    : 0.38
  const yMax = chartData.length
    ? Math.max(...chartData.map(d => d.ci_upper ?? d.win_rate)) + 0.01
    : 0.64
  const yDomain: [number, number] = [
    Math.min(yMin, 0.38),
    Math.max(yMax, 0.64),
  ]

  const AngledTick = ({ x, y, payload }: { x?: number; y?: number; payload?: { value: number } }) => {
    const iv = chartData.find(d => d.mid === payload?.value)
    const label = iv ? iv.label : String(payload?.value ?? '')
    return (
      <g transform={`translate(${x ?? 0},${y ?? 0})`}>
        <text
          x={0}
          y={0}
          dy={10}
          textAnchor="end"
          fill={theme.palette.text.secondary}
          fontSize={11}
          transform="rotate(-35)"
        >
          {label}
        </text>
      </g>
    )
  }

  const ciColor = theme.palette.primary.main

  return (
    <Box sx={{ p: { xs: 1.5, sm: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap', mb: 3 }}>
        <Autocomplete
          options={championNames}
          value={selectedChamp}
          onChange={(_, v) => setSelectedChamp(v)}
          renderInput={params => <TextField {...params} label="Select Champion" size="small" />}
          sx={{ width: { xs: '100%', sm: 260 } }}
        />

        {availableLanes.length > 1 && (
          <ToggleButtonGroup
            value={selectedLane}
            exclusive
            size="small"
            onChange={(_, v) => v && setSelectedLane(v)}
          >
            <ToggleButton value="ALL">All Lanes</ToggleButton>
            {availableLanes.map(l => (
              <ToggleButton key={l} value={l}>{fmtLane(l)}</ToggleButton>
            ))}
          </ToggleButtonGroup>
        )}
      </Box>

      {!selectedChamp && (
        <Typography color="text.secondary">Select a champion to view their win rate by mastery interval.</Typography>
      )}

      {curveData && curveData.intervals.length === 0 && (
        <Typography color="text.secondary">
          No mastery curve data available. Re-run <code>python src/analyze.py</code> to generate interval data.
        </Typography>
      )}

      {curveData && curveData.intervals.length > 0 && (
        <Box>
          <Typography variant="h6" sx={{ mb: 0.5 }}>
            {selectedChamp}{selectedLane !== 'ALL' ? ` — ${fmtLane(selectedLane)}` : ''} — Win Rate by Mastery Interval
          </Typography>
          {selectedLane !== 'ALL' && (
            <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
              Mastery axis = total champion mastery, not {fmtLane(selectedLane)}-specific.
              Riot's API does not provide per-role mastery data.
            </Typography>
          )}
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={chartData} margin={{ top: 10, right: isMobile ? 16 : 40, left: 10, bottom: isMobile ? 48 : 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis
                type="number"
                dataKey="mid"
                domain={[-0.5, chartData.length - 0.5]}
                ticks={chartData.map(d => d.mid)}
                tick={<AngledTick />}
                label={{ value: 'Experience Bracket', position: 'insideBottom', offset: -35, fontSize: 12, fill: theme.palette.text.secondary }}
              />
              <YAxis
                domain={yDomain}
                tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
                label={{ value: 'Win Rate', angle: -90, position: 'insideLeft', offset: 0, fontSize: 12, fill: theme.palette.text.secondary }}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={0.5}
                stroke={theme.palette.warning.main}
                strokeDasharray={pabuThreshold != null ? undefined : '5 5'}
                label={{ value: '50%', position: 'insideTopRight', fontSize: 11, fill: theme.palette.warning.main }}
              />
              {pabuThreshold != null && (
                <ReferenceLine
                  y={pabuThreshold}
                  stroke={theme.palette.secondary.main}
                  strokeDasharray="5 5"
                  label={{ value: `Elo avg (${(pabuThreshold * 100).toFixed(1)}%)`, position: 'insideBottomRight', fontSize: 11, fill: theme.palette.secondary.main }}
                />
              )}
              {/* CI band: ci_upper fills down, ci_lower masks below it, leaving only the band */}
              <Area
                type="monotone"
                dataKey="ci_upper"
                fill={ciColor}
                fillOpacity={0.12}
                stroke="none"
                dot={false}
                activeDot={false}
                isAnimationActive={false}
                legendType="none"
                name=""
              />
              <Area
                type="monotone"
                dataKey="ci_lower"
                fill={theme.palette.background.paper}
                fillOpacity={1}
                stroke="none"
                dot={false}
                activeDot={false}
                isAnimationActive={false}
                legendType="none"
                name=""
              />
              <Line
                type="monotone"
                dataKey="win_rate"
                stroke={theme.palette.primary.main}
                strokeWidth={2}
                dot={{ r: 4, fill: theme.palette.primary.main }}
                activeDot={{ r: 6 }}
                name="Win Rate"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
      )}
    </Box>
  )
}
