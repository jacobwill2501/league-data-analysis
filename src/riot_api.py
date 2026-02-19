"""
Riot API client with rate limiting
"""
import time
import logging
import requests
from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime, timedelta
import threading

import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter with per-second and per-2-minute limits
    Tracks limits per (endpoint_group, region) pair
    """

    def __init__(self, endpoint_group: str, region: str, limits: Dict[str, int]):
        """
        Initialize rate limiter

        Args:
            endpoint_group: API endpoint group (e.g., 'match-v5')
            region: Region code
            limits: Dictionary with 'per_second' and 'per_2min' keys
        """
        self.endpoint_group = endpoint_group
        self.region = region
        self.per_second_limit = limits['per_second']
        self.per_2min_limit = int(limits['per_2min'] * 0.95)  # 5% margin for timing drift

        # Sliding window tracking
        self.per_second_requests = deque()
        self.per_2min_requests = deque()

        # Thread safety
        self.lock = threading.Lock()

        logger.debug(
            f"RateLimiter initialized for {endpoint_group}/{region}: "
            f"{self.per_second_limit}/s, {self.per_2min_limit}/2min"
        )

    RATE_LIMIT_BUFFER = 0.1  # 100ms safety margin

    def _clean_old_requests(self, now: float):
        """Remove timestamps outside the tracking windows"""
        # Clean per-second window
        while self.per_second_requests and self.per_second_requests[0] < now - 1:
            self.per_second_requests.popleft()

        # Clean per-2-minute window
        while self.per_2min_requests and self.per_2min_requests[0] < now - 120:
            self.per_2min_requests.popleft()

    def reset(self):
        """Backfill to capacity after a 429 to prevent burst"""
        with self.lock:
            now = time.time()
            self.per_second_requests.clear()
            self.per_2min_requests.clear()
            for _ in range(self.per_second_limit):
                self.per_second_requests.append(now)
            for _ in range(self.per_2min_limit):
                self.per_2min_requests.append(now)
            logger.debug(f"Rate limiter backfilled for {self.endpoint_group}/{self.region}")

    def wait_if_needed(self) -> float:
        """
        Wait if necessary to respect rate limits

        Returns:
            Time waited in seconds
        """
        wait_time = 0.0
        with self.lock:
            now = time.time()
            self._clean_old_requests(now)

            # Check per-second limit
            if len(self.per_second_requests) >= self.per_second_limit:
                oldest = self.per_second_requests[0]
                wait_until = oldest + 1
                if wait_until > now:
                    wait_time = max(wait_time, wait_until - now + self.RATE_LIMIT_BUFFER)

            # Check per-2-minute limit
            if len(self.per_2min_requests) >= self.per_2min_limit:
                oldest = self.per_2min_requests[0]
                wait_until = oldest + 120
                if wait_until > now:
                    wait_time = max(wait_time, wait_until - now + self.RATE_LIMIT_BUFFER)

            # Reserve a slot with estimated completion time so other
            # threads see accurate capacity while we sleep outside the lock
            estimated_time = now + wait_time if wait_time > 0 else now
            self.per_second_requests.append(estimated_time)
            self.per_2min_requests.append(estimated_time)

        # Sleep OUTSIDE the lock — other threads can now check/sleep independently
        if wait_time > 0:
            logger.debug(
                f"Rate limit reached for {self.endpoint_group}/{self.region}, "
                f"waiting {wait_time:.2f}s"
            )
            time.sleep(wait_time)

        return wait_time


class RiotAPIClient:
    """
    Riot API client with automatic rate limiting and retry logic
    """

    def __init__(self, api_key: Optional[str] = None, use_dev_key: bool = False):
        """
        Initialize Riot API client

        Args:
            api_key: Riot API key (defaults to config.RIOT_API_KEY)
            use_dev_key: Use development key rate limits
        """
        self.api_key = api_key or config.RIOT_API_KEY
        if not self.api_key:
            raise ValueError("Riot API key not provided")

        self.use_dev_key = use_dev_key
        self.rate_limits = config.get_rate_limits(use_dev_key)

        # Rate limiters per (endpoint_group, region)
        self.limiters: Dict[tuple, RateLimiter] = {}
        self.limiter_lock = threading.Lock()

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({'X-Riot-Token': self.api_key})

        logger.info(
            f"RiotAPIClient initialized with "
            f"{'development' if use_dev_key else 'production'} rate limits"
        )

    def _get_limiter(self, endpoint_group: str, region: str) -> RateLimiter:
        """
        Get or create rate limiter for endpoint group and region

        Args:
            endpoint_group: API endpoint group
            region: Region code

        Returns:
            RateLimiter instance
        """
        key = (endpoint_group, region)

        with self.limiter_lock:
            if key not in self.limiters:
                limits = self.rate_limits[endpoint_group]
                self.limiters[key] = RateLimiter(endpoint_group, region, limits)

            return self.limiters[key]

    def _make_request(self, url: str, endpoint_group: str, region: str,
                     params: Optional[Dict] = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        Make an API request with rate limiting and retry logic

        Args:
            url: Full API URL
            endpoint_group: API endpoint group for rate limiting
            region: Region code
            params: Query parameters
            max_retries: Maximum number of retries

        Returns:
            Response JSON data

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        limiter = self._get_limiter(endpoint_group, region)

        for attempt in range(max_retries):
            # Wait for rate limits
            limiter.wait_if_needed()

            try:
                response = self.session.get(url, params=params, timeout=10)

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 1))
                    logger.warning(
                        f"Rate limited (429) for {endpoint_group}/{region}, "
                        f"retrying after {retry_after}s"
                    )
                    limiter.reset()
                    time.sleep(retry_after)
                    continue

                # Handle bad request (400) - permanent client error, no point retrying
                if response.status_code == 400:
                    logger.warning(
                        f"Bad request (400): {url} | "
                        f"Response: {response.text}"
                    )
                    return None

                # Handle not found (404) - valid response for some endpoints
                if response.status_code == 404:
                    logger.debug(f"Resource not found (404): {url}")
                    return None

                # Handle server errors (502, 503) - transient, retry with backoff
                if response.status_code in (502, 503):
                    logger.warning(
                        f"Server error ({response.status_code}) for {endpoint_group}/{region}, "
                        f"attempt {attempt + 1}/{max_retries}, retrying after {2 ** attempt}s"
                    )
                    time.sleep(2 ** attempt)
                    continue

                # Raise for other HTTP errors
                response.raise_for_status()

                # Log actual rate limits from headers on first success per endpoint
                if not hasattr(self, '_logged_limits'):
                    self._logged_limits = set()
                if endpoint_group not in self._logged_limits:
                    self._logged_limits.add(endpoint_group)
                    app_limit = response.headers.get('X-App-Rate-Limit', 'unknown')
                    method_limit = response.headers.get('X-Method-Rate-Limit', 'unknown')
                    app_count = response.headers.get('X-App-Rate-Limit-Count', 'unknown')
                    logger.info(
                        f"Rate limits for {endpoint_group}: "
                        f"app={app_limit}, method={method_limit}, current_usage={app_count}"
                    )

                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                logger.error(f"Request timeout after {max_retries} attempts for {url}, skipping")
                return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                logger.error(f"Request failed after {max_retries} attempts for {url}, skipping")
                return None

        # All retries exhausted — skip rather than crash
        logger.error(f"Max retries ({max_retries}) exceeded for {url}, skipping")
        return None

    # League-v4 endpoints
    def get_league_entries(self, region: str, queue: str, tier: str,
                          division: str, page: int = 1) -> List[Dict]:
        """
        Get league entries for a specific tier/division

        Args:
            region: Region code (NA, EUW, KR)
            queue: Queue type (e.g., 'RANKED_SOLO_5x5')
            tier: Tier (e.g., 'DIAMOND')
            division: Division (I, II, III, IV)
            page: Page number (1-indexed)

        Returns:
            List of league entry dictionaries
        """
        platform = config.REGIONS[region]['platform']
        url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/{queue}/{tier}/{division}"
        params = {'page': page}

        result = self._make_request(url, 'league-v4', region, params)
        return result if result else []

    def get_master_league(self, region: str, queue: str) -> Dict:
        """Get Master tier league"""
        platform = config.REGIONS[region]['platform']
        url = f"https://{platform}.api.riotgames.com/lol/league/v4/masterleagues/by-queue/{queue}"
        return self._make_request(url, 'league-v4', region)

    def get_grandmaster_league(self, region: str, queue: str) -> Dict:
        """Get Grandmaster tier league"""
        platform = config.REGIONS[region]['platform']
        url = f"https://{platform}.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/{queue}"
        return self._make_request(url, 'league-v4', region)

    def get_challenger_league(self, region: str, queue: str) -> Dict:
        """Get Challenger tier league"""
        platform = config.REGIONS[region]['platform']
        url = f"https://{platform}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/{queue}"
        return self._make_request(url, 'league-v4', region)

    # Summoner-v4 endpoints
    def get_summoner_by_id(self, region: str, summoner_id: str) -> Dict:
        """
        Get summoner by encrypted summoner ID

        Args:
            region: Region code
            summoner_id: Encrypted summoner ID

        Returns:
            Summoner data including puuid
        """
        platform = config.REGIONS[region]['platform']
        url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
        return self._make_request(url, 'summoner-v4', region)

    # Match-v5 endpoints
    def get_match_ids_by_puuid(self, region: str, puuid: str,
                               queue: Optional[int] = None,
                               start: int = 0, count: int = 100,
                               start_time: Optional[int] = None,
                               end_time: Optional[int] = None) -> List[str]:
        """
        Get match IDs for a player

        Args:
            region: Region code
            puuid: Player PUUID
            queue: Queue ID (420 for ranked solo)
            start: Start index
            count: Number of matches to return
            start_time: Epoch timestamp (seconds) for earliest match
            end_time: Epoch timestamp (seconds) for latest match

        Returns:
            List of match IDs
        """
        routing = config.REGIONS[region]['routing']
        url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"

        params = {'start': start, 'count': count}
        if queue:
            params['queue'] = queue
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        result = self._make_request(url, 'match-v5', region, params)
        return result if result else []

    def get_match(self, region: str, match_id: str) -> Optional[Dict]:
        """
        Get match details

        Args:
            region: Region code
            match_id: Match ID

        Returns:
            Match data dictionary or None if not found
        """
        routing = config.REGIONS[region]['routing']
        url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return self._make_request(url, 'match-v5', region)

    # Champion-mastery-v4 endpoints
    def get_all_champion_mastery(self, region: str, puuid: str) -> Optional[List[Dict]]:
        """
        Get all champion mastery entries for a player in one call

        Args:
            region: Region code
            puuid: Player PUUID

        Returns:
            List of mastery data dicts, or None on error
        """
        platform = config.REGIONS[region]['platform']
        url = (f"https://{platform}.api.riotgames.com/lol/champion-mastery/v4/"
               f"champion-masteries/by-puuid/{puuid}")
        return self._make_request(url, 'champion-mastery-v4', region)

    def get_champion_mastery(self, region: str, puuid: str, champion_id: int) -> Optional[Dict]:
        """
        Get champion mastery for a player-champion pair

        Args:
            region: Region code
            puuid: Player PUUID
            champion_id: Champion ID

        Returns:
            Mastery data or None if no mastery
        """
        platform = config.REGIONS[region]['platform']
        url = (f"https://{platform}.api.riotgames.com/lol/champion-mastery/v4/"
               f"champion-masteries/by-puuid/{puuid}/by-champion/{champion_id}")
        return self._make_request(url, 'champion-mastery-v4', region)

    def close(self):
        """Close the session"""
        self.session.close()
        logger.info("RiotAPIClient session closed")
