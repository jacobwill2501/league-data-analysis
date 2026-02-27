import { useState } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Autocomplete from '@mui/material/Autocomplete'
import TextField from '@mui/material/TextField'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import type { MasteryChampionCurve, MasteryInterval } from '../types/analysis'
import { useTheme } from '@mui/material/styles'

const getMid = (iv: MasteryInterval): number => {
  if (iv.min === 0) return 500
  if (iv.max === null) return iv.min * 1.5
  return (iv.min + iv.max) / 2
}

interface Props {
  masteryChampionCurves: Record<string, MasteryChampionCurve>
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
    </Box>
  )
}

export function MasteryCurveView({ masteryChampionCurves, pabuThreshold }: Props) {
  const [selectedChamp, setSelectedChamp] = useState<string | null>(null)
  const theme = useTheme()

  const championNames = Object.keys(masteryChampionCurves).sort()
  const curveData = selectedChamp ? masteryChampionCurves[selectedChamp] : null
  const chartData = curveData ? curveData.intervals.map(iv => ({ ...iv, mid: getMid(iv) })) : []

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

  return (
    <Box sx={{ p: 3 }}>
      <Autocomplete
        options={championNames}
        value={selectedChamp}
        onChange={(_, v) => setSelectedChamp(v)}
        renderInput={params => <TextField {...params} label="Select Champion" size="small" />}
        sx={{ width: 260, mb: 3 }}
      />

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
          <Typography variant="h6" sx={{ mb: 2 }}>
            {selectedChamp} — Win Rate by Mastery Interval
          </Typography>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 10, right: 40, left: 10, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis
                type="number"
                dataKey="mid"
                scale="log"
                domain={['auto', 'auto']}
                ticks={chartData.map(d => d.mid)}
                tick={<AngledTick />}
                label={{ value: 'Mastery Points', position: 'insideBottom', offset: -35, fontSize: 12, fill: theme.palette.text.secondary }}
              />
              <YAxis
                domain={[0.38, 0.64]}
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
              <Line
                type="monotone"
                dataKey="win_rate"
                stroke={theme.palette.primary.main}
                strokeWidth={2}
                dot={{ r: 4, fill: theme.palette.primary.main }}
                activeDot={{ r: 6 }}
                name="Win Rate"
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}
    </Box>
  )
}
