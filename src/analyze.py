"""
Analysis script - Compute all mastery statistics from SQLite database

Reads match and mastery data, computes statistics for different elo filters,
and outputs JSON files for visualization and export.
"""

import argparse
import datetime
import json
import logging
import math
import os
import sys
import time
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


def _learning_tier(score):
    """Assign a tier label based on Learning Effectiveness Score"""
    if score is None:
        return None
    if score > 0:
        return 'Safe Blind Pick'
    if score > -5:
        return 'Low Risk'
    if score > -15:
        return 'Moderate'
    if score > -25:
        return 'High Risk'
    return 'Avoid'


def _mastery_tier(score):
    """Assign a tier label based on Mastery Effectiveness Score"""
    if score is None:
        return None
    if score > 8:
        return 'Exceptional Payoff'
    if score > 5:
        return 'High Payoff'
    if score > 2:
        return 'Moderate Payoff'
    if score > 0:
        return 'Low Payoff'
    return 'Not Worth Mastering'


MASTERY_PER_GAME = 700
SLOPE_MIN_MASTERY = 3500   # Skip 1–5 games band (selection bias dominated)
SLOPE_MIN_GAMES   = 200    # Stricter sample threshold for slope vs. 100 for visualization
SLOPE_PLATEAU_THRESHOLD = 0.5  # pp — WR within this of peak counts as "plateaued"


def _wilson_ci(wins: int, n: int, z: float = 1.96):
    """Wilson score confidence interval for a binomial proportion.

    Returns (ci_lower, ci_upper) as proportions, or (None, None) if n == 0.
    """
    if n == 0:
        return None, None
    p = wins / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return center - margin, center + margin


def _slope_tier(early_slope):
    """Assign a tier label based on early WR slope (pickup difficulty) in percentage points."""
    if early_slope is None:
        return None
    if early_slope < 2:
        return 'Easy Pickup'
    if early_slope < 5:
        return 'Mild Pickup'
    if early_slope < 8:
        return 'Hard Pickup'
    return 'Very Hard Pickup'


def _growth_type(late_slope: float | None) -> str | None:
    """Classify late-mastery growth from last-3-interval smoothed slope."""
    if late_slope is None:
        return None
    if late_slope < 0.5:
        return 'Plateau'
    if late_slope < 1.5:
        return 'Gradual'
    return 'Continual'


def _smooth_curve(intervals: list) -> list:
    """Games-weighted 3-point moving average over an interval list.

    Downweights noisy low-sample brackets (e.g. high-mastery endpoints)
    relative to their denser neighbors. Returns smoothed win_rate values
    at the same indices as the input list.
    """
    n = len(intervals)
    result = []
    for i in range(n):
        window = intervals[max(0, i - 1):i + 2]
        total_games = sum(iv['games'] for iv in window)
        result.append(sum(iv['win_rate'] * iv['games'] for iv in window) / total_games)
    return result


