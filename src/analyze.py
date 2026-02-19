"""
Analysis script - Compute all mastery statistics from SQLite database

Reads match and mastery data, computes statistics for different elo filters,
and outputs JSON files for visualization and export.
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional

from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (ELO_FILTERS, MASTERY_BUCKETS, MINIMUM_SAMPLE_SIZE,
                    WIN_RATE_INTERVALS, LANES, LANE_DISPLAY_NAMES)
from db import Database
from utils import (setup_logging, format_number, format_percentage,
                   PatchManager, create_output_dirs)

logger = logging.getLogger(__name__)


def get_mastery_bucket(mastery_points: int) -> str:
    """Determine mastery bucket for a given point value"""
    if mastery_points < MASTERY_BUCKETS['low']['max']:
        return 'low'
    elif mastery_points < MASTERY_BUCKETS['medium']['max']:
        return 'medium'
    else:
        return 'high'


class MasteryAnalyzer:
    """Analyzes champion mastery impact on win rates"""

    def __init__(self, db: Database, elo_filter: str, output_dir: str,
                 patch_filter: Optional[List[str]] = None):
        self.db = db
        self.elo_filter = elo_filter
        self.output_dir = output_dir
        self.patch_filter = patch_filter
        self.filter_config = ELO_FILTERS[elo_filter]

        self.participants = []
        self.mastery_data = {}

    def load_data(self):
        """Load and filter data from database"""
        logger.info(f"Loading data for filter: {self.elo_filter}")
        logger.info(f"  Tiers: {self.filter_config['tiers']}")

        # Get filtered match IDs
        match_ids = self.db.get_filtered_matches(self.elo_filter, self.patch_filter)
        logger.info(f"  Filtered to {format_number(len(match_ids))} matches")

        if not match_ids:
            logger.warning("No matches found for this filter!")
            return

        # Load participants for those matches
        self.participants = self.db.get_all_participants(match_ids)
        logger.info(f"  Loaded {format_number(len(self.participants))} participant records")

        # Load mastery data
        self.mastery_data = self.db.get_all_mastery_dict()
        logger.info(f"  Loaded {format_number(len(self.mastery_data))} mastery records")

    def compute_summary(self) -> Dict:
        """Compute summary/verification statistics"""
        logger.info("Computing summary statistics...")

        unique_matches = set()
        unique_players = set()
        unique_champions = set()
        total_wins = 0
        region_match_counts = defaultdict(set)
        participants_with_mastery = 0

        for p in self.participants:
            unique_matches.add(p['match_id'])
            unique_players.add(p['puuid'])
            unique_champions.add(p['champion_name'])

            if p['win']:
                total_wins += 1

            # Determine region from match_id prefix
            mid = p['match_id']
            if mid.startswith('NA'):
                region_match_counts['NA'].add(mid)
            elif mid.startswith('EUW') or mid.startswith('EU'):
                region_match_counts['EUW'].add(mid)
            elif mid.startswith('KR'):
                region_match_counts['KR'].add(mid)

            key = (p['puuid'], p['champion_id'])
            if key in self.mastery_data:
                participants_with_mastery += 1

        total = len(self.participants)
        n_matches = len(unique_matches)

        summary = {
            'total_matches': n_matches,
            'total_participants': total,
            'total_unique_players': len(unique_players),
            'total_unique_champions': len(unique_champions),
            'overall_win_rate': total_wins / total if total > 0 else 0,
            'region_balance': {r: len(ids) for r, ids in region_match_counts.items()},
            'mastery_coverage': participants_with_mastery / total if total > 0 else 0,
        }

        # Verification checks
        self._run_verification(summary)

        return summary

    def _run_verification(self, summary: Dict):
        """Run verification checks from the PRD"""
        wr = summary['overall_win_rate']
        if not (0.49 <= wr <= 0.51):
            logger.warning(f"Overall win rate {wr:.4f} is outside expected 49-51% range")
        else:
            logger.info(f"  Overall win rate: {wr:.4f} (OK)")

        total_m = summary['total_matches']
        if total_m > 0:
            region_bal = summary['region_balance']
            for r, cnt in region_bal.items():
                pct = cnt / total_m
                if pct > 0.45 or pct < 0.22:
                    logger.warning(f"Region {r} has {pct:.1%} of matches (outside 22-45% range)")

        coverage = summary['mastery_coverage']
        if coverage < 0.95:
            logger.warning(f"Mastery coverage is {coverage:.1%} (below 95% target)")
        else:
            logger.info(f"  Mastery coverage: {coverage:.1%} (OK)")

        if summary['total_unique_champions'] < 150:
            logger.warning(f"Only {summary['total_unique_champions']} champions with data (expected >150)")

    def compute_mastery_distribution(self) -> Dict:
        """Compute mastery distribution statistics"""
        logger.info("Computing mastery distribution...")

        mastery_values = []
        bucket_counts = defaultdict(int)
        lane_bucket_counts = defaultdict(lambda: defaultdict(int))

        for p in self.participants:
            key = (p['puuid'], p['champion_id'])
            if key not in self.mastery_data:
                continue

            points = self.mastery_data[key]['mastery_points']
            mastery_values.append(points)
            bucket = get_mastery_bucket(points)
            bucket_counts[bucket] += 1

            lane = p.get('individual_position')
            if lane:
                lane_bucket_counts[lane][bucket] += 1

        if not mastery_values:
            return {}

        mastery_values.sort()
        n = len(mastery_values)

        def percentile(pct):
            idx = int(n * pct / 100)
            return mastery_values[min(idx, n - 1)]

        distribution = {
            'count': n,
            'mean': sum(mastery_values) / n,
            'median': mastery_values[n // 2],
            'p25': percentile(25),
            'p75': percentile(75),
            'p90': percentile(90),
            'p95': percentile(95),
            'p99': percentile(99),
            'bucket_counts': dict(bucket_counts),
            'bucket_percentages': {
                b: cnt / n * 100 for b, cnt in bucket_counts.items()
            },
            'by_lane': {
                lane: dict(counts) for lane, counts in lane_bucket_counts.items()
            },
            'raw_values': mastery_values,  # For histogram visualization
        }

        return distribution

    def compute_overall_winrate_by_bucket(self) -> Dict:
        """Compute overall win rate by mastery bucket"""
        logger.info("Computing overall win rate by bucket...")

        stats = defaultdict(lambda: {'wins': 0, 'games': 0})

        for p in self.participants:
            key = (p['puuid'], p['champion_id'])
            if key not in self.mastery_data:
                continue

            points = self.mastery_data[key]['mastery_points']
            bucket = get_mastery_bucket(points)
            stats[bucket]['games'] += 1
            if p['win']:
                stats[bucket]['wins'] += 1

        results = {}
        for bucket in ['low', 'medium', 'high']:
            s = stats[bucket]
            if s['games'] > 0:
                results[bucket] = {
                    'win_rate': s['wins'] / s['games'],
                    'games': s['games'],
                }

        return results

    def compute_winrate_curve(self) -> List[Dict]:
        """Compute win rate at various mastery intervals"""
        logger.info("Computing win rate curve...")

        interval_stats = defaultdict(lambda: {'wins': 0, 'games': 0})

        for p in self.participants:
            key = (p['puuid'], p['champion_id'])
            if key not in self.mastery_data:
                continue

            points = self.mastery_data[key]['mastery_points']

            for i, (lo, hi) in enumerate(WIN_RATE_INTERVALS):
                if lo <= points < hi:
                    interval_stats[i]['games'] += 1
                    if p['win']:
                        interval_stats[i]['wins'] += 1
                    break

        curve = []
        for i, (lo, hi) in enumerate(WIN_RATE_INTERVALS):
            s = interval_stats[i]
            if s['games'] > 0:
                if hi == float('inf'):
                    label = f"{lo // 1000}k+"
                else:
                    label = f"{lo // 1000}k-{hi // 1000}k"
                curve.append({
                    'interval': label,
                    'min': lo,
                    'max': hi if hi != float('inf') else None,
                    'win_rate': s['wins'] / s['games'],
                    'games': s['games'],
                })

        return curve

    def compute_champion_stats(self) -> Dict:
        """Compute per-champion statistics"""
        logger.info("Computing per-champion statistics...")

        champ_data = defaultdict(lambda: {
            'low': {'wins': 0, 'games': 0},
            'medium': {'wins': 0, 'games': 0},
            'high': {'wins': 0, 'games': 0},
            'lane_counts': defaultdict(int),
        })

        for p in self.participants:
            key = (p['puuid'], p['champion_id'])
            if key not in self.mastery_data:
                continue

            champ = p['champion_name']
            points = self.mastery_data[key]['mastery_points']
            bucket = get_mastery_bucket(points)

            champ_data[champ][bucket]['games'] += 1
            if p['win']:
                champ_data[champ][bucket]['wins'] += 1

            lane = p.get('individual_position')
            if lane:
                champ_data[champ]['lane_counts'][lane] += 1

        results = {}
        low_data_champs = []

        for champ, data in champ_data.items():
            low_wr = None
            med_wr = None
            high_wr = None

            if data['low']['games'] >= MINIMUM_SAMPLE_SIZE:
                low_wr = data['low']['wins'] / data['low']['games']
            if data['medium']['games'] >= MINIMUM_SAMPLE_SIZE:
                med_wr = data['medium']['wins'] / data['medium']['games']
            if data['high']['games'] >= MINIMUM_SAMPLE_SIZE:
                high_wr = data['high']['wins'] / data['high']['games']

            low_ratio = low_wr / med_wr if (low_wr is not None and med_wr is not None) else None
            high_ratio = high_wr / med_wr if (high_wr is not None and med_wr is not None) else None

            lane_counts = data['lane_counts']
            most_common_lane = max(lane_counts, key=lane_counts.get) if lane_counts else None

            # Track low-data champions
            for bucket_name in ['low', 'medium', 'high']:
                if data[bucket_name]['games'] < MINIMUM_SAMPLE_SIZE and data[bucket_name]['games'] > 0:
                    low_data_champs.append(
                        f"{champ} ({bucket_name}: {data[bucket_name]['games']} games)"
                    )

            results[champ] = {
                'low_wr': low_wr,
                'medium_wr': med_wr,
                'high_wr': high_wr,
                'low_games': data['low']['games'],
                'medium_games': data['medium']['games'],
                'high_games': data['high']['games'],
                'low_ratio': low_ratio,
                'high_ratio': high_ratio,
                'most_common_lane': most_common_lane,
            }

        if low_data_champs:
            logger.info(f"  Champions with <{MINIMUM_SAMPLE_SIZE} games in a bucket: {len(low_data_champs)}")

        return results

    def compute_lane_impact(self, champion_stats: Dict) -> Dict:
        """Compute mastery impact by lane"""
        logger.info("Computing lane impact...")

        lane_data = defaultdict(lambda: {
            'low_wr': [], 'medium_wr': [], 'high_wr': [],
            'low_ratio': [], 'high_ratio': [],
        })

        for champ, stats in champion_stats.items():
            lane = stats['most_common_lane']
            if not lane:
                continue

            if stats['low_wr'] is not None:
                lane_data[lane]['low_wr'].append(stats['low_wr'])
            if stats['medium_wr'] is not None:
                lane_data[lane]['medium_wr'].append(stats['medium_wr'])
            if stats['high_wr'] is not None:
                lane_data[lane]['high_wr'].append(stats['high_wr'])
            if stats['low_ratio'] is not None:
                lane_data[lane]['low_ratio'].append(stats['low_ratio'])
            if stats['high_ratio'] is not None:
                lane_data[lane]['high_ratio'].append(stats['high_ratio'])

        def avg(lst):
            return sum(lst) / len(lst) if lst else None

        results = {}
        for lane in LANES:
            d = lane_data.get(lane, {})
            if not d:
                continue
            results[lane] = {
                'display_name': LANE_DISPLAY_NAMES.get(lane, lane),
                'avg_low_wr': avg(d.get('low_wr', [])),
                'avg_medium_wr': avg(d.get('medium_wr', [])),
                'avg_high_wr': avg(d.get('high_wr', [])),
                'avg_low_ratio': avg(d.get('low_ratio', [])),
                'avg_high_ratio': avg(d.get('high_ratio', [])),
            }

        return results

    def analyze(self) -> Dict:
        """Run the full analysis pipeline"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Analysis: {self.elo_filter} ({self.filter_config['description']})")
        logger.info(f"{'='*60}\n")

        self.load_data()

        if not self.participants:
            logger.error("No data to analyze!")
            return {}

        summary = self.compute_summary()
        distribution = self.compute_mastery_distribution()
        overall_buckets = self.compute_overall_winrate_by_bucket()
        winrate_curve = self.compute_winrate_curve()
        champion_stats = self.compute_champion_stats()
        lane_impact = self.compute_lane_impact(champion_stats)

        # Rankings
        easiest_to_learn = sorted(
            [(c, s) for c, s in champion_stats.items() if s['low_ratio'] is not None],
            key=lambda x: x[1]['low_ratio'],
            reverse=True
        )

        best_to_master = sorted(
            [(c, s) for c, s in champion_stats.items() if s['high_ratio'] is not None],
            key=lambda x: x[1]['high_ratio'],
            reverse=True
        )

        # Strip raw_values from distribution before saving (too large for JSON)
        dist_for_save = {k: v for k, v in distribution.items() if k != 'raw_values'}

        results = {
            'filter': self.elo_filter,
            'filter_description': self.filter_config['description'],
            'summary': summary,
            'mastery_distribution': dist_for_save,
            'overall_winrate_by_bucket': overall_buckets,
            'winrate_curve': winrate_curve,
            'champion_stats': champion_stats,
            'lane_impact': lane_impact,
            'easiest_to_learn': [
                {'champion': c, **s} for c, s in easiest_to_learn
            ],
            'best_to_master': [
                {'champion': c, **s} for c, s in best_to_master
            ],
        }

        return results

    def save_results(self, results: Dict):
        """Save analysis results to JSON"""
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, f"{self.elo_filter}_results.json")

        # Handle float('inf') values in JSON serialization
        class InfEncoder(json.JSONEncoder):
            def default(self, obj):
                if obj == float('inf'):
                    return "Infinity"
                return super().default(obj)

        with open(path, 'w') as f:
            json.dump(results, f, indent=2, cls=InfEncoder)

        logger.info(f"Results saved to: {path}")


