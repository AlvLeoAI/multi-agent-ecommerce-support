# quality_tracker.py
import sqlite3
import time
from datetime import datetime
from typing import Optional
import pandas as pd

class QualityTracker:
    """Track agent quality metrics - Simple, no ML needed"""
    
    def __init__(self, db_path: str = "ecommerce_agent.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Create quality metrics table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
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
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversation_history(conversation_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Quality metrics table created/verified")
    
    def track_conversation(self, 
                          conversation_id: str,
                          response_time: float,
                          tokens_used: Optional[int],
                          steps_count: int,
                          agent_used: str,
                          success: bool = True,
                          error_occurred: bool = False):
        """Track a single conversation's quality metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO quality_metrics 
            (conversation_id, response_time, tokens_used, steps_count, 
             agent_used, success, error_occurred, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (conversation_id, response_time, tokens_used, steps_count,
              agent_used, success, error_occurred, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def save_user_rating(self, conversation_id: str, rating: int):
        """Save user rating (1 for thumbs up, 0 for thumbs down)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE quality_metrics 
            SET user_rating = ?
            WHERE conversation_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (rating, conversation_id))
        
        conn.commit()
        conn.close()
    
    def get_metrics_summary(self, days: int = 7) -> dict:
        """Get aggregated metrics for the last N days"""
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
            SELECT 
                COUNT(*) as total_conversations,
                AVG(response_time) as avg_response_time,
                MIN(response_time) as min_response_time,
                MAX(response_time) as max_response_time,
                SUM(tokens_used) as total_tokens,
                AVG(tokens_used) as avg_tokens,
                AVG(steps_count) as avg_steps,
                COUNT(CASE WHEN success = 1 THEN 1 END) * 100.0 / COUNT(*) as success_rate,
                COUNT(CASE WHEN error_occurred = 1 THEN 1 END) * 100.0 / COUNT(*) as error_rate,
                COUNT(CASE WHEN user_rating IS NOT NULL THEN 1 END) as total_ratings,
                AVG(CASE WHEN user_rating IS NOT NULL THEN user_rating END) * 100 as satisfaction_score
            FROM quality_metrics
            WHERE timestamp >= datetime('now', '-{days} days')
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df.iloc[0].to_dict() if not df.empty else {}
    
    def get_metrics_by_agent(self, days: int = 7) -> pd.DataFrame:
        """Get metrics broken down by agent type"""
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
            SELECT 
                agent_used,
                COUNT(*) as conversations,
                AVG(response_time) as avg_response_time,
                AVG(tokens_used) as avg_tokens,
                COUNT(CASE WHEN success = 1 THEN 1 END) * 100.0 / COUNT(*) as success_rate
            FROM quality_metrics
            WHERE timestamp >= datetime('now', '-{days} days')
            GROUP BY agent_used
            ORDER BY conversations DESC
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df
    
    def get_trends(self, days: int = 7) -> pd.DataFrame:
        """Get daily trends for charts"""
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as conversations,
                AVG(response_time) as avg_response_time,
                AVG(tokens_used) as avg_tokens,
                COUNT(CASE WHEN success = 1 THEN 1 END) * 100.0 / COUNT(*) as success_rate
            FROM quality_metrics
            WHERE timestamp >= datetime('now', '-{days} days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df


def estimate_tokens(text: str) -> int:
    """Simple token estimation (roughly 4 chars per token)"""
    return len(text) // 4


# Test the setup
if __name__ == "__main__":
    tracker = QualityTracker()
    print("✅ QualityTracker initialized successfully!")
    
    # Test tracking a conversation
    tracker.track_conversation(
        conversation_id="test_123",
        response_time=1.5,
        tokens_used=450,
        steps_count=3,
        agent_used="ProductAgent",
        success=True
    )
    print("✅ Test conversation tracked!")
    
    # Get metrics
    metrics = tracker.get_metrics_summary(days=30)
    print("\n📊 Current Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")