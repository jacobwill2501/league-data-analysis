"""
Standalone CSV export for Games to 50% Win Rate analysis.

Usage:
    python src/export_games_to_50.py            # export all filters
    python src/export_games_to_50.py --filter emerald_plus
"""

import argparse
import glob
import logging
import os
import sys

from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ELO_FILTERS
from export_csv import load_results, export_games_to_50_winrate
from utils import setup_logging, create_output_dirs

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Export Games to 50%% Win Rate CSVs')
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

    logger.info("Starting Games to 50%% Win Rate CSV export...")
    create_output_dirs()

    os.makedirs(args.output, exist_ok=True)

    # Only remove old "Games to 50 Percent" CSVs, not other CSVs
    old_csvs = glob.glob(os.path.join(args.output, '*Games to 50 Percent Winrate.csv'))
    if old_csvs:
        for f in old_csvs:
            os.remove(f)
        logger.info(f"Removed {len(old_csvs)} old Games to 50%% CSV(s)")

    filters = list(ELO_FILTERS.keys()) if args.filter == 'all' else [args.filter]

    for i, filter_name in enumerate(tqdm(filters, desc="Exporting", unit="filter"), 1):
        logger.info(f"Processing filter {i} of {len(filters)}: {filter_name}")
        results = load_results(args.input, filter_name)
        if results is None:
            logger.warning(f"Skipping {filter_name} — no results file found")
            continue

        export_games_to_50_winrate(results, args.output, filter_name)

    logger.info("\nGames to 50%% Win Rate CSV export complete!")


if __name__ == '__main__':
    main()
