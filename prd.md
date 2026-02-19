# PRD: Champion Mastery Analysis for Emerald+ Elo

## Overview

Replicate and extend the Champion Mastery statistical analysis originally conducted on ~1M Gold-elo games (patch 13.7, NA/EUW/KR) — but for **Emerald+ elo**. The original study found sub-10k mastery players had a 44% win rate vs 51.5% for 10k+. We want to see how this changes at higher elo.

**Original study:** `reddit-post.txt` in this repo
**Original data:** `past-data/` directory (3 CSVs)

---

## Architecture

Three layers, each runnable independently:

1. **Data Collection** — Collect from Riot API, store in SQLite
2. **Analysis** — Compute mastery statistics from SQLite
3. **Visualization/Export** — Charts + CSV files matching past-data format

---

## Project Structure

```
src/
  config.py              # Config, API keys, rate limits, elo filters
  riot_api.py            # API client with rate limiting (prod + dev key support)
  db.py                  # SQLite schema and helpers
  utils.py               # Patch version lookup, logging helpers
  collect_players.py     # Step 1: Get Emerald+ player lists via league-v4
  collect_matches.py     # Step 2: Get match IDs + details via match-v5
  collect_mastery.py     # Step 3: Get champion mastery via champion-mastery-v4
  analyze.py             # Compute all statistics
  visualize.py           # Generate charts (matplotlib/seaborn)
  export_csv.py          # Export CSVs matching past-data format
data/                    # SQLite DB (gitignored)
output/charts/           # Generated charts
output/csv/              # Generated CSVs
requirements.txt         # Python dependencies
.gitignore               # data/, output/, .env, __pycache__
```

---

## Configuration (`src/config.py`)

### API Key

- Read from environment variable `RIOT_API_KEY`
- Support `--dev-key` CLI flag on all collection scripts to use conservative dev-key rate limits instead of production limits

### Regions

| Region Label | Platform (match-v5 routing) | Platform (league-v4) |
|---|---|---|
| NA | `americas` | `na1` |
| EUW | `europe` | `euw1` |
| KR | `asia` | `kr` |

Target: equal split across all three regions.

### Elo Filters

All data is collected for Emerald+ players. Analysis is then run separately for each filter:

| Filter Name | Tiers Included | Config Key |
|---|---|---|
| `emerald_plus` | Emerald, Diamond, Master, Grandmaster, Challenger | `emerald_plus` |
| `diamond_plus` | Diamond, Master, Grandmaster, Challenger | `diamond_plus` |
| `diamond2_plus` | Diamond II+, Master, Grandmaster, Challenger | `diamond2_plus` |

The filter is applied at analysis time, not collection time — we collect all Emerald+ data and filter down.

### Patch Configuration

- `--patches current` (default): Only include matches from the current patch
- `--patches last3`: Include matches from the current and two prior patches
- Use the Riot Data Dragon API to resolve patch versions: `https://ddragon.leagueoflegends.com/api/versions.json`
- Match timestamps are compared against known patch release dates to filter

### Mastery Buckets

Matching the original study exactly:

| Bucket | Range | Label |
|---|---|---|
| Low | < 10,000 | `low` |
| Medium | 10,000 – 100,000 | `medium` |
| High | 100,000+ | `high` |

### Rate Limits (Production Key)

| Endpoint Group | Requests/sec | Requests/2min |
|---|---|---|
| `league-v4` | 10 | 600 |
| `match-v5` | 20 | 100 |
| `champion-mastery-v4` | 20 | 100 |
| `summoner-v4` | 20 | 100 |
| `account-v1` | 20 | 100 |

**Dev key fallback** (when `--dev-key` is passed):

| Endpoint Group | Requests/sec | Requests/2min |
|---|---|---|
| All | 20 | 100 |

Rate limiter must:
- Track per-endpoint-group limits independently
- Track per-region limits independently (each region has its own rate limit bucket)
- Respect `Retry-After` headers on 429 responses
- Use a sliding window approach
- Log rate limit events at DEBUG level

---

## Database Schema (`src/db.py`)

SQLite database stored at `data/mastery_analysis.db`.

### Table: `players`

```sql
CREATE TABLE players (
    puuid TEXT PRIMARY KEY,
    summoner_id TEXT NOT NULL,
    region TEXT NOT NULL,           -- 'NA', 'EUW', 'KR'
    tier TEXT NOT NULL,             -- 'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'
    rank TEXT,                      -- 'I', 'II', 'III', 'IV' (NULL for Master+)
    league_points INTEGER,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_players_region ON players(region);
CREATE INDEX idx_players_tier ON players(tier);
```

