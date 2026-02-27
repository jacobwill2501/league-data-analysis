# Methodology

## Study Overview

This project investigates the relationship between **champion mastery** (a measure of cumulative experience on a specific champion) and **win rate** in League of Legends ranked solo queue. The core question: does playing a champion more actually make you win more, and if so, by how much?

The study builds on Jack J's original Gold-elo analysis by expanding the scope to **Emerald+ players across three major regions** (NA, EUW, KR). By focusing on higher-elo players, we control for baseline game knowledge and isolate the effect of champion-specific experience. Collecting across three regions guards against server-specific meta biases.

## Why the Three-Phase Pipeline

The data collection pipeline runs in a strict order: **players → matches → mastery**. This isn't arbitrary — it's dictated by how the Riot API is structured and by practical efficiency constraints.

### Phase 1: Players First

The Riot Match-v5 endpoint requires a **PUUID** (a player's unique identifier) to look up match history. There is no way to search for "all Emerald+ matches" directly. We must first discover who the Emerald+ players are, then use their PUUIDs to find their games.

The League-v4 API provides this: given a tier and division, it returns all players at that rank. Standard tiers (Emerald, Diamond) are **paginated** — we iterate through pages of 205 entries until exhausted. Apex tiers (Master, Grandmaster, Challenger) return all entries in a **single call** since their populations are small enough.

### Phase 2: Matches Second

With a pool of player PUUIDs, we fetch each player's recent ranked match IDs via Match-v5, then download the full match details. Each match produces 10 participant records — one per player — containing the champion played, win/loss outcome, lane assignment, and game metadata.

This phase reveals which `(puuid, champion_id)` pairs actually exist in ranked games. This is critical for Phase 3.

### Phase 3: Mastery Third

The Champion-Mastery-v4 endpoint takes a specific `(puuid, champion_id)` pair and returns the player's mastery points on that champion. Without match data telling us which pairs to query, we would have to blindly check all 160+ champions per player. That's ~160x more API calls, the vast majority returning data we don't need (champions the player never brought into ranked).

By only querying pairs observed in actual match data, we minimize API calls to only relevant combinations.

## Player Collection

**Script:** `src/collect_players.py`

Players are collected from three regions:

| Region | Platform | Routing |
|--------|----------|---------|
| NA     | na1      | americas |
| EUW    | euw1     | europe   |
| KR     | kr       | asia     |

The tiers collected are Emerald, Diamond, Master, Grandmaster, and Challenger — everything from Emerald upward.

- **Standard tiers** (Emerald I–IV, Diamond I–IV): Fetched via paginated `league-v4/entries` calls. Each page returns up to 205 entries. We iterate until an empty page is returned, with a safety cap at page 200.
- **Apex tiers** (Master, Grandmaster, Challenger): Each has a dedicated endpoint that returns all entries in one call. The tier label is injected into each entry since the API omits it.

Players are stored by PUUID with their tier, division, region, and league points. Duplicate PUUIDs are skipped on insert.

## Match Collection

**Script:** `src/collect_matches.py`

The target is ~1,000,000 total matches (~333,000 per region). To ensure representation across skill levels, matches are allocated by tier group:

| Tier Group | Allocation | Tiers Included |
|------------|-----------|----------------|
| Apex       | 30%       | Challenger, Grandmaster, Master |
| Diamond    | 45%       | Diamond I–IV |
| Emerald    | 25%       | Emerald I–IV |

For each player, we fetch up to 100 recent ranked match IDs. Each match is then downloaded and validated:

- **Queue filter:** Only queue ID 420 (Ranked Solo/Duo)
- **Participant count:** Exactly 10 (rejects corrupted data)
- **Duration filter:** Game must exceed 300 seconds (5 minutes) to exclude remakes

All 10 participants from each valid match are stored, capturing: champion ID/name, win/loss, team, lane/role/position, game duration, game version (patch), and game creation timestamp.

**Deduplication:** Before fetching a match, we check if the match ID already exists in the database. Since multiple collected players may share the same match, this avoids redundant API calls.

**Concurrency:** Regions are collected concurrently using a thread pool, with one worker per region. Within each region, players are processed sequentially to respect rate limits.

## Mastery Collection

**Script:** `src/collect_mastery.py`

After match collection, the database contains a set of `(puuid, champion_id)` pairs from `match_participants`. The mastery collector queries `get_pending_mastery_pairs()` — a LEFT JOIN that finds pairs without a corresponding `champion_mastery` row — and fetches mastery data for each.

Key details:

- **Point-in-time snapshot:** The mastery API returns the player's *current* mastery points, not what they had at the time of the match. This is a known limitation (see below).
- **404 handling:** If the API returns no data for a pair (player has no mastery record for that champion), we store 0 mastery points. This prevents re-fetching on subsequent runs and correctly represents "no meaningful experience."
- **Error resilience:** On API errors, we also store 0 points to avoid infinite retry loops on consistently failing pairs.

## Analysis Approach

**Script:** `src/analyze.py`

The analysis runs independently for each elo filter:

| Filter | Tiers Included |
|--------|---------------|
| `emerald_plus` | Emerald, Diamond, Master, Grandmaster, Challenger |
| `diamond_plus` | Diamond, Master, Grandmaster, Challenger |
| `diamond2_plus` | Diamond II+, Master, Grandmaster, Challenger |

For each filter, the analyzer:

1. **Loads filtered matches** — Joins `match_participants` against `players` to include only matches where at least one participant belongs to the target tier range. Optionally filters by game version (patch).

2. **Joins mastery data** — Each participant record is matched to its `(puuid, champion_id)` mastery entry.

3. **Buckets mastery points** — Each participant–champion pair is assigned to a mastery bucket:
   - **Low:** 0–9,999 points
   - **Medium:** 10,000–99,999 points
   - **High:** 100,000+ points

4. **Computes statistics:**
   - **Overall win rate by bucket** — Are high-mastery games won more often than low-mastery games?
   - **Win rate curve** — Win rate across 11 mastery intervals from 0–1k up to 1M+, producing a continuous curve.
   - **Per-champion stats** — Win rate in each bucket per champion, plus low-to-medium and high-to-medium ratios. Champions with fewer than 100 games in a bucket are flagged as low-data.
   - **Lane impact** — Average mastery-to-winrate ratios grouped by most-common-lane, revealing whether mastery matters more for certain roles.
   - **Rankings** — "Easiest to learn" (highest low/medium ratio) and "Best to master" (highest high/medium ratio) champion lists.

5. **Verification checks:**
   - Overall win rate should be ~50% (49–51% expected range)
   - No single region should exceed 45% or fall below 22% of total matches
   - Mastery coverage (% of participant records with mastery data) should exceed 95%
   - At least 150 unique champions should appear in the dataset

Results are saved as JSON files per elo filter.

## Slope Analysis (Slope Iterations View)

`compute_slope_iterations()` in `analyze.py` produces per-champion learning curve metrics, modelling the Fitts & Posner three-stage skill acquisition model:

### Three Signals

| Signal | Field | Phase |
|---|---|---|
| Pickup difficulty | `early_slope` / `slope_tier` | Cognitive (5–100 games) |
| Games to competency | `inflection_games` | Associative boundary |
| Continual growth | `late_slope` / `growth_type` | Autonomous (100k–end of data) |

### Curve Smoothing

Before computing any metric, raw interval win rates are smoothed using a **games-weighted 3-point moving average**. Each smoothed point is the weighted average of itself and its immediate neighbors, weighted by each interval's game count. This prevents single noisy brackets (e.g. a high-mastery interval with only 200 games) from corrupting metrics. The result has the same length as the input; endpoints naturally use a 2-point average.

### Metric Computation

- **Early slope** — smoothed WR gain across the first 3 intervals (5–100 games).
- **Late slope** — smoothed WR gain across the last 3 intervals (100k to end of available data, including the 1M+ bracket when it has ≥ 200 games). Only computed when there are ≥ 5 intervals so early and late don't overlap.
- **Total slope** — smoothed peak WR minus smoothed initial WR (percentage points).
- **Inflection mastery** — first interval entry point where smoothed WR ≥ smoothed peak − 0.5 pp.
- **Games to competency** — `inflection_mastery / 700` (approximate mastery per game).

`initial_wr` and `peak_wr` are kept as raw (unsmoothed) values since they are display fields shown in the table.

### Tier Labels

**Pickup tier** (based on `early_slope`):
| Label | Threshold |
|---|---|
| Easy Pickup | < 2 pp |
| Mild Pickup | 2–5 pp |
| Hard Pickup | 5–8 pp |
| Very Hard Pickup | ≥ 8 pp |

**Growth type** (based on `late_slope`):
| Label | Threshold |
|---|---|
| Plateau | < 0.5 pp |
| Gradual | 0.5–1.5 pp |
| Continual | ≥ 1.5 pp |

### Interval Filters

Intervals must satisfy:
- `min >= 3500` (skip the 1–5 games band, which is dominated by selection bias)
- `games >= 200` (stricter threshold than the 100-game visualization threshold)

At least 3 qualifying intervals are required to produce any metrics.

## Key Limitations

1. **Mastery is current, not historical.** The Champion-Mastery-v4 endpoint returns a player's mastery at the time of the API call, not at the time the match was played. A player who had 50k mastery during a match but has since climbed to 200k will be recorded at 200k. This biases mastery values upward for older matches and blurs the relationship somewhat. Restricting to recent patches (the `--patches current` filter) mitigates this by narrowing the time gap.

2. **Patch scope.** Game balance changes between patches can shift champion win rates independently of mastery. The patch filter helps control for this, but combining data across patches introduces some noise.

3. **Sample size requirements.** Per-champion statistics require at least 100 games per mastery bucket to be considered valid. Niche champions or underplayed roles may not meet this threshold, especially at higher elo filters where the player pool shrinks.

4. **Self-selection bias.** Players who have high mastery on a champion likely choose to play that champion because they are already successful with it. The observed correlation between mastery and win rate partially reflects player self-selection, not purely the causal effect of practice.

5. **Elo snapshot timing.** Player ranks are captured at collection time but may have changed between when they played their matches and when we collected their data. A player currently in Diamond may have played some matches while in Emerald.
