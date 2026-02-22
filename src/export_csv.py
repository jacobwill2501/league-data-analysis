"""
CSV Export script - Export CSVs matching the exact format of the original study

Generates four CSVs per elo filter matching past-data/ format:
  - Data Intro
  - Easiest to Learn
  - Best to Master
  - Best Investment
"""

import argparse
import csv
import glob
import json
import logging
import os
import sys

from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ELO_FILTERS, LANE_DISPLAY_NAMES
from utils import setup_logging, create_output_dirs

logger = logging.getLogger(__name__)


def load_results(input_dir: str, filter_name: str) -> dict:
    """Load analysis results JSON"""
    path = os.path.join(input_dir, f"{filter_name}_results.json")
    if not os.path.exists(path):
        logger.error(f"Results file not found: {path}")
        return None

    with open(path, 'r') as f:
        return json.load(f)


def format_win_rate(value) -> str:
    """Format win rate as percentage with 2 decimal places"""
    if value is None:
        return 'low data'
    return f'{value * 100:.2f}%'


def format_ratio(value) -> str:
    """Format ratio to 2 decimal places"""
    if value is None:
        return 'low data'
    return f'{value:.2f}'


def format_delta(value) -> str:
    """Format win rate delta as percentage points with sign"""
    if value is None:
        return 'low data'
    return f'{value:+.2f}pp'


def format_score(value) -> str:
    """Format mastery effectiveness score to 2 decimal places"""
    if value is None:
        return 'low data'
    return f'{value:.2f}'


def get_lane_display(lane: str) -> str:
    """Convert internal lane name to display name"""
    return LANE_DISPLAY_NAMES.get(lane, lane or '')


