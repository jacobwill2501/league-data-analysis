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
import type { MasteryChampionCurve } from '../types/analysis'
import { useTheme } from '@mui/material/styles'

interface Props {
  masteryChampionCurves: Record<string, MasteryChampionCurve>
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { payload: { win_rate: number; games: number } }[]; label?: string }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', p: 1.5, borderRadius: 1 }}>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>{label}</Typography>
      <Typography variant="body2" fontFamily="monospace" color={d.win_rate >= 0.5 ? 'success.main' : 'error.main'}>
        WR: {(d.win_rate * 100).toFixed(2)}%
      </Typography>
      <Typography variant="body2" fontFamily="monospace" color="text.secondary">
        Games: {d.games.toLocaleString()}
      </Typography>
    </Box>
  )
}

export function MasteryCurveView({ masteryChampionCurves }: Props) {
  const [selectedChamp, setSelectedChamp] = useState<string | null>(null)
  const theme = useTheme()

  const championNames = Object.keys(masteryChampionCurves).sort()
  const curveData = selectedChamp ? masteryChampionCurves[selectedChamp] : null

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
            <LineChart data={curveData.intervals} margin={{ top: 10, right: 40, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
                label={{ value: 'Mastery Points', position: 'insideBottom', offset: -10, fontSize: 12, fill: theme.palette.text.secondary }}
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
                strokeDasharray="5 5"
                label={{ value: '50%', position: 'insideTopRight', fontSize: 11, fill: theme.palette.warning.main }}
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
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}
    </Box>
  )
}
