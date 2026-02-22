"""
Step 2: Collect match data from Riot API

For each collected player, fetch their recent ranked match IDs,
then fetch full match details and store participants.
"""

import argparse
import logging
import os
import signal
import sqlite3
import sys
import time
from typing import Optional

from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (REGIONS, RANKED_SOLO_QUEUE_ID, MINIMUM_GAME_DURATION,
                    DEFAULT_MATCH_TARGET, MATCH_TARGET_PRESETS,
                    TIER_ALLOCATION, APEX_TIERS)
from db import Database
from riot_api import RiotAPIClient, TransientAPIError, _shutdown_event, _interruptible_sleep
from utils import setup_logging, format_duration, format_number, PatchManager

logger = logging.getLogger(__name__)

_shutdown = False


def _signal_handler(sig, frame):
    global _shutdown
    logger.info("\nShutdown requested, finishing current task...")
    _shutdown = True
    _shutdown_event.set()  # Wake up any sleeping threads immediately


signal.signal(signal.SIGINT, _signal_handler)


def get_patch_time_range(patches_mode: str) -> tuple:
    """Get start/end epoch timestamps for patch filtering.
    Returns (start_time, end_time) or (None, None) if not filtering."""
    # We use the match-v5 startTime/endTime params for filtering.
    # For 'current' mode, we don't set timestamps — we rely on game_version filtering later.
    # The API doesn't directly support patch filtering, so we fetch recent matches
    # and filter by game_version during validation.
    return (None, None)


def validate_match(match_data: dict) -> bool:
    """Validate a match meets our requirements"""
    if not match_data or 'info' not in match_data:
        return False

    info = match_data['info']

    if info.get('queueId') != RANKED_SOLO_QUEUE_ID:
        return False

    if len(info.get('participants', [])) != 10:
        logger.warning(f"Match has {len(info.get('participants', []))} participants, skipping")
        return False

    if info.get('gameDuration', 0) <= MINIMUM_GAME_DURATION:
        return False

    return True


def process_match(api: RiotAPIClient, db: Database, region: str, match_id: str) -> bool:
    """Fetch, validate, and store a single match. Returns True if stored."""
    match_data = api.get_match(region, match_id)

    if not match_data:
        return False

    if not validate_match(match_data):
        return False

    info = match_data['info']

    # Store match ID and participants
    participants = []
    for p in info['participants']:
        participants.append({
            'match_id': match_id,
            'puuid': p['puuid'],
            'champion_id': p['championId'],
            'champion_name': p['championName'],
            'team_id': p['teamId'],
            'win': p['win'],
            'lane': p.get('lane'),
            'role': p.get('role'),
            'individual_position': p.get('individualPosition'),
            'game_duration': info['gameDuration'],
            'game_version': info['gameVersion'],
            'queue_id': info['queueId'],
            'game_creation': info['gameCreation']
        })

    try:
        db.insert_match_id(match_id, region)
        db.insert_match_participants_batch(participants)
    except sqlite3.OperationalError as e:
        logger.warning(f"DB write failed for {match_id} (will retry next run): {e}")
        return False

    return True


def collect_matches_for_player(api: RiotAPIClient, db: Database,
                                region: str, puuid: str,
                                failed_match_ids: Optional[dict] = None) -> int:
    """Collect match IDs for a player and fetch details. Returns new match count.

    Transiently failed match IDs (502/503 exhaustion) are added to
    failed_match_ids (match_id → region) when provided, so the caller
    can schedule a retry pass after the main loop.
    """
    try:
        match_ids = api.get_match_ids_by_puuid(
            region, puuid, queue=RANKED_SOLO_QUEUE_ID,
            start=0, count=100
        )

        if not match_ids:
            return 0

        new_matches = 0
        for match_id in match_ids:
            if _shutdown:
                break

            if db.match_exists(match_id):
                continue

            try:
                if process_match(api, db, region, match_id):
                    new_matches += 1
            except TransientAPIError:
                logger.warning(
                    f"Transient failure fetching {match_id}, queuing for retry"
                )
                if failed_match_ids is not None:
                    failed_match_ids[match_id] = region

        return new_matches

    except Exception as e:
        logger.error(f"Error collecting matches for {puuid}: {e}")
        return 0


