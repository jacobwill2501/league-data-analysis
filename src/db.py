"""
Database schema and helpers for Champion Mastery Analysis
"""
import sqlite3
import logging
import time
import functools
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import json
from tqdm import tqdm

import config

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
INITIAL_BACKOFF = 1  # seconds


def _retry_on_locked(func):
    """Decorator that retries a function on SQLite 'locked' or 'busy' errors
    with exponential backoff."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if ('locked' in msg or 'busy' in msg) and attempt < MAX_RETRIES:
                    wait = INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning(f"Database locked (attempt {attempt + 1}/{MAX_RETRIES}), "
                                   f"retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise
    return wrapper


class Database:
    """SQLite database manager"""

    def __init__(self, db_path: str = config.DB_PATH):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._connection = None
        self._analysis_conn = None

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Uses WAL mode and a longer timeout to handle concurrent access
        from multiple threads/regions.

        Yields:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path, timeout=60)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            self._commit_with_retry(conn)
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    @_retry_on_locked
    def _commit_with_retry(conn):
        """Commit with retry logic for lock contention."""
        conn.commit()

    def init_schema(self):
        """Create all database tables if they don't exist"""
        logger.info(f"Initializing database schema at {self.db_path}")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Table: players
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    puuid TEXT PRIMARY KEY,
                    summoner_id TEXT NOT NULL DEFAULT '',
                    region TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    rank TEXT,
                    league_points INTEGER,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_region ON players(region)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_tier ON players(tier)")

            # Table: match_ids
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_ids (
                    match_id TEXT PRIMARY KEY,
                    region TEXT NOT NULL,
                    collected_from_puuid TEXT,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_ids_region ON match_ids(region)")

            # Table: match_participants
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_participants (
                    match_id TEXT NOT NULL,
                    puuid TEXT NOT NULL,
                    champion_id INTEGER NOT NULL,
                    champion_name TEXT NOT NULL,
                    team_id INTEGER NOT NULL,
                    win BOOLEAN NOT NULL,
                    lane TEXT,
                    role TEXT,
                    individual_position TEXT,
                    game_duration INTEGER NOT NULL,
                    game_version TEXT NOT NULL,
                    queue_id INTEGER NOT NULL,
                    game_creation BIGINT NOT NULL,
                    PRIMARY KEY (match_id, puuid)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mp_champion ON match_participants(champion_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mp_puuid ON match_participants(puuid)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mp_game_version ON match_participants(game_version)")

            # Table: champion_mastery
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS champion_mastery (
                    puuid TEXT NOT NULL,
                    champion_id INTEGER NOT NULL,
                    mastery_points INTEGER NOT NULL,
                    mastery_level INTEGER,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (puuid, champion_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cm_champion ON champion_mastery(champion_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mp_puuid_champion ON match_participants(puuid, champion_id)")

            # Table: collection_progress
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_progress (
                    task_name TEXT NOT NULL,
                    region TEXT NOT NULL,
                    key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    PRIMARY KEY (task_name, region, key)
                )
            """)

            conn.commit()
            logger.info("Database schema initialized successfully")

    # Player operations
    def insert_player(self, puuid: str, summoner_id: str, region: str,
                     tier: str, rank: Optional[str], league_points: int):
        """Insert or replace a player record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO players
                (puuid, summoner_id, region, tier, rank, league_points)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (puuid, summoner_id, region, tier, rank, league_points))

    def get_players_by_region(self, region: str) -> List[sqlite3.Row]:
        """Get all players for a specific region"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM players WHERE region = ?", (region,))
            return cursor.fetchall()

    def get_all_players(self) -> List[sqlite3.Row]:
        """Get all players"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM players")
            return cursor.fetchall()

    # Match operations
    def insert_match_id(self, match_id: str, region: str, puuid: Optional[str] = None):
        """Insert a match ID if it doesn't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO match_ids (match_id, region, collected_from_puuid)
                VALUES (?, ?, ?)
            """, (match_id, region, puuid))
            return cursor.rowcount > 0  # True if inserted, False if already existed

    def match_exists(self, match_id: str) -> bool:
        """Check if a match ID already exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM match_ids WHERE match_id = ?", (match_id,))
            return cursor.fetchone() is not None

    def insert_match_participant(self, match_id: str, puuid: str, champion_id: int,
                                champion_name: str, team_id: int, win: bool,
                                lane: Optional[str], role: Optional[str],
                                individual_position: Optional[str], game_duration: int,
                                game_version: str, queue_id: int, game_creation: int):
        """Insert a match participant record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO match_participants
                (match_id, puuid, champion_id, champion_name, team_id, win,
                 lane, role, individual_position, game_duration, game_version,
                 queue_id, game_creation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (match_id, puuid, champion_id, champion_name, team_id, win,
                  lane, role, individual_position, game_duration, game_version,
                  queue_id, game_creation))

    def get_match_count(self, region: Optional[str] = None) -> int:
        """Get total number of unique matches"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if region:
                cursor.execute("SELECT COUNT(*) FROM match_ids WHERE region = ?", (region,))
            else:
                cursor.execute("SELECT COUNT(*) FROM match_ids")
            return cursor.fetchone()[0]

    # Mastery operations
    def insert_mastery(self, puuid: str, champion_id: int, mastery_points: int,
                      mastery_level: Optional[int] = None):
        """Insert or replace mastery data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO champion_mastery
                (puuid, champion_id, mastery_points, mastery_level)
                VALUES (?, ?, ?, ?)
            """, (puuid, champion_id, mastery_points, mastery_level))

    def mastery_exists(self, puuid: str, champion_id: int) -> bool:
        """Check if mastery data exists for a player-champion pair"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM champion_mastery
                WHERE puuid = ? AND champion_id = ?
            """, (puuid, champion_id))
            return cursor.fetchone() is not None

    def get_unique_player_champion_pairs(self, region: Optional[str] = None) -> List[tuple]:
        """
        Get unique (puuid, champion_id) pairs from match_participants
        that don't have mastery data yet
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if region:
                cursor.execute("""
                    SELECT DISTINCT mp.puuid, mp.champion_id
                    FROM match_participants mp
                    JOIN players p ON mp.puuid = p.puuid
                    LEFT JOIN champion_mastery cm
                        ON mp.puuid = cm.puuid AND mp.champion_id = cm.champion_id
                    WHERE p.region = ? AND cm.puuid IS NULL
                """, (region,))
            else:
                cursor.execute("""
                    SELECT DISTINCT mp.puuid, mp.champion_id
                    FROM match_participants mp
                    LEFT JOIN champion_mastery cm
                        ON mp.puuid = cm.puuid AND mp.champion_id = cm.champion_id
                    WHERE cm.puuid IS NULL
                """)

            return cursor.fetchall()

    # Progress tracking operations
    def update_progress(self, task_name: str, region: str, key: str,
                       status: str, metadata: Optional[Dict] = None):
        """Update collection progress"""
        metadata_json = json.dumps(metadata) if metadata else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO collection_progress
                (task_name, region, key, status, last_updated, metadata)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (task_name, region, key, status, metadata_json))

    def get_progress(self, task_name: str, region: str, key: str) -> Optional[sqlite3.Row]:
        """Get progress for a specific task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM collection_progress
                WHERE task_name = ? AND region = ? AND key = ?
            """, (task_name, region, key))
            return cursor.fetchone()

    def get_all_progress(self, task_name: str, status: Optional[str] = None) -> List[sqlite3.Row]:
        """Get all progress entries for a task, optionally filtered by status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("""
                    SELECT * FROM collection_progress
                    WHERE task_name = ? AND status = ?
                """, (task_name, status))
            else:
                cursor.execute("""
                    SELECT * FROM collection_progress
                    WHERE task_name = ?
                """, (task_name,))
            return cursor.fetchall()

    # Analysis helper methods
    def get_filtered_matches(self, elo_filter: str, patch_filter: Optional[List[str]] = None) -> List[str]:
        """
        Get match IDs that match the elo and patch filters

        Args:
            elo_filter: Name of elo filter ('emerald_plus', 'diamond_plus', 'diamond2_plus')
            patch_filter: List of patch versions to include (e.g., ['14.10', '14.11'])

        Returns:
            List of match IDs
        """
        filter_config = config.ELO_FILTERS.get(elo_filter)
        if not filter_config:
            raise ValueError(f"Unknown elo filter: {elo_filter}")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build the WHERE clause for tier filtering
            tiers = filter_config['tiers']
            tier_placeholders = ','.join('?' * len(tiers))

            # Special handling for diamond2_plus
            if elo_filter == 'diamond2_plus':
                query = f"""
                    SELECT DISTINCT mp.match_id
                    FROM match_participants mp
                    JOIN players p ON mp.puuid = p.puuid
                    WHERE (
                        (p.tier = 'DIAMOND' AND p.rank IN ('II', 'I'))
                        OR p.tier IN ('MASTER', 'GRANDMASTER', 'CHALLENGER')
                    )
                """
                params = []
            else:
                query = f"""
                    SELECT DISTINCT mp.match_id
                    FROM match_participants mp
                    JOIN players p ON mp.puuid = p.puuid
                    WHERE p.tier IN ({tier_placeholders})
                """
                params = tiers

            # Add patch filter if provided
            if patch_filter:
                patch_conditions = ' OR '.join(['mp.game_version LIKE ?' for _ in patch_filter])
                query += f" AND ({patch_conditions})"
                params.extend([f"{patch}.%" for patch in patch_filter])

            cursor.execute(query, params)
            return [row[0] for row in cursor.fetchall()]

    # Batch insert helpers
    def insert_players_batch(self, players: List[Dict]):
        """Insert multiple players in a single transaction"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO players
                (puuid, summoner_id, region, tier, rank, league_points)
                VALUES (:puuid, :summoner_id, :region, :tier, :rank, :league_points)
            """, players)

    def insert_match_participants_batch(self, participants: List[Dict]):
        """Insert multiple match participants in a single transaction"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO match_participants
                (match_id, puuid, champion_id, champion_name, team_id, win,
                 lane, role, individual_position, game_duration, game_version,
                 queue_id, game_creation)
                VALUES (:match_id, :puuid, :champion_id, :champion_name, :team_id, :win,
                        :lane, :role, :individual_position, :game_duration, :game_version,
                        :queue_id, :game_creation)
            """, participants)

    # Count helpers
    def count_players(self, region: Optional[str] = None) -> int:
        """Count players, optionally filtered by region"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if region:
                cursor.execute("SELECT COUNT(*) FROM players WHERE region = ?", (region,))
            else:
                cursor.execute("SELECT COUNT(*) FROM players")
            return cursor.fetchone()[0]

    def count_matches(self, region: Optional[str] = None) -> int:
        """Count matches, optionally filtered by region"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if region:
                cursor.execute("SELECT COUNT(*) FROM match_ids WHERE region = ?", (region,))
            else:
                cursor.execute("SELECT COUNT(*) FROM match_ids")
            return cursor.fetchone()[0]

    def count_mastery(self) -> int:
        """Count total mastery records"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM champion_mastery")
            return cursor.fetchone()[0]

    def get_player_by_puuid(self, puuid: str) -> Optional[sqlite3.Row]:
        """Check if a player with the given PUUID already exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM players WHERE puuid = ?", (puuid,))
            return cursor.fetchone()

    def get_player_by_summoner_id(self, summoner_id: str, region: str) -> Optional[sqlite3.Row]:
        """Get a player by summoner ID and region (legacy)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM players WHERE summoner_id = ? AND region = ?",
                (summoner_id, region)
            )
            return cursor.fetchone()

    def get_player_puuids(self, region: Optional[str] = None) -> List[str]:
        """Get all player PUUIDs, optionally filtered by region"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if region:
                cursor.execute("SELECT puuid FROM players WHERE region = ?", (region,))
            else:
                cursor.execute("SELECT puuid FROM players")
            return [row[0] for row in cursor.fetchall()]

    def get_puuids_by_filter(self, elo_filter: str) -> set:
        """Get PUUIDs matching an elo filter"""
        filter_config = config.ELO_FILTERS.get(elo_filter)
        if not filter_config:
            raise ValueError(f"Unknown elo filter: {elo_filter}")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            if elo_filter == 'diamond2_plus':
                cursor.execute("""
                    SELECT puuid FROM players
                    WHERE (tier = 'DIAMOND' AND rank IN ('II', 'I'))
                       OR tier IN ('MASTER', 'GRANDMASTER', 'CHALLENGER')
                """)
            else:
                tiers = filter_config['tiers']
                placeholders = ','.join('?' * len(tiers))
                cursor.execute(f"SELECT puuid FROM players WHERE tier IN ({placeholders})", tiers)

            return {row[0] for row in cursor.fetchall()}

    def get_all_mastery_dict(self) -> Dict[tuple, Dict]:
        """Get all mastery data as a dict keyed by (puuid, champion_id)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT puuid, champion_id, mastery_points, mastery_level FROM champion_mastery")
            result = {}
            for row in cursor.fetchall():
                result[(row[0], row[1])] = {
                    'mastery_points': row[2],
                    'mastery_level': row[3]
                }
            return result

    def get_all_participants(self, match_ids: Optional[List[str]] = None) -> List[Dict]:
        """Get all match participants, optionally filtered by match IDs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if match_ids:
                # Process in chunks to avoid SQLite variable limit
                all_rows = []
                chunk_size = 500
                for i in range(0, len(match_ids), chunk_size):
                    chunk = match_ids[i:i + chunk_size]
                    placeholders = ','.join('?' * len(chunk))
                    cursor.execute(f"""
                        SELECT match_id, puuid, champion_id, champion_name, team_id,
                               win, lane, role, individual_position, game_duration,
                               game_version, queue_id, game_creation
                        FROM match_participants
                        WHERE match_id IN ({placeholders})
                    """, chunk)
                    all_rows.extend(cursor.fetchall())
            else:
                cursor.execute("""
                    SELECT match_id, puuid, champion_id, champion_name, team_id,
                           win, lane, role, individual_position, game_duration,
                           game_version, queue_id, game_creation
                    FROM match_participants
                """)
                all_rows = cursor.fetchall()

            columns = ['match_id', 'puuid', 'champion_id', 'champion_name', 'team_id',
                       'win', 'lane', 'role', 'individual_position', 'game_duration',
                       'game_version', 'queue_id', 'game_creation']
            return [dict(zip(columns, row)) for row in all_rows]

    def insert_mastery_batch(self, records: List[Dict]):
        """Insert multiple mastery records in a single transaction.

        Args:
            records: List of dicts with keys: puuid, champion_id, mastery_points, mastery_level
        """
        if not records:
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO champion_mastery
                (puuid, champion_id, mastery_points, mastery_level)
                VALUES (:puuid, :champion_id, :mastery_points, :mastery_level)
            """, records)

    def get_pending_mastery_puuids(self, region: str) -> Dict[str, List[int]]:
        """
        Get pending mastery pairs grouped by PUUID for a region.

        Returns:
            Dict mapping puuid -> list of champion_ids that need mastery data
        """
        CHUNK = 10_000
        QUERY = """
            SELECT DISTINCT mp.puuid, mp.champion_id
            FROM match_participants mp
            JOIN match_ids mi ON mp.match_id = mi.match_id
            LEFT JOIN champion_mastery cm
                ON mp.puuid = cm.puuid AND mp.champion_id = cm.champion_id
            WHERE mi.region = ? AND cm.puuid IS NULL
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT COUNT(*) FROM ({QUERY})",
                (region,)
            )
            total = cursor.fetchone()[0]

            result: Dict[str, List[int]] = {}
            cursor.execute(QUERY, (region,))
            with tqdm(total=total, desc=f"Loading pairs ({region})", unit="pair", leave=False) as pbar:
                while True:
                    rows = cursor.fetchmany(CHUNK)
                    if not rows:
                        break
                    for row in rows:
                        result.setdefault(row[0], []).append(row[1])
                    pbar.update(len(rows))
        return result

    def get_pending_mastery_pairs(self, region: Optional[str] = None) -> List[tuple]:
        """
        Get unique (puuid, champion_id) pairs that need mastery data.
        Returns list of (puuid, champion_id) tuples.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if region:
                cursor.execute("""
                    SELECT DISTINCT mp.puuid, mp.champion_id
                    FROM match_participants mp
                    JOIN match_ids mi ON mp.match_id = mi.match_id
                    LEFT JOIN champion_mastery cm
                        ON mp.puuid = cm.puuid AND mp.champion_id = cm.champion_id
                    WHERE mi.region = ? AND cm.puuid IS NULL
                """, (region,))
            else:
                cursor.execute("""
                    SELECT DISTINCT mp.puuid, mp.champion_id
                    FROM match_participants mp
                    LEFT JOIN champion_mastery cm
                        ON mp.puuid = cm.puuid AND mp.champion_id = cm.champion_id
                    WHERE cm.puuid IS NULL
                """)

            return [(row[0], row[1]) for row in cursor.fetchall()]

    def delete_players_by_tier(self, region: str, tier: str, rank: str = None) -> int:
        """Delete players by region + tier + rank. Returns count of deleted rows."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if rank:
                cursor.execute(
                    "DELETE FROM players WHERE region = ? AND tier = ? AND rank = ?",
                    (region, tier, rank)
                )
            else:
                cursor.execute(
                    "DELETE FROM players WHERE region = ? AND tier = ?",
                    (region, tier)
                )
            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted} players for {region} {tier} {rank or ''}")
            return deleted

    def delete_progress(self, task_name: str, region: str, key: str) -> bool:
        """Delete a specific progress entry. Returns True if a row was deleted."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM collection_progress WHERE task_name = ? AND region = ? AND key = ?",
                (task_name, region, key)
            )
            return cursor.rowcount > 0

    def delete_progress_for_puuids(self, task_name: str, region: str, puuids: List[str]) -> int:
        """Delete progress entries for a list of PUUIDs. Returns count of deleted rows."""
        if not puuids:
            return 0
        deleted = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            chunk_size = 500
            for i in range(0, len(puuids), chunk_size):
                chunk = puuids[i:i + chunk_size]
                placeholders = ','.join('?' * len(chunk))
                cursor.execute(
                    f"DELETE FROM collection_progress WHERE task_name = ? AND region = ? AND key IN ({placeholders})",
                    [task_name, region] + chunk
                )
                deleted += cursor.rowcount
        return deleted

    def get_player_puuids_by_tier(self, region: str, tier: str, rank: str = None) -> List[str]:
        """Get PUUIDs for players matching region + tier + rank."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if rank:
                cursor.execute(
                    "SELECT puuid FROM players WHERE region = ? AND tier = ? AND rank = ?",
                    (region, tier, rank)
                )
            else:
                cursor.execute(
                    "SELECT puuid FROM players WHERE region = ? AND tier = ?",
                    (region, tier)
                )
            return [row[0] for row in cursor.fetchall()]

    def get_player_puuids_by_tiers(self, region: str, tiers: List[str]) -> List[str]:
        """Get player PUUIDs for specific tiers in a region"""
        placeholders = ','.join('?' for _ in tiers)
        query = f"SELECT puuid FROM players WHERE region = ? AND tier IN ({placeholders})"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [region] + tiers)
            return [row[0] for row in cursor.fetchall()]

    # ---- SQL-aggregation methods (OOM-safe analysis) ----

    def begin_analysis_session(self, elo_filter: str, patch_filter=None):
        """Materialize filtered match IDs and pre-joined participant data for the session.

        Creates two temp tables:
          _fm  — filtered match IDs (WITHOUT ROWID, PK index for O(log n) join)
          _mp  — pre-joined (match_participants JOIN _fm JOIN champion_mastery) with
                 only the columns needed for analysis, indexed by champion_name.

        All subsequent aggregation queries run against _mp (a single small table),
        avoiding repeated 3-way JOINs that cause SQLite to choose bad query plans
        when champion_name is in the GROUP BY.
        """
        if self._analysis_conn is not None:
            self.end_analysis_session()
        match_ids = self.get_filtered_matches(elo_filter, patch_filter)
        conn = sqlite3.connect(self.db_path, timeout=300)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=300000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size = -524288")   # 512 MB page cache
        conn.execute("PRAGMA mmap_size = 4294967296") # 4 GB memory-mapped I/O
        conn.row_factory = sqlite3.Row

        # Step 1: filtered match IDs
        conn.execute(
            "CREATE TEMP TABLE _fm (match_id TEXT NOT NULL PRIMARY KEY) WITHOUT ROWID"
        )
        conn.executemany("INSERT INTO _fm VALUES (?)", [(m,) for m in match_ids])
        conn.commit()
        logger.info(f"  Materialized {len(match_ids):,} filtered match IDs into _fm")

        # Step 2: pre-join all needed columns once; index by champion_name so
        # subsequent GROUP BY champion_name queries scan in order (no sort needed).
        logger.info("  Materializing pre-joined participant data into _mp...")
        conn.execute("""
            CREATE TEMP TABLE _mp AS
            SELECT
                mp.champion_name,
                mp.individual_position,
                CAST(mp.win AS INTEGER)                AS win,
                COALESCE(cm.mastery_points, 0)         AS mastery_points
            FROM match_participants mp
            JOIN _fm fm ON mp.match_id = fm.match_id
            JOIN champion_mastery cm
                ON mp.puuid = cm.puuid AND mp.champion_id = cm.champion_id
        """)
        conn.execute("CREATE INDEX _idx_mp_champ ON _mp(champion_name)")
        conn.commit()
        row_count = conn.execute("SELECT COUNT(*) FROM _mp").fetchone()[0]
        logger.info(f"  Materialized {row_count:,} rows into _mp")

        self._analysis_conn = conn

    def end_analysis_session(self):
        """Close the analysis session connection and drop the _fm TEMP TABLE."""
        if self._analysis_conn is not None:
            self._analysis_conn.close()
            self._analysis_conn = None

    def _build_filter_cte(self, elo_filter: str,
                          patch_filter: Optional[List[str]] = None) -> tuple:
        """Return (cte_sql, params) for the filtered_matches CTE."""
        filter_config = config.ELO_FILTERS.get(elo_filter)
        if not filter_config:
            raise ValueError(f"Unknown elo filter: {elo_filter}")

        params: list = []

        if elo_filter == 'diamond2_plus':
            tier_clause = (
                "(p.tier = 'DIAMOND' AND p.rank IN ('II', 'I'))"
                " OR p.tier IN ('MASTER', 'GRANDMASTER', 'CHALLENGER')"
            )
        else:
            tiers = filter_config['tiers']
            placeholders = ','.join('?' * len(tiers))
            tier_clause = f"p.tier IN ({placeholders})"
            params.extend(tiers)

        if patch_filter:
            patch_conds = ' OR '.join(
                ['mp.game_version LIKE ?' for _ in patch_filter]
            )
            patch_clause = f"AND ({patch_conds})"
            params.extend([f"{p}.%" for p in patch_filter])
        else:
            patch_clause = ""

        cte = f"""WITH filtered_matches AS (
            SELECT DISTINCT mp.match_id
            FROM match_participants mp
            JOIN players p ON mp.puuid = p.puuid
            WHERE ({tier_clause})
            {patch_clause}
        )"""
        return cte, params

    def get_summary_stats(self, elo_filter: str,
                          patch_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """Return aggregated summary stats for the given filter (no full load)."""
        conn = self._analysis_conn
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(DISTINCT mp.match_id),
                COUNT(*),
                COUNT(DISTINCT mp.puuid),
                COUNT(DISTINCT mp.champion_name),
                SUM(CASE WHEN mp.win THEN 1 ELSE 0 END),
                SUM(CASE WHEN cm.mastery_points IS NOT NULL THEN 1 ELSE 0 END)
            FROM match_participants mp
            JOIN _fm fm ON mp.match_id = fm.match_id
            LEFT JOIN champion_mastery cm
                ON mp.puuid = cm.puuid AND mp.champion_id = cm.champion_id
        """)
        row = cur.fetchone()
        total_matches         = row[0] or 0
        total_participants    = row[1] or 0
        total_unique_players  = row[2] or 0
        total_unique_champions = row[3] or 0
        total_wins            = row[4] or 0
        participants_with_mastery = row[5] or 0

        cur.execute("""
            SELECT
                CASE
                    WHEN match_id LIKE 'NA%'  THEN 'NA'
                    WHEN match_id LIKE 'EUW%' THEN 'EUW'
                    WHEN match_id LIKE 'EU%'  THEN 'EUW'
                    WHEN match_id LIKE 'KR%'  THEN 'KR'
                    ELSE 'OTHER'
                END AS region,
                COUNT(*) AS cnt
            FROM _fm
            GROUP BY region
        """)
        region_balance = {r[0]: r[1] for r in cur.fetchall()}

        return {
            'total_matches': total_matches,
            'total_participants': total_participants,
            'total_unique_players': total_unique_players,
            'total_unique_champions': total_unique_champions,
            'total_wins': total_wins,
            'participants_with_mastery': participants_with_mastery,
            'region_balance': region_balance,
        }

    def get_mastery_points_list(self, elo_filter: str,
                                patch_filter: Optional[List[str]] = None) -> List[int]:
        """Return sorted mastery_points list for participants WITH mastery data."""
        cur = self._analysis_conn.cursor()
        cur.execute("SELECT mastery_points FROM _mp ORDER BY mastery_points")
        return [r[0] for r in cur.fetchall()]

    def get_mastery_distribution_extras(
            self, elo_filter: str,
            patch_filter: Optional[List[str]] = None) -> tuple:
        """Return (bucket_counts, lane_bucket_counts) dicts for mastery distribution."""
        bucket_case = """CASE
            WHEN mastery_points < 10000  THEN 'low'
            WHEN mastery_points < 100000 THEN 'medium'
            ELSE 'high'
        END"""

        cur = self._analysis_conn.cursor()

        cur.execute(f"""
            SELECT {bucket_case} AS bucket, COUNT(*) AS cnt
            FROM _mp
            GROUP BY bucket
        """)
        bucket_counts: Dict[str, int] = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute(f"""
            SELECT individual_position, {bucket_case} AS bucket, COUNT(*) AS cnt
            FROM _mp
            WHERE individual_position IS NOT NULL
            GROUP BY individual_position, bucket
        """)
        lane_bucket_counts: Dict[str, Dict[str, int]] = {}
        for r in cur.fetchall():
            lane_bucket_counts.setdefault(r[0], {})[r[1]] = r[2]

        return bucket_counts, lane_bucket_counts

    def get_winrate_by_bucket(self, elo_filter: str,
                              patch_filter: Optional[List[str]] = None) -> List[Dict]:
        """Return [{'bucket', 'wins', 'games'}] rows — one per mastery bucket."""
        cur = self._analysis_conn.cursor()
        cur.execute("""
            SELECT
                CASE
                    WHEN mastery_points < 10000  THEN 'low'
                    WHEN mastery_points < 100000 THEN 'medium'
                    ELSE 'high'
                END AS bucket,
                SUM(win) AS wins,
                COUNT(*) AS games
            FROM _mp
            GROUP BY bucket
        """)
        return [{'bucket': r[0], 'wins': r[1], 'games': r[2]}
                for r in cur.fetchall()]

    def get_winrate_curve_data(self, elo_filter: str,
                               patch_filter: Optional[List[str]] = None) -> List[Dict]:
        """Return [{'interval_index', 'wins', 'games'}] — one per mastery interval."""
        interval_case = """CASE
            WHEN mastery_points < 1000    THEN 0
            WHEN mastery_points < 2000    THEN 1
            WHEN mastery_points < 5000    THEN 2
            WHEN mastery_points < 10000   THEN 3
            WHEN mastery_points < 20000   THEN 4
            WHEN mastery_points < 50000   THEN 5
            WHEN mastery_points < 100000  THEN 6
            WHEN mastery_points < 200000  THEN 7
            WHEN mastery_points < 500000  THEN 8
            WHEN mastery_points < 1000000 THEN 9
            ELSE 10
        END"""
        cur = self._analysis_conn.cursor()
        cur.execute(f"""
            SELECT
                {interval_case} AS interval_idx,
                SUM(win) AS wins,
                COUNT(*) AS games
            FROM _mp
            GROUP BY interval_idx
        """)
        return [{'interval_index': r[0], 'wins': r[1], 'games': r[2]}
                for r in cur.fetchall()]

    def get_champion_stats_aggregated(
            self, elo_filter: str,
            patch_filter: Optional[List[str]] = None) -> tuple:
        """Return (bucket_rows, lane_rows) for champion stats with standard buckets."""
        bucket_case = """CASE
            WHEN mastery_points < 10000  THEN 'low'
            WHEN mastery_points < 100000 THEN 'medium'
            ELSE 'high'
        END"""
        cur = self._analysis_conn.cursor()
        cur.execute(f"""
            SELECT
                champion_name,
                {bucket_case} AS bucket,
                SUM(win) AS wins,
                COUNT(*) AS games
            FROM _mp
            GROUP BY champion_name, bucket
        """)
        bucket_rows = [
            {'champion_name': r[0], 'bucket': r[1], 'wins': r[2], 'games': r[3]}
            for r in cur.fetchall()
        ]

        cur.execute("""
            SELECT champion_name, individual_position, COUNT(*) AS cnt
            FROM _mp
            WHERE individual_position IS NOT NULL
            GROUP BY champion_name, individual_position
        """)
        lane_rows = [
            {'champion_name': r[0], 'lane': r[1], 'cnt': r[2]}
            for r in cur.fetchall()
        ]
        return bucket_rows, lane_rows

    def get_pabu_champion_stats_aggregated(
            self, elo_filter: str,
            patch_filter: Optional[List[str]] = None) -> tuple:
        """Return (bucket_rows, lane_rows) with Pabu bucket thresholds (30k / 100k)."""
        bucket_case = """CASE
            WHEN mastery_points < 30000  THEN 'low'
            WHEN mastery_points < 100000 THEN 'medium'
            ELSE 'high'
        END"""
        cur = self._analysis_conn.cursor()
        cur.execute(f"""
            SELECT
                champion_name,
                {bucket_case} AS bucket,
                SUM(win) AS wins,
                COUNT(*) AS games
            FROM _mp
            GROUP BY champion_name, bucket
        """)
        bucket_rows = [
            {'champion_name': r[0], 'bucket': r[1], 'wins': r[2], 'games': r[3]}
            for r in cur.fetchall()
        ]

        cur.execute("""
            SELECT champion_name, individual_position, COUNT(*) AS cnt
            FROM _mp
            WHERE individual_position IS NOT NULL
            GROUP BY champion_name, individual_position
        """)
        lane_rows = [
            {'champion_name': r[0], 'lane': r[1], 'cnt': r[2]}
            for r in cur.fetchall()
        ]
        return bucket_rows, lane_rows

    def get_mastery_curves_aggregated(
            self, elo_filter: str,
            patch_filter: Optional[List[str]] = None) -> tuple:
        """Return (interval_rows, lane_rows) for per-champion mastery curves."""
        interval_case = """CASE
            WHEN mastery_points < 1000    THEN 0
            WHEN mastery_points < 2000    THEN 1
            WHEN mastery_points < 5000    THEN 2
            WHEN mastery_points < 10000   THEN 3
            WHEN mastery_points < 20000   THEN 4
            WHEN mastery_points < 50000   THEN 5
            WHEN mastery_points < 100000  THEN 6
            WHEN mastery_points < 200000  THEN 7
            WHEN mastery_points < 500000  THEN 8
            WHEN mastery_points < 1000000 THEN 9
            ELSE 10
        END"""
        cur = self._analysis_conn.cursor()
        cur.execute(f"""
            SELECT
                champion_name,
                {interval_case} AS interval_idx,
                SUM(win) AS wins,
                COUNT(*) AS games
            FROM _mp
            GROUP BY champion_name, interval_idx
        """)
        interval_rows = [
            {'champion_name': r[0], 'interval_index': r[1],
             'wins': r[2], 'games': r[3]}
            for r in cur.fetchall()
        ]

        cur.execute("""
            SELECT champion_name, individual_position, COUNT(*) AS cnt
            FROM _mp
            WHERE individual_position IS NOT NULL
            GROUP BY champion_name, individual_position
        """)
        lane_rows = [
            {'champion_name': r[0], 'lane': r[1], 'cnt': r[2]}
            for r in cur.fetchall()
        ]
        return interval_rows, lane_rows

    def iter_bias_mastery_data(self, elo_filter: str,
                               patch_filter: Optional[List[str]] = None):
        """Generator yielding (champion_name, mastery_points, win, lane) rows.

        Streams data in chunks to avoid loading all rows into memory at once.
        Used exclusively by compute_bias_champion_stats for exact bucketing.
        """
        cur = self._analysis_conn.cursor()
        cur.execute("""
            SELECT champion_name, mastery_points, win, individual_position
            FROM _mp
        """)
        chunk = 10_000
        while True:
            rows = cur.fetchmany(chunk)
            if not rows:
                break
            yield from rows

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get summary statistics for verification"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total players
            cursor.execute("SELECT COUNT(*) FROM players")
            stats['total_players'] = cursor.fetchone()[0]

            # Players by region
            cursor.execute("""
                SELECT region, COUNT(*) as count
                FROM players
                GROUP BY region
            """)
            stats['players_by_region'] = {row[0]: row[1] for row in cursor.fetchall()}

            # Total matches
            cursor.execute("SELECT COUNT(*) FROM match_ids")
            stats['total_matches'] = cursor.fetchone()[0]

            # Matches by region
            cursor.execute("""
                SELECT region, COUNT(*) as count
                FROM match_ids
                GROUP BY region
            """)
            stats['matches_by_region'] = {row[0]: row[1] for row in cursor.fetchall()}

            # Total match participants
            cursor.execute("SELECT COUNT(*) FROM match_participants")
            stats['total_participants'] = cursor.fetchone()[0]

            # Total mastery records
            cursor.execute("SELECT COUNT(*) FROM champion_mastery")
            stats['total_mastery_records'] = cursor.fetchone()[0]

            # Unique champions
            cursor.execute("SELECT COUNT(DISTINCT champion_name) FROM match_participants")
            stats['unique_champions'] = cursor.fetchone()[0]

            # Mastery coverage
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT mp.puuid || '-' || mp.champion_id) as total_pairs,
                    COUNT(DISTINCT CASE WHEN cm.puuid IS NOT NULL
                                   THEN mp.puuid || '-' || mp.champion_id END) as covered_pairs
                FROM match_participants mp
                LEFT JOIN champion_mastery cm ON mp.puuid = cm.puuid AND mp.champion_id = cm.champion_id
            """)
            row = cursor.fetchone()
            total_pairs = row[0]
            covered_pairs = row[1]
            stats['mastery_coverage'] = (covered_pairs / total_pairs * 100) if total_pairs > 0 else 0

            return stats
