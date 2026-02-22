# Champion Mastery Web App — Implementation Plan

## Status

| Plan | Description | State |
|------|-------------|-------|
| Plan 2 | Games to 50% Win Rate analysis + CSV export | ✅ Implemented (staged) |
| Plan 3 | Dynamic per-champion mastery buckets + CSV exports | ✅ Implemented (staged) |
| **This Plan** | React web app to explore analysis data | 🔄 In Progress |

**Analysis JSON files** are ready in `output/analysis/` (3 elo tiers).

---

## Context

The project outputs analysis as JSON files (3 elo tiers × 172 champions). We want a single-page React app to explore this data interactively — one table where the user configures everything (view, elo, filters, sort) from controls above the table. Fully static, deployable to GitHub Pages.

---

## Tech Stack

| Tool | Purpose | Notes |
|------|---------|-------|
| Vite + React + TypeScript | App framework | `web/` subdirectory |
| @tanstack/react-table v8 | Headless table (sort/filter) | ~15 KB |
| Tailwind CSS v4 | Styling | Via `@tailwindcss/vite` plugin, no config file |
| Data Dragon CDN | Champion icons | Riot's official asset CDN |

No router needed — single page app, all state in React.

---

## Project Structure

```
web/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  public/
    data/
      emerald_plus_results.json
      diamond_plus_results.json
      diamond2_plus_results.json
  src/
    main.tsx
    App.tsx                        # Single page: header + controls + table
    types/
      analysis.ts                  # TS interfaces for JSON data
    hooks/
      useAnalysisData.ts           # Fetch + parse JSON by elo filter
      useTheme.ts                  # Dark/light mode + localStorage
    components/
      Header.tsx                   # Title, elo selector, theme toggle
      TableControls.tsx            # View selector, search, lane filter, tier filter
      ChampionTable.tsx            # @tanstack/react-table instance
      ChampionIcon.tsx             # Data Dragon portrait (32×32, lazy)
    utils/
      format.ts                    # Percentage, ratio, score formatting
      columns.ts                   # Column definitions per view preset (8 views)
      championMapping.ts           # Display name → Data Dragon key
    styles/
      index.css                    # @import "tailwindcss" + custom theme vars
```

---

## Single Page Layout

```
┌─────────────────────────────────────────────────────┐
│  Header: Title | Elo Selector | Theme Toggle        │
├─────────────────────────────────────────────────────┤
│  Controls:                                          │
│  [View: ▾] [Search...] [Lane: ▾] [Tier: ▾]        │
│                               Showing 43 of 172     │
├─────────────────────────────────────────────────────┤
│  # │ 🖼 Champion │ Lane │ Score │ Tier │ WR │ ...   │
│  1 │ ...         │      │       │      │    │       │
│  2 │ ...         │      │       │      │    │       │
│  ...                                                │
└─────────────────────────────────────────────────────┘
```

### Controls Bar

**View Selector** (dropdown) — switches which columns are shown and the default sort:

**Standard views** (use fixed global mastery buckets: Low <10k, Medium 10k-100k, High 100k+):
1. Easiest to Learn (default)
2. Best to Master
3. Best Investment
4. All Stats

**Dynamic views** (use per-champion mastery thresholds from Plan 2/3):
5. Dynamic Easiest to Learn
6. Dynamic Best to Master
7. Dynamic Best Investment
8. Games to 50% Win Rate

**Elo Selector** (toggle/dropdown):
- Emerald+ | Diamond+ | Diamond 2+

**Search** — case-insensitive champion name filter

**Lane Filter** — ALL / Top / Jungle / Mid / Bot / Support

**Tier Filter** — contextual to current view (learning tiers or mastery tiers)

**Row Count** — "Showing X of Y champions"

All controls update the single table in place. No page navigation.

---

## Data Layer

### Source Data

Three JSON files in `output/analysis/` (copied to `web/public/data/`):
- `emerald_plus_results.json`
- `diamond_plus_results.json`
- `diamond2_plus_results.json`

Each contains `champion_stats` (172 champions) with:
- `low_wr`, `medium_wr`, `high_wr` — win rates by mastery bucket
- `low_games`, `medium_games`, `high_games` — game counts
- `low_ratio`, `high_ratio` — ratio vs overall win rate
- `low_delta`, `delta` — win rate deltas
- `learning_score`, `mastery_score`, `investment_score` — composite metrics
- `learning_tier`, `mastery_tier` — categorical tiers
- `most_common_lane` — primary lane

**Added by Plan 2 & 3:**
- `games_to_50_winrate` — array of per-champion: `estimated_games`, `mastery_threshold`, `starting_winrate`, `status`
- `dynamic_champion_stats` — per-champion stats with dynamic bucket boundaries, plus `dynamic_status`, `mastery_threshold`, `estimated_games`, `difficulty_label`
- `dynamic_easiest_to_learn`, `dynamic_best_to_master`, `dynamic_best_investment` — pre-sorted rankings using dynamic buckets

### Loading

- `useAnalysisData(eloFilter)` fetches `${BASE_URL}data/${eloFilter}_results.json`
- Converts `champion_stats` object → array (add `champion` name field from key)
- Converts `dynamic_champion_stats` object → array similarly
- Caches fetched data in state to avoid re-fetching on view/filter changes
- Graceful error/loading states

---

## Column Configs Per View

Switching the **View** dropdown changes visible columns and default sort.

### Standard Views

#### Easiest to Learn (default sort: learning_score desc)
Rank | Icon+Champion | Lane | Learning Tier | Learning Score | Low WR | Medium WR | Low Ratio | Low Delta | Low Games

#### Best to Master (default sort: mastery_score desc)
Rank | Icon+Champion | Lane | Mastery Tier | Mastery Score | High WR | Medium WR | High Ratio | Delta | High Games

#### Best Investment (default sort: investment_score desc)
Rank | Icon+Champion | Lane | Investment Score | Learning Score | Mastery Score | Learning Tier | Mastery Tier

#### All Stats (default sort: champion name alpha)
Icon+Champion | Lane | Low/Med/High WR | Low/Med/High Games | Low Ratio | High Ratio | Low Delta | Delta | Learning Score | Mastery Score | Investment Score | Learning Tier | Mastery Tier

### Dynamic Views

#### Dynamic Easiest to Learn (default sort: learning_score desc, "Instantly Viable" first)
Rank | Icon+Champion | Lane | Difficulty | Est. Games | Learning Tier | Learning Score | Low WR | Medium WR | Low Ratio | Low Delta

#### Dynamic Best to Master (default sort: mastery_score desc)
Rank | Icon+Champion | Lane | Difficulty | Est. Games | Mastery Tier | Mastery Score | Medium WR | High WR | High Ratio | Delta

#### Dynamic Best Investment (default sort: investment_score desc)
Rank | Icon+Champion | Lane | Difficulty | Est. Games | Investment Score | Learning Score | Mastery Score | Low WR | High WR

#### Games to 50% WR (default sort: estimated_games asc, "always above 50%" first)
Rank | Icon+Champion | Lane | Status | Est. Games | Mastery Threshold | Starting WR | Difficulty

---

## Table Features

- Column header click to sort (asc/desc toggle with arrow indicators)
- Rank column auto-numbers based on current sort (not a data field)
- Alternating row colors, hover highlight
- Sticky header row
- Champion icon (32×32) + name in the first data column
- Horizontal scroll on mobile

---

## Styling

- **Dark/light mode** via `dark:` class strategy, persisted to localStorage, system preference detection
- **Tier badges** color-coded:
  - Learning: Safe Blind Pick (green) → Low Risk (light green) → Moderate (yellow) → High Risk (orange) → Avoid (red)
  - Mastery: Exceptional Payoff (green) → High Payoff (light green) → Moderate Payoff (yellow) → Low Payoff (orange) → Not Worth Mastering (red)
- **Difficulty badges**: Instantly Viable (green) → Extremely Hard to Learn (red) → Never Viable (gray)
- **Win rates** color-coded: <48% red, 48–52% neutral, >52% green
- **Compact** row padding for data density
- **Responsive:** horizontal table scroll on small screens

---

## Champion Icons

- `https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{key}.png`
- `championMapping.ts` maps display names → Data Dragon keys (e.g. "Vel'Koz" → "Velkoz")
- 32×32, lazy loaded, fallback placeholder on error

---

## GitHub Pages Deployment

`vite.config.ts` sets `base: '/league-data-analysis/'`.

**GitHub Actions** (`.github/workflows/deploy.yml`):
1. Trigger on push to main (`web/**`) + manual dispatch
2. Copy `output/analysis/*.json` → `web/public/data/`
3. `npm ci && npm run build` in `web/`
4. Deploy `web/dist/` via `actions/deploy-pages`

---

## Implementation Phases

### Phase 1: Scaffold ✅
1. Create `web/` with `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`
2. Install deps: `@tanstack/react-table`, `tailwindcss`, `@tailwindcss/vite`
3. Configure `vite.config.ts` (base + tailwind plugin)
4. Set up `index.css` with `@import "tailwindcss"`
5. Copy JSON files into `public/data/`
6. Verify dev server starts

### Phase 2: Types + Data ✅
1. Define TypeScript interfaces in `types/analysis.ts` (include dynamic fields)
2. Implement `useAnalysisData` hook (fetch + parse + cache, include dynamic arrays)
3. Implement `useTheme` hook

### Phase 3: UI Shell ✅
1. Build `Header` (title, elo selector, theme toggle)
2. Build `TableControls` (view selector, search, lane filter, tier filter, row count)
3. Wire up all control state in `App.tsx`
4. Style header + controls (dark/light working)

### Phase 4: Table ✅
1. Create `format.ts` (percentages, ratios, scores)
2. Create `championMapping.ts` (172 champion name → key mappings)
3. Build `ChampionIcon` component
4. Define column configs per view in `columns.ts` (8 views)
5. Build `ChampionTable` with @tanstack/react-table (sorting, filtering)
6. Style table (alternating rows, sticky header, tier badges, WR colors, difficulty badges)

### Phase 5: Polish + Deploy ✅
1. Loading spinner + error states
2. Responsive (mobile horizontal scroll)
3. GitHub Actions workflow (`.github/workflows/deploy.yml`)
4. `npm run build` — passes (217 KB JS, 17 KB CSS gzipped)
5. `copy-data` npm script

---

## Verification Checklist

- [ ] `cd web && npm run dev` — app loads, table shows data
- [ ] Switch elo — data refetches, table updates
- [ ] Switch view — columns change, sort resets to view default (all 8 views)
- [ ] Sort columns — click headers, asc/desc toggle
- [ ] Search — type name, table filters live
- [ ] Lane/tier dropdowns — filter correctly
- [ ] Dark/light toggle — persists on refresh
- [ ] Champion icons load from Data Dragon
- [ ] Missing JSON — graceful error message
- [ ] Dynamic views show "Instantly Viable" / "Never Viable" badges
- [ ] Games to 50% WR view shows estimated game counts
- [x] `npm run build` — production build passes (217 KB JS, 17 KB CSS)
