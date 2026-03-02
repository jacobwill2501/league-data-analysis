import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'

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

function GoalRow({ goal, action }: { goal: string; action: React.ReactNode }) {
  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1,
        mb: 1,
        alignItems: 'flex-start',
      }}
    >
      <Typography
        variant="body2"
        sx={{
          minWidth: 260,
          fontStyle: 'italic',
          color: 'text.secondary',
          flexShrink: 0,
        }}
      >
        {goal}
      </Typography>
      <Typography variant="body2">{action}</Typography>
    </Box>
  )
}

export function UserGuideModal({ open, onClose }: Props) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth scroll="paper">
      <DialogTitle>How to Use This Dashboard</DialogTitle>

      <DialogContent dividers>
        <Section title="Getting Started">
          <P>
            Each tab in this dashboard answers a different question about champion learning. Here is
            what each view is for:
          </P>
          <P>
            <strong>Easiest to Learn</strong> — Which champions perform well with very little
            experience? Use this tab when you want to pick up something new without a steep early
            penalty.
          </P>
          <P>
            <strong>Best to Master</strong> — Which champions keep rewarding you the more you play
            them? Use this tab when you want a long-term main with a high skill ceiling.
          </P>
          <P>
            <strong>Off-Role Picks</strong> — Which champions are safest to play when you are out of
            position? Ranked by how well low-mastery players perform, filtered to champions commonly
            played in multiple roles.
          </P>
          <P>
            <strong>Slope Iterations</strong> — Detailed learning curve stats broken into three
            phases: how hard the pickup is, how long until you hit peak performance, and whether the
            champion keeps growing past that point.
          </P>
          <P>
            <strong>Learning Profile</strong> — A scatter chart plotting every champion by learning
            speed (X axis) and win rate ceiling (Y axis). Useful for quickly comparing categories of
            champions at a glance.
          </P>
          <P>
            <strong>Mastery Curve</strong> — A line chart for a single champion showing win rate
            across mastery brackets from first game to veteran level. Use this when you want to see
            the full arc of a specific champion's learning curve.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Finding the Right Champion">
          <P>
            Match your goal to the right tab and sort to find what you need:
          </P>
          <GoalRow
            goal='"I want to pick up something new"'
            action={
              <>
                Go to <strong>Easiest to Learn</strong>, sort by Floor WR descending, and look for
                champions with an <strong>Easy Pickup</strong> chip.
              </>
            }
          />
          <GoalRow
            goal='"I want to main a champion long-term"'
            action={
              <>
                Go to <strong>Best to Master</strong> and look for champions with a{' '}
                <strong>Continual</strong> growth type — these keep rewarding mastery past the early
                learning phase.
              </>
            }
          />
          <GoalRow
            goal='"I am off-roled and need something safe"'
            action={
              <>
                Go to <strong>Off-Role Picks</strong> and sort by Floor WR. Champions near the top
                of this list lose the least when played with low mastery.
              </>
            }
          />
          <GoalRow
            goal='"I want to know how long it will take"'
            action={
              <>
                Check <strong>Slope Iterations</strong> for the Games to Competency column, or open
                the <strong>Learning Profile</strong> chart and read the X axis (Games to Plateau).
              </>
            }
          />
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Reading the Scatter Chart">
          <P>
            The Learning Profile chart plots every champion on two axes:
          </P>
          <P>
            <strong>X axis — Games to Plateau:</strong> How many games it takes until your win rate
            levels off. Champions on the left plateau quickly; champions on the right take longer to
            reach their ceiling.
          </P>
          <P>
            <strong>Y axis — WR Gain:</strong> How much your win rate improves from your first game
            to your peak. Champions at the top have a high skill ceiling; champions at the bottom
            perform similarly at all mastery levels.
          </P>
          <P>
            The chart is divided into four quadrants by the median of each axis:
          </P>
          <Box sx={{ pl: 2, mb: 1 }}>
            <P>
              <strong>Top-left — "Pick up and commit":</strong> Fast to plateau, high WR gain.
              These champions are the best overall investment — you reach their ceiling quickly and
              that ceiling is high.
            </P>
            <P>
              <strong>Top-right — "Deep investment":</strong> Slow to plateau, high WR gain. High
              ceiling but a long road to get there. Worth it if you plan to play the champion
              extensively.
            </P>
            <P>
              <strong>Bottom-left — "Off-role safe":</strong> Fast to plateau, low WR gain. Low
              learning curve and consistent performance from the start. Good for off-role or flex
              situations.
            </P>
            <P>
              <strong>Bottom-right — "Avoid":</strong> Slow to plateau, low WR gain. These
              champions demand significant investment but don't pay off with a meaningfully higher
              ceiling.
            </P>
          </Box>
          <P>
            <strong>Dot size</strong> reflects the volume of data for that champion. Larger dots
            mean more games were recorded, making the position on the chart more reliable.
          </P>
          <P>
            <strong>Click any dot</strong> to open the full Mastery Curve for that champion and see
            the win rate arc across all mastery brackets.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="ELO Filters">
          <P>
            Use the ELO toggle in the header to switch between three data sets:
          </P>
          <P>
            <strong>Emerald+</strong> — The largest dataset, covering Emerald through Challenger.
            Best for general champion picks. Most champions will have enough data for reliable
            stats.
          </P>
          <P>
            <strong>Diamond+</strong> — Excludes Emerald. Useful for a tighter skill range where
            Emerald-level play does not factor in. Sample sizes are smaller, so more champions may
            show low data warnings.
          </P>
          <P>
            <strong>Diamond 2+</strong> — The smallest and highest-elo dataset. Best for
            high-elo-specific questions. Expect more low data cells, especially for niche champions.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Lane Filter">
          <P>
            The lane selector (visible in most views) filters all tables and charts to show stats
            for that role only. When a lane is selected:
          </P>
          <P>
            Tables draw from per-lane stats, so flex picks like Lux appear in every role they are
            commonly played — not just their most frequent one. Win rates and scores reflect only
            games played in that lane.
          </P>
          <P>
            <strong>Important:</strong> The mastery axis on lane-filtered curves shows{' '}
            <em>total champion mastery</em>, not role-specific mastery. This is a Riot API
            limitation — per-role mastery data is not available. A player with 50,000 total mastery
            on a champion may have only played 10 of those games in the selected lane.
          </P>
        </Section>

        <Divider sx={{ my: 2 }} />

        <Section title="Reading the Tables">
          <P>
            <strong>Win rate colors:</strong> Win rate cells are colored green when above 52%, red
            when below 48%, and neutral for values in between. This makes it easy to spot champions
            that over- or under-perform at a given mastery level at a glance.
          </P>
          <P>
            <strong>Rare Picks toggle:</strong> Enabling this filter hides champions with very few
            total games in the dataset. Stats for rare picks are less reliable, so toggling this
            off keeps the table focused on champions with enough data to be meaningful.
          </P>
          <P>
            <strong>Pickup chip:</strong> The colored chip in the Slope Iterations view shows how
            steep the early learning curve is — <strong>Easy</strong>, <strong>Mild</strong>,{' '}
            <strong>Hard</strong>, or <strong>Very Hard</strong>. A faded chip with a "?" means the
            tier is statistically uncertain: the champion is close to the boundary between two
            categories. Hover the chip to see the confidence interval.
          </P>
          <P>
            <strong>Growth type:</strong> <strong>Continual</strong> means the champion's win rate
            keeps climbing meaningfully at 100,000+ mastery. <strong>Plateau</strong> means the win
            rate levels off after the basics are learned. Use growth type to decide whether long-term
            investment is worthwhile.
          </P>
          <P>
            <strong>Sorting:</strong> Click any column header to sort ascending or descending.
            Hover a column header to see a tooltip explaining what that column measures.
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
