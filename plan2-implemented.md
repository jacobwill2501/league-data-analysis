# Plan 2: Games to 50% Win Rate Analysis

## Context

We want a new analysis that answers: **"How many games does it take to reach a 50% win rate on each champion?"** This gives players a practical estimate of the learning investment required per champion.

Since the dataset tracks mastery points (not sequential game history), we'll use mastery points as a proxy for games played, computing per-champion win rates across fine-grained mastery intervals and finding where the win rate crosses 50%. The mastery threshold is then converted to an approximate game count.

## Approach

### 1. Add a new analysis method to `src/analyze.py`

Add `compute_games_to_50_winrate()` to the `MasteryAnalyzer` class.

**Logic:**
- For each champion, compute win rates at fine-grained mastery intervals (reuse `WIN_RATE_INTERVALS` from config or define finer intervals for better resolution)
- For each champion, walk the intervals in order and find where win rate crosses 50%
- Use linear interpolation between the two bounding intervals to estimate the exact mastery-point crossover
- Convert mastery points to approximate game count using **~700 mastery points per game** (standard Riot average)
- Champions that never reach 50% or start above 50% get special labels (e.g., "always above 50%" or "never reaches 50%")
- Enforce `MINIMUM_SAMPLE_SIZE` per interval per champion (skip intervals with too few games)

**Output per champion:**
- `champion_name`
- `lane` (primary lane)
- `mastery_threshold` — mastery points where 50% WR is reached
- `estimated_games` — `mastery_threshold / 700`
- `starting_winrate` — win rate in the lowest mastery interval
- `status` — "crosses 50%", "always above", "never reaches", or "low data"

### 2. Integrate into the analysis pipeline

In `MasteryAnalyzer.run()`, call `compute_games_to_50_winrate()` and store the result in the JSON output under a new key `games_to_50_winrate`.

### 3. Add CSV export in `src/export_csv.py`

Add a new export function `export_games_to_50_winrate()` that generates a CSV per elo filter:
- **Filename:** `{filter_name} - Games to 50 Percent Winrate.csv`
- **Columns:** Lane, Champion, Estimated Games, Mastery Threshold, Starting WR, Status
- **Sorted by:** Estimated Games ascending (champions that are easiest to pick up first)
- Champions that are "always above 50%" listed at the top (0 games needed)
- Champions that "never reach 50%" listed at the bottom

### 4. Wire into `export_csv.py` main flow

Call the new export function alongside the existing 4 CSVs so it runs automatically with `python src/export_csv.py`.

## Files to Modify

| File | Change |
|------|--------|
| `src/analyze.py` | Add `compute_games_to_50_winrate()` method + call it in `run()` |
| `src/export_csv.py` | Add `export_games_to_50_winrate()` function + call it in main |

## Key Existing Code to Reuse

- `WIN_RATE_INTERVALS` from `src/config.py` (may define finer intervals for this analysis)
- `get_mastery_bucket()` pattern from `src/analyze.py`
- `MINIMUM_SAMPLE_SIZE` from `src/config.py` (100 games minimum)
- `format_win_rate()`, `get_lane_display()` from `src/export_csv.py`
- Existing participant + mastery data loading in `MasteryAnalyzer.__init__`

## Verification

1. Run `python src/analyze.py` — confirm JSON output includes `games_to_50_winrate` key
2. Run `python src/export_csv.py` — confirm new CSV is generated in `output/csv/`
3. Spot-check CSV: champions known to be easy (e.g., Garen, Annie) should have low game counts; complex champions (e.g., Azir, Aphelios) should have higher counts
4. Verify "always above 50%" and "never reaches 50%" categories make sense
