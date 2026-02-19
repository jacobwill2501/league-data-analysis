"""
Step 1: Collect Emerald+ players from Riot API

Builds a list of all Emerald+ players across NA, EUW, KR.
Uses league-v4 to fetch player entries (which include PUUIDs directly).
"""

import argparse
import logging
import os
import signal
import sys
import time

from tqdm import tqdm

# Allow running as script from src/ or project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (REGIONS, RANKED_SOLO_QUEUE, TIERS, DIVISIONS, APEX_TIERS)
from db import Database
from riot_api import RiotAPIClient
from utils import setup_logging, format_duration, format_number

logger = logging.getLogger(__name__)

# Graceful shutdown flag
_shutdown = False


def _signal_handler(sig, frame):
    global _shutdown
    logger.info("\nShutdown requested, finishing current task...")
    _shutdown = True


signal.signal(signal.SIGINT, _signal_handler)


def collect_tier_division(api: RiotAPIClient, db: Database, region: str,
                          tier: str, division: str = None) -> int:
    """
    Collect players for a specific tier/division.
    Returns number of new players added.
    """
    task_key = f"{tier}_{division}" if division else tier
    progress = db.get_progress('collect_players', region, task_key)

    if progress and progress['status'] == 'completed':
        logger.info(f"Skipping {region} {tier} {division or ''} - already completed")
        return 0

    db.update_progress('collect_players', region, task_key, 'in_progress')

    try:
        logger.info(f"Collecting {region} {tier} {division or ''}...")

        if tier in APEX_TIERS:
            entries = _fetch_apex_tier(api, region, tier)
        else:
            entries = _fetch_tier_division(api, region, tier, division)

        logger.info(f"Found {len(entries)} entries for {tier} {division or ''}")

        players_added = 0
        pbar = tqdm(entries, desc=f"Processing ({tier} {division or ''})",
                    unit="player", leave=False)
        for entry in pbar:
            if _shutdown:
                logger.info("Shutdown requested, saving progress...")
                break

            puuid = entry.get('puuid')
            if not puuid:
                logger.warning(f"Entry missing puuid, skipping: {entry.get('summonerName', '?')}")
                continue

            # Check if already in DB
            if db.get_player_by_puuid(puuid):
                continue

            db.insert_player(
                puuid=puuid,
                summoner_id=entry.get('summonerId', ''),
                region=region,
                tier=entry.get('tier', tier),
                rank=entry.get('rank'),
                league_points=entry.get('leaguePoints', 0)
            )
            players_added += 1
            pbar.set_postfix(added=players_added)
        pbar.close()

        logger.info(f"Added {players_added} new players for {tier} {division or ''}")

        if not _shutdown:
            db.update_progress('collect_players', region, task_key, 'completed')

        return players_added

    except Exception as e:
        logger.error(f"Error collecting {tier} {division or ''}: {e}")
        db.update_progress('collect_players', region, task_key, 'failed')
        raise


def _fetch_tier_division(api: RiotAPIClient, region: str, tier: str, division: str):
    """Fetch entries for a standard tier/division (paginated)"""
    all_entries = []
    page = 1

    while True:
        data = api.get_league_entries(region, RANKED_SOLO_QUEUE, tier, division, page)

        if not data or len(data) == 0:
            break

        all_entries.extend(data)
        logger.debug(f"  Page {page}: {len(data)} entries")
        page += 1

        if page > 200:  # Safety limit
            logger.warning(f"Hit page limit for {tier} {division}")
            break

    return all_entries


def _fetch_apex_tier(api: RiotAPIClient, region: str, tier: str):
    """Fetch entries for apex tiers (Master/Grandmaster/Challenger)"""
    fetch_fn = {
        'MASTER': api.get_master_league,
        'GRANDMASTER': api.get_grandmaster_league,
        'CHALLENGER': api.get_challenger_league,
    }

    data = fetch_fn[tier](region, RANKED_SOLO_QUEUE)

    if not data or 'entries' not in data:
        return []

    entries = data['entries']
    for entry in entries:
        entry['tier'] = tier

    return entries


def collect_all_for_region(api: RiotAPIClient, db: Database, region: str) -> int:
    """Collect all Emerald+ players for a region"""
    total = 0

    # Standard tiers with divisions
    for tier in TIERS:
        for division in DIVISIONS:
            if _shutdown:
                return total
            total += collect_tier_division(api, db, region, tier, division)

    # Apex tiers (no divisions)
    for tier in APEX_TIERS:
        if _shutdown:
            return total
        total += collect_tier_division(api, db, region, tier)

    return total


def main():
    parser = argparse.ArgumentParser(description='Collect Emerald+ players from Riot API')
    parser.add_argument('--region', choices=['NA', 'EUW', 'KR'],
                        help='Specific region to collect (default: all)')
    parser.add_argument('--dev-key', action='store_true',
                        help='Use conservative dev key rate limits')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--log-file', type=str,
                        help='Write logs to file')
    parser.add_argument('--reset', nargs='+', metavar='TIER_RANK',
                        help='Reset stale players for given tier/division specs '
                             '(e.g. EMERALD_I EMERALD_II EMERALD_III). '
                             'Deletes players and progress so they are re-collected.')

    args = parser.parse_args()
    setup_logging(verbose=args.verbose, log_file=args.log_file)

    logger.info("Starting player collection...")

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    api = RiotAPIClient(use_dev_key=args.dev_key)
    db = Database()
    db.init_schema()

    regions = [args.region] if args.region else list(REGIONS.keys())

    # Handle --reset: delete stale players and progress for specified tier/divisions
    if args.reset:
        if not args.region:
            logger.error("--reset requires --region to be specified")
            sys.exit(1)
        for spec in args.reset:
            parts = spec.upper().split('_', 1)
            if len(parts) == 2:
                tier, rank = parts[0], parts[1]
            else:
                tier, rank = parts[0], None

            # Get PUUIDs before deleting so we can clean up match progress
            puuids = db.get_player_puuids_by_tier(args.region, tier, rank)
            logger.info(f"Resetting {spec}: found {len(puuids)} existing players")

            # Delete the players
            deleted = db.delete_players_by_tier(args.region, tier, rank)
            logger.info(f"Deleted {deleted} players for {args.region} {spec}")

            # Reset collect_players progress for this tier/division
            task_key = f"{tier}_{rank}" if rank else tier
            db.delete_progress('collect_players', args.region, task_key)
            logger.info(f"Reset collect_players progress for {task_key}")

            # Reset collect_matches progress for the deleted PUUIDs
            if puuids:
                match_deleted = db.delete_progress_for_puuids(
                    'collect_matches', args.region, puuids
                )
                logger.info(f"Reset {match_deleted} collect_matches progress entries")

    start_time = time.time()
    total_collected = 0
    errors = 0

    try:
        for region in regions:
            if _shutdown:
                break
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing region: {region}")
            logger.info(f"{'='*60}")

            try:
                count = collect_all_for_region(api, db, region)
                total_collected += count
                logger.info(f"Region {region} complete: {count} new players")
            except Exception as e:
                logger.error(f"Error in region {region}: {e}", exc_info=True)
                errors += 1

    finally:
        api.close()

    # Summary
    elapsed = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info("COLLECTION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"New players collected: {format_number(total_collected)}")
    logger.info(f"Errors encountered: {errors}")
    logger.info(f"Time elapsed: {format_duration(int(elapsed))}")

    for region in regions:
        count = db.count_players(region)
        logger.info(f"  {region}: {format_number(count)} total players")


if __name__ == '__main__':
    main()
