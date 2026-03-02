import { useMemo } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import type { SlopeIterationStat } from '../types/analysis'
import { SLOPE_TIER_LINE_COLOR } from '../utils/tiers'

interface Props {
  data: SlopeIterationStat[]
  rarePicks?: boolean
  pabuThreshold?: number | null
  totalUniquePlayers?: number
  onNavigateToMasteryCurve?: (champion: string) => void
}

/** Point shape passed into the ScatterChart dataset for a single tier group. */
interface PlotPoint {
  champion: string
  slope_tier: string | null
  initial_wr: number | null
  peak_wr: number | null
  inflection_games: number
  growth_type: string | null
  medium_games: number
  wrGainPp: number
  /** Pre-computed dot radius for this point */
  r: number
}

function median(values: number[]): number {
  if (values.length === 0) return 1
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid]
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

// Recharts calls the custom tooltip component with active + payload props.
// The payload array items each have a `payload` property holding the raw data point.
interface TooltipEntry {
  payload: PlotPoint
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipEntry[] }) {
  const theme = useTheme()
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null

  const fmtWr = (wr: number | null) =>
    wr == null ? '—' : `${(wr * 100).toFixed(1)}%`

  return (
    <Box
      sx={{
        bgcolor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        p: 1.5,
        borderRadius: 1,
        minWidth: 180,
      }}
    >
      <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
        {d.champion}
      </Typography>
      {d.slope_tier && (
        <Typography
          variant="body2"
          sx={{
            color: SLOPE_TIER_LINE_COLOR[d.slope_tier] ?? theme.palette.text.secondary,
            mb: 0.5,
          }}
        >
          {d.slope_tier}
        </Typography>
      )}
      <Typography variant="body2" fontFamily="monospace" color="text.secondary">
        Starting WR: {fmtWr(d.initial_wr)}
      </Typography>
      <Typography variant="body2" fontFamily="monospace" color="text.secondary">
        Peak WR: {fmtWr(d.peak_wr)}
      </Typography>
      <Typography variant="body2" fontFamily="monospace" color="text.secondary">
        Games to Plateau: {d.inflection_games.toLocaleString()}
      </Typography>
      {d.growth_type && (
        <Typography variant="body2" fontFamily="monospace" color="text.secondary">
          Growth: {d.growth_type}
        </Typography>
      )}
    </Box>
  )
}

const TIER_ORDER = ['Easy Pickup', 'Mild Pickup', 'Hard Pickup', 'Very Hard Pickup']
const FALLBACK_COLOR = '#90CAF9'

export function LearningProfileChart({
  data,
  rarePicks,
  totalUniquePlayers,
  onNavigateToMasteryCurve,
}: Props) {
  const theme = useTheme()

  const visiblePoints = useMemo((): PlotPoint[] => {
    const minMediumGames =
      rarePicks === false && totalUniquePlayers != null
        ? totalUniquePlayers * 0.005
        : 0

    // SlopeIterationStat doesn't declare medium_games in TypeScript but the
    // actual JSON data includes it (it comes from the analysis pipeline).
    // We access it via an index signature cast so TypeScript stays happy.
    const getMediumGames = (d: SlopeIterationStat): number =>
      ((d as unknown as Record<string, unknown>)['medium_games'] as number | undefined) ?? 0

    const filtered = data.filter(
      (d) =>
        d.inflection_games != null &&
        d.initial_wr != null &&
        d.peak_wr != null &&
        getMediumGames(d) >= minMediumGames,
    )

    if (filtered.length === 0) return []

    const medianGames = median(filtered.map((d) => getMediumGames(d)))
    const safeDenom = medianGames > 0 ? medianGames : 1

    return filtered.map((d) => {
      const mg = getMediumGames(d)
      const rawR = 5 + Math.sqrt(mg / safeDenom) * 3
      return {
        champion: d.champion,
        slope_tier: d.slope_tier,
        initial_wr: d.initial_wr,
        peak_wr: d.peak_wr,
        inflection_games: d.inflection_games as number,
        growth_type: d.growth_type,
        medium_games: mg,
        wrGainPp: ((d.peak_wr as number) - (d.initial_wr as number)) * 100,
        r: clamp(rawR, 4, 12),
      }
    })
  }, [data, rarePicks, totalUniquePlayers])

  const medianInflection = useMemo(() => {
    const vals = visiblePoints.map((p) => p.inflection_games)
    return median(vals)
  }, [visiblePoints])

  const tierGroups = useMemo(() => {
    const groups: Record<string, PlotPoint[]> = {}
    for (const p of visiblePoints) {
      const key = p.slope_tier ?? 'Unknown'
      if (!groups[key]) groups[key] = []
      groups[key].push(p)
    }
    return groups
  }, [visiblePoints])

  const orderedTiers = useMemo(() => {
    const knownTiers = TIER_ORDER.filter((t) => tierGroups[t])
    const otherTiers = Object.keys(tierGroups).filter((t) => !TIER_ORDER.includes(t))
    return [...knownTiers, ...otherTiers]
  }, [tierGroups])

  const WR_GAIN_REF = 3

  const quadrantLabelStyle = {
    fontSize: 11,
    fill: theme.palette.text.disabled,
  }

  if (visiblePoints.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="text.secondary">
          No champions with inflection_games data available. Run analysis to generate slope iteration stats.
        </Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ p: { xs: 1.5, sm: 3 } }}>
      <Typography variant="h6" sx={{ mb: 0.5 }}>
        Learning Profile Chart
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        X axis: how many games until win rate plateaus. Y axis: total WR gain from start to peak.
        Dot size scales with volume of games at medium mastery.
      </Typography>

      <ResponsiveContainer width="100%" height={480}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 50, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />

          <XAxis
            type="number"
            dataKey="inflection_games"
            name="Games to Plateau"
            tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
            label={{
              value: 'Games to Plateau',
              position: 'insideBottom',
              offset: -35,
              fontSize: 12,
              fill: theme.palette.text.secondary,
            }}
          />

          <YAxis
            type="number"
            dataKey="wrGainPp"
            name="WR Gain (pp)"
            tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
            label={{
              value: 'WR Gain (pp)',
              angle: -90,
              position: 'insideLeft',
              offset: 10,
              fontSize: 12,
              fill: theme.palette.text.secondary,
            }}
          />

          <Tooltip
            content={<CustomTooltip />}
            cursor={{ strokeDasharray: '3 3' }}
          />

          {/* Vertical quadrant divider at median inflection_games */}
          <ReferenceLine
            x={medianInflection}
            stroke={theme.palette.divider}
            strokeDasharray="6 3"
          />

          {/* Horizontal quadrant divider at 3pp WR gain */}
          <ReferenceLine
            y={WR_GAIN_REF}
            stroke={theme.palette.divider}
            strokeDasharray="6 3"
          />

          {/* Quadrant labels — one ReferenceLine per label so positions don't conflict */}
          <ReferenceLine
            x={medianInflection}
            stroke="none"
            label={{
              value: 'Pick up & commit',
              position: 'insideTopLeft',
              ...quadrantLabelStyle,
            }}
          />
          <ReferenceLine
            x={medianInflection}
            stroke="none"
            label={{
              value: 'Deep investment',
              position: 'insideTopRight',
              ...quadrantLabelStyle,
            }}
          />
          <ReferenceLine
            y={WR_GAIN_REF}
            stroke="none"
            label={{
              value: 'Off-role safe',
              position: 'insideBottomLeft',
              ...quadrantLabelStyle,
            }}
          />
          <ReferenceLine
            y={WR_GAIN_REF}
            stroke="none"
            label={{
              value: 'Avoid',
              position: 'insideBottomRight',
              ...quadrantLabelStyle,
            }}
          />

          {orderedTiers.map((tier) => {
            const color = SLOPE_TIER_LINE_COLOR[tier] ?? FALLBACK_COLOR
            const points = tierGroups[tier]
            return (
              <Scatter
                key={tier}
                name={tier}
                data={points}
                fill={color}
                opacity={0.85}
                shape={(shapeProps: { cx?: number; cy?: number; payload?: PlotPoint }) => {
                  const { cx = 0, cy = 0, payload } = shapeProps
                  const r = payload?.r ?? 6
                  return (
                    <circle
                      cx={cx}
                      cy={cy}
                      r={r}
                      fill={color}
                      fillOpacity={0.85}
                      stroke={theme.palette.background.paper}
                      strokeWidth={1}
                      style={{ cursor: onNavigateToMasteryCurve ? 'pointer' : 'default' }}
                      onClick={() => {
                        if (payload?.champion && onNavigateToMasteryCurve) {
                          onNavigateToMasteryCurve(payload.champion)
                        }
                      }}
                    />
                  )
                }}
              />
            )
          })}
        </ScatterChart>
      </ResponsiveContainer>

      {/* Custom legend */}
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 2,
          justifyContent: 'center',
          mt: 1,
        }}
      >
        {orderedTiers.map((tier) => {
          const color = SLOPE_TIER_LINE_COLOR[tier] ?? FALLBACK_COLOR
          return (
            <Box key={tier} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  bgcolor: color,
                  opacity: 0.85,
                  flexShrink: 0,
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {tier}
              </Typography>
            </Box>
          )
        })}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              border: '1px solid',
              borderColor: 'text.disabled',
              bgcolor: 'transparent',
              flexShrink: 0,
            }}
          />
          <Typography variant="caption" color="text.secondary">
            dot size = medium-mastery game volume
          </Typography>
        </Box>
      </Box>

      {onNavigateToMasteryCurve && (
        <Typography
          variant="caption"
          color="text.disabled"
          sx={{ display: 'block', textAlign: 'center', mt: 0.5 }}
        >
          Click a dot to open the mastery curve for that champion.
        </Typography>
      )}
    </Box>
  )
}