def export_data_intro(results: dict, output_dir: str, filter_name: str):
    """Export the Data Intro CSV matching original format"""
    summary = results.get('summary', {})
    total_matches = summary.get('total_matches', 0)
    filter_desc = results.get('filter_description', filter_name)

    # Approximate match count for display
    if total_matches >= 1000000:
        match_display = f'~{total_matches / 1000000:.1f}M games'
    elif total_matches >= 1000:
        match_display = f'~{total_matches / 1000:.0f}K games'
    else:
        match_display = f'~{total_matches} games'

    rows = [
        ['', '', ''],
        ['', '', ''],
        ['', '', 'Introduction'],
        ['', '', 'This is a replication and extension of Jack J\'s Champion Mastery analysis.'],
        ['', '', 'Original study: https://jackjgaming.substack.com/p/mastery-a-statistical-summary-of'],
        ['', '', ''],
        ['', '', 'The goal is to answer two questions using real match data:'],
        ['', '', '1. Which champions can you pick up and perform well on immediately? (Easiest to Learn)'],
        ['', '', '2. Which champions reward you the most for investing time to master them? (Best to Master)'],
        ['', '', ''],
        ['', '', 'We compare win rates across mastery levels to measure how much experience matters per champion.'],
        ['', '', 'Champions are grouped by mastery points into Low / Medium / High buckets, and we compare'],
        ['', '', 'win rates between buckets to find which champions improve (or don\'t) with practice.'],
        ['', '', ''],
        ['', '', 'This sheet contains the raw values split into three tabs:'],
        ['', '', 'Easiest to Learn: Champions ranked by Learning Effectiveness Score (see below)'],
        ['', '', 'Best to Master: Champions ranked by Mastery Effectiveness Score (see below)'],
        ['', '', 'Best Investment: Champions ranked by combined Investment Score (see below)'],
        ['', '', ''],
        ['', '', 'To sort/filter tables:'],
        ['', '', '1. Click into either tab'],
        ['', '', '2. Click anywhere on the table'],
        ['', '', '3. In the top bar, click "Data" > "Filter views" > "Create new filter view"'],
        ['', '', '4.  Filter or Sort the table by clicking the icon'],
        ['', '', ''],
        ['', '', 'Data Info.'],
        ['', '', match_display],
        ['', '', 'Ranked Solo Queue only'],
        ['', '', 'Patch current'],
        ['', '', 'Roughly equal mix of EUW, NA & KR'],
        ['', '', f'Elo filter: {filter_desc}'],
        ['', '', ''],
        ['', '', 'Mastery Buckets & Approximate Games Played'],
        ['', '', 'Mastery points are earned per game: ~1,000 for a win, ~200 for a loss (~600 avg at 50% WR)'],
        ['', '', 'Low Mastery: <10,000 points (~10 wins to ~50 losses, roughly 17 games at 50% WR)'],
        ['', '', 'Medium Mastery: 10,000-100,000 points (~17 to ~167 games at 50% WR)'],
        ['', '', 'High Mastery: 100,000+ points (~100 wins to ~500 losses, roughly 167+ games at 50% WR)'],
        ['', '', 'Minimum sample size: 100 games per bucket'],
        ['', '', ''],
        ['', '', 'Key Metrics'],
        ['', '', 'Win Rate Delta: Raw percentage-point difference in win rate between mastery levels'],
        ['', '', 'Mastery Effectiveness Score = (High WR% - 50) + (High Ratio - 1) * 50'],
        ['', '', '  Balances absolute win rate viability with mastery improvement'],
        ['', '', '  Champions that both improve significantly AND end up above 50% WR score highest'],
        ['', '', '  Champions still sub-50% after mastery investment get penalized'],
        ['', '', 'Learning Effectiveness Score = (Low WR% - 50) + (Low Ratio - 1) * 50'],
        ['', '', '  Balances low-mastery viability with how small the inexperience drop is'],
        ['', '', '  Champions that are both viable at low mastery AND don\'t drop much score highest'],
        ['', '', 'Investment Score = Learning Score * 0.4 + Mastery Score * 0.6'],
        ['', '', '  Weighted combination: 40% ease of learning, 60% mastery payoff'],
        ['', '', '  Champions that are easy to pick up AND rewarding to master score highest'],
    ]

    path = os.path.join(output_dir, f'{filter_name} - Data Intro.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_easiest_to_learn(results: dict, output_dir: str, filter_name: str):
    """Export the Easiest to Learn CSV matching original format exactly"""
    ranking = results.get('easiest_to_learn', [])

    rows = []

    # Header row (row 1)
    rows.append(['', '', 'Most Common Lane', 'Champion Name',
                 'Low Mastery Win Rate', 'Medium Mastery Win Rate',
                 'Low Mastery Ratio', 'Win Rate Delta', 'Learning Effectiveness Score',
                 'Tier', '', '', ''])

    # Data rows with annotation columns
    for i, entry in enumerate(ranking):
        lane = get_lane_display(entry.get('most_common_lane', ''))
        champ = entry.get('champion', '')
        low_wr = format_win_rate(entry.get('low_wr'))
        med_wr = format_win_rate(entry.get('medium_wr'))
        ratio = format_ratio(entry.get('low_ratio'))
        low_delta = format_delta(entry.get('low_delta'))
        score = format_score(entry.get('learning_score'))
        tier = entry.get('learning_tier', '')

        row = ['', '', lane, champ, low_wr, med_wr, ratio, low_delta, score, tier, '', '', '']

        # Annotation columns
        if i == 1:  # Row 3 in spreadsheet
            row[11] = 'Learning Effectiveness Score'
        elif i == 2:  # Row 4
            row[11] = 'If high:'
            row[12] = 'Viable at low mastery + small drop'
        elif i == 3:  # Row 5
            row[11] = 'If low/negative:'
            row[12] = 'Sub-50% WR or big inexperience penalty'
        elif i == 5:  # Row 7
            row[11] = 'Low Mastery:'
            row[12] = '<10,000 (~10 wins to ~50 losses on champ)'
        elif i == 6:  # Row 8
            row[11] = 'Medium Mastery:'
            row[12] = '10,000-100,000 (~17 games at 50% WR)'

        rows.append(row)

    path = os.path.join(output_dir, f'{filter_name} - Easiest to Learn.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_best_to_master(results: dict, output_dir: str, filter_name: str):
    """Export the Best to Master CSV matching original format exactly"""
    ranking = results.get('best_to_master', [])

    # Include all champions, even those with low data
    # The original study shows "low data" for champions without enough high mastery games
    champion_stats = results.get('champion_stats', {})

    # Build complete ranking: champions with high_ratio first (sorted desc),
    # then champions without high_ratio (low data)
    ranked_with_data = [e for e in ranking]
    ranked_names = {e['champion'] for e in ranking}

    # Add champions that have medium_wr but no high data
    low_data_entries = []
    for champ, stats in champion_stats.items():
        if champ not in ranked_names and stats.get('medium_wr') is not None:
            low_data_entries.append({
                'champion': champ,
                'medium_wr': stats['medium_wr'],
                'high_wr': None,
                'high_ratio': None,
                'delta': None,
                'mastery_score': None,
                'most_common_lane': stats.get('most_common_lane'),
            })

    all_entries = low_data_entries + ranked_with_data  # low data first (like Milio in original)
    # Actually the original puts low data at top, then sorted by ratio desc
    # Let's match: low data entries at top, then sorted desc
    all_entries = low_data_entries + ranked_with_data

    rows = []

    # Header row
    rows.append(['', '', 'Most Common Lane', 'Champion Name',
                 'Medium Mastery Win Rate', 'High Mastery Win Rate',
                 'High Mastery Ratio', 'Win Rate Delta', 'Mastery Effectiveness Score',
                 'Tier', '', '', ''])

    for i, entry in enumerate(all_entries):
        lane = get_lane_display(entry.get('most_common_lane', ''))
        champ = entry.get('champion', '')
        med_wr = format_win_rate(entry.get('medium_wr'))
        high_wr = format_win_rate(entry.get('high_wr'))
        ratio = format_ratio(entry.get('high_ratio'))
        delta = format_delta(entry.get('delta'))
        score = format_score(entry.get('mastery_score'))
        tier = entry.get('mastery_tier', '')

        row = ['', '', lane, champ, med_wr, high_wr, ratio, delta, score, tier, '', '', '']

        # Annotation columns
        if i == 1:  # Row 3
            row[11] = 'Mastery Effectiveness Score'
        elif i == 2:  # Row 4
            row[11] = 'If high:'
            row[12] = 'High WR + big mastery improvement'
        elif i == 3:  # Row 5
            row[11] = 'If low/negative:'
            row[12] = 'Still sub-50% WR after mastery'
        elif i == 5:  # Row 7
            row[11] = 'High Mastery:'
            row[12] = '100K+ (~100 wins to ~500 losses on champ)'
        elif i == 6:  # Row 8
            row[11] = 'Medium Mastery:'
            row[12] = '10,000-100,000 (~17 games at 50% WR)'

        rows.append(row)

    path = os.path.join(output_dir, f'{filter_name} - Best to Master.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_best_investment(results: dict, output_dir: str, filter_name: str):
    """Export the Best Investment CSV combining learning + mastery scores"""
    ranking = results.get('best_investment', [])

    rows = []

    # Header row
    rows.append(['', '', 'Most Common Lane', 'Champion Name',
                 'Low Mastery Win Rate', 'High Mastery Win Rate',
                 'Learning Score', 'Mastery Score', 'Investment Score',
                 '', '', ''])

    for i, entry in enumerate(ranking):
        lane = get_lane_display(entry.get('most_common_lane', ''))
        champ = entry.get('champion', '')
        low_wr = format_win_rate(entry.get('low_wr'))
        high_wr = format_win_rate(entry.get('high_wr'))
        learn = format_score(entry.get('learning_score'))
        master = format_score(entry.get('mastery_score'))
        invest = format_score(entry.get('investment_score'))

        row = ['', '', lane, champ, low_wr, high_wr, learn, master, invest, '', '', '']

        # Annotation columns
        if i == 1:
            row[10] = 'Investment Score'
        elif i == 2:
            row[10] = 'Formula:'
            row[11] = 'Learn * 0.4 + Master * 0.6'
        elif i == 3:
            row[10] = 'If high:'
            row[11] = 'Easy to pick up AND rewarding to master'
        elif i == 5:
            row[10] = 'Learn Score:'
            row[11] = 'Low-mastery viability + small drop'
        elif i == 6:
            row[10] = 'Master Score:'
            row[11] = 'High-mastery viability + big improvement'

        rows.append(row)

    path = os.path.join(output_dir, f'{filter_name} - Best Investment.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_games_to_50_winrate(results: dict, output_dir: str, filter_name: str):
    """Export the Games to 50% Win Rate CSV"""
    entries = results.get('games_to_50_winrate', [])
    if not entries:
        logger.warning(f"  No games_to_50_winrate data for {filter_name}")
        return

    rows = []

    # Header row
    rows.append(['', '', 'Most Common Lane', 'Champion Name',
                 'Estimated Games', 'Mastery Threshold', 'Starting Win Rate',
                 'Status', '', '', ''])

    for i, entry in enumerate(entries):
        lane = get_lane_display(entry.get('lane', ''))
        champ = entry.get('champion_name', '')
        est_games = entry.get('estimated_games')
        threshold = entry.get('mastery_threshold')
        starting_wr = format_win_rate(entry.get('starting_winrate'))
        status = entry.get('status', '')

        if est_games is not None:
            est_games_str = str(est_games)
        else:
            est_games_str = 'N/A'

        if threshold is not None:
            threshold_str = f"{threshold:,}"
        else:
            threshold_str = 'N/A'

        row = ['', '', lane, champ, est_games_str, threshold_str, starting_wr, status, '', '', '']

        # Annotation columns
        if i == 1:
            row[9] = 'Estimated Games to 50% Win Rate'
        elif i == 2:
            row[9] = 'Uses ~700 mastery points per game'
        elif i == 3:
            row[9] = 'Interpolates between mastery intervals'
        elif i == 5:
            row[9] = '"always above 50%":'
            row[10] = 'Already above 50% at lowest mastery'
        elif i == 6:
            row[9] = '"never reaches 50%":'
            row[10] = 'Never crosses 50% at any mastery level'

        rows.append(row)

    path = os.path.join(output_dir, f'{filter_name} - Games to 50 Percent Winrate.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_dynamic_easiest_to_learn(results: dict, output_dir: str, filter_name: str):
    """Export Dynamic Easiest to Learn CSV using per-champion mastery thresholds"""
    ranking = results.get('dynamic_easiest_to_learn', [])

    rows = []
    rows.append(['', '', 'Most Common Lane', 'Champion Name',
                 'Low Mastery Win Rate', 'Medium Mastery Win Rate',
                 'Low Mastery Ratio', 'Win Rate Delta', 'Learning Effectiveness Score',
                 'Tier', '50% WR Games', 'Difficulty'])

    for entry in ranking:
        lane = get_lane_display(entry.get('most_common_lane', ''))
        champ = entry.get('champion', '')
        status = entry.get('dynamic_status', '')
        difficulty = entry.get('difficulty_label', '') or ''
        est_games = entry.get('estimated_games')
        games_str = str(est_games) if est_games is not None else 'N/A'

        if status == 'always above 50%':
            low_wr = 'N/A'
            med_wr = format_win_rate(entry.get('medium_wr'))
            ratio = 'N/A'
            low_delta = 'N/A'
            score = 'N/A'
            tier = 'Instantly Viable'
        else:
            low_wr = format_win_rate(entry.get('low_wr'))
            med_wr = format_win_rate(entry.get('medium_wr'))
            ratio = format_ratio(entry.get('low_ratio'))
            low_delta = format_delta(entry.get('low_delta'))
            score = format_score(entry.get('learning_score'))
            tier = entry.get('learning_tier', '') or ''

        rows.append(['', '', lane, champ, low_wr, med_wr, ratio, low_delta, score, tier, games_str, difficulty])

    path = os.path.join(output_dir, f'{filter_name} - Dynamic Easiest to Learn.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_dynamic_best_to_master(results: dict, output_dir: str, filter_name: str):
    """Export Dynamic Best to Master CSV using per-champion mastery thresholds"""
    ranking = results.get('dynamic_best_to_master', [])

    rows = []
    rows.append(['', '', 'Most Common Lane', 'Champion Name',
                 'Medium Mastery Win Rate', 'High Mastery Win Rate',
                 'High Mastery Ratio', 'Win Rate Delta', 'Mastery Effectiveness Score',
                 'Tier', '50% WR Games', 'Difficulty'])

    for entry in ranking:
        lane = get_lane_display(entry.get('most_common_lane', ''))
        champ = entry.get('champion', '')
        difficulty = entry.get('difficulty_label', '') or ''
        est_games = entry.get('estimated_games')
        games_str = str(est_games) if est_games is not None else 'N/A'

        med_wr = format_win_rate(entry.get('medium_wr'))
        high_wr = format_win_rate(entry.get('high_wr'))
        ratio = format_ratio(entry.get('high_ratio'))
        delta = format_delta(entry.get('delta'))
        score = format_score(entry.get('mastery_score'))
        tier = entry.get('mastery_tier', '') or ''

        rows.append(['', '', lane, champ, med_wr, high_wr, ratio, delta, score, tier, games_str, difficulty])

    path = os.path.join(output_dir, f'{filter_name} - Dynamic Best to Master.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_dynamic_best_investment(results: dict, output_dir: str, filter_name: str):
    """Export Dynamic Best Investment CSV using per-champion mastery thresholds"""
    ranking = results.get('dynamic_best_investment', [])

    rows = []
    rows.append(['', '', 'Most Common Lane', 'Champion Name',
                 'Low Mastery Win Rate', 'High Mastery Win Rate',
                 'Learning Score', 'Mastery Score', 'Investment Score',
                 '50% WR Games', 'Difficulty'])

    for entry in ranking:
        lane = get_lane_display(entry.get('most_common_lane', ''))
        champ = entry.get('champion', '')
        difficulty = entry.get('difficulty_label', '') or ''
        est_games = entry.get('estimated_games')
        games_str = str(est_games) if est_games is not None else 'N/A'

        low_wr = format_win_rate(entry.get('low_wr'))
        high_wr = format_win_rate(entry.get('high_wr'))
        learn = format_score(entry.get('learning_score'))
        master = format_score(entry.get('mastery_score'))
        invest = format_score(entry.get('investment_score'))

        rows.append(['', '', lane, champ, low_wr, high_wr, learn, master, invest, games_str, difficulty])

    path = os.path.join(output_dir, f'{filter_name} - Dynamic Best Investment.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_all_csvs(results: dict, output_dir: str, filter_name: str):
    """Export all CSVs for a filter"""
    logger.info(f"\nExporting CSVs for: {filter_name}")

    os.makedirs(output_dir, exist_ok=True)

    export_data_intro(results, output_dir, filter_name)
    export_easiest_to_learn(results, output_dir, filter_name)
    export_best_to_master(results, output_dir, filter_name)
    export_best_investment(results, output_dir, filter_name)
    export_games_to_50_winrate(results, output_dir, filter_name)
    export_dynamic_easiest_to_learn(results, output_dir, filter_name)
    export_dynamic_best_to_master(results, output_dir, filter_name)
    export_dynamic_best_investment(results, output_dir, filter_name)


def main():
    parser = argparse.ArgumentParser(description='Export CSVs matching original study format')
    parser.add_argument('--filter', choices=list(ELO_FILTERS.keys()) + ['all'],
                        default='all',
                        help='Elo filter to export (default: all)')
    parser.add_argument('--input', type=str, default='output/analysis',
                        help='Input directory with analysis JSON files')
    parser.add_argument('--output', type=str, default='output/csv',
                        help='Output directory for CSVs')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    logger.info("Starting CSV export...")
    create_output_dirs()

    # Clean out old CSVs before writing new ones
    old_csvs = glob.glob(os.path.join(args.output, '*.csv'))
    if old_csvs:
        for f in old_csvs:
            os.remove(f)
        logger.info(f"Removed {len(old_csvs)} old CSV file(s) from {args.output}")

    filters = list(ELO_FILTERS.keys()) if args.filter == 'all' else [args.filter]
    csvs_per_filter = 8
    logger.info(f"Will generate up to {len(filters) * csvs_per_filter} CSV files across {len(filters)} filter(s)")

    for i, filter_name in enumerate(tqdm(filters, desc="Exporting CSVs", unit="filter"), 1):
        logger.info(f"Processing filter {i} of {len(filters)}: {filter_name}")
        results = load_results(args.input, filter_name)
        if results is None:
            logger.warning(f"Skipping {filter_name} — no results file found")
            continue

        export_all_csvs(results, args.output, filter_name)

    logger.info("\nCSV export complete!")


if __name__ == '__main__':
    main()
