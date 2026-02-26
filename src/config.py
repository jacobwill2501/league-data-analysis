"""
Configuration for Champion Mastery Analysis
"""
import os
from typing import Dict, List

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# API Configuration
RIOT_API_KEY = os.getenv('RIOT_API_KEY', '')

# Region Configuration
REGIONS = {
    'NA': {
        'platform': 'na1',          # league-v4
        'routing': 'americas'       # match-v5
    },
    'EUW': {
        'platform': 'euw1',
        'routing': 'europe'
    },
    'KR': {
        'platform': 'kr',
        'routing': 'asia'
    }
}

# Elo Filter Configuration
ELO_FILTERS = {
    'emerald_plus': {
        'tiers': ['EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'],
        'description': 'Emerald, Diamond, Master, Grandmaster, Challenger'
    },
    'diamond_plus': {
        'tiers': ['DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'],
        'description': 'Diamond, Master, Grandmaster, Challenger'
    },
    'diamond2_plus': {
        'tiers': ['DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'],
        'divisions': ['II', 'I'],  # For Diamond only
        'description': 'Diamond II+, Master, Grandmaster, Challenger'
    }
}

# Mastery Bucket Configuration
MASTERY_BUCKETS = {
    'low': {
        'min': 0,
        'max': 10000,
        'label': 'Low (<10k)'
    },
    'medium': {
        'min': 10000,
        'max': 100000,
        'label': 'Medium (10k-100k)'
    },
    'high': {
        'min': 100000,
        'max': float('inf'),
        'label': 'High (100k+)'
    }
}

# Rate Limits - Production Key
PRODUCTION_RATE_LIMITS = {
    'league-v4': {
        'per_second': 10,
        'per_2min': 600
    },
    'match-v5': {
        'per_second': 20,
        'per_2min': 100
    },
    'champion-mastery-v4': {
        'per_second': 20,
        'per_2min': 100
    },
    'summoner-v4': {
        'per_second': 20,
        'per_2min': 100
    },
    'account-v1': {
        'per_second': 20,
        'per_2min': 100
    }
}

# Rate Limits - Development Key
DEV_RATE_LIMITS = {
    'league-v4': {
        'per_second': 20,
        'per_2min': 100
    },
    'match-v5': {
        'per_second': 20,
        'per_2min': 100
    },
    'champion-mastery-v4': {
        'per_second': 20,
        'per_2min': 100
    },
    'summoner-v4': {
        'per_second': 20,
        'per_2min': 100
    },
    'account-v1': {
        'per_second': 20,
        'per_2min': 100
    }
}

# Queue Configuration
RANKED_SOLO_QUEUE = 'RANKED_SOLO_5x5'
RANKED_SOLO_QUEUE_ID = 420

# Tiers and Divisions
TIERS = ['EMERALD', 'DIAMOND']
DIVISIONS = ['I', 'II', 'III', 'IV']
APEX_TIERS = ['MASTER', 'GRANDMASTER', 'CHALLENGER']  # No divisions

# Analysis Configuration
MINIMUM_SAMPLE_SIZE = 100  # Minimum games per bucket for valid stats
MINIMUM_GAME_DURATION = 300  # Skip remakes (< 5 minutes)

# Patch Configuration
PATCH_MODES = ['current', 'last3', 'season']

# Data Dragon URLs
DDRAGON_VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json'
DDRAGON_CHAMPION_URL = 'https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json'

# Database Configuration
DB_PATH = 'data/mastery_analysis.db'

# Logging Configuration
LOG_FORMAT = '[%(asctime)s] %(levelname)s %(name)s: %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Collection Target Presets (total matches across all regions)
MATCH_TARGET_PRESETS = {
    '500k': 500_000,
    '1m':  1_000_000,
}
DEFAULT_MATCH_TARGET = MATCH_TARGET_PRESETS['1m']
MATCHES_PER_REGION = DEFAULT_MATCH_TARGET // 3  # ~333k per region

# Tier group allocation for match collection (must sum to 1.0)
TIER_ALLOCATION = {
    'apex': 0.30,      # Challenger + Grandmaster + Master
    'diamond': 0.45,   # Diamond I-IV
    'emerald': 0.25,   # Emerald I-IV
}

# Chart Configuration
CHART_DPI = 150
CHART_FIGSIZE_LARGE = (12, 8)
CHART_FIGSIZE_MEDIUM = (10, 8)
MASTERY_DISPLAY_CAP = 250000  # Cap mastery display at 250k for readability

# Win Rate Intervals for Curve Analysis
WIN_RATE_INTERVALS = [
    (0, 1000),
    (1000, 2000),
    (2000, 5000),
    (5000, 10000),
    (10000, 20000),
    (20000, 50000),
    (50000, 100000),
    (100000, 200000),
    (200000, 500000),
    (500000, 1000000),
    (1000000, float('inf'))
]

# Lane Configuration
LANES = ['TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY']
LANE_DISPLAY_NAMES = {
    'TOP': 'Top',
    'JUNGLE': 'Jungle',
    'MIDDLE': 'Middle',
    'BOTTOM': 'ADC',
    'UTILITY': 'Support'
}


def get_rate_limits(use_dev_key: bool = False) -> Dict:
    """
    Get rate limits based on key type

    Args:
        use_dev_key: Whether to use dev key rate limits

    Returns:
        Dictionary of rate limits by endpoint group
    """
    return DEV_RATE_LIMITS if use_dev_key else PRODUCTION_RATE_LIMITS


PABU_MASTERY_BUCKETS = {
    'low': {
        'min': 0,
        'max': 30000,
        'label': 'Low (<30k)'
    },
    'medium': {
        'min': 30000,
        'max': 100000,
        'label': 'Medium (30k–100k)'
    },
    'high': {
        'min': 100000,
        'max': float('inf'),
        'label': 'High (100k+)'
    }
}


def get_pabu_mastery_bucket(mastery_points: int) -> str:
    """Determine Pabu mastery bucket (30k medium boundary) for a given point value"""
    if mastery_points < 30000:
        return 'low'
    if mastery_points < 100000:
        return 'medium'
    return 'high'


def get_mastery_bucket(mastery_points: int) -> str:
    """
    Determine which mastery bucket a value falls into

    Args:
        mastery_points: Champion mastery points

    Returns:
        Bucket name ('low', 'medium', or 'high')
    """
    if mastery_points < MASTERY_BUCKETS['low']['max']:
        return 'low'
    elif mastery_points < MASTERY_BUCKETS['medium']['max']:
        return 'medium'
    else:
        return 'high'


def validate_config() -> List[str]:
    """
    Validate configuration settings

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not RIOT_API_KEY:
        errors.append("RIOT_API_KEY environment variable not set")

    return errors
