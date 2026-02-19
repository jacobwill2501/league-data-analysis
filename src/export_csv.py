"""
CSV Export script - Export CSVs matching the exact format of the original study

Generates three CSVs per elo filter matching past-data/ format:
  - Data Intro
  - Easiest to Learn
  - Best to Master
"""

import argparse
import csv
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
        ['', '', 'This is a replication of Jack J\'s Champion Mastery analysis for Emerald+ elo.'],
        ['', '', 'Original study: https://jackjgaming.substack.com/p/mastery-a-statistical-summary-of'],
        ['', '', 'This sheet contains the raw values split into two tabs:'],
        ['', '', 'Easiest to Learn: The Champions which have the lowest decrease in their win rate when played by someone with low Mastery (<10K)'],
        ['', '', 'Best to Master: The Champions which gain the most win rate when played by someone with high Mastery (+100K)'],
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
        ['', '', 'Analysis Details'],
        ['', '', 'Mastery buckets: Low (<10k) / Medium (10k-100k) / High (100k+)'],
        ['', '', 'Minimum sample size: 100 games per bucket'],
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
                 'Low Mastery Ratio', '', '', ''])

    # Data rows with annotation columns starting at row 3
    for i, entry in enumerate(ranking):
        lane = get_lane_display(entry.get('most_common_lane', ''))
        champ = entry.get('champion', '')
        low_wr = format_win_rate(entry.get('low_wr'))
        med_wr = format_win_rate(entry.get('medium_wr'))
        ratio = format_ratio(entry.get('low_ratio'))

        row = ['', '', lane, champ, low_wr, med_wr, ratio, '', '', '']

        # Annotation columns (G, H) at specific rows
        # row index 1 = data row 1 (i=0), annotations at rows 3-8 in spreadsheet
        # Row 3 in spreadsheet = index 2 in our rows list (after header)
        # But the original has annotations starting at row 3 (0-indexed row 2)
        # which corresponds to data row 2 (i=1)
        if i == 1:  # Row 3 in spreadsheet
            row[6] = 'Low Mastery Ratio'
        elif i == 2:  # Row 4
            row[6] = 'If high:'
            row[7] = 'Easy to Learn'
        elif i == 3:  # Row 5
            row[6] = 'If low:'
            row[7] = 'Hard to Learn'
        elif i == 5:  # Row 7
            row[6] = 'Low Mastery:'
            row[7] = '<10,000'
        elif i == 6:  # Row 8
            row[6] = 'Medium Mastery:'
            row[7] = '10,000-100,000'

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
                 'High Mastery Ratio', '', '', ''])

    for i, entry in enumerate(all_entries):
        lane = get_lane_display(entry.get('most_common_lane', ''))
        champ = entry.get('champion', '')
        med_wr = format_win_rate(entry.get('medium_wr'))
        high_wr = format_win_rate(entry.get('high_wr'))
        ratio = format_ratio(entry.get('high_ratio'))

        row = ['', '', lane, champ, med_wr, high_wr, ratio, '', '', '']

        # Annotation columns
        if i == 1:  # Row 3
            row[6] = 'High Mastery Ratio'
        elif i == 2:  # Row 4
            row[6] = 'If high:'
            row[7] = 'Highest benefit to mastering'
        elif i == 3:  # Row 5
            row[6] = 'If low:'
            row[7] = 'Lowest benefit to mastering'
        elif i == 5:  # Row 7
            row[6] = 'High Mastery:'
            row[7] = '100K+'
        elif i == 6:  # Row 8
            row[6] = 'Medium Mastery:'
            row[7] = '10,000-100,000'

        rows.append(row)

    path = os.path.join(output_dir, f'{filter_name} - Best to Master.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    logger.info(f"  Saved: {path}")


def export_all_csvs(results: dict, output_dir: str, filter_name: str):
    """Export all three CSVs for a filter"""
    logger.info(f"\nExporting CSVs for: {filter_name}")

    os.makedirs(output_dir, exist_ok=True)

    export_data_intro(results, output_dir, filter_name)
    export_easiest_to_learn(results, output_dir, filter_name)
    export_best_to_master(results, output_dir, filter_name)


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

    filters = list(ELO_FILTERS.keys()) if args.filter == 'all' else [args.filter]
    csvs_per_filter = 3
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
