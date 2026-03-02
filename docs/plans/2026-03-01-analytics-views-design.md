# Design: Analytics Views Expansion + Dual Help Modals

**Date:** 2026-03-01
**Status:** Approved

---

## Goal

Answer five analytical questions about champion learning curves through enriched existing views, one new dedicated tab, one new scatter chart view, and split help documentation into a User Guide and a Methodology reference.

### The Five Questions

| # | Question | Primary Signal | Where It Lives |
|---|---|---|---|
| Q1 | What champions are easiest to learn? | `low_ratio` + `initial_wr` + `slope_tier` | easiest_to_learn (enriched) |
| Q2 | Which give the best rewards for consistent play? | `high_ratio` + `growth_type` + `late_slope` | best_to_master (enriched) |
| Q3 | What to play when off-roled (few games available)? | `initial_wr` + `slope_tier` + `estimated_games` | New "Off-Role Picks" tab |
| Q4 | How many games before you start to matter? | `inflection_games` (scatter X-axis) | slope_iterations (enriched) + scatter chart |
| Q5 | When do gains plateau — when to diversify? | `peak_wr − initial_wr` + `growth_type` (scatter Y-axis) | scatter chart |

---

## Approach: Column Enrichment + One Scatter Chart + One New Tab + Dual Modals

### Overview

- Enrich three existing table views with cross-joined slope iteration fields
- Add a new `off_role` view tab sourced from slope_iterations sorted by floor WR
- Add a new `learning_profile` scatter chart view answering Q4 + Q5
- Split the single help button into User Guide (how-to) and Methodology (technical)

---

## New View: Off-Role Picks (`ViewMode = 'off_role'`)

**Purpose:** "I can only put 3–5 games in — what champion has the highest floor and gets viable fastest?"

**Data source:** `slopeIterations` joined with `gameTo50` lookup map.

**Default sort:** `initial_wr` descending (highest floor WR first).

**Columns:**

| Column | Field | Notes |
|---|---|---|
| Champion | `champion` | Name + icon |
| Lane | `most_common_lane` | Formatted lane string |
| Pickup | `slope_tier` | Chip: Easy / Mild / Hard / Very Hard |
| Floor WR | `initial_wr` | WR in the 5–25 games bracket (color-coded) |
| Est. Games to 50% | `estimated_games` + `games_to_50_status` | Chip for status + numeric value |
| Peak WR | `peak_wr` | Ceiling WR if you invest deeply (color-coded) |

**Filters:** Rare picks toggle + lane filter both apply. Uses `slopeIterationsByLane` when a lane is selected.

---

## Column Enrichments to Existing Views

All new columns are sourced via a `slopeIterationsMap: Map<string, SlopeIterationStat>` computed in `App.tsx`, keyed by champion name. This map is built from `data.slopeIterations` and used to cross-join fields onto `ChampionStat` rows at render time (or in a dedicated `useMemo`).

### Easiest to Learn — additions

| New Column | Field | Purpose |
|---|---|---|
| Pickup | `slope_tier` | How steep is the early curve? Adds pickup difficulty context alongside the ratio-based ranking. |
| Floor WR | `initial_wr` | Absolute floor: what WR will you have in your first ~10 games? |

### Best to Master — additions

| New Column | Field | Purpose |
|---|---|---|
| Growth | `growth_type` | Plateau / Gradual / Continual chip — does the champion keep rewarding mastery? |
| Late Slope | `late_slope` | WR gain in the 100k+ bracket in pp — the "is it still worth investing?" signal. |
| Games to Plateau | `inflection_games` | How many games until you hit near-peak performance? |

### Slope Iterations — additions

| New Column | Field | Purpose |
|---|---|---|
| Est. Games to 50% | `estimated_games` + `games_to_50_status` | Joins from `gameTo50` lookup. The missing Q4 signal currently absent from this view. |

---

## New View: Learning Profile Scatter Chart (`ViewMode = 'learning_profile'`)

**Purpose:** Population-level view of Q4 (time to matter) and Q5 (diminishing returns) across all champions simultaneously.

### Axes

| Axis | Field | Answers |
|---|---|---|
| X | `inflection_games` | Q4: How many games until you plateau / reach near-peak WR? |
| Y | `peak_wr − initial_wr` (pp) | Q5: Is there meaningful WR gain to be had at all from investing? |

### Visual Encoding

