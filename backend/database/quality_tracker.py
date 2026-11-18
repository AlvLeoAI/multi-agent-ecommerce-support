"""
QualityTracker Database & Telemetry Layer.
Tracks response time, token usage, step counts, delegated specialist agent,
and success/error rates using parameterized SQLite queries, connection hygiene,
and NaN-safe aggregates.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

_CANDIDATE_ROOT = Path(__file__).resolve().parent.parent.parent
if _CANDIDATE_ROOT == Path("/") or not os.access(_CANDIDATE_ROOT, os.W_OK):
    _DEFAULT_ROOT = Path(__file__).resolve().parent.parent
else:
    _DEFAULT_ROOT = _CANDIDATE_ROOT

DEFAULT_QUALITY_DB_PATH = os.getenv("QUALITY_DB_PATH", str(_DEFAULT_ROOT / "ecommerce_agent.db"))


class QualityTracker:
    """Track agent quality metrics in SQLite with parameterized queries and NaN-safe summaries."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = str(db_path) if db_path is not None else DEFAULT_QUALITY_DB_PATH
        self.setup_database()

    @contextlib.contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")
            yield conn
        finally:
            conn.close()

    def setup_database(self) -> None:
        """Create quality metrics table if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    response_time REAL NOT NULL,
                    tokens_used INTEGER,
                    steps_count INTEGER NOT NULL,
                    agent_used TEXT,
                    success BOOLEAN DEFAULT 1,
                    user_rating INTEGER,
                    error_occurred BOOLEAN DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def track_conversation(
        self,
        conversation_id: str,
        response_time: float,
        tokens_used: int | None,
        steps_count: int,
        agent_used: str,
        success: bool = True,
        error_occurred: bool = False,
    ) -> None:
        """Track a single conversation turn's quality metrics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            utc_timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO quality_metrics
                (conversation_id, response_time, tokens_used, steps_count,
                 agent_used, success, error_occurred, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    float(response_time),
                    tokens_used,
                    int(steps_count),
                    agent_used,
                    bool(success),
                    bool(error_occurred),
                    utc_timestamp,
                ),
            )
            conn.commit()

    def save_user_rating(self, conversation_id: str, rating: int) -> None:
        """Save user rating (1 for thumbs up, 0 for thumbs down)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE quality_metrics
                SET user_rating = ?
                WHERE id = (
                    SELECT id FROM quality_metrics
                    WHERE conversation_id = ?
                    ORDER BY timestamp DESC, id DESC
                    LIMIT 1
                )
                """,
                (int(rating), conversation_id),
            )
            conn.commit()

    def get_metrics_summary(self, days: int = 7) -> dict[str, Any]:
        """Get aggregated metrics for the last N days with parameterized SQL and NaN sanitization."""
        with self._get_connection() as conn:
            window_modifier = f"-{int(days)} days"
            query = """
                SELECT
                    COUNT(*) as total_conversations,
                    AVG(response_time) as avg_response_time,
                    MIN(response_time) as min_response_time,
                    MAX(response_time) as max_response_time,
                    COALESCE(SUM(tokens_used), 0) as total_tokens,
                    AVG(tokens_used) as avg_tokens,
                    AVG(steps_count) as avg_steps,
                    COUNT(CASE WHEN success = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) as success_rate,
                    COUNT(CASE WHEN error_occurred = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) as error_rate,
                    COUNT(CASE WHEN user_rating IS NOT NULL THEN 1 END) as total_ratings,
                    AVG(CASE WHEN user_rating IS NOT NULL THEN user_rating END) * 100 as satisfaction_score
                FROM quality_metrics
                WHERE timestamp >= datetime('now', ?)
            """
            df = pd.read_sql(query, conn, params=(window_modifier,))

        if df.empty:
            return {
                "total_conversations": 0,
                "avg_response_time": 0.0,
                "min_response_time": 0.0,
                "max_response_time": 0.0,
                "total_tokens": 0,
                "avg_tokens": 0.0,
                "avg_steps": 0.0,
                "success_rate": 0.0,
                "error_rate": 0.0,
                "total_ratings": 0,
                "satisfaction_score": 0.0,
            }

        raw = df.iloc[0].to_dict()
        int_fields = {"total_conversations", "total_tokens", "total_ratings"}
        sanitized: dict[str, Any] = {}
        for key, value in raw.items():
            if value is None or pd.isna(value):
                sanitized[key] = 0 if key in int_fields else 0.0
            elif key in int_fields:
                sanitized[key] = int(value)
            else:
                sanitized[key] = float(value)
        return sanitized

    def get_metrics_by_agent(self, days: int = 7) -> pd.DataFrame:
        """Get metrics broken down by agent type using parameterized SQL."""
        with self._get_connection() as conn:
            window_modifier = f"-{int(days)} days"
            query = """
                SELECT
                    agent_used,
                    COUNT(*) as conversations,
                    AVG(response_time) as avg_response_time,
                    AVG(tokens_used) as avg_tokens,
                    COUNT(CASE WHEN success = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) as success_rate
                FROM quality_metrics
                WHERE timestamp >= datetime('now', ?)
                GROUP BY agent_used
                ORDER BY conversations DESC
            """
            return pd.read_sql(query, conn, params=(window_modifier,))

    def get_trends(self, days: int = 7) -> pd.DataFrame:
        """Get daily trends for charts using parameterized SQL."""
        with self._get_connection() as conn:
            window_modifier = f"-{int(days)} days"
            query = """
                SELECT
                    DATE(timestamp) as date,
                    COUNT(*) as conversations,
                    AVG(response_time) as avg_response_time,
                    AVG(tokens_used) as avg_tokens,
                    COUNT(CASE WHEN success = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) as success_rate
                FROM quality_metrics
                WHERE timestamp >= datetime('now', ?)
                GROUP BY DATE(timestamp)
                ORDER BY date
            """
            return pd.read_sql(query, conn, params=(window_modifier,))


def estimate_tokens(text: str) -> int:
    """Simple token estimation (roughly 4 chars per token)."""
    return len(text) // 4
