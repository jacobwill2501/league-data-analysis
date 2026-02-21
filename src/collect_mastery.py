"""
Step 3: Collect champion mastery data from Riot API

For every unique (puuid, champion_id) pair found in match_participants,
fetch the player's mastery on that champion.
"""

import argparse
import logging
import os
import signal
import sys
import time

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import REGIONS
from db import Database
from riot_api import RiotAPIClient, _shutdown_event
from utils import setup_logging, format_duration, format_number

logger = logging.getLogger(__name__)

_shutdown = False


def _signal_handler(sig, frame):
    global _shutdown
    logger.info("\nShutdown requested, finishing current task...")
    _shutdown = True
    _shutdown_event.set()  # Wake up any sleeping threads immediately


signal.signal(signal.SIGINT, _signal_handler)


BATCH_SIZE = 500
WORKER_COUNT = 5


def _fetch_mastery_for_puuid(api: RiotAPIClient, region: str, puuid: str,
                              needed_champs: list) -> list:
    """Fetch all mastery for one PUUID and return records for the needed champions."""
    records = []
    try:
        all_mastery = api.get_all_champion_mastery(region, puuid)

        # Build lookup from API response
        mastery_by_champ = {}
        if all_mastery:
            for entry in all_mastery:
                mastery_by_champ[entry['championId']] = entry

        # Match against needed pairs
        for champ_id in needed_champs:
            entry = mastery_by_champ.get(champ_id)
            if entry:
                records.append({
                    'puuid': puuid,
                    'champion_id': champ_id,
                    'mastery_points': entry.get('championPoints', 0),
                    'mastery_level': entry.get('championLevel'),
                })
            else:
                records.append({
                    'puuid': puuid,
                    'champion_id': champ_id,
                    'mastery_points': 0,
                    'mastery_level': None,
                })
    except Exception as e:
        logger.debug(f"Error fetching mastery for {puuid}: {e}")
        # Store 0 for all needed champs so we don't re-fetch
        for champ_id in needed_champs:
            records.append({
                'puuid': puuid,
                'champion_id': champ_id,
                'mastery_points': 0,
                'mastery_level': None,
            })

    return records


def collect_mastery_for_region(api: RiotAPIClient, db: Database, region: str) -> int:
    """Collect all pending mastery data for a region. Returns count collected."""
    logger.info(f"Querying pending mastery pairs for {region} (this may take a moment)...")
    puuid_map = db.get_pending_mastery_puuids(region)
    total_puuids = len(puuid_map)
    total_pairs = sum(len(v) for v in puuid_map.values())

    if total_puuids == 0:
        logger.info(f"No pending mastery data for {region}")
        return 0

    logger.info(
        f"Collecting mastery for {format_number(total_pairs)} pairs "
        f"across {format_number(total_puuids)} players in {region} "
        f"({total_pairs / total_puuids:.1f} avg champs/player)..."
    )

    collected = 0
    errors = 0
    buffer = []

    puuid_list = list(puuid_map.items())

    pbar = tqdm(total=total_puuids, desc=f"Mastery ({region})",
                unit="player", leave=False)

    def _flush_buffer():
        nonlocal buffer
        if buffer:
            db.insert_mastery_batch(buffer)
            buffer = []

    with ThreadPoolExecutor(max_workers=WORKER_COUNT) as pool:
        futures = {}
        for puuid, champs in puuid_list:
            if _shutdown:
                break
            fut = pool.submit(_fetch_mastery_for_puuid, api, region, puuid, champs)
            futures[fut] = puuid

        for future in as_completed(futures):
            if _shutdown:
                break
            try:
                records = future.result()
                buffer.extend(records)
                collected += len(records)

                if len(buffer) >= BATCH_SIZE:
                    _flush_buffer()

            except Exception as e:
                logger.debug(f"Future error for {futures[future]}: {e}")
                errors += 1

            pbar.update(1)
            pbar.set_postfix(pairs=collected, errors=errors)

            if pbar.n % 500 == 0:
                logger.info(
                    f"[{region}] {pbar.n}/{total_puuids} players, "
                    f"{collected} pairs collected ({errors} errors)"
                )

    # Flush remaining
    _flush_buffer()
    pbar.close()

    logger.info(
        f"Collected {format_number(collected)} mastery records for {region} "
        f"from {format_number(total_puuids)} API calls ({errors} errors)"
    )
    return collected


def main():
    parser = argparse.ArgumentParser(description='Collect champion mastery data from Riot API')
    parser.add_argument('--region', choices=['NA', 'EUW', 'KR'],
                        help='Specific region to collect (default: all)')
    parser.add_argument('--dev-key', action='store_true',
                        help='Use conservative dev key rate limits')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--log-file', type=str,
                        help='Write logs to file')

    args = parser.parse_args()
    setup_logging(verbose=args.verbose, log_file=args.log_file)

    logger.info("Starting mastery collection...")

    os.makedirs('data', exist_ok=True)

    api = RiotAPIClient(use_dev_key=args.dev_key)
    db = Database()
    db.init_schema()

    regions = [args.region] if args.region else list(REGIONS.keys())

    start_time = time.time()
    total_collected = 0

    try:
        for region in regions:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing region: {region}")
            logger.info(f"{'='*60}")

        with ThreadPoolExecutor(max_workers=len(regions)) as executor:
            futures = {
                executor.submit(collect_mastery_for_region, api, db, region): region
                for region in regions
            }
            for future in as_completed(futures):
                if _shutdown:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                region = futures[future]
                try:
                    count = future.result()
                    total_collected += count
                    logger.info(f"Region {region} complete: {count} mastery records")
                except Exception as e:
                    logger.error(f"Region {region} failed: {e}")

    finally:
        api.close()

    elapsed = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info("COLLECTION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total mastery records collected: {format_number(total_collected)}")
    logger.info(f"Time elapsed: {format_duration(int(elapsed))}")
    logger.info(f"Total mastery records in DB: {format_number(db.count_mastery())}")


if __name__ == '__main__':
    main()