def collect_all_for_region(api: RiotAPIClient, db: Database,
                           region: str, target: int, bar_position: int = 0) -> int:
    """Collect matches for all players in a region until target is reached.
    Processes tier groups in priority order: apex -> diamond -> emerald,
    allocating each group a share of the target based on TIER_ALLOCATION."""
    TIER_GROUPS = [
        ('apex',    APEX_TIERS),
        ('diamond', ['DIAMOND']),
        ('emerald', ['EMERALD']),
    ]

    total_new = 0
    failed_match_ids: dict = {}  # match_id → region, populated by transient failures

    # Pre-compute cumulative group targets from total target
    group_targets = {}
    cumulative = 0
    for group_name, _ in TIER_GROUPS:
        alloc = TIER_ALLOCATION[group_name]
        cumulative += max(1, int(target * alloc))
        group_targets[group_name] = min(cumulative, target)

    for group_name, tiers in TIER_GROUPS:
        if _shutdown or db.count_matches(region) >= target:
            break

        group_target = group_targets[group_name]

        puuids = db.get_player_puuids_by_tiers(region, tiers)
        logger.debug(f"[{region}] {group_name}: {len(puuids)} players, "
                     f"sub-target {group_target - db.count_matches(region)} matches")

        existing_region = db.count_matches(region)
        pbar = tqdm(total=target, initial=existing_region,
                    desc=f"Matches ({region} {group_name})",
                    unit="match", leave=False, position=bar_position)
        for puuid in puuids:
            if _shutdown:
                break
            current = db.count_matches(region)
            if current >= group_target:
                break
            new = collect_matches_for_player(api, db, region, puuid, failed_match_ids)
            total_new += new
            pbar.n = db.count_matches(region)
            pbar.set_postfix(new=total_new)
            pbar.refresh()
        pbar.close()

    # Retry pass: re-attempt matches that hit sustained 5xx errors
    if failed_match_ids and not _shutdown:
        logger.info(
            f"[{region}] Retrying {len(failed_match_ids)} transiently failed matches "
            f"after 60s pause..."
        )
        _interruptible_sleep(60)
        recovered = 0
        still_failed = 0
        for match_id, match_region in failed_match_ids.items():
            if _shutdown:
                break
            try:
                if process_match(api, db, match_region, match_id):
                    recovered += 1
            except TransientAPIError:
                still_failed += 1
                logger.warning(f"Match {match_id} still unreachable after retry pass")
        logger.info(
            f"[{region}] Recovered {recovered}/{len(failed_match_ids)} "
            f"previously failed matches ({still_failed} still failing)"
        )
        total_new += recovered

    return total_new


def main():
    parser = argparse.ArgumentParser(description='Collect match data from Riot API')
    parser.add_argument('--region', choices=['NA', 'EUW', 'KR'],
                        help='Specific region to collect (default: all)')
    parser.add_argument('--target', default='1m',
                        help='Match target: preset name (500k, 1m) or integer')
    parser.add_argument('--patches', choices=['current', 'last3'], default='current',
                        help='Patch range to collect (default: current)')
    parser.add_argument('--dev-key', action='store_true',
                        help='Use conservative dev key rate limits')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--log-file', type=str,
                        help='Write logs to file')

    args = parser.parse_args()
    setup_logging(verbose=args.verbose, log_file=args.log_file)

    if args.target in MATCH_TARGET_PRESETS:
        total_target = MATCH_TARGET_PRESETS[args.target]
    else:
        total_target = int(args.target)

    logger.info("Starting match collection...")
    logger.info(f"Target: {format_number(total_target)} matches | Patches: {args.patches}")

    os.makedirs('data', exist_ok=True)

    api = RiotAPIClient(use_dev_key=args.dev_key)
    db = Database()
    db.init_schema()

    regions = [args.region] if args.region else list(REGIONS.keys())
    per_region_target = total_target // len(regions)

    existing = db.count_matches()
    remaining = max(0, total_target - existing)
    logger.info(f"Existing matches: {format_number(existing)} | Still needed: {format_number(remaining)}")

    start_time = time.time()
    total_collected = 0

    try:
        for region in regions:
            logger.debug(f"\n{'='*60}")
            logger.debug(f"Processing region: {region} (target: {format_number(per_region_target)})")
            logger.debug(f"{'='*60}")

        with ThreadPoolExecutor(max_workers=len(regions)) as executor:
            futures = {
                executor.submit(collect_all_for_region, api, db, region, per_region_target, i): region
                for i, region in enumerate(regions)
            }
            for future in as_completed(futures):
                if _shutdown:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                region = futures[future]
                try:
                    count = future.result()
                    total_collected += count
                    logger.debug(f"Region {region} complete: {count} new matches")
                except Exception as e:
                    logger.error(f"Region {region} failed: {e}")

    finally:
        api.close()

    elapsed = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info("COLLECTION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"New matches collected: {format_number(total_collected)}")
    logger.info(f"Time elapsed: {format_duration(int(elapsed))}")

    for region in regions:
        count = db.count_matches(region)
        logger.info(f"  {region}: {format_number(count)} matches")

    logger.info(f"Total matches in DB: {format_number(db.count_matches())}")


if __name__ == '__main__':
    main()
