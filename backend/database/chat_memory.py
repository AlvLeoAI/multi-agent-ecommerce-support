"""
Chat Memory Database
Persistent storage for chat sessions and user preferences
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "my_agent_data.db"


def init_chat_memory_db():
    """Initialize the chat memory database tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    """)
    
    # Create messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        )
    """)
    
    # Create user preferences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            preferences TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, content: str, user_id: Optional[str] = None):
    """Save a message to the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure session exists
    cursor.execute("""
        INSERT OR IGNORE INTO chat_sessions (session_id, user_id)
        VALUES (?, ?)
    """, (session_id, user_id or session_id))
    
    # Update last_active
    cursor.execute("""
        UPDATE chat_sessions 
        SET last_active = CURRENT_TIMESTAMP 
        WHERE session_id = ?
    """, (session_id,))
    
    # Insert message
    cursor.execute("""
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (?, ?, ?)
    """, (session_id, role, content))
    
    conn.commit()
    conn.close()


def get_session_history(session_id: str, limit: int = 50) -> List[Dict]:
    """Get message history for a session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, content, timestamp
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY timestamp ASC
        LIMIT ?
    """, (session_id, limit))
    
    messages = [
        {
            "role": row[0],
            "content": row[1],
            "timestamp": row[2]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return messages


def get_user_sessions(user_id: str, limit: int = 10) -> List[Dict]:
    """Get all sessions for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT session_id, created_at, last_active
        FROM chat_sessions
        WHERE user_id = ?
        ORDER BY last_active DESC
        LIMIT ?
    """, (user_id, limit))
    
    sessions = [
        {
            "session_id": row[0],
            "created_at": row[1],
            "last_active": row[2]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return sessions


def save_user_preference(user_id: str, preferences: Dict):
    """Save user preferences"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_preferences (user_id, preferences, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (user_id, json.dumps(preferences)))
    
    conn.commit()
    conn.close()


def get_user_preferences(user_id: str) -> Optional[Dict]:
    """Get user preferences"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT preferences
        FROM user_preferences
        WHERE user_id = ?
    """, (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return None


def delete_session(session_id: str):
    """Delete a session and its messages"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
    
    conn.commit()
    conn.close()


def get_chat_metrics() -> Dict:
    """Get chat metrics from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total conversations
    cursor.execute("SELECT COUNT(*) FROM chat_sessions")
    total_conversations = cursor.fetchone()[0]
    
    # Total messages
    cursor.execute("SELECT COUNT(*) FROM chat_messages")
    total_messages = cursor.fetchone()[0]
    
    # Active sessions (last 24 hours)
    cursor.execute("""
        SELECT COUNT(*) FROM chat_sessions
        WHERE last_active >= datetime('now', '-1 day')
    """)
    active_sessions = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "active_sessions": active_sessions,
        "avg_messages_per_conversation": round(
            total_messages / max(total_conversations, 1), 2
        )
    }


# Initialize database on import
init_chat_memory_db()