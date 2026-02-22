"""
Utility functions for Champion Mastery Analysis
"""
import logging
import json
import os
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

import config

logger = logging.getLogger(__name__)


class TqdmLoggingHandler(logging.Handler):
    """Logging handler that routes output through tqdm.write() to avoid breaking progress bars."""
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
        except Exception:
            self.handleError(record)


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """
    Configure logging for the application

    Args:
        verbose: Enable DEBUG level logging
        log_file: Optional file path to write logs
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = TqdmLoggingHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")


class PatchManager:
    """Manages patch version information"""

    def __init__(self):
        self.versions: List[str] = []
        self.cache_file = 'data/patch_versions.json'

    def fetch_versions(self, force_refresh: bool = False) -> List[str]:
        """
        Fetch available patch versions from Data Dragon

        Args:
            force_refresh: Force refresh even if cache exists

        Returns:
            List of patch versions (e.g., ['14.10.1', '14.9.1', ...])
        """
        # Try to load from cache
        if not force_refresh and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.versions = data['versions']
                    logger.debug(f"Loaded {len(self.versions)} patch versions from cache")
                    return self.versions
            except Exception as e:
                logger.warning(f"Failed to load patch cache: {e}")

        # Fetch from API
        try:
            logger.info("Fetching patch versions from Data Dragon...")
            response = requests.get(config.DDRAGON_VERSIONS_URL, timeout=10)
            response.raise_for_status()
            self.versions = response.json()

            # Cache the result
            os.makedirs('data', exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump({'versions': self.versions, 'fetched_at': datetime.now().isoformat()}, f)

            logger.info(f"Fetched {len(self.versions)} patch versions")
            return self.versions

        except Exception as e:
            logger.error(f"Failed to fetch patch versions: {e}")
            raise

    def get_current_patch(self) -> str:
        """
        Get the current patch version

        Returns:
            Current patch (e.g., '14.10')
        """
        if not self.versions:
            self.fetch_versions()

        # Return first version, truncated to major.minor
        current = self.versions[0]
        return '.'.join(current.split('.')[:2])

    def get_last_n_patches(self, n: int = 3) -> List[str]:
        """
        Get the last N patch versions

        Args:
            n: Number of patches to return

        Returns:
            List of patch versions (e.g., ['14.10', '14.9', '14.8'])
        """
        if not self.versions:
            self.fetch_versions()

        # Get unique major.minor versions
        patches = []
        seen = set()

        for version in self.versions:
            patch = '.'.join(version.split('.')[:2])
            if patch not in seen:
                patches.append(patch)
                seen.add(patch)

            if len(patches) >= n:
                break

        return patches

    def get_season_patches(self, season: int) -> List[str]:
        """
        Get all patches for a given season (major version number).

        Args:
            season: Season/major version number (e.g., 16 for S16)

        Returns:
            List of patch versions (e.g., ['16.1', '16.2', '16.3', '16.4'])
        """
        if not self.versions:
            self.fetch_versions()

        patches = []
        seen = set()
        prefix = f"{season}."

        for version in self.versions:
            if version.startswith(prefix):
                patch = '.'.join(version.split('.')[:2])
                if patch not in seen:
                    patches.append(patch)
                    seen.add(patch)

        # Return in ascending order (oldest first)
        patches.sort(key=lambda p: int(p.split('.')[1]))
        return patches

    def match_patch_filter(self, game_version: str, patches: List[str]) -> bool:
        """
        Check if a game version matches any of the specified patches

        Args:
            game_version: Full game version string (e.g., '14.10.123.456')
            patches: List of patches to match (e.g., ['14.10', '14.9'])

        Returns:
            True if game version matches any patch
        """
        # Extract major.minor from game version
        try:
            game_patch = '.'.join(game_version.split('.')[:2])
            return game_patch in patches
        except Exception:
            return False


class ChampionMapper:
    """Manages champion ID to name mapping"""

    def __init__(self):
        self.id_to_name: Dict[int, str] = {}
        self.name_to_id: Dict[str, int] = {}
        self.cache_file = 'data/champion_mapping.json'

    def fetch_champions(self, force_refresh: bool = False) -> None:
        """
        Fetch champion data from Data Dragon

        Args:
            force_refresh: Force refresh even if cache exists
        """
        # Try to load from cache
        if not force_refresh and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.id_to_name = {int(k): v for k, v in data['id_to_name'].items()}
                    self.name_to_id = {k: int(v) for k, v in data['name_to_id'].items()}
                    logger.debug(f"Loaded {len(self.id_to_name)} champions from cache")
                    return
            except Exception as e:
                logger.warning(f"Failed to load champion cache: {e}")

        # Fetch from API
        try:
            # Get current version first
            patch_manager = PatchManager()
            version = patch_manager.fetch_versions()[0]

            logger.info("Fetching champion data from Data Dragon...")
            url = config.DDRAGON_CHAMPION_URL.format(version=version)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Build mappings
            self.id_to_name = {}
            self.name_to_id = {}

            for champ_name, champ_data in data['data'].items():
                champ_id = int(champ_data['key'])
                self.id_to_name[champ_id] = champ_name
                self.name_to_id[champ_name] = champ_id

            # Cache the result
            os.makedirs('data', exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'id_to_name': {str(k): v for k, v in self.id_to_name.items()},
                    'name_to_id': {k: str(v) for k, v in self.name_to_id.items()},
                    'fetched_at': datetime.now().isoformat()
                }, f)

            logger.info(f"Fetched {len(self.id_to_name)} champions")

        except Exception as e:
            logger.error(f"Failed to fetch champion data: {e}")
            raise

    def get_name(self, champion_id: int) -> Optional[str]:
        """
        Get champion name from ID

        Args:
            champion_id: Champion ID

        Returns:
            Champion name or None if not found
        """
        if not self.id_to_name:
            self.fetch_champions()

        return self.id_to_name.get(champion_id)

    def get_id(self, champion_name: str) -> Optional[int]:
        """
        Get champion ID from name

        Args:
            champion_name: Champion name

        Returns:
            Champion ID or None if not found
        """
        if not self.name_to_id:
            self.fetch_champions()

        return self.name_to_id.get(champion_name)


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., '2h 30m 15s')
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return ' '.join(parts)


def format_number(num: int) -> str:
    """
    Format large numbers with commas

    Args:
        num: Number to format

    Returns:
        Formatted string (e.g., '1,000,000')
    """
    return f"{num:,}"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Value to return if denominator is zero

    Returns:
        Result of division or default
    """
    return numerator / denominator if denominator != 0 else default


def calculate_win_rate(wins: int, total: int) -> float:
    """
    Calculate win rate percentage

    Args:
        wins: Number of wins
        total: Total number of games

    Returns:
        Win rate as percentage (0-100)
    """
    return safe_divide(wins, total, 0.0) * 100


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a percentage value

    Args:
        value: Percentage value (0-100)
        decimals: Number of decimal places

    Returns:
        Formatted string (e.g., '47.75%')
    """
    return f"{value:.{decimals}f}%"


def validate_region(region: str) -> bool:
    """
    Validate region code

    Args:
        region: Region code

    Returns:
        True if valid
    """
    return region in config.REGIONS


def get_all_regions() -> List[str]:
    """
    Get list of all valid region codes

    Returns:
        List of region codes
    """
    return list(config.REGIONS.keys())


def create_output_dirs() -> None:
    """Create output directories if they don't exist"""
    dirs = [
        'data',
        'output',
        'output/charts',
        'output/csv',
        'output/analysis'
    ]

    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {dir_path}")


# Global instances for reuse
patch_manager = PatchManager()
champion_mapper = ChampionMapper()