### Table: `match_ids`

```sql
CREATE TABLE match_ids (
    match_id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    collected_from_puuid TEXT,      -- which player we found this match through
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table: `match_participants`

```sql
CREATE TABLE match_participants (
    match_id TEXT NOT NULL,
    puuid TEXT NOT NULL,
    champion_id INTEGER NOT NULL,
    champion_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,       -- 100 or 200
    win BOOLEAN NOT NULL,
    lane TEXT,                      -- 'TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY'
    role TEXT,                      -- from participant data
    individual_position TEXT,       -- from participant data (more reliable)
    game_duration INTEGER NOT NULL, -- seconds
    game_version TEXT NOT NULL,     -- patch string e.g. "14.10.123.456"
    queue_id INTEGER NOT NULL,      -- should be 420 (ranked solo)
    game_creation BIGINT NOT NULL,  -- epoch ms
    PRIMARY KEY (match_id, puuid)
);
CREATE INDEX idx_mp_champion ON match_participants(champion_name);
CREATE INDEX idx_mp_puuid ON match_participants(puuid);
CREATE INDEX idx_mp_game_version ON match_participants(game_version);
```

### Table: `champion_mastery`

```sql
CREATE TABLE champion_mastery (
    puuid TEXT NOT NULL,
    champion_id INTEGER NOT NULL,
    mastery_points INTEGER NOT NULL,
    mastery_level INTEGER,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (puuid, champion_id)
);
CREATE INDEX idx_cm_champion ON champion_mastery(champion_id);
```

### Table: `collection_progress`

```sql
CREATE TABLE collection_progress (
    task_name TEXT NOT NULL,        -- 'collect_players', 'collect_matches', 'collect_mastery'
    region TEXT NOT NULL,
    key TEXT NOT NULL,              -- varies: tier/division for players, puuid for matches/mastery
    status TEXT NOT NULL,           -- 'pending', 'in_progress', 'completed', 'failed'
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                  -- JSON blob for extra state (e.g., last cursor/page)
    PRIMARY KEY (task_name, region, key)
);
```

---

## Data Collection Scripts

### General Requirements for All Collection Scripts

- All scripts are resumable: they check `collection_progress` before starting and skip completed work
- All scripts log progress with Python's `logging` module (INFO level by default, DEBUG with `--verbose`)
- All scripts accept `--region` to run for a single region (default: all three)
- All scripts accept `--dev-key` to use conservative rate limits
- All scripts print a summary on completion (records collected, time taken, errors encountered)
- On interrupt (Ctrl+C), gracefully save progress and exit

### Step 1: `collect_players.py`

**Purpose:** Build a list of all Emerald+ players across NA, EUW, KR.

**API Endpoints:**
- `GET /lol/league/v4/entries/{queue}/{tier}/{division}` — for Emerald and Diamond (paginated, iterate I-IV)
- `GET /lol/league/v4/masterleagues/by-queue/{queue}` — all Master players
- `GET /lol/league/v4/grandmasterleagues/by-queue/{queue}` — all Grandmaster players
- `GET /lol/league/v4/challengerleagues/by-queue/{queue}` — all Challenger players

**Note on PUUID resolution:** The league-v4 entries endpoint returns `summonerId` but not `puuid`. We need `puuid` for match-v5 and champion-mastery-v4. Use:
- `GET /lol/summoner/v4/summoners/{encryptedSummonerId}` — returns `puuid`

Batch this PUUID resolution efficiently. Track resolution progress in `collection_progress` so it can resume.

**Queue:** `RANKED_SOLO_5x5` only.

**Output:** Rows inserted into `players` table.

**CLI:**
```
python src/collect_players.py [--region NA|EUW|KR] [--dev-key] [--verbose]
```

### Step 2: `collect_matches.py`

**Purpose:** For each collected player, fetch their recent ranked match IDs, then fetch full match details.

**API Endpoints:**
- `GET /lol/match/v5/matches/by-puuid/{puuid}/ids` — get match IDs
  - Params: `queue=420` (ranked solo), `type=ranked`, `start=0`, `count=100`
  - Apply patch filter: use `startTime` / `endTime` params based on patch dates
- `GET /lol/match/v5/matches/{matchId}` — get full match details

**Match routing:** Use regional routing values (`americas`, `europe`, `asia`), not platform values.

**Deduplication:** Many players will share the same matches. Before fetching match details, check if the `match_id` already exists in `match_ids` table.

**Match validation before storing:**
- `queueId` must be `420` (ranked solo)
- Must have exactly 10 participants
- `gameDuration` must be > 300 seconds (skip remakes)

**Participant extraction:** For each of the 10 participants in a valid match, insert a row into `match_participants` with:
- `match_id`, `puuid`, `championId`, `championName`, `teamId`, `win`
- `individualPosition` (use this for lane assignment — it's more reliable than `lane`/`role` fields)
- `gameDuration`, `gameVersion`, `queueId`, `gameCreation`

**Target:** ~1M total matches (~333k per region). The script should stop collecting for a region once it hits the target. Log progress every 1000 matches.

**CLI:**
```
python src/collect_matches.py [--region NA|EUW|KR] [--target 1000000] [--patches current|last3] [--dev-key] [--verbose]
```

### Step 3: `collect_mastery.py`

**Purpose:** For every unique (puuid, champion_id) pair found in `match_participants`, fetch the player's mastery on that champion.

**API Endpoint:**
- `GET /lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{championId}` — single champion mastery

**Deduplication:** Only fetch mastery data we don't already have. Check `champion_mastery` table first.

**Note:** A player may appear on multiple champions across matches. Fetch mastery for each unique (puuid, champion_id) combination.

**Error handling:** If a player has no mastery data for a champion (404), store mastery_points as 0.

**CLI:**
```
python src/collect_mastery.py [--region NA|EUW|KR] [--dev-key] [--verbose]
```

---

## Analysis (`src/analyze.py`)

**Purpose:** Read from SQLite, compute all statistics, store results as JSON for visualization and export.

**CLI:**
```
python src/analyze.py [--filter emerald_plus|diamond_plus|diamond2_plus|all] [--patches current|last3] [--output output/analysis/]
```

Default `--filter` is `all` (runs all three filters).

### Filter Application

At the start of analysis, determine which matches to include:

1. Get the set of `puuid` values from `players` table matching the current elo filter
2. Get all `match_id` values from `match_participants` where at least one participant is in the filtered player set
3. Apply patch version filter to `game_version`
4. All subsequent analysis uses this filtered match set

### Statistics to Compute

For each elo filter, compute:

#### 1. Mastery Distribution Stats

- Total number of (player, champion) pairs with mastery data
- Mean mastery points
- Median mastery points
- 25th, 75th, 90th, 95th, 99th percentiles
- % of players in each mastery bucket (Low / Medium / High)
- Same stats broken down by lane

#### 2. Win Rate by Mastery Bucket (Overall)

- Overall win rate for Low mastery bucket
- Overall win rate for Medium mastery bucket
- Overall win rate for High mastery bucket
- Win rate curve: compute win rate at intervals (0-1k, 1k-2k, 2k-5k, 5k-10k, 10k-20k, 20k-50k, 50k-100k, 100k-200k, 200k-500k, 500k-1M, 1M+)

#### 3. Win Rate by Mastery Bucket per Champion

For each champion:
- Win rate in Low bucket, sample size
- Win rate in Medium bucket, sample size
- Win rate in High bucket, sample size
- Low Mastery Ratio = low_win_rate / medium_win_rate
- High Mastery Ratio = high_win_rate / medium_win_rate
- Most common lane (by play count in filtered matches)

**Minimum sample size:** Require at least 100 games in a bucket to include the stat. If a bucket has < 100 games, output `"low data"` (matching the original study — see Milio in the Best to Master CSV).

#### 4. "Easiest to Learn" Rankings

Sort champions by Low Mastery Ratio descending (highest ratio = easiest to learn with low mastery).

#### 5. "Best to Master" Rankings

Sort champions by High Mastery Ratio descending (highest ratio = most reward for high mastery).

#### 6. Impact by Lane

For each lane (Top, Jungle, Middle, Bottom/ADC, Support):
- Average Low Mastery win rate across all champions in that lane
- Average Medium Mastery win rate
- Average High Mastery win rate
- Average Low Mastery Ratio
- Average High Mastery Ratio

#### 7. Summary Stats (for verification)

- Total matches analyzed
- Total unique players
- Total unique champions
- Overall win rate (should be ~50%)
- Region balance (count per region)
- Mastery coverage % (how many match_participants have corresponding mastery data)

### Output

Write results as JSON to `output/analysis/{filter_name}_results.json`. Structure:

```json
{
  "filter": "emerald_plus",
  "summary": { ... },
  "mastery_distribution": { ... },
  "overall_winrate_by_bucket": { ... },
  "winrate_curve": [ ... ],
  "champion_stats": { "Aatrox": { ... }, ... },
  "lane_impact": { ... },
  "easiest_to_learn": [ ... ],
  "best_to_master": [ ... ]
}
```

---

## Visualization (`src/visualize.py`)

**Purpose:** Generate charts from analysis JSON files.

**CLI:**
```
python src/visualize.py [--filter emerald_plus|diamond_plus|diamond2_plus|all] [--input output/analysis/] [--output output/charts/]
```

### Charts to Generate

For each elo filter:

1. **Mastery Distribution Histogram** (`{filter}_mastery_distribution.png`)
   - X: mastery points (capped at 250k for readability, matching original)
   - Y: count of players
   - Title: "Distribution of Champion Mastery ({filter})"

2. **Win Rate by Mastery Curve** (`{filter}_winrate_curve.png`)
   - X: mastery bracket (use the intervals from analysis)
   - Y: win rate %
   - Horizontal line at 50%
   - Title: "Mastery Impact on Win Rates ({filter})"

3. **Win Rate by Lane** (`{filter}_lane_impact.png`)
   - Grouped bar chart: lanes on X, bars for Low/Medium/High mastery
   - Y: win rate %
   - Title: "Mastery Impact on Win Rate by Lane ({filter})"

4. **Top 10 Easiest to Learn** (`{filter}_easiest_to_learn.png`)
   - Horizontal bar chart, sorted by Low Mastery Ratio
   - Show champion name + lane

5. **Top 10 Best to Master** (`{filter}_best_to_master.png`)
   - Horizontal bar chart, sorted by High Mastery Ratio
   - Show champion name + lane

### Style

- Use seaborn's default style with a clean white grid
- Consistent color palette across all charts
- DPI: 150
- Figure size: 12x8 for distribution/curve charts, 10x8 for bar charts

---

## CSV Export (`src/export_csv.py`)

**Purpose:** Export CSVs matching the exact format of the original study's spreadsheets in `past-data/`.

**CLI:**
```
python src/export_csv.py [--filter emerald_plus|diamond_plus|diamond2_plus|all] [--input output/analysis/] [--output output/csv/]
```

### Output Files

For each elo filter, generate three CSVs:

#### `{filter} - Data Intro.csv`

Match the exact format of `past-data/Mastery impact by Champion - Data Intro.csv`:

```csv
,,
,,
,,Introduction
,,"This is a replication of Jack J's Champion Mastery analysis for Emerald+ elo."
,,"Original study: https://jackjgaming.substack.com/p/mastery-a-statistical-summary-of"
,,This sheet contains the raw values split into two tabs:
,,Easiest to Learn: The Champions which have the lowest decrease in their win rate when played by someone with low Mastery (<10K)
,,Best to Master: The Champions which gain the most win rate when played by someone with high Mastery (+100K)
,,
,,To sort/filter tables:
,,1. Click into either tab
,,2. Click anywhere on the table
,,"3. In the top bar, click ""Data"" > ""Filter views"" > ""Create new filter view"""
,,4.  Filter or Sort the table by clicking the icon
,,
,,Data Info.
,,~{total_matches} matches
,,Ranked Solo Queue only
,,Patch {patch_version}
,,"Roughly equal mix of EUW, NA & KR"
,,Elo filter: {filter_description}
,,
,,Analysis Details
,,Mastery buckets: Low (<10k) / Medium (10k-100k) / High (100k+)
,,Minimum sample size: 100 games per bucket
```

#### `{filter} - Easiest to Learn.csv`

Match the exact format of `past-data/Mastery impact by Champion - Easiest to Learn.csv`:

```csv
,,Most Common Lane,Champion Name,Low Mastery Win Rate,Medium Mastery Win Rate,Low Mastery Ratio,,,
```

- Columns: `,,Most Common Lane,Champion Name,Low Mastery Win Rate,Medium Mastery Win Rate,Low Mastery Ratio,,,`
- Two leading empty columns (matching original format)
- Three trailing empty columns (matching original format)
- Win rates formatted as percentages with 2 decimal places (e.g., `47.75%`)
- Low Mastery Ratio formatted to 2 decimal places (e.g., `0.93`)
- Sorted by Low Mastery Ratio descending (easiest at top, hardest at bottom)
- Include annotation columns in row 3-8 area explaining the metric (matching original):
  - Row 3, col G: `Low Mastery Ratio`
  - Row 4, col G: `If high:` col H: `Easy to Learn`
  - Row 5, col G: `If low:` col H: `Hard to Learn`
  - Row 7, col G: `Low Mastery:` col H: `<10,000`
  - Row 8, col G: `Medium Mastery:` col H: `10,000-100,000`

#### `{filter} - Best to Master.csv`

Match the exact format of `past-data/Mastery impact by Champion - Best to Master.csv`:

```csv
,,Most Common Lane,Champion Name,Medium Mastery Win Rate,High Mastery Win Rate,High Mastery Ratio,,,
```

- Same structure as Easiest to Learn but with High Mastery columns
- Sorted by High Mastery Ratio descending
- If a champion has insufficient data for the High bucket, show `low data` for both win rate and ratio
- Include annotation columns:
  - Row 3, col G: `High Mastery Ratio`
  - Row 4, col G: `If high:` col H: `Highest benefit to mastering`
  - Row 5, col G: `If low:` col H: `Lowest benefit to mastering`
  - Row 7, col G: `High Mastery:` col H: `100K+`
  - Row 8, col G: `Medium Mastery:` col H: `10,000-100,000`

---

## Utility Functions (`src/utils.py`)

### Patch Version Lookup

- Fetch current patch from Data Dragon: `https://ddragon.leagueoflegends.com/api/versions.json`
- Maintain a mapping of patch version to approximate release date (for `--patches last3` filtering)
- Match `game_version` field (e.g., `"14.10.123.456"`) by comparing the first two version segments (e.g., `"14.10"`)

