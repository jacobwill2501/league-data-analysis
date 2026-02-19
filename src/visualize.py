"""
Visualization script - Generate charts from analysis JSON files
"""

import argparse
import json
import logging
import os
import sys

from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from config import (ELO_FILTERS, CHART_DPI, CHART_FIGSIZE_LARGE,
                    CHART_FIGSIZE_MEDIUM, MASTERY_DISPLAY_CAP, LANE_DISPLAY_NAMES)
from utils import setup_logging, create_output_dirs

logger = logging.getLogger(__name__)

# Consistent color palette
COLORS = {
    'low': '#e74c3c',      # Red
    'medium': '#f39c12',   # Orange
    'high': '#2ecc71',     # Green
    'curve': '#3498db',    # Blue
    'reference': '#95a5a6', # Gray
}


def load_results(input_dir: str, filter_name: str) -> dict:
    """Load analysis results JSON"""
    path = os.path.join(input_dir, f"{filter_name}_results.json")
    if not os.path.exists(path):
        logger.error(f"Results file not found: {path}")
        return None

    with open(path, 'r') as f:
        return json.load(f)


def chart_mastery_distribution(results: dict, output_dir: str, filter_name: str):
    """Generate mastery distribution histogram"""
    dist = results.get('mastery_distribution', {})
    if not dist:
        logger.warning("No mastery distribution data, skipping histogram")
        return

    # We don't have raw_values in the saved JSON (stripped to save space).
    # Use bucket counts to create a summary bar chart instead.
    bucket_counts = dist.get('bucket_counts', {})
    if not bucket_counts:
        return

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_LARGE)

    labels = ['Low (<10k)', 'Medium (10k-100k)', 'High (100k+)']
    counts = [
        bucket_counts.get('low', 0),
        bucket_counts.get('medium', 0),
        bucket_counts.get('high', 0),
    ]
    colors = [COLORS['low'], COLORS['medium'], COLORS['high']]

    bars = ax.bar(labels, counts, color=colors, edgecolor='white', linewidth=0.5)

    # Add count labels on bars
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f'{count:,}', ha='center', va='bottom', fontsize=11)

    ax.set_title(f'Distribution of Champion Mastery ({filter_name})', fontsize=14, pad=15)
    ax.set_ylabel('Count of Player-Champion Pairs', fontsize=12)
    ax.set_xlabel('Mastery Bucket', fontsize=12)

    # Add stats annotation
    stats_text = (
        f"Mean: {dist.get('mean', 0):,.0f}\n"
        f"Median: {dist.get('median', 0):,.0f}\n"
        f"Total: {dist.get('count', 0):,}"
    )
    ax.text(0.98, 0.95, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    path = os.path.join(output_dir, f'{filter_name}_mastery_distribution.png')
    fig.savefig(path, dpi=CHART_DPI)
    plt.close(fig)
    logger.info(f"  Saved: {path}")


def chart_winrate_curve(results: dict, output_dir: str, filter_name: str):
    """Generate win rate by mastery curve"""
    curve = results.get('winrate_curve', [])
    if not curve:
        logger.warning("No win rate curve data, skipping")
        return

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_LARGE)

    labels = [pt['interval'] for pt in curve]
    win_rates = [pt['win_rate'] * 100 for pt in curve]
    games = [pt['games'] for pt in curve]

    ax.plot(labels, win_rates, color=COLORS['curve'], marker='o',
            linewidth=2, markersize=8, zorder=3)

    # Fill area under/above 50%
    ax.fill_between(range(len(labels)), win_rates, 50,
                    where=[wr >= 50 for wr in win_rates],
                    color=COLORS['high'], alpha=0.15)
    ax.fill_between(range(len(labels)), win_rates, 50,
                    where=[wr < 50 for wr in win_rates],
                    color=COLORS['low'], alpha=0.15)

    # 50% reference line
    ax.axhline(y=50, color=COLORS['reference'], linestyle='--', linewidth=1, label='50% Win Rate')

    # Annotate points with sample sizes
    for i, (label, wr, n) in enumerate(zip(labels, win_rates, games)):
        ax.annotate(f'{wr:.1f}%\n({n:,})', (i, wr),
                    textcoords="offset points", xytext=(0, 12),
                    ha='center', fontsize=8)

    ax.set_title(f'Mastery Impact on Win Rates ({filter_name})', fontsize=14, pad=15)
    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_xlabel('Mastery Points', fontsize=12)
    ax.legend(fontsize=10)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    path = os.path.join(output_dir, f'{filter_name}_winrate_curve.png')
    fig.savefig(path, dpi=CHART_DPI)
    plt.close(fig)
    logger.info(f"  Saved: {path}")


def chart_lane_impact(results: dict, output_dir: str, filter_name: str):
    """Generate win rate by lane grouped bar chart"""
    lane_data = results.get('lane_impact', {})
    if not lane_data:
        logger.warning("No lane impact data, skipping")
        return

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_MEDIUM)

    lanes = []
    low_wrs = []
    med_wrs = []
    high_wrs = []

    for lane_key, data in lane_data.items():
        display = data.get('display_name', LANE_DISPLAY_NAMES.get(lane_key, lane_key))
        lanes.append(display)
        low_wrs.append((data.get('avg_low_wr') or 0) * 100)
        med_wrs.append((data.get('avg_medium_wr') or 0) * 100)
        high_wrs.append((data.get('avg_high_wr') or 0) * 100)

    import numpy as np
    x = np.arange(len(lanes))
    width = 0.25

    bars1 = ax.bar(x - width, low_wrs, width, label='Low (<10k)',
                   color=COLORS['low'], edgecolor='white')
    bars2 = ax.bar(x, med_wrs, width, label='Medium (10k-100k)',
                   color=COLORS['medium'], edgecolor='white')
    bars3 = ax.bar(x + width, high_wrs, width, label='High (100k+)',
                   color=COLORS['high'], edgecolor='white')

    ax.set_title(f'Mastery Impact on Win Rate by Lane ({filter_name})', fontsize=14, pad=15)
    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(lanes, fontsize=11)
    ax.legend(fontsize=10)
    ax.axhline(y=50, color=COLORS['reference'], linestyle='--', linewidth=0.8)

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, height,
                        f'{height:.1f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    path = os.path.join(output_dir, f'{filter_name}_lane_impact.png')
    fig.savefig(path, dpi=CHART_DPI)
    plt.close(fig)
    logger.info(f"  Saved: {path}")


