# Plan 3: Dynamic Per-Champion Mastery Buckets

## Context

The current analysis uses fixed global mastery buckets (Low: 0-10k, Medium: 10k-100k, High: 100k+) for all champions. This treats "medium mastery" identically whether a champion takes 5 games or 100 games to become viable. The user wants a second set of CSVs where "medium mastery" is defined per-champion: a player has medium mastery once they've played enough games for that champion to reach 50% win rate. The recently implemented `compute_games_to_50_winrate()` already provides each champion's threshold.

**Existing CSVs remain untouched.** The new "Dynamic" CSVs are additive.

## Files to Modify

| File | Change |
|------|--------|
| `src/analyze.py` | Add `compute_dynamic_champion_stats()` method, call it in `analyze()`, add dynamic rankings to results |
| `src/export_csv.py` | Add 3 new `export_dynamic_*()` functions, wire into `export_all_csvs()` |
| `plan3.md` | Write this plan to repo root |

## Step 1: Add `compute_dynamic_champion_stats()` to `src/analyze.py`

New method on `MasteryAnalyzer`, placed after `compute_champion_stats()`.

**Signature:** `def compute_dynamic_champion_stats(self, games_to_50: List[Dict]) -> Dict`

**Per-champion bucket logic:**

| Champion Status | Low Bucket | Medium Bucket | High Bucket |
|----------------|-----------|--------------|------------|
| `crosses 50%` | 0 → threshold | threshold → 100k | 100k+ |
| `always above 50%` | *(none — skip)* | 0 → 100k | 100k+ |
| `never reaches 50%` | 0 → 100k | *(none — empty)* | 100k+ |
| `low data` | Skip champion entirely | | |

**Special labels added per champion:**
- `always above 50%` → **"Instantly Viable"**
- `crosses 50%` with threshold ≥ 90,000 → **"Extremely Hard to Learn"**
- `never reaches 50%` → **"Never Viable"**

**Computation:** Same loop over `self.participants` as `compute_champion_stats()`, but using dynamic per-champion bucket boundaries. Same score formulas (learning_score, mastery_score, investment_score), same `MINIMUM_SAMPLE_SIZE` enforcement, same tier labels.

**Extra fields per champion:** `dynamic_status`, `mastery_threshold`, `estimated_games`, `difficulty_label`.

## Step 2: Update `analyze()` method

After `games_to_50 = self.compute_games_to_50_winrate()`:

1. Call `dynamic_champion_stats = self.compute_dynamic_champion_stats(games_to_50)`
2. Build 3 sorted rankings: `dynamic_easiest_to_learn`, `dynamic_best_to_master`, `dynamic_best_investment` (same sort patterns as existing rankings)
3. For `dynamic_easiest_to_learn`: prepend "Instantly Viable" champions (sorted by medium_wr desc) since they have no learning_score but are by definition easiest
4. Add all 4 new keys to the results dict

## Step 3: Add 3 export functions to `src/export_csv.py`

### `export_dynamic_easiest_to_learn()`
- **Filename:** `{filter} - Dynamic Easiest to Learn.csv`
- **Columns:** Lane, Champion, Low WR, Medium WR, Low Ratio, WR Delta, Learning Score, Tier, 50% WR Games, Difficulty
- "Instantly Viable" champions show at top with N/A for low-bucket metrics

### `export_dynamic_best_to_master()`
- **Filename:** `{filter} - Dynamic Best to Master.csv`
- **Columns:** Lane, Champion, Medium WR, High WR, High Ratio, WR Delta, Mastery Score, Tier, 50% WR Games, Difficulty

### `export_dynamic_best_investment()`
- **Filename:** `{filter} - Dynamic Best Investment.csv`
- **Columns:** Lane, Champion, Low WR, High WR, Learning Score, Mastery Score, Investment Score, 50% WR Games, Difficulty

## Step 4: Wire into `export_all_csvs()`

Add calls to the 3 new functions. Update `csvs_per_filter` from 5 to 8.

## Verification

1. `python3 src/analyze.py` → JSON includes `dynamic_champion_stats`, `dynamic_easiest_to_learn`, `dynamic_best_to_master`, `dynamic_best_investment`
2. `python3 src/export_csv.py` → 8 CSVs per filter (5 existing + 3 new Dynamic)
3. Spot-check: "Instantly Viable" champs at top of Dynamic Easiest to Learn
4. Spot-check: "Extremely Hard to Learn" flag on champs with threshold ≥ 90k
5. Existing CSVs unchanged