- **Color:** slope_tier (reuses existing `SLOPE_TIER_COLORS` palette)
- **Dot size:** scales with `medium_games` (larger = more data = more confident result)
- **Hover:** champion card showing champion name, slope_tier, initial_wr, peak_wr, inflection_games, growth_type
- **Click:** navigates to Mastery Curve for that champion (`handleNavigateToMasteryCurve`)

### Quadrant Labels

Reference lines at `median(inflection_games)` on X and `3pp` on Y divide the chart into four interpretive quadrants:

| Quadrant | Label | Interpretation |
|---|---|---|
| Top-left (fast plateau, high gain) | "Pick up & commit" | Easy to learn, strong ceiling — best all-round investment |
| Top-right (slow plateau, high gain) | "Deep investment" | Takes many games but keeps rewarding mastery |
| Bottom-left (fast plateau, low gain) | "Off-role safe" | Competent quickly, won't improve much — ideal with few games |
| Bottom-right (slow plateau, low gain) | "Avoid" | Takes forever and doesn't reward mastery |

### Filters

Lane filter applies (uses `slopeIterationsByLane` when a specific lane is selected). Rare picks toggle applies (hides champions below `0.5% × total_unique_players` in medium_games).

### Library

Recharts `ScatterChart` (already a project dependency via recharts used in `SlopeIterationsView`).

---

## Dual Help Modals

The current single `HelpOutlineIcon` ("Help & methodology") in `Header.tsx` is replaced by two icon buttons:

### Button 1: User Guide (`MenuBookIcon`, tooltip "User Guide")

New component: `UserGuideModal.tsx`

Content structure (goal-first framing, not technical):

1. **Getting Started** — What each tab is for in plain language
2. **Finding the Right Champion**
   - "I want to pick up something new" → Easiest to Learn, sort by Floor WR, look for Easy Pickup
   - "I want to main a champion long-term" → Best to Master, look for Continual growth
   - "I'm off-roled and need something safe" → Off-Role Picks, sort by Floor WR
   - "I want to know how long it'll take" → Slope Iterations or Learning Profile chart
3. **Reading the Scatter Chart** — How to interpret the four quadrants, what X and Y mean in plain terms
4. **ELO Filters** — When to use each (broader data vs. higher-elo specificity)
5. **Lane Filter** — What it does, the mastery-axis caveat for lane-filtered curves
6. **Reading the Tables** — Color coding, sorting, "low data" cells, CI on hover

### Button 2: Methodology (`ScienceIcon`, tooltip "Technical Methodology")

Repurposed from current `HelpModal.tsx`. Renamed to `MethodologyModal.tsx`.

Content stays the same as current HelpModal, with additions for new views:

- New entry under "Views" for Off-Role Picks and Learning Profile
- New entry under "Scoring Methodology" for the scatter chart axes (inflection_games derivation, peak_wr − initial_wr definition)

---

## Data Layer Changes

### `ParsedData` (useAnalysisData.ts)

No new fields needed on `ParsedData` itself. Cross-joining is done in `App.tsx` via lookup maps:

```ts
const slopeMap = useMemo(
  () => new Map(data.slopeIterations.map(s => [s.champion, s])),
  [data]
)

const g50Map = useMemo(
  () => new Map(data.gameTo50.map(e => [e.champion_name, e])),
  [data]
)
```

### `ViewMode` type (analysis.ts)

Add two values:

```ts
| 'off_role'
| 'learning_profile'
```

---

## Files to Create

| File | Purpose |
|---|---|
| `web/src/components/OffRoleView.tsx` | New off-role picks table (SlopeIterationStat rows enriched with g50 data) |
| `web/src/components/LearningProfileChart.tsx` | Scatter chart for Q4/Q5 |
| `web/src/components/UserGuideModal.tsx` | New user guide modal |

## Files to Modify

| File | Change |
|---|---|
| `web/src/types/analysis.ts` | Add `off_role` and `learning_profile` to `ViewMode` |
| `web/src/components/HelpModal.tsx` | Rename to `MethodologyModal.tsx`, add new-view entries |
| `web/src/components/Header.tsx` | Split one help button into two (UserGuide + Methodology) |
| `web/src/components/TableControls.tsx` | Add `off_role` and `learning_profile` to view toggle options |
| `web/src/utils/columns.ts` | Add enriched column sets for easiest_to_learn and best_to_master |
| `web/src/components/SlopeIterationsView.tsx` | Add Est. Games to 50% column |
| `web/src/App.tsx` | Add routing/data logic for two new views; slopeMap + g50Map lookups |

---

## Out of Scope

- No backend/analysis.py changes — all new data is already computed and present in the JSON
- No new API calls
- No changes to CSV export or visualization scripts