def chart_easiest_to_learn(results: dict, output_dir: str, filter_name: str):
    """Generate top 10 easiest to learn horizontal bar chart"""
    ranking = results.get('easiest_to_learn', [])
    if not ranking:
        logger.warning("No easiest to learn data, skipping")
        return

    top10 = ranking[:10]
    top10.reverse()  # Reverse for horizontal bar chart (top at top)

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_MEDIUM)

    labels = []
    for entry in top10:
        lane = LANE_DISPLAY_NAMES.get(entry.get('most_common_lane', ''),
                                       entry.get('most_common_lane', ''))
        labels.append(f"{entry['champion']} ({lane})")

    ratios = [entry['low_ratio'] for entry in top10]

    colors = [COLORS['high'] if r >= 0.90 else COLORS['medium'] if r >= 0.85 else COLORS['low']
              for r in ratios]

    bars = ax.barh(labels, ratios, color=colors, edgecolor='white')

    # Add ratio labels
    for bar, ratio in zip(bars, ratios):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                f'{ratio:.2f}', ha='left', va='center', fontsize=10)

    ax.set_title(f'Top 10 Easiest to Learn ({filter_name})', fontsize=14, pad=15)
    ax.set_xlabel('Low Mastery Ratio (higher = easier to learn)', fontsize=11)
    ax.axvline(x=1.0, color=COLORS['reference'], linestyle='--', linewidth=0.8)

    plt.tight_layout()
    path = os.path.join(output_dir, f'{filter_name}_easiest_to_learn.png')
    fig.savefig(path, dpi=CHART_DPI)
    plt.close(fig)
    logger.info(f"  Saved: {path}")


def chart_best_to_master(results: dict, output_dir: str, filter_name: str):
    """Generate top 10 best to master horizontal bar chart"""
    ranking = results.get('best_to_master', [])
    if not ranking:
        logger.warning("No best to master data, skipping")
        return

    top10 = ranking[:10]
    top10.reverse()

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_MEDIUM)

    labels = []
    for entry in top10:
        lane = LANE_DISPLAY_NAMES.get(entry.get('most_common_lane', ''),
                                       entry.get('most_common_lane', ''))
        labels.append(f"{entry['champion']} ({lane})")

    ratios = [entry['high_ratio'] for entry in top10]

    colors = [COLORS['high'] if r >= 1.07 else COLORS['medium'] if r >= 1.04 else COLORS['low']
              for r in ratios]

    bars = ax.barh(labels, ratios, color=colors, edgecolor='white')

    for bar, ratio in zip(bars, ratios):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                f'{ratio:.2f}', ha='left', va='center', fontsize=10)

    ax.set_title(f'Top 10 Best to Master ({filter_name})', fontsize=14, pad=15)
    ax.set_xlabel('High Mastery Ratio (higher = more reward for mastery)', fontsize=11)
    ax.axvline(x=1.0, color=COLORS['reference'], linestyle='--', linewidth=0.8)

    plt.tight_layout()
    path = os.path.join(output_dir, f'{filter_name}_best_to_master.png')
    fig.savefig(path, dpi=CHART_DPI)
    plt.close(fig)
    logger.info(f"  Saved: {path}")


def generate_all_charts(results: dict, output_dir: str, filter_name: str):
    """Generate all charts for a filter"""
    logger.info(f"\nGenerating charts for: {filter_name}")

    os.makedirs(output_dir, exist_ok=True)

    # Set seaborn style
    sns.set_theme(style='whitegrid')

    chart_mastery_distribution(results, output_dir, filter_name)
    chart_winrate_curve(results, output_dir, filter_name)
    chart_lane_impact(results, output_dir, filter_name)
    chart_easiest_to_learn(results, output_dir, filter_name)
    chart_best_to_master(results, output_dir, filter_name)


def main():
    parser = argparse.ArgumentParser(description='Generate charts from analysis results')
    parser.add_argument('--filter', choices=list(ELO_FILTERS.keys()) + ['all'],
                        default='all',
                        help='Elo filter to visualize (default: all)')
    parser.add_argument('--input', type=str, default='output/analysis',
                        help='Input directory with analysis JSON files')
    parser.add_argument('--output', type=str, default='output/charts',
                        help='Output directory for charts')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    logger.info("Starting visualization...")
    create_output_dirs()

    filters = list(ELO_FILTERS.keys()) if args.filter == 'all' else [args.filter]
    charts_per_filter = 5
    logger.info(f"Will generate up to {len(filters) * charts_per_filter} charts across {len(filters)} filter(s)")

    for i, filter_name in enumerate(tqdm(filters, desc="Generating charts", unit="filter"), 1):
        logger.info(f"Processing filter {i} of {len(filters)}: {filter_name}")
        results = load_results(args.input, filter_name)
        if results is None:
            logger.warning(f"Skipping {filter_name} — no results file found")
            continue

        generate_all_charts(results, args.output, filter_name)

    logger.info("\nVisualization complete!")


if __name__ == '__main__':
    main()
