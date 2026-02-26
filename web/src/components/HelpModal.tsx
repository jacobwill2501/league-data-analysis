import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'

interface Props {
  open: boolean
  onClose: () => void
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom fontWeight="bold">
        {title}
      </Typography>
      {children}
    </Box>
  )
}

function P({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="body2" sx={{ mb: 1, display: 'block' }}>
      {children}
    </Typography>
  )
}

function TierTable({
  rows,
  scoreLabel,
}: {
  rows: { tier: string; score: string }[]
  scoreLabel: string
}) {
  return (
    <Table size="small" sx={{ mb: 1 }}>
      <TableHead>
        <TableRow>
          <TableCell>Tier</TableCell>
          <TableCell>{scoreLabel}</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map(r => (
          <TableRow key={r.tier}>
            <TableCell>{r.tier}</TableCell>
            <TableCell>{r.score}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

const LEARNING_TIERS = [
  { tier: 'Safe Blind Pick', score: '> 0' },
  { tier: 'Low Risk', score: '-5 to 0' },
  { tier: 'Moderate', score: '-15 to -5' },
  { tier: 'High Risk', score: '-25 to -15' },
  { tier: 'Avoid', score: '< -25' },
]

const MASTERY_TIERS = [
  { tier: 'Exceptional Payoff', score: '> 8' },
  { tier: 'High Payoff', score: '5 to 8' },
  { tier: 'Moderate Payoff', score: '2 to 5' },
  { tier: 'Low Payoff', score: '0 to 2' },
  { tier: 'Not Worth Mastering', score: '< 0' },
]

export function HelpModal({ open, onClose }: Props) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth scroll="paper">
      <DialogTitle>About This Study</DialogTitle>

      <DialogContent dividers>
        <Section title="About">
          <P>
            This dashboard visualizes a statistical analysis of champion mastery and win rates in
            Emerald+ ranked solo queue, covering approximately 9 million matches across NA, EUW, and
            KR — with a roughly equal split between the three regions.
          </P>
          <P>
            Data is collected via the Riot Games API. Champion mastery is a current snapshot (not
            the mastery at the time of each match), which is a known limitation shared with the
            original Gold-elo study this project replicates.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Views">
          <P>
            <strong>Easiest to Learn</strong> — Champions ranked by Learning Score. Use this tab to
            find champions you can pick up and perform reasonably well with immediately. Champions at
            the top of the list lose the least win rate from low mastery.
          </P>
          <P>
            <strong>Best to Master</strong> — Champions ranked by Mastery Score. Use this tab to
            find champions worth long-term investment. Champions at the top gain the most win rate
            from high mastery.
          </P>
          <P>
            <strong>All Stats</strong> — Full table showing every champion with all win rates (Low,
            Medium, High mastery buckets), both ratios, all three scores (Learning, Mastery,
            Investment), and the assigned tier labels.
          </P>
          <P>
            <strong>Games to 50%</strong> — An estimate of how many games a player needs to play on
            a champion before reaching a 50% win rate, based on mastery curve intervals. Lower
            values mean the champion is easier to reach baseline performance on. Champions where
            low-mastery win rate already exceeds 50% show 0.
          </P>
          <P>
            <strong>Mastery Curve</strong> — An interactive per-champion line chart showing win rate
            across mastery intervals (0–1k, 1k–2k, 2k–5k, … 1M+). Select a champion to see how
            their win rate evolves as players invest more time. Requires a minimum sample size per
            interval.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Scoring Methodology">
          <Typography variant="subtitle2" gutterBottom fontWeight="bold">
            Learning Effectiveness Score
          </Typography>
          <Box
            component="pre"
            sx={{
              fontFamily: 'monospace',
              bgcolor: 'action.hover',
              p: 1,
              borderRadius: 1,
              mb: 1,
              fontSize: '0.8rem',
              overflowX: 'auto',
            }}
          >
            {'Learning Score = (Low WR% − 50) + (Low Ratio − 1) × 50'}
          </Box>
          <P>
            Answers: <em>"Can I pick this champion up and perform well immediately?"</em> Combines
            the raw win rate penalty at low mastery with how much worse low-mastery players perform
            versus medium-mastery players.
          </P>
          <TierTable rows={LEARNING_TIERS} scoreLabel="Score" />

          <Typography variant="subtitle2" gutterBottom fontWeight="bold" sx={{ mt: 2 }}>
            Mastery Effectiveness Score
          </Typography>
          <Box
            component="pre"
            sx={{
              fontFamily: 'monospace',
              bgcolor: 'action.hover',
              p: 1,
              borderRadius: 1,
              mb: 1,
              fontSize: '0.8rem',
              overflowX: 'auto',
            }}
          >
            {'Mastery Score = (High WR% − 50) + (High Ratio − 1) × 50'}
          </Box>
          <P>
            Answers: <em>"Which champions reward the most from investing time to master them?"</em>{' '}
            Combines the absolute win rate at high mastery with how much high-mastery players
            outperform medium-mastery players.
          </P>
          <TierTable rows={MASTERY_TIERS} scoreLabel="Score" />

          <Typography variant="subtitle2" gutterBottom fontWeight="bold" sx={{ mt: 2 }}>
            Investment Score
          </Typography>
          <Box
            component="pre"
            sx={{
              fontFamily: 'monospace',
              bgcolor: 'action.hover',
              p: 1,
              borderRadius: 1,
              mb: 1,
              fontSize: '0.8rem',
              overflowX: 'auto',
            }}
          >
            {'Investment Score = Learning Score × 0.4 + Mastery Score × 0.6'}
          </Box>
          <P>
            Answers: <em>"Which champions are the best total investment?"</em> Weighted 60% toward
            mastery payoff since most players care more about the ceiling than the starting point.
            Visible in the All Stats tab.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Mastery Buckets">
          <P>
            Champions are grouped into three buckets based on the player's current mastery points on
            that champion at the time of data collection:
          </P>
          <Table size="small" sx={{ mb: 1 }}>
            <TableHead>
              <TableRow>
                <TableCell>Bucket</TableCell>
                <TableCell>Mastery Points</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Low</TableCell>
                <TableCell>{'< 10,000'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Medium</TableCell>
                <TableCell>10,000 – 100,000</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>High</TableCell>
                <TableCell>{'100,000+'}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <P>
            Ratios compare bucket win rates to the Medium bucket (the baseline). A Low Mastery Ratio
            of 0.95 means low-mastery players win 5% less often than medium-mastery players on the
            same champion.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="ELO Filters">
          <P>
            Data is collected for all Emerald+ players but can be filtered at analysis time. Use the
            toggle in the header to switch between filters:
          </P>
          <Table size="small" sx={{ mb: 1 }}>
            <TableHead>
              <TableRow>
                <TableCell>Filter</TableCell>
                <TableCell>Tiers Included</TableCell>
                <TableCell>When to Use</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Emerald+</TableCell>
                <TableCell>Emerald, Diamond, Master, GM, Challenger</TableCell>
                <TableCell>Broadest dataset, most statistical power</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Diamond+</TableCell>
                <TableCell>Diamond, Master, GM, Challenger</TableCell>
                <TableCell>Excludes Emerald; tighter skill range</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Diamond 2+</TableCell>
                <TableCell>Diamond II+, Master, GM, Challenger</TableCell>
                <TableCell>High-end only; smallest sample, highest elo</TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <P>
            Higher filters have smaller sample sizes, which means more champions will show "low
            data" in the rarer mastery buckets.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Pabu Beta Views (β)">
          <P>
            The <strong>Pabu β</strong> views are experimental analyses that apply an elo-normalized
            threshold instead of the fixed 50% win rate baseline.
          </P>
          <Typography variant="subtitle2" gutterBottom fontWeight="bold">
            Why not 50%?
          </Typography>
          <P>
            In a perfectly symmetric dataset the average win rate is exactly 50%, but real sampling
            (region balance, mastery-coverage bias) shifts it slightly. The Pabu threshold uses the
            bracket's <em>empirical average win rate</em> — the actual observed mean across all
            tracked participants. This is an <em>excess win rate</em> frame: a champion "crosses the
            threshold" when players start contributing positively above what an average player in
            that bracket already achieves.
          </P>
          <Typography variant="subtitle2" gutterBottom fontWeight="bold">
            Pabu Easiest to Learn β
          </Typography>
          <P>
            Same structure as Easiest to Learn, but "Est. Games" now estimates how many games until
            the champion's win rate exceeds the elo bracket average rather than 50%. Champions that
            barely cross 50% but remain below the elo average will appear as "never reaches
            threshold" here.
          </P>
          <Typography variant="subtitle2" gutterBottom fontWeight="bold">
            Pabu Best to Master β
          </Typography>
          <P>
            Same scoring as Best to Master, but mastery buckets use a <strong>30,000-point</strong>{' '}
            medium boundary instead of 10,000. This shifts more players into the "low mastery" bucket,
            giving a broader view of early-investment performance.
          </P>
          <Table size="small" sx={{ mb: 1 }}>
            <TableHead>
              <TableRow>
                <TableCell>Bucket</TableCell>
                <TableCell>Mastery Points</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Low</TableCell>
                <TableCell>{'< 30,000'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Medium</TableCell>
                <TableCell>30,000 – 100,000</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>High</TableCell>
                <TableCell>{'100,000+'}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <Typography variant="subtitle2" gutterBottom fontWeight="bold">
            Pabu Mastery Curve β
          </Typography>
          <P>
            Same interactive chart as Mastery Curve, but shows two reference lines: a solid 50%
            line and a dashed line at the elo bracket's empirical average win rate. This makes it
            easy to see whether a champion exceeds the meaningful performance baseline at each
            mastery level.
          </P>
          <P>
            <em>These views are experimental and may change in future releases.</em>
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Reading the Table">
          <P>
            <strong>Color coding:</strong> Win rate cells are colored green when {'>'} 52%, red when{' '}
            {'<'} 48%, and gray/neutral for 48–52%. This makes it easy to spot champions that
            perform well or poorly in a given bucket at a glance.
          </P>
          <P>
            <strong>Sorting:</strong> Click any column header to sort ascending or descending. The
            default sort for Easiest to Learn is Learning Score descending; for Best to Master it is
            Mastery Score descending.
          </P>
          <P>
            <strong>"low data":</strong> A bucket shows "low data" when fewer than 100 games exist
            for that champion in that bucket. Scores and ratios that depend on "low data" buckets
            are omitted from rankings.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Data Limitations">
          <P>
            <strong>Mastery is a current snapshot.</strong> Champion mastery is fetched at
            collection time, not at the time each match was played. A player who has gained mastery
            since their match was recorded will appear in a higher bucket than they were in during
            that match. This affects all bucket win rates and is a known limitation shared with the
            original Gold-elo study.
          </P>
          <P>
            <strong>Minimum sample size.</strong> A minimum of 100 games per bucket per champion is
            required for a stat to be reported. Champions played infrequently (especially in High
            mastery) will show "low data" in those cells.
          </P>
          <P>
            <strong>Mastery curve intervals.</strong> The Mastery Curve view only shows data points
            where sufficient games exist in that interval. Sparse intervals are hidden rather than
            shown with misleading small-sample numbers.
          </P>
        </Section>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  )
}
