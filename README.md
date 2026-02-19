# Champion Mastery Analysis — Emerald+ Elo

A replication and extension of [Jack J's Champion Mastery statistical analysis](https://jackjgaming.substack.com/p/mastery-a-statistical-summary-of) (originally ~1M Gold-elo games, patch 13.7) — targeting **Emerald+ elo** across NA, EUW, and KR.

The original study found that sub-10k mastery players had a **44% win rate** vs **51.5%** for 10k+. This project investigates how that relationship changes at higher elo, with additional breakdowns by Diamond+ and Diamond II+.

## Prerequisites

- Python 3.10+
- A [Riot Games API key](https://developer.riotgames.com/) (development or production)

## Setup

```bash
# Install dependencies
pip install -r requirements.txt
# or python3 -m pip install -r requirements.txt

# Copy the example env file and add your API key
cp .env.example .env
```

Then edit `.env` and paste in your key:

```
RIOT_API_KEY=RGAPI-your-key-here
```

## Usage

The pipeline has three phases that run in order: **Collection → Analysis → Output**.

### Phase 1: Data Collection

Each collection script is **resumable** — if interrupted (Ctrl+C), it saves progress and picks up where it left off on the next run.

**Step 1 — Collect players** (builds Emerald+ player lists):

```bash
python3 src/collect_players.py
```

**Step 2 — Collect matches** (fetches ranked match data):

```bash
python3 src/collect_matches.py --target 1000000 --patches current
```

**Step 3 — Collect mastery** (fetches champion mastery for each player-champion pair):

```bash
python3 src/collect_mastery.py
```

### Phase 2: Analysis

Computes win rates by mastery bucket, per-champion stats, lane impact, and rankings. Outputs JSON to `output/analysis/`.

```bash
python3 src/analyze.py --filter all
```

### Phase 3: Output

**Generate charts** (saved to `output/charts/`):

```bash
python3 src/visualize.py --filter all
```

**Export CSVs** matching the original study's spreadsheet format (saved to `output/csv/`):

```bash
python3 src/export_csv.py --filter all
```

### Dev/Testing Mode

For testing with a development API key and a smaller dataset:

```bash
python3 src/collect_players.py --dev-key --region NA --verbose
python3 src/collect_matches.py --dev-key --region NA --target 1000 --verbose
python3 src/collect_mastery.py --dev-key --region NA --verbose
python3 src/analyze.py --filter emerald_plus
python3 src/visualize.py --filter emerald_plus
python3 src/export_csv.py --filter emerald_plus
```

## CLI Options

All collection scripts support:

| Flag                   | Description                                  |
| ---------------------- | -------------------------------------------- |
| `--region NA\|EUW\|KR` | Run for a single region (default: all three) |
| `--dev-key`            | Use conservative dev-key rate limits         |
| `--verbose`            | Enable debug logging                         |
| `--log-file PATH`      | Write logs to a file                         |

`collect_players.py` also supports:

| Flag                              | Description                                                                 |
| --------------------------------- | --------------------------------------------------------------------------- |
| `--reset TIER_RANK [TIER_RANK …]` | Delete stale players and reset progress for the given tier/division specs   |

Use `--reset` when your API key has rotated and stored PUUIDs are no longer valid:

```bash
python3 src/collect_players.py --region NA --reset EMERALD_I EMERALD_II EMERALD_III --verbose
```

This deletes the matching players, clears their `collect_players` and `collect_matches` progress entries, then re-collects them with the current API key.

`collect_matches.py` also supports:

| Flag                       | Description                               |
| -------------------------- | ----------------------------------------- |
| `--target N`               | Total match target (default: 1,000,000)   |
| `--patches current\|last3` | Patch range to collect (default: current) |

Analysis/visualization/export scripts support:

| Flag       | Description                                               |
| ---------- | --------------------------------------------------------- |
| `--filter` | `emerald_plus`, `diamond_plus`, `diamond2_plus`, or `all` |

## Elo Filters

Data is collected for all Emerald+ players, then filtered at analysis time:

| Filter          | Tiers Included                                    |
| --------------- | ------------------------------------------------- |
| `emerald_plus`  | Emerald, Diamond, Master, Grandmaster, Challenger |
| `diamond_plus`  | Diamond, Master, Grandmaster, Challenger          |
| `diamond2_plus` | Diamond II+, Master, Grandmaster, Challenger      |

## Project Structure

```
src/
  config.py              # Configuration constants, API keys, rate limits
  riot_api.py            # Riot API client with per-region rate limiting
  db.py                  # SQLite schema and query helpers
  utils.py               # Patch lookup, champion mapping, logging
  collect_players.py     # Step 1: Collect Emerald+ player lists
  collect_matches.py     # Step 2: Collect match IDs + details
  collect_mastery.py     # Step 3: Collect champion mastery data
  analyze.py             # Compute all statistics from collected data
  visualize.py           # Generate charts (matplotlib/seaborn)
  export_csv.py          # Export CSVs matching original study format
data/                    # SQLite DB (gitignored)
output/
  analysis/              # JSON results
  charts/                # Generated chart PNGs
  csv/                   # Exported CSVs
past-data/               # Original study's CSV data for reference
```

## Original Study

- **Reddit post**: `reddit-post.txt` in this repo
- **Original data**: `past-data/` directory (3 CSVs from the Gold-elo study)
- **Article**: [jackjgaming.substack.com](https://jackjgaming.substack.com/p/mastery-a-statistical-summary-of)