def main():
    parser = argparse.ArgumentParser(description='Analyze mastery impact on win rates')
    parser.add_argument('--filter', choices=list(ELO_FILTERS.keys()) + ['all'],
                        default='all',
                        help='Elo filter to analyze (default: all)')
    parser.add_argument('--patches', choices=['current', 'last3'], default='current',
                        help='Patch range to include (default: current)')
    parser.add_argument('--output', type=str, default='output/analysis',
                        help='Output directory')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    logger.info("Starting analysis...")
    create_output_dirs()

    db = Database()

    # Resolve patch filter
    patch_mgr = PatchManager()
    if args.patches == 'current':
        patch_versions = [patch_mgr.get_current_patch()]
    else:
        patch_versions = patch_mgr.get_last_n_patches(3)
    logger.info(f"Patch filter: {patch_versions}")

    filters = list(ELO_FILTERS.keys()) if args.filter == 'all' else [args.filter]
    logger.info(f"Processing {len(filters)} filter(s)")

    for i, elo_filter in enumerate(tqdm(filters, desc="Analyzing filters", unit="filter"), 1):
        logger.info(f"Processing filter {i} of {len(filters)}: {elo_filter}")
        try:
            analyzer = MasteryAnalyzer(db, elo_filter, args.output, patch_versions)
            results = analyzer.analyze()

            if not results:
                continue

            analyzer.save_results(results)

            s = results['summary']
            logger.info(f"\n  {elo_filter} Summary:")
            logger.info(f"    Matches: {format_number(s['total_matches'])}")
            logger.info(f"    Players: {format_number(s['total_unique_players'])}")
            logger.info(f"    Champions: {s['total_unique_champions']}")
            logger.info(f"    Overall WR: {format_percentage(s['overall_win_rate'] * 100)}")
            logger.info(f"    Mastery coverage: {format_percentage(s['mastery_coverage'] * 100)}")

            # Print top 5 easiest to learn
            if results['easiest_to_learn']:
                logger.info(f"\n  Top 5 Easiest to Learn:")
                for entry in results['easiest_to_learn'][:5]:
                    logger.info(
                        f"    {entry['champion']:20s} "
                        f"Low ratio: {entry['low_ratio']:.3f} "
                        f"({entry['most_common_lane']})"
                    )

            # Print top 5 best to master
            if results['best_to_master']:
                logger.info(f"\n  Top 5 Best to Master:")
                for entry in results['best_to_master'][:5]:
                    logger.info(
                        f"    {entry['champion']:20s} "
                        f"High ratio: {entry['high_ratio']:.3f} "
                        f"({entry['most_common_lane']})"
                    )

        except Exception as e:
            logger.error(f"Error analyzing {elo_filter}: {e}", exc_info=True)

    logger.info("\nAnalysis complete!")


if __name__ == '__main__':
    main()