### Logging

- Consistent log format: `[%(asctime)s] %(levelname)s %(name)s: %(message)s`
- Console handler always present
- Optional file handler when `--log-file` is passed

### Champion ID to Name Mapping

- Fetch from Data Dragon: `https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json`
- Cache locally in `data/champion_mapping.json`

---

## Verification Checks

Run these as part of `analyze.py` and print results to console:

| Check | Expected | Action if Fail |
|---|---|---|
| Total matches analyzed | ~1M (within 10%) | Warning |
| Players per region | Roughly balanced | Warning if any region < 25% of total |
| Participants per match | Exactly 10 | Error — skip match |
| Overall win rate | 49-51% | Warning if outside range |
| Mastery coverage | > 95% of match_participants have mastery data | Warning if below |
| Region balance | No region > 45% or < 22% of matches | Warning |
| Champion count | > 150 champions with data | Warning |
| Bucket sample sizes | Log champions with < 100 games in any bucket | Info |

---

## Dependencies (`requirements.txt`)

```
requests>=2.31.0
matplotlib>=3.8.0
seaborn>=0.13.0
pandas>=2.1.0
tqdm>=4.66.0
```

---

## `.gitignore`

```
data/
output/
.env
__pycache__/
*.pyc
.DS_Store
```

---

## Execution Order

