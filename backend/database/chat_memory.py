"""
Chat Memory Database
Persistent storage for chat sessions and user preferences with hardened
path resolution, connection hygiene, and foreign-key enforcement.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_CANDIDATE_ROOT = Path(__file__).resolve().parent.parent.parent
if _CANDIDATE_ROOT == Path("/") or not os.access(_CANDIDATE_ROOT, os.W_OK):
    _DEFAULT_ROOT = Path(__file__).resolve().parent.parent
else:
    _DEFAULT_ROOT = _CANDIDATE_ROOT

DB_PATH = Path(os.getenv("SQLITE_DB_PATH", str(_DEFAULT_ROOT / "my_agent_data.db")))


@contextlib.contextmanager
def _get_connection(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    target = Path(db_path) if db_path is not None else DB_PATH
    conn = sqlite3.connect(target)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        yield conn
    finally:
        conn.close()


def init_chat_memory_db(db_path: Path | str | None = None) -> None:
    """Initialize the chat memory database tables."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                preferences TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()


def save_message(
    session_id: str,
    role: str,
    content: str,
    user_id: str | None = None,
) -> None:
    """Save a message to the database."""
    init_chat_memory_db()
    with _get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO chat_sessions (session_id, user_id)
            VALUES (?, ?)
            """,
            (session_id, user_id or session_id),
        )

        cursor.execute(
            """
            UPDATE chat_sessions
            SET last_active = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (session_id,),
        )

        cursor.execute(
            """
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role, content),
        )

        conn.commit()


def get_session_history(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """
    Get the most recent `limit` messages for a session in chronological order.
    Resolves F-06 by selecting the newest `limit` rows via `ORDER BY id DESC`
    and returning them ordered by `id ASC`.
    """
    init_chat_memory_db()
    with _get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role, content, timestamp
            FROM (
                SELECT id, role, content, timestamp
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (session_id, limit),
        )

        return [
            {
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
            }
            for row in cursor.fetchall()
        ]


def get_session_context(session_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Retrieve the most recent `limit` messages for conversation context in
    strict chronological order (`oldest -> newest` among the latest `limit` turns).
    """
    return get_session_history(session_id=session_id, limit=limit)


def get_user_sessions(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get all sessions for a user."""
    init_chat_memory_db()
    with _get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT session_id, created_at, last_active
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY last_active DESC
            LIMIT ?
            """,
            (user_id, limit),
        )

        return [
            {
                "session_id": row[0],
                "created_at": row[1],
                "last_active": row[2],
            }
            for row in cursor.fetchall()
        ]


def save_user_preference(user_id: str, preferences: dict[str, Any]) -> None:
    """Save user preferences."""
    init_chat_memory_db()
    with _get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO user_preferences (user_id, preferences, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, json.dumps(preferences)),
        )

        conn.commit()


def get_user_preferences(user_id: str) -> dict[str, Any] | None:
    """Get user preferences."""
    init_chat_memory_db()
    with _get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT preferences
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user_id,),
        )

        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None


def delete_session(session_id: str) -> None:
    """Delete a session and its messages."""
    init_chat_memory_db()
    with _get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))

        conn.commit()


def get_chat_metrics() -> dict[str, Any]:
    """Get chat metrics from database."""
    init_chat_memory_db()
    with _get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM chat_sessions")
        total_conversations = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        total_messages = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM chat_sessions
            WHERE last_active >= datetime('now', '-1 day')
        """)
        active_sessions = cursor.fetchone()[0]

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "active_sessions": active_sessions,
            "avg_messages_per_conversation": round(total_messages / max(total_conversations, 1), 2),
        }


# Initialize database on import
init_chat_memory_db()
