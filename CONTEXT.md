# Project Context: Champion Mastery Analysis

## Purpose

Replication and extension of [Jack J's Champion Mastery study](https://jackjgaming.substack.com/p/mastery-a-statistical-summary-of) (originally ~1M Gold-elo games, patch 13.7). This project targets **Emerald+ elo** across NA, EUW, and KR to investigate how the mastery-to-winrate relationship changes at higher skill levels.

The original study found sub-10k mastery players had a **44% win rate** vs **51.5%** for 10k+.

## Architecture

Three-layer pipeline, each phase runnable independently:

```
Collection (Riot API → SQLite) → Analysis (SQLite → JSON) → Output (JSON → Charts + CSVs)
```

### Data Flow

1. **collect_players.py** — League-v4 API → `players` table (PUUIDs by tier/region)
2. **collect_matches.py** — Match-v5 API → `match_ids` + `match_participants` tables
3. **collect_mastery.py** — Champion-Mastery-v4 API → `champion_mastery` table
4. **analyze.py** — SQLite joins → JSON results per elo filter
5. **visualize.py** — JSON → PNG charts (matplotlib/seaborn)
6. **export_csv.py** — JSON → CSVs matching original study's spreadsheet format

## Tech Stack

- **Python 3.10+**
- **SQLite** (WAL mode, `data/mastery_analysis.db`)
- **requests** — HTTP client for Riot API
- **matplotlib + seaborn** — chart generation
- **pandas** — data manipulation (listed in requirements, used lightly)
- **tqdm** — progress bars
- **python-dotenv** — `.env` file loading

### Dependencies (`requirements.txt`)

```
requests>=2.31.0
matplotlib>=3.8.0
seaborn>=0.13.0
pandas>=2.1.0
tqdm>=4.66.0
```

## Project Structure

```
src/
  config.py              # All constants: API keys, regions, rate limits, buckets, chart settings
  riot_api.py            # RiotAPIClient with RateLimiter (per-endpoint, per-region, thread-safe)
  db.py                  # Database class: schema init, CRUD, batch ops, analysis queries
  utils.py               # PatchManager, ChampionMapper, logging setup, formatting helpers
  collect_players.py     # Step 1: Emerald+ player lists via league-v4 (paginated + apex)
  collect_matches.py     # Step 2: Match IDs + details via match-v5 (concurrent per-region)
  collect_mastery.py     # Step 3: Champion mastery via champion-mastery-v4 (concurrent)
  analyze.py             # MasteryAnalyzer: all statistics, verification checks
  visualize.py           # 5 chart types per elo filter
  export_csv.py          # 3 CSVs per elo filter matching past-data/ format
data/                    # SQLite DB + caches (gitignored)
output/
  analysis/              # JSON results per filter
  charts/                # PNG charts
  csv/                   # Exported CSVs
past-data/               # Original study's 3 CSVs for format reference
```

## Database Schema

SQLite at `data/mastery_analysis.db`, WAL mode, 60s busy timeout.

| Table | Primary Key | Purpose |
|---|---|---|
| `players` | `puuid` | Player roster with tier, rank, region, summoner_id |
| `match_ids` | `match_id` | Deduplicated match registry with region |
| `match_participants` | `(match_id, puuid)` | 10 rows per match: champion, win, lane, game metadata |
| `champion_mastery` | `(puuid, champion_id)` | Mastery points/level per player-champion pair |
| `collection_progress` | `(task_name, region, key)` | Resumability tracker for all collection scripts |

Key indexes: `players(region)`, `players(tier)`, `match_participants(champion_name)`, `match_participants(puuid)`, `match_participants(game_version)`, `match_participants(puuid, champion_id)`, `champion_mastery(champion_id)`.

## Configuration Constants (`src/config.py`)

### Regions

| Label | Platform (league-v4) | Routing (match-v5) |
|---|---|---|
| NA | na1 | americas |
| EUW | euw1 | europe |
| KR | kr | asia |

### Elo Filters (applied at analysis time, not collection)

| Filter | Tiers |
|---|---|
| `emerald_plus` | Emerald, Diamond, Master, Grandmaster, Challenger |
| `diamond_plus` | Diamond, Master, Grandmaster, Challenger |
| `diamond2_plus` | Diamond II+, Master, Grandmaster, Challenger |

### Mastery Buckets

| Bucket | Range |
|---|---|
| Low | 0 – 9,999 |
| Medium | 10,000 – 99,999 |
| High | 100,000+ |

### Rate Limits (Production Key)

| Endpoint | /sec | /2min |
|---|---|---|
| league-v4 | 10 | 600 |
| match-v5, champion-mastery-v4, summoner-v4, account-v1 | 20 | 100 |

Dev key: 20/s, 100/2min for all endpoints.

### Other Constants

- `MINIMUM_SAMPLE_SIZE = 100` — per bucket for valid per-champion stats
- `MINIMUM_GAME_DURATION = 300` — skip remakes
- `DEFAULT_MATCH_TARGET = 1,000,000` (~333k per region)
- `TIER_ALLOCATION`: apex 30%, diamond 45%, emerald 25%
- `CHART_DPI = 150`, large charts 12x8, medium 10x8, mastery cap 250k

## Key Design Decisions

1. **PUUID is the universal key.** League-v4 returns entries with `puuid` directly. Match-v5 and champion-mastery-v4 both use PUUID.

2. **Match deduplication at collection time.** `match_exists()` check before API call — critical since many players share matches.

3. **`individualPosition` for lane assignment.** The `lane` and `role` fields in match-v5 are unreliable. `individualPosition` returns: TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY.

4. **Mastery is a point-in-time snapshot.** Current mastery, not historical. Known limitation shared with original study. Restricting to `--patches current` mitigates.

5. **Rate limiting is per-(endpoint, region).** Thread-safe sliding window with `Retry-After` header respect. Limiter resets on 429.

6. **All collection scripts are resumable.** `collection_progress` table tracks status per task/region/key. Ctrl+C triggers graceful shutdown via signal handler.

7. **Concurrent region processing.** `collect_matches.py` and `collect_mastery.py` use `ThreadPoolExecutor` with one worker per region.

8. **DB retry on lock.** `_retry_on_locked` decorator with exponential backoff handles SQLite contention from concurrent threads.

9. **CSV format matches original exactly.** Two leading empty columns, percentage formatting, annotation cells, `low data` sentinel for insufficient samples.

## CLI Usage

### Collection Phase (sequential, resumable)

```bash
python3 src/collect_players.py [--region NA|EUW|KR] [--dev-key] [--verbose] [--log-file PATH]
python3 src/collect_matches.py --target 1000000 --patches current [--region ...] [--dev-key] [--verbose]
python3 src/collect_mastery.py [--region ...] [--dev-key] [--verbose]
```

Special: `collect_players.py --reset EMERALD_I EMERALD_II` deletes stale players and progress for re-collection.

### Analysis + Output Phase

```bash
python3 src/analyze.py --filter all [--patches current|last3]
python3 src/visualize.py --filter all
python3 src/export_csv.py --filter all
```

`--filter` accepts: `emerald_plus`, `diamond_plus`, `diamond2_plus`, or `all`.

### Dev/Testing Mode

```bash
python3 src/collect_players.py --dev-key --region NA --verbose
python3 src/collect_matches.py --dev-key --region NA --target 1000 --verbose
python3 src/collect_mastery.py --dev-key --region NA --verbose
python3 src/analyze.py --filter emerald_plus
```

## Analysis Outputs

Per elo filter, `analyze.py` produces JSON with:
- **summary** — match count, player/champion counts, win rate, region balance, mastery coverage
- **mastery_distribution** — mean, median, percentiles, bucket counts, by-lane breakdown
- **overall_winrate_by_bucket** — win rate for low/medium/high
- **winrate_curve** — win rate across 11 mastery intervals (0-1k through 1M+)
- **champion_stats** — per-champion win rates, sample sizes, low/high ratios, most common lane
- **lane_impact** — average mastery ratios by lane
- **easiest_to_learn** — champions sorted by low_ratio descending
- **best_to_master** — champions sorted by high_ratio descending

### Verification Checks (run during analysis)

| Check | Expected |
|---|---|
| Overall win rate | 49–51% |
| Region balance | No region >45% or <22% |
| Mastery coverage | >95% of participants have mastery data |
| Champion count | >150 with data |
| Match count | ~1M (within 10%) |

## Known Limitations

1. **Mastery is current, not historical** — biases upward for older matches
2. **Patch scope** — balance changes between patches introduce noise
3. **Sample size** — niche champions may not meet 100-game threshold, especially at higher elo filters
4. **Self-selection bias** — high-mastery players choose champions they're already good at
5. **Elo snapshot timing** — player ranks captured at collection time, may differ from match time

## Environment

- API key via `RIOT_API_KEY` env var (loaded from `.env`)
- `.gitignore` covers: `data/`, `output/`, `.env`, `__pycache__/`, `*.pyc`, `.DS_Store`