```bash
# 1. Collect players (run once)
python src/collect_players.py

# 2. Collect matches (takes longest — resumable)
python src/collect_matches.py --target 1000000 --patches current

# 3. Collect mastery data (resumable)
python src/collect_mastery.py

# 4. Run analysis
python src/analyze.py --filter all

# 5. Generate visualizations
python src/visualize.py --filter all

# 6. Export CSVs
python src/export_csv.py --filter all
```

For development/testing with a dev key:
```bash
python src/collect_players.py --dev-key --region NA --verbose
python src/collect_matches.py --dev-key --region NA --target 1000 --verbose
python src/collect_mastery.py --dev-key --region NA --verbose
python src/analyze.py --filter emerald_plus
```

---

## Key Implementation Notes

1. **PUUID is the universal key.** League-v4 returns `summonerId`, but match-v5 and champion-mastery-v4 use `puuid`. The collection pipeline must resolve this mapping in Step 1.

2. **Match deduplication is critical.** With ~hundreds of thousands of players, many will share matches. Always check the DB before fetching match details.

3. **`individualPosition` is the correct lane field.** The `lane` and `role` fields in match-v5 are unreliable. Use `individualPosition` which returns: `TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM`, `UTILITY`.

4. **Mastery data is a point-in-time snapshot.** We're getting current mastery, not mastery at the time of the match. This is a known limitation (same as the original study).

5. **Rate limiting must be per-region.** Each region has independent rate limits. The rate limiter should track limits per (endpoint_group, region) pair.

6. **Production key limits vary by endpoint.** The `match-v5` endpoint has different limits than `league-v4`. See the rate limit table above.

7. **Resumability is non-negotiable.** These collection scripts may run for hours/days. Every script must be able to pick up where it left off after interruption.

8. **CSV format must match exactly.** The output CSVs must have the same column structure, formatting, and sorting as the originals in `past-data/`. This includes the two leading empty columns, percentage formatting, and annotation cells.