class MasteryAnalyzer:
    """Analyzes champion mastery impact on win rates"""

    def __init__(self, db: Database, elo_filter: str, output_dir: str,
                 patch_filter: Optional[List[str]] = None):
        self.db = db
        self.elo_filter = elo_filter
        self.output_dir = output_dir
        self.patch_filter = patch_filter
        self.filter_config = ELO_FILTERS[elo_filter]

    def compute_summary(self) -> Dict:
        """Compute summary/verification statistics via SQL aggregation."""
        logger.info("Computing summary statistics...")

        stats = self.db.get_summary_stats(self.elo_filter, self.patch_filter)
        total = stats['total_participants']
        total_wins = stats['total_wins']

        summary = {
            'total_matches': stats['total_matches'],
            'total_participants': total,
            'total_unique_players': stats['total_unique_players'],
            'total_unique_champions': stats['total_unique_champions'],
            'overall_win_rate': total_wins / total if total > 0 else 0,
            'region_balance': stats['region_balance'],
            'mastery_coverage': (
                stats['participants_with_mastery'] / total if total > 0 else 0
            ),
        }

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
        """Compute mastery distribution statistics via SQL aggregation."""
        logger.info("Computing mastery distribution...")

        # Sorted list for percentile computation (~100 MB, vs 6 GB full load)
        mastery_values = self.db.get_mastery_points_list(
            self.elo_filter, self.patch_filter)
        bucket_counts, lane_bucket_counts = self.db.get_mastery_distribution_extras(
            self.elo_filter, self.patch_filter)

        if not mastery_values:
            return {}

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
            'bucket_counts': bucket_counts,
            'bucket_percentages': {
                b: cnt / n * 100 for b, cnt in bucket_counts.items()
            },
            'by_lane': lane_bucket_counts,
        }

        return distribution

    def compute_overall_winrate_by_bucket(self) -> Dict:
        """Compute overall win rate by mastery bucket via SQL aggregation."""
        logger.info("Computing overall win rate by bucket...")

        rows = self.db.get_winrate_by_bucket(self.elo_filter, self.patch_filter)
        results = {}
        for row in rows:
            if row['games'] > 0:
                results[row['bucket']] = {
                    'win_rate': row['wins'] / row['games'],
                    'games': row['games'],
                }
        return results

    def compute_winrate_curve(self) -> List[Dict]:
        """Compute win rate at various mastery intervals via SQL aggregation."""
        logger.info("Computing win rate curve...")

        rows = self.db.get_winrate_curve_data(self.elo_filter, self.patch_filter)
        idx_to_stats = {r['interval_index']: r for r in rows}

        curve = []
        for i, (lo, hi, label) in enumerate(WIN_RATE_INTERVALS):
            s = idx_to_stats.get(i)
            if s is None or s['games'] == 0:
                continue
            curve.append({
                'interval': label,
                'min': lo,
                'max': hi if hi != float('inf') else None,
                'win_rate': s['wins'] / s['games'],
                'games': s['games'],
            })
        return curve

    def compute_champion_stats(self) -> Dict:
        """Compute per-champion statistics via SQL aggregation."""
        logger.info("Computing per-champion statistics...")

        bucket_rows, lane_rows = self.db.get_champion_stats_aggregated(
            self.elo_filter, self.patch_filter)

        champ_data = defaultdict(lambda: {
            'low': {'wins': 0, 'games': 0},
            'medium': {'wins': 0, 'games': 0},
            'high': {'wins': 0, 'games': 0},
            'lane_counts': defaultdict(int),
        })
        for row in bucket_rows:
            champ_data[row['champion_name']][row['bucket']]['wins'] = row['wins']
            champ_data[row['champion_name']][row['bucket']]['games'] = row['games']
        for row in lane_rows:
            champ_data[row['champion_name']]['lane_counts'][row['lane']] = row['cnt']

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

            # Win Rate Delta: raw percentage-point change from medium mastery
            low_delta = (low_wr - med_wr) * 100 if (low_wr is not None and med_wr is not None) else None
            delta = (high_wr - med_wr) * 100 if (high_wr is not None and med_wr is not None) else None
            # Mastery Effectiveness Score: balances absolute WR viability with mastery improvement
            mastery_score = ((high_wr * 100 - 50) + (high_ratio - 1) * 50) if (high_wr is not None and high_ratio is not None) else None
            # Learning Effectiveness Score: balances low-mastery viability with small inexperience drop
            learning_score = ((low_wr * 100 - 50) + (low_ratio - 1) * 50) if (low_wr is not None and low_ratio is not None) else None
            # Investment Score: weighted combination of learning + mastery payoff
            investment_score = (learning_score * 0.4 + mastery_score * 0.6) if (learning_score is not None and mastery_score is not None) else None

            # Tier labels
            learning_tier = _learning_tier(learning_score)
            mastery_tier = _mastery_tier(mastery_score)

            lane_counts = data['lane_counts']
            most_common_lane = max(lane_counts, key=lane_counts.get) if lane_counts else None

            # Track low-data champions
            for bucket_name in ['low', 'medium', 'high']:
                if data[bucket_name]['games'] < MINIMUM_SAMPLE_SIZE and data[bucket_name]['games'] > 0:
                    low_data_champs.append(
                        f"{champ} ({bucket_name}: {data[bucket_name]['games']} games)"
                    )

            low_ci  = _wilson_ci(data['low']['wins'],    data['low']['games'])
            med_ci  = _wilson_ci(data['medium']['wins'], data['medium']['games'])
            high_ci = _wilson_ci(data['high']['wins'],   data['high']['games'])

            results[champ] = {
                'low_wr': low_wr,
                'medium_wr': med_wr,
                'high_wr': high_wr,
                'low_games': data['low']['games'],
                'medium_games': data['medium']['games'],
                'high_games': data['high']['games'],
                'low_ratio': low_ratio,
                'high_ratio': high_ratio,
                'low_delta': low_delta,
                'delta': delta,
                'mastery_score': mastery_score,
                'learning_score': learning_score,
                'investment_score': investment_score,
                'learning_tier': learning_tier,
                'mastery_tier': mastery_tier,
                'most_common_lane': most_common_lane,
                'low_wr_ci_lower':    round(low_ci[0],  4) if low_ci[0]  is not None else None,
                'low_wr_ci_upper':    round(low_ci[1],  4) if low_ci[1]  is not None else None,
                'medium_wr_ci_lower': round(med_ci[0],  4) if med_ci[0]  is not None else None,
                'medium_wr_ci_upper': round(med_ci[1],  4) if med_ci[1]  is not None else None,
                'high_wr_ci_lower':   round(high_ci[0], 4) if high_ci[0] is not None else None,
                'high_wr_ci_upper':   round(high_ci[1], 4) if high_ci[1] is not None else None,
            }

        if low_data_champs:
            logger.info(f"  Champions with <{MINIMUM_SAMPLE_SIZE} games in a bucket: {len(low_data_champs)}")

        return results

    def compute_pabu_champion_stats(self) -> Dict:
        """Compute per-champion statistics using Pabu mastery buckets (30k medium boundary)."""
        logger.info("Computing Pabu per-champion statistics (30k medium boundary)...")

        bucket_rows, lane_rows = self.db.get_pabu_champion_stats_aggregated(
            self.elo_filter, self.patch_filter)

        champ_data = defaultdict(lambda: {
            'low': {'wins': 0, 'games': 0},
            'medium': {'wins': 0, 'games': 0},
            'high': {'wins': 0, 'games': 0},
            'lane_counts': defaultdict(int),
        })
        for row in bucket_rows:
            champ_data[row['champion_name']][row['bucket']]['wins'] = row['wins']
            champ_data[row['champion_name']][row['bucket']]['games'] = row['games']
        for row in lane_rows:
            champ_data[row['champion_name']]['lane_counts'][row['lane']] = row['cnt']

        results = {}

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

            low_delta = (low_wr - med_wr) * 100 if (low_wr is not None and med_wr is not None) else None
            delta = (high_wr - med_wr) * 100 if (high_wr is not None and med_wr is not None) else None
            mastery_score = ((high_wr * 100 - 50) + (high_ratio - 1) * 50) if (high_wr is not None and high_ratio is not None) else None
            learning_score = ((low_wr * 100 - 50) + (low_ratio - 1) * 50) if (low_wr is not None and low_ratio is not None) else None
            investment_score = (learning_score * 0.4 + mastery_score * 0.6) if (learning_score is not None and mastery_score is not None) else None

            learning_tier = _learning_tier(learning_score)
            mastery_tier = _mastery_tier(mastery_score)

            lane_counts = data['lane_counts']
            most_common_lane = max(lane_counts, key=lane_counts.get) if lane_counts else None

            results[champ] = {
                'low_wr': low_wr,
                'medium_wr': med_wr,
                'high_wr': high_wr,
                'low_games': data['low']['games'],
                'medium_games': data['medium']['games'],
                'high_games': data['high']['games'],
                'low_ratio': low_ratio,
                'high_ratio': high_ratio,
                'low_delta': low_delta,
                'delta': delta,
                'mastery_score': mastery_score,
                'learning_score': learning_score,
                'investment_score': investment_score,
                'learning_tier': learning_tier,
                'mastery_tier': mastery_tier,
                'most_common_lane': most_common_lane,
            }

        return results

    def compute_games_to_50_winrate(self, interval_rows: List[Dict],
                                     lane_rows: List[Dict],
                                     threshold: float = 0.50) -> List[Dict]:
        """Estimate how many games it takes each champion to reach the win rate threshold.

        Uses pre-aggregated per-champion/interval data (from SQL), finds where
        the curve crosses `threshold`, and converts the mastery-point threshold
        to an approximate game count (~700 pts/game).

        Args:
            interval_rows: Aggregated rows from get_mastery_curves_aggregated().
            lane_rows:      Lane count rows from get_mastery_curves_aggregated().
            threshold:      Win rate threshold to find crossing for (default 0.50).
        """
        logger.info(f"Computing games to {threshold:.1%} win rate...")

        champ_interval: Dict = defaultdict(
            lambda: defaultdict(lambda: {'wins': 0, 'games': 0}))
        champ_lanes: Dict = defaultdict(lambda: defaultdict(int))

        for row in interval_rows:
            champ_interval[row['champion_name']][row['interval_index']]['wins'] = row['wins']
            champ_interval[row['champion_name']][row['interval_index']]['games'] = row['games']
        for row in lane_rows:
            champ_lanes[row['champion_name']][row['lane']] = row['cnt']

        results = []

        for champ, intervals in champ_interval.items():
            # Build ordered list of (midpoint, win_rate) for intervals with enough data
            points_wr = []
            for idx, (lo, hi, _label) in enumerate(WIN_RATE_INTERVALS):
                s = intervals.get(idx)
                if s is None or s['games'] < MINIMUM_SAMPLE_SIZE:
                    continue
                mid = lo + (min(hi, 1_000_000) - lo) / 2
                wr = s['wins'] / s['games']
                points_wr.append((lo, hi, mid, wr))

            lane_counts = champ_lanes.get(champ, {})
            most_common_lane = max(lane_counts, key=lane_counts.get) if lane_counts else None

            if len(points_wr) < 2:
                results.append({
                    'champion_name': champ,
                    'lane': most_common_lane,
                    'mastery_threshold': None,
                    'estimated_games': None,
                    'starting_winrate': points_wr[0][3] if points_wr else None,
                    'win_rate_threshold': threshold,
                    'status': 'low data',
                })
                continue

            starting_wr = points_wr[0][3]

            # Check if always above threshold
            if all(wr >= threshold for _, _, _, wr in points_wr):
                results.append({
                    'champion_name': champ,
                    'lane': most_common_lane,
                    'mastery_threshold': 0,
                    'estimated_games': 0,
                    'starting_winrate': starting_wr,
                    'win_rate_threshold': threshold,
                    'status': 'always above 50%',
                })
                continue

            # Look for the crossing point
            crossed = False
            for i in range(len(points_wr) - 1):
                lo1, hi1, mid1, wr1 = points_wr[i]
                lo2, hi2, mid2, wr2 = points_wr[i + 1]

                if wr1 < threshold <= wr2:
                    # Verify the average of all post-crossing intervals is also >= threshold
                    post_crossing_wrs = [wr for _, _, _, wr in points_wr[i + 1:]]
                    avg_post = sum(post_crossing_wrs) / len(post_crossing_wrs)

                    if avg_post < threshold:
                        continue  # Not a sustained crossing — keep looking

                    # Linear interpolation between midpoints
                    if wr2 != wr1:
                        frac = (threshold - wr1) / (wr2 - wr1)
                        mastery_pt = mid1 + frac * (mid2 - mid1)
                    else:
                        mastery_pt = mid1
                    results.append({
                        'champion_name': champ,
                        'lane': most_common_lane,
                        'mastery_threshold': round(mastery_pt),
                        'estimated_games': round(mastery_pt / MASTERY_PER_GAME),
                        'starting_winrate': starting_wr,
                        'win_rate_threshold': threshold,
                        'status': 'crosses 50%',
                    })
                    crossed = True
                    break

            if not crossed:
                results.append({
                    'champion_name': champ,
                    'lane': most_common_lane,
                    'mastery_threshold': None,
                    'estimated_games': None,
                    'starting_winrate': starting_wr,
                    'win_rate_threshold': threshold,
                    'status': 'never reaches 50%',
                })

        # Sort: always above (0 games) first, then crosses by games asc, then never reaches
        def sort_key(r):
            status = r['status']
            if status == 'always above 50%':
                return (0, 0, r['champion_name'])
            elif status == 'crosses 50%':
                return (1, r['estimated_games'], r['champion_name'])
            elif status == 'never reaches 50%':
                return (2, 0, r['champion_name'])
            else:  # low data
                return (3, 0, r['champion_name'])

        results.sort(key=sort_key)

        logger.info(f"  Champions always above 50%%: {sum(1 for r in results if r['status'] == 'always above 50%')}")
        logger.info(f"  Champions that cross 50%%: {sum(1 for r in results if r['status'] == 'crosses 50%')}")
        logger.info(f"  Champions that never reach 50%%: {sum(1 for r in results if r['status'] == 'never reaches 50%')}")
        logger.info(f"  Low data: {sum(1 for r in results if r['status'] == 'low data')}")

        return results

    def compute_mastery_curves_by_champion(self, interval_rows: List[Dict],
                                           lane_rows: List[Dict]) -> Dict:
        """Compute per-champion win rate at each mastery interval.

        Uses pre-aggregated per-champion/interval data (from SQL).
        Returns a dict keyed by champion name with lane and a list of interval
        stats (only intervals meeting MINIMUM_SAMPLE_SIZE).
        """
        logger.info("Computing mastery curves by champion...")

        champ_interval: Dict = defaultdict(
            lambda: defaultdict(lambda: {'wins': 0, 'games': 0}))
        champ_lanes: Dict = defaultdict(lambda: defaultdict(int))

        for row in interval_rows:
            champ_interval[row['champion_name']][row['interval_index']]['wins'] = row['wins']
            champ_interval[row['champion_name']][row['interval_index']]['games'] = row['games']
        for row in lane_rows:
            champ_lanes[row['champion_name']][row['lane']] = row['cnt']

        results = {}

        for champ, intervals in champ_interval.items():
            lane_counts = champ_lanes.get(champ, {})
            most_common_lane = max(lane_counts, key=lane_counts.get) if lane_counts else None

            interval_list = []
            for idx, (lo, hi, label) in enumerate(WIN_RATE_INTERVALS):
                s = intervals.get(idx)
                if s is None or s['games'] < MINIMUM_SAMPLE_SIZE:
                    continue

                ci_lo, ci_hi = _wilson_ci(s['wins'], s['games'])
                interval_list.append({
                    'label': label,
                    'min': lo,
                    'max': hi if hi != float('inf') else None,
                    'win_rate': s['wins'] / s['games'],
                    'games': s['games'],
                    'ci_lower': round(ci_lo, 4) if ci_lo is not None else None,
                    'ci_upper': round(ci_hi, 4) if ci_hi is not None else None,
                })

            if interval_list:
                results[champ] = {
                    'lane': most_common_lane,
                    'intervals': interval_list,
                }

        logger.info(f"  Champions with mastery curve data: {len(results)}")
        return results

    def compute_slope_iterations(self, mastery_curves: Dict) -> List[Dict]:
        """Compute learning curve steepness for each champion.

        For each champion, measures how quickly win rate improves as mastery
        accumulates. Uses the already-computed mastery_curves data.

        Returns a list of per-champion dicts sorted by slope tier (flat first),
        then inflection_games ascending (null last).
        """
        logger.info("Computing slope iterations...")

        results = []

        def _geomid(iv):
            """Geometric midpoint of a bounded interval."""
            return (iv['min'] * iv['max']) ** 0.5

        for champ, curve in mastery_curves.items():
            lane = curve.get('lane')
            intervals = list(curve.get('intervals', []))

            # Visualization-quality count (used in output for data-quality context)
            valid_intervals = len(intervals)

            # Slope-specific filtered intervals: skip low-mastery noise bands,
            # require stricter sample threshold
            slope_ivs = [
                iv for iv in intervals
                if iv['min'] >= SLOPE_MIN_MASTERY
                and iv['games'] >= SLOPE_MIN_GAMES
            ]

            if len(slope_ivs) < 3:
                results.append({
                    'champion': champ,
                    'most_common_lane': lane,
                    'initial_wr': None,
                    'peak_wr': None,
                    'total_slope': None,
                    'early_slope': None,
                    'late_slope': None,
                    'inflection_mastery': None,
                    'inflection_games': None,
                    'slope_tier': None,
                    'growth_type': None,
                    'valid_intervals': valid_intervals,
                })
                continue

            # Raw values kept for display (Starting WR / Peak WR columns)
            initial_wr = slope_ivs[0]['win_rate']
            peak_wr = max(iv['win_rate'] for iv in slope_ivs)

            # All metrics derived from smoothed values
            smoothed = _smooth_curve(slope_ivs)

            s_initial = smoothed[0]
            s_peak    = max(smoothed)
            total_slope = (s_peak - s_initial) * 100

            # Early slope: gain across first 3 intervals (Cognitive phase, ~5k–50k mastery)
            early_end   = min(3, len(smoothed) - 1)
            early_slope = (smoothed[early_end] - smoothed[0]) * 100

            # Approximate 95% CI for early slope using SE of boundary intervals' win rates
            iv0 = slope_ivs[0]
            iv2 = slope_ivs[min(2, len(slope_ivs) - 1)]
            se0 = iv0['win_rate'] * (1 - iv0['win_rate']) / iv0['games']
            se2 = iv2['win_rate'] * (1 - iv2['win_rate']) / iv2['games']
            early_slope_ci = round(1.96 * math.sqrt(se0 + se2) * 100, 2)

            # Late slope: gain across last 3 intervals (Autonomous phase, 100k–end of data)
            # Only computed when there are enough intervals for early and late not to overlap.
            late_slope = None
            if len(smoothed) >= 5:
                late_slope = (smoothed[-1] - smoothed[-3]) * 100

            inflection_mastery = None
            inflection_games   = None

            if total_slope > 0:
                near_peak_swr = s_peak - (SLOPE_PLATEAU_THRESHOLD / 100)
                for iv, swr in zip(slope_ivs, smoothed):
                    if swr >= near_peak_swr:
                        inflection_mastery = iv['min']
                        inflection_games   = round(inflection_mastery / MASTERY_PER_GAME)
                        break

            results.append({
                'champion': champ,
                'most_common_lane': lane,
                'initial_wr': round(initial_wr, 4),
                'peak_wr': round(peak_wr, 4),
                'total_slope': round(total_slope, 2),
                'early_slope': round(early_slope, 2),
                'early_slope_ci': early_slope_ci,
                'late_slope': round(late_slope, 2) if late_slope is not None else None,
                'inflection_mastery': inflection_mastery,
                'inflection_games': inflection_games,
                'slope_tier': _slope_tier(early_slope),
                'growth_type': _growth_type(late_slope),
                'valid_intervals': valid_intervals,
            })

        slope_tier_order = {
            'Easy Pickup': 0,
            'Mild Pickup': 1,
            'Hard Pickup': 2,
            'Very Hard Pickup': 3,
        }

        def sort_key(entry):
            tier_idx = slope_tier_order.get(entry.get('slope_tier'), len(slope_tier_order))
            ig = entry.get('inflection_games')
            return (tier_idx, ig if ig is not None else float('inf'))

        results.sort(key=sort_key)
        logger.info(f"  Champions with slope data: {len(results)}")
        return results

    def compute_champion_stats_by_lane(
            self, bucket_rows: List[Dict], lane_rows: List[Dict]) -> Dict:
        """Compute per-champion, per-lane bucket statistics.

        Returns a nested dict keyed by champion name → lane → stat dict.
        Only emits a (champion, lane) entry when that lane has >= MINIMUM_SAMPLE_SIZE
        games in the medium bucket to prevent tiny flex-play entries.

        NOTE: mastery_points used here are total champion mastery, not lane-specific.
        Riot's API provides no per-lane mastery breakdown.
        """
        logger.info("Computing per-champion per-lane statistics...")

        champ_lane_data: Dict = defaultdict(
            lambda: defaultdict(lambda: {
                'low':    {'wins': 0, 'games': 0},
                'medium': {'wins': 0, 'games': 0},
                'high':   {'wins': 0, 'games': 0},
            })
        )
        for row in bucket_rows:
            champ_lane_data[row['champion_name']][row['lane']][row['bucket']]['wins']  = row['wins']
            champ_lane_data[row['champion_name']][row['lane']][row['bucket']]['games'] = row['games']

        results: Dict = {}
        for champ, lane_map in champ_lane_data.items():
            results[champ] = {}
            for lane, data in lane_map.items():
                if data['medium']['games'] < MINIMUM_SAMPLE_SIZE:
                    continue

                low_wr  = data['low']['wins']    / data['low']['games']    if data['low']['games']    >= MINIMUM_SAMPLE_SIZE else None
                med_wr  = data['medium']['wins']  / data['medium']['games']
                high_wr = data['high']['wins']   / data['high']['games']   if data['high']['games']   >= MINIMUM_SAMPLE_SIZE else None

                low_ratio  = low_wr  / med_wr if (low_wr  is not None) else None
                high_ratio = high_wr / med_wr if (high_wr is not None) else None
                low_delta  = (low_wr  - med_wr) * 100 if low_ratio  is not None else None
                delta      = (high_wr - med_wr) * 100 if high_ratio is not None else None

                mastery_score    = ((high_wr * 100 - 50) + (high_ratio - 1) * 50) if (high_wr is not None and high_ratio is not None) else None
                learning_score   = ((low_wr  * 100 - 50) + (low_ratio  - 1) * 50) if (low_wr  is not None and low_ratio  is not None) else None
                investment_score = (learning_score * 0.4 + mastery_score * 0.6)    if (learning_score is not None and mastery_score is not None) else None

                low_ci  = _wilson_ci(data['low']['wins'],    data['low']['games'])
                med_ci  = _wilson_ci(data['medium']['wins'], data['medium']['games'])
                high_ci = _wilson_ci(data['high']['wins'],   data['high']['games'])

                results[champ][lane] = {
                    'low_wr':           low_wr,
                    'medium_wr':        med_wr,
                    'high_wr':          high_wr,
                    'low_games':        data['low']['games'],
                    'medium_games':     data['medium']['games'],
                    'high_games':       data['high']['games'],
                    'low_ratio':        low_ratio,
                    'high_ratio':       high_ratio,
                    'low_delta':        low_delta,
                    'delta':            delta,
                    'mastery_score':    mastery_score,
                    'learning_score':   learning_score,
                    'investment_score': investment_score,
                    'learning_tier':    _learning_tier(learning_score),
                    'mastery_tier':     _mastery_tier(mastery_score),
                    'low_wr_ci_lower':    round(low_ci[0],  4) if low_ci[0]  is not None else None,
                    'low_wr_ci_upper':    round(low_ci[1],  4) if low_ci[1]  is not None else None,
                    'medium_wr_ci_lower': round(med_ci[0],  4) if med_ci[0]  is not None else None,
                    'medium_wr_ci_upper': round(med_ci[1],  4) if med_ci[1]  is not None else None,
                    'high_wr_ci_lower':   round(high_ci[0], 4) if high_ci[0] is not None else None,
                    'high_wr_ci_upper':   round(high_ci[1], 4) if high_ci[1] is not None else None,
                }

            if not results[champ]:
                del results[champ]

        logger.info(f"  Champions with per-lane stats: {len(results)}")
        return results

    def compute_mastery_curves_by_champion_and_lane(
            self, lane_interval_rows: List[Dict]) -> Dict:
        """Compute per-champion, per-lane mastery curves.

        Returns a nested dict: champion → lane → {intervals: [...]}.
        Only emits a lane when at least one interval meets MINIMUM_SAMPLE_SIZE.

        NOTE: The mastery axis represents total champion mastery, not lane-specific
        mastery. Riot's API provides no per-lane mastery breakdown.
        """
        logger.info("Computing per-lane mastery curves...")

        champ_lane_interval: Dict = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'games': 0}))
        )
        for row in lane_interval_rows:
            slot = champ_lane_interval[row['champion_name']][row['lane']][row['interval_index']]
            slot['wins']  = row['wins']
            slot['games'] = row['games']

        results: Dict = {}
        for champ, lane_map in champ_lane_interval.items():
            results[champ] = {}
            for lane, intervals in lane_map.items():
                interval_list = []
                for idx, (lo, hi, label) in enumerate(WIN_RATE_INTERVALS):
                    s = intervals.get(idx)
                    if s is None or s['games'] < MINIMUM_SAMPLE_SIZE:
                        continue
                    ci_lo, ci_hi = _wilson_ci(s['wins'], s['games'])
                    interval_list.append({
                        'label':    label,
                        'min':      lo,
                        'max':      hi if hi != float('inf') else None,
                        'win_rate': s['wins'] / s['games'],
                        'games':    s['games'],
                        'ci_lower': round(ci_lo, 4) if ci_lo is not None else None,
                        'ci_upper': round(ci_hi, 4) if ci_hi is not None else None,
                    })
                if interval_list:
                    results[champ][lane] = {'intervals': interval_list}

            if not results[champ]:
                del results[champ]

        logger.info(f"  Champions with per-lane mastery curve data: {len(results)}")
        return results

    def compute_slope_iterations_by_lane(self, mastery_curves_by_lane: Dict) -> List[Dict]:
        """Compute slope iterations for each (champion, lane) pair.

        Re-uses compute_slope_iterations() on per-lane curve data.
        Each result row includes a 'lane' field alongside 'most_common_lane'.
        """
        logger.info("Computing per-lane slope iterations...")

        results = []
        for champ, lane_map in mastery_curves_by_lane.items():
            for lane, curve_data in lane_map.items():
                single_curve = {champ: {'lane': lane, 'intervals': curve_data['intervals']}}
                for r in self.compute_slope_iterations(single_curve):
                    r['lane'] = lane
                    results.append(r)

        slope_tier_order = {
            'Easy Pickup': 0, 'Mild Pickup': 1, 'Hard Pickup': 2, 'Very Hard Pickup': 3,
        }

        def sort_key(entry):
            tier_idx = slope_tier_order.get(entry.get('slope_tier'), len(slope_tier_order))
            ig = entry.get('inflection_games')
            return (tier_idx, ig if ig is not None else float('inf'))

        results.sort(key=sort_key)
        logger.info(f"  Per-lane slope entries: {len(results)}")
        return results

    def compute_bias_champion_stats(self, games_to_50: List[Dict]) -> Dict:
        """Compute per-champion statistics using bias (per-champion) mastery buckets.

        Bucket boundaries are derived from games_to_50 thresholds:
          - 'crosses 50%'     → Low: 0→threshold, Medium: threshold→100k, High: 100k+
          - 'always above 50%'→ (no Low), Medium: 0→100k, High: 100k+
          - 'never reaches 50%' → Low: 0→100k, (no Medium), High: 100k+
          - 'low data'        → skip entirely

        Uses a streaming SQL cursor so only O(n_champions) data lives in memory.
        """
        logger.info("Computing bias per-champion statistics...")

        HIGH_THRESHOLD = MASTERY_BUCKETS['medium']['max']  # 100_000

        g50_by_champ = {entry['champion_name']: entry for entry in games_to_50}

        champ_data = defaultdict(lambda: {
            'low': {'wins': 0, 'games': 0},
            'medium': {'wins': 0, 'games': 0},
            'high': {'wins': 0, 'games': 0},
            'lane_counts': defaultdict(int),
        })

        for champion_name, mastery_points, win, lane in self.db.iter_bias_mastery_data(
                self.elo_filter, self.patch_filter):

            g50_entry = g50_by_champ.get(champion_name)
            if g50_entry is None:
                continue

            status = g50_entry['status']
            if status == 'low data':
                continue

            threshold = g50_entry['mastery_threshold']

            if status == 'always above 50%':
                bucket = 'medium' if mastery_points < HIGH_THRESHOLD else 'high'
            elif status == 'crosses 50%':
                if threshold is None:
                    continue
                if mastery_points < threshold:
                    bucket = 'low'
                elif mastery_points < HIGH_THRESHOLD:
                    bucket = 'medium'
                else:
                    bucket = 'high'
            elif status == 'never reaches 50%':
                bucket = 'low' if mastery_points < HIGH_THRESHOLD else 'high'
            else:
                continue

            champ_data[champion_name][bucket]['games'] += 1
            if win:
                champ_data[champion_name][bucket]['wins'] += 1
            if lane:
                champ_data[champion_name]['lane_counts'][lane] += 1

        results = {}

        for champ, data in champ_data.items():
            g50_entry = g50_by_champ.get(champ, {})
            status = g50_entry.get('status')
            mastery_threshold = g50_entry.get('mastery_threshold')
            estimated_games = g50_entry.get('estimated_games')

            # Difficulty label
            if status == 'always above 50%':
                difficulty_label = 'Instantly Viable'
            elif status == 'crosses 50%' and mastery_threshold is not None and mastery_threshold >= 90_000:
                difficulty_label = 'Extremely Hard to Learn'
            elif status == 'never reaches 50%':
                difficulty_label = 'Never Viable'
            else:
                difficulty_label = None

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

            low_delta = (low_wr - med_wr) * 100 if (low_wr is not None and med_wr is not None) else None
            delta = (high_wr - med_wr) * 100 if (high_wr is not None and med_wr is not None) else None

            mastery_score = ((high_wr * 100 - 50) + (high_ratio - 1) * 50) if (high_wr is not None and high_ratio is not None) else None
            learning_score = ((low_wr * 100 - 50) + (low_ratio - 1) * 50) if (low_wr is not None and low_ratio is not None) else None
            investment_score = (learning_score * 0.4 + mastery_score * 0.6) if (learning_score is not None and mastery_score is not None) else None

            learning_tier = _learning_tier(learning_score)
            mastery_tier = _mastery_tier(mastery_score)

            lane_counts = data['lane_counts']
            most_common_lane = max(lane_counts, key=lane_counts.get) if lane_counts else None

            results[champ] = {
                'low_wr': low_wr,
                'medium_wr': med_wr,
                'high_wr': high_wr,
                'low_games': data['low']['games'],
                'medium_games': data['medium']['games'],
                'high_games': data['high']['games'],
                'low_ratio': low_ratio,
                'high_ratio': high_ratio,
                'low_delta': low_delta,
                'delta': delta,
                'mastery_score': mastery_score,
                'learning_score': learning_score,
                'investment_score': investment_score,
                'learning_tier': learning_tier,
                'mastery_tier': mastery_tier,
                'most_common_lane': most_common_lane,
                'bias_status': status,
                'mastery_threshold': mastery_threshold,
                'estimated_games': estimated_games,
                'difficulty_label': difficulty_label,
            }

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
        """Run the full analysis pipeline (all aggregation done in SQLite)."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Analysis: {self.elo_filter} ({self.filter_config['description']})")
        logger.info(f"{'='*60}\n")

        pipeline_start = time.time()
        self.db.begin_analysis_session(self.elo_filter, self.patch_filter)
        db_elapsed = time.time() - pipeline_start
        logger.info(f"  DB materialization done in {db_elapsed:.1f}s ({db_elapsed/60:.1f} min)")
        try:
            return self._analyze_inner(pipeline_start)
        finally:
            self.db.end_analysis_session()

    def _analyze_inner(self, pipeline_start: float) -> Dict:
        """Inner analysis pipeline — called with _fm already materialized."""
        STEPS_TOTAL = 17  # 1 DB materialization + 16 compute steps
        steps_done = [1]  # DB materialization already counted as step 1

        def step(name, fn, *args, **kwargs):
            n = steps_done[0] + 1
            logger.info(f"  [{n}/{STEPS_TOTAL}] {name}...")
            t0 = time.time()
            result = fn(*args, **kwargs)
            elapsed = time.time() - t0
            steps_done[0] = n
            total_so_far = time.time() - pipeline_start
            remaining = STEPS_TOTAL - n
            if remaining > 0:
                eta_secs = (total_so_far / n) * remaining
                finish_at = datetime.datetime.now() + datetime.timedelta(seconds=eta_secs)
                logger.info(
                    f"         done in {elapsed:.1f}s"
                    f" | {remaining} steps left"
                    f" — est. {eta_secs/60:.1f} min"
                    f" (done ~{finish_at.strftime('%I:%M %p')})"
                )
            else:
                logger.info(f"         done in {elapsed:.1f}s")
            return result

        summary = step("Summary", self.compute_summary)
        if summary.get('total_matches', 0) == 0:
            logger.error("No data to analyze!")
            return {}

        distribution = step("Mastery distribution", self.compute_mastery_distribution)
        overall_buckets = step("Overall WR by bucket", self.compute_overall_winrate_by_bucket)
        winrate_curve = step("Win rate curve", self.compute_winrate_curve)
        champion_stats = step("Champion stats", self.compute_champion_stats)
        lane_impact = step("Lane impact", self.compute_lane_impact, champion_stats)

        # Fetch shared per-champion/interval data once; reused by three methods
        interval_rows, lane_rows = step(
            "Load mastery curve data",
            self.db.get_mastery_curves_aggregated, self.elo_filter, self.patch_filter)
        games_to_50 = step("Games to 50% WR", self.compute_games_to_50_winrate, interval_rows, lane_rows)
        bias_champion_stats = step("Bias champion stats", self.compute_bias_champion_stats, games_to_50)
        mastery_curves = step("Mastery curves", self.compute_mastery_curves_by_champion, interval_rows, lane_rows)
        slope_iterations = step("Slope iterations", self.compute_slope_iterations, mastery_curves)

        # Per-lane analysis
        lane_bucket_rows, lane_lane_rows = step(
            "Champion stats by lane (load)", self.db.get_champion_stats_aggregated_by_lane)
        lane_interval_rows = step(
            "Mastery curves by lane (load)", self.db.get_mastery_curves_aggregated_by_lane)
        champion_stats_by_lane = step(
            "Champion stats by lane",
            self.compute_champion_stats_by_lane, lane_bucket_rows, lane_lane_rows)
        mastery_curves_by_lane = step(
            "Mastery curves by lane",
            self.compute_mastery_curves_by_champion_and_lane, lane_interval_rows)
        slope_iterations_by_lane = step(
            "Slope iterations by lane",
            self.compute_slope_iterations_by_lane, mastery_curves_by_lane)

        # Pabu: 30k medium boundary + elo-normalized threshold
        elo_avg_wr = summary['overall_win_rate']
        pabu_champion_stats = step("Pabu champion stats", self.compute_pabu_champion_stats)
        pabu_games_to_threshold = step(
            "Pabu games to threshold",
            self.compute_games_to_50_winrate, interval_rows, lane_rows, threshold=elo_avg_wr)

        # Bias rankings
        bias_instantly_viable = sorted(
            [(c, s) for c, s in bias_champion_stats.items()
             if s.get('bias_status') == 'always above 50%' and s.get('medium_wr') is not None],
            key=lambda x: x[1]['medium_wr'],
            reverse=True
        )
        bias_easiest_base = sorted(
            [(c, s) for c, s in bias_champion_stats.items() if s['learning_score'] is not None],
            key=lambda x: x[1]['learning_score'],
            reverse=True
        )
        bias_easiest_to_learn = [
            {'champion': c, **s} for c, s in (bias_instantly_viable + bias_easiest_base)
        ]

        bias_best_to_master = sorted(
            [(c, s) for c, s in bias_champion_stats.items() if s['mastery_score'] is not None],
            key=lambda x: x[1]['mastery_score'],
            reverse=True
        )

        bias_best_investment = sorted(
            [(c, s) for c, s in bias_champion_stats.items() if s['investment_score'] is not None],
            key=lambda x: x[1]['investment_score'],
            reverse=True
        )

        # Rankings — easiest_to_learn sorted by games-to-50 approach
        g50_lookup = {entry['champion_name']: entry for entry in games_to_50}

        def easiest_sort_key(item):
            champ, _ = item
            g50 = g50_lookup.get(champ)
            if g50 is None:
                return (3, 0, champ)
            status = g50.get('status', '')
            if status == 'always above 50%':
                return (0, 0, champ)
            elif status == 'crosses 50%':
                est = g50.get('estimated_games') or 0
                return (1, est, champ)
            elif status == 'never reaches 50%':
                return (2, 0, champ)
            else:  # low data
                return (3, 0, champ)

        easiest_to_learn = sorted(champion_stats.items(), key=easiest_sort_key)

        best_to_master = sorted(
            [(c, s) for c, s in champion_stats.items() if s['mastery_score'] is not None],
            key=lambda x: x[1]['mastery_score'],
            reverse=True
        )

        best_investment = sorted(
            [(c, s) for c, s in champion_stats.items() if s['investment_score'] is not None],
            key=lambda x: x[1]['investment_score'],
            reverse=True
        )

        # Pabu rankings — easiest_to_learn sorted by games-to-threshold
        pabu_g50_lookup = {entry['champion_name']: entry for entry in pabu_games_to_threshold}

        def pabu_easiest_sort_key(item):
            champ, _ = item
            g50 = pabu_g50_lookup.get(champ)
            if g50 is None:
                return (3, 0, champ)
            status = g50.get('status', '')
            if status == 'always above 50%':
                return (0, 0, champ)
            elif status == 'crosses 50%':
                est = g50.get('estimated_games') or 0
                return (1, est, champ)
            elif status == 'never reaches 50%':
                return (2, 0, champ)
            else:
                return (3, 0, champ)

        pabu_easiest_sorted = sorted(pabu_champion_stats.items(), key=pabu_easiest_sort_key)

        pabu_best_to_master_sorted = sorted(
            [(c, s) for c, s in pabu_champion_stats.items() if s['mastery_score'] is not None],
            key=lambda x: x[1]['mastery_score'],
            reverse=True,
        )

        # Strip raw_values from distribution before saving (too large for JSON)
        dist_for_save = {k: v for k, v in distribution.items() if k != 'raw_values'}

        results = {
            'filter': self.elo_filter,
            'filter_description': self.filter_config['description'],
            'generated_at': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'summary': summary,
            'mastery_distribution': dist_for_save,
            'overall_winrate_by_bucket': overall_buckets,
            'winrate_curve': winrate_curve,
            'champion_stats': champion_stats,
            'lane_impact': lane_impact,
            'easiest_to_learn': [
                {
                    'champion': c,
                    'games_to_50_status': g50_lookup.get(c, {}).get('status'),
                    'estimated_games': g50_lookup.get(c, {}).get('estimated_games'),
                    'mastery_threshold': g50_lookup.get(c, {}).get('mastery_threshold'),
                    'starting_winrate': g50_lookup.get(c, {}).get('starting_winrate'),
                    **s
                } for c, s in easiest_to_learn
            ],
            'best_to_master': [
                {'champion': c, **s} for c, s in best_to_master
            ],
            'best_investment': [
                {'champion': c, **s} for c, s in best_investment
            ],
            'games_to_50_winrate': games_to_50,
            'bias_champion_stats': bias_champion_stats,
            'bias_easiest_to_learn': bias_easiest_to_learn,
            'bias_best_to_master': [
                {'champion': c, **s} for c, s in bias_best_to_master
            ],
            'bias_best_investment': [
                {'champion': c, **s} for c, s in bias_best_investment
            ],
            'mastery_curves': mastery_curves,
            'slope_iterations': slope_iterations,
            'champion_stats_by_lane': champion_stats_by_lane,
            'mastery_curves_by_lane': mastery_curves_by_lane,
            'slope_iterations_by_lane': slope_iterations_by_lane,
            'pabu_champion_stats': pabu_champion_stats,
            'pabu_games_to_threshold': pabu_games_to_threshold,
            'pabu_easiest_to_learn': [
                {
                    'champion': c,
                    'games_to_50_status': pabu_g50_lookup.get(c, {}).get('status'),
                    'estimated_games': pabu_g50_lookup.get(c, {}).get('estimated_games'),
                    'mastery_threshold': pabu_g50_lookup.get(c, {}).get('mastery_threshold'),
                    'starting_winrate': pabu_g50_lookup.get(c, {}).get('starting_winrate'),
                    **s
                } for c, s in pabu_easiest_sorted
            ],
            'pabu_best_to_master': [
                {'champion': c, **s} for c, s in pabu_best_to_master_sorted
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
    parser.add_argument('--patches', choices=['current', 'last3', 'season'], default='season',
                        help='Patch range to include (default: season — all S16 patches)')
    parser.add_argument('--season', type=int, default=16,
                        help='Season number for --patches=season (default: 16)')
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
    elif args.patches == 'season':
        patch_versions = patch_mgr.get_season_patches(args.season)
    else:
        patch_versions = patch_mgr.get_last_n_patches(3)
    logger.info(f"Patch filter: {patch_versions}")

    filters = list(ELO_FILTERS.keys()) if args.filter == 'all' else [args.filter]
    logger.info(f"Processing {len(filters)} filter(s)")

    run_start = time.time()
    filter_times = []

    for i, elo_filter in enumerate(tqdm(filters, desc="Analyzing filters", unit="filter"), 1):
        logger.info(f"Processing filter {i} of {len(filters)}: {elo_filter}")
        filter_start = time.time()
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
                    est = entry.get('estimated_games')
                    est_str = f"{est} games" if est is not None else 'N/A'
                    logger.info(
                        f"    {entry['champion']:20s} "
                        f"Status: {entry.get('games_to_50_status', 'N/A'):20s} "
                        f"Est: {est_str:12s} "
                        f"({entry['most_common_lane']})"
                    )

            # Print top 5 best to master
            if results['best_to_master']:
                logger.info(f"\n  Top 5 Best to Master:")
                for entry in results['best_to_master'][:5]:
                    logger.info(
                        f"    {entry['champion']:20s} "
                        f"Score: {entry['mastery_score']:.2f}  "
                        f"Ratio: {entry['high_ratio']:.3f}  "
                        f"Delta: {entry['delta']:+.2f}pp "
                        f"({entry['most_common_lane']})"
                    )

            # Print top 5 best investment
            if results['best_investment']:
                logger.info(f"\n  Top 5 Best Investment:")
                for entry in results['best_investment'][:5]:
                    logger.info(
                        f"    {entry['champion']:20s} "
                        f"Investment: {entry['investment_score']:.2f}  "
                        f"Learn: {entry['learning_score']:.2f}  "
                        f"Master: {entry['mastery_score']:.2f} "
                        f"({entry['most_common_lane']})"
                    )

            filter_elapsed = time.time() - filter_start
            filter_times.append(filter_elapsed)
            avg = sum(filter_times) / len(filter_times)
            remaining = len(filters) - i
            eta_secs = avg * remaining
            finish_at = datetime.datetime.now() + datetime.timedelta(seconds=eta_secs)
            logger.info(
                f"\n  Timing: {elo_filter} took {filter_elapsed:.1f}s"
                f" | avg {avg:.1f}s/filter"
                + (f" | {remaining} remaining — est. {eta_secs/60:.1f} min"
                   f" (done ~{finish_at.strftime('%I:%M %p')})"
                   if remaining else "")
            )

        except Exception as e:
            filter_elapsed = time.time() - filter_start
            filter_times.append(filter_elapsed)
            logger.error(f"Error analyzing {elo_filter}: {e}", exc_info=True)

    total_elapsed = time.time() - run_start
    logger.info(f"\nAnalysis complete! Total time: {total_elapsed/60:.1f} min ({total_elapsed:.0f}s)")


if __name__ == '__main__':
    main()
