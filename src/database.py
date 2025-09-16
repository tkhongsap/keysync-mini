"""Database schema and management for KeySync Mini."""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import json

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for state persistence."""

    def __init__(self, db_path: str = "data/keysync.db"):
        """Initialize database connection and schema."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()

    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

    def _init_schema(self):
        """Initialize database schema."""
        with self.conn:
            # Reconciliation runs table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS reconciliation_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    run_mode TEXT NOT NULL CHECK(run_mode IN ('full', 'incremental')),
                    execution_mode TEXT NOT NULL CHECK(execution_mode IN ('normal', 'dry-run', 'auto-approve')),
                    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
                    config_snapshot TEXT,
                    stats_json TEXT,
                    error_message TEXT,
                    checkpoint_data TEXT,
                    completed_at TIMESTAMP
                )
            """)

            # Master key registry table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS master_key_registry (
                    master_key_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    master_key TEXT NOT NULL UNIQUE,
                    source_system TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('proposed', 'active', 'deprecated')),
                    provisioning_strategy TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    activated_at TIMESTAMP,
                    deprecated_at TIMESTAMP,
                    run_id INTEGER REFERENCES reconciliation_runs(run_id)
                )
            """)

            # Key tracking table for temporal aspects
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS key_tracking (
                    tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_name TEXT NOT NULL,
                    key_value TEXT NOT NULL,
                    normalized_key TEXT NOT NULL,
                    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    run_id INTEGER REFERENCES reconciliation_runs(run_id),
                    UNIQUE(system_name, normalized_key)
                )
            """)

            # Audit log table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    run_id INTEGER REFERENCES reconciliation_runs(run_id),
                    event_type TEXT NOT NULL,
                    event_details TEXT,
                    system_name TEXT,
                    key_value TEXT,
                    action_taken TEXT,
                    result TEXT
                )
            """)

            # Create indexes for performance
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_timestamp
                ON reconciliation_runs(run_timestamp DESC)
            """)

            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_master_key_status
                ON master_key_registry(status, created_at DESC)
            """)

            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_key_tracking_lookup
                ON key_tracking(system_name, normalized_key)
            """)

            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_run
                ON audit_log(run_id, timestamp DESC)
            """)

    def start_run(self, run_mode: str, execution_mode: str, config: Dict[str, Any]) -> int:
        """Start a new reconciliation run."""
        cursor = self.conn.execute("""
            INSERT INTO reconciliation_runs
            (run_mode, execution_mode, status, config_snapshot)
            VALUES (?, ?, 'running', ?)
        """, (run_mode, execution_mode, json.dumps(config)))
        self.conn.commit()
        return cursor.lastrowid

    def complete_run(self, run_id: int, stats: Dict[str, Any], error: Optional[str] = None):
        """Mark a run as completed or failed."""
        status = 'failed' if error else 'completed'
        # Convert sets to lists for JSON serialization
        serializable_stats = self._make_json_serializable(stats)
        self.conn.execute("""
            UPDATE reconciliation_runs
            SET status = ?, stats_json = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
            WHERE run_id = ?
        """, (status, json.dumps(serializable_stats), error, run_id))
        self.conn.commit()

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert non-serializable objects (like sets) to JSON-serializable format."""
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        return obj

    def save_checkpoint(self, run_id: int, checkpoint_data: Dict[str, Any]):
        """Save checkpoint data for recovery."""
        # Convert sets to lists for JSON serialization
        serializable_data = self._make_json_serializable(checkpoint_data)
        self.conn.execute("""
            UPDATE reconciliation_runs
            SET checkpoint_data = ?
            WHERE run_id = ?
        """, (json.dumps(serializable_data), run_id))
        self.conn.commit()

    def get_last_successful_run(self) -> Optional[Dict[str, Any]]:
        """Get the last successful run for incremental mode."""
        cursor = self.conn.execute("""
            SELECT * FROM reconciliation_runs
            WHERE status = 'completed'
            ORDER BY run_timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None

    def propose_master_key(self, run_id: int, master_key: str, source_system: str,
                          source_key: str, strategy: str) -> int:
        """Propose a new master key."""
        cursor = self.conn.execute("""
            INSERT INTO master_key_registry
            (master_key, source_system, source_key, status, provisioning_strategy, run_id)
            VALUES (?, ?, ?, 'proposed', ?, ?)
        """, (master_key, source_system, source_key, strategy, run_id))
        self.conn.commit()
        return cursor.lastrowid

    def activate_master_keys(self, run_id: int):
        """Activate all proposed master keys from a run."""
        self.conn.execute("""
            UPDATE master_key_registry
            SET status = 'active', activated_at = CURRENT_TIMESTAMP
            WHERE run_id = ? AND status = 'proposed'
        """, (run_id,))
        self.conn.commit()

    def track_key(self, run_id: int, system_name: str, key_value: str, normalized_key: str):
        """Track a key occurrence for temporal analysis."""
        self.conn.execute("""
            INSERT INTO key_tracking (system_name, key_value, normalized_key, run_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(system_name, normalized_key)
            DO UPDATE SET last_seen_at = CURRENT_TIMESTAMP, run_id = ?
        """, (system_name, key_value, normalized_key, run_id, run_id))

    def log_event(self, run_id: int, event_type: str, event_details: str,
                  system_name: Optional[str] = None, key_value: Optional[str] = None,
                  action_taken: Optional[str] = None, result: Optional[str] = None):
        """Log an audit event."""
        self.conn.execute("""
            INSERT INTO audit_log
            (run_id, event_type, event_details, system_name, key_value, action_taken, result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_id, event_type, event_details, system_name, key_value, action_taken, result))
        self.conn.commit()

    def get_master_keys(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get master keys by status."""
        query = "SELECT * FROM master_key_registry"
        params = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at DESC"

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()