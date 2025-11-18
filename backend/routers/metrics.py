"""
Metrics API Router
Handles analytics and performance metrics
"""

from fastapi import APIRouter
from typing import Dict, List
from datetime import datetime, timedelta
import json
from pathlib import Path
from collections import Counter
import sys

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import database functions
from database.chat_memory import get_chat_metrics as get_db_chat_metrics

# Load products for reference
DATABASE_PATH = Path(__file__).parent.parent / "database" / "products.json"
with open(DATABASE_PATH, 'r') as f:
    PRODUCT_DB = json.load(f)


@router.get("/overview")
async def get_metrics_overview() -> Dict:
    """
    Get high-level metrics overview
    Combines data from SQLite (chat) and products.json (inventory)
    """
    # Get chat metrics from SQLite database
    chat_data = get_db_chat_metrics()
    
    # Products stats from JSON
    products = PRODUCT_DB["products"]
    total_products = len(products)
    in_stock = sum(1 for p in products if p["stock"] > 0)
    out_of_stock = total_products - in_stock
    low_stock = sum(1 for p in products if 0 < p["stock"] < 10)
    
    return {
        "conversations": {
            "total": chat_data["total_conversations"],
            "total_messages": chat_data["total_messages"],
            "avg_messages_per_conversation": chat_data["avg_messages_per_conversation"],
            "active_sessions_24h": chat_data["active_sessions"]
        },
        "products": {
            "total": total_products,
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "total_queries": 0  # Could track this in DB later
        },
        "agents": {
            "total_calls": chat_data["total_messages"] // 2,  # Estimate: user + agent messages
            "customer_support_calls": 0,  # Could track this in DB later
            "product_catalog_calls": 0   # Could track this in DB later
        }
    }


@router.get("/products/top-queried")
async def get_top_queried_products(limit: int = 10) -> List[Dict]:
    """
    Get most queried products
    Currently returns sample data - could be enhanced with query tracking
    """
    # Return sample data from products.json
    products = PRODUCT_DB["products"][:limit]
    return [
        {
            "product_id": p["id"],
            "product_name": p["name"],
            "category": p["category"],
            "query_count": 0,  # Could track this in DB later
            "price": p["price"],
            "stock": p["stock"]
        }
        for p in products
    ]


@router.get("/products/by-category")
async def get_product_distribution() -> Dict:
    """Get product distribution by category"""
    products = PRODUCT_DB["products"]
    categories = PRODUCT_DB["categories"]
    
    category_counts = Counter(p["category"] for p in products)
    total = len(products)
    
    distribution = []
    for category in categories:
        count = category_counts.get(category, 0)
        distribution.append({
            "category": category,
            "count": count,
            "percentage": round((count / total * 100) if total > 0 else 0, 1),
            "in_stock": sum(1 for p in products if p["category"] == category and p["stock"] > 0)
        })
    
    return {
        "total_products": total,
        "categories": distribution
    }


@router.get("/agents/performance")
async def get_agent_performance() -> Dict:
    """
    Get agent performance metrics
    Currently returns estimates - could be enhanced with detailed tracking
    """
    # Get basic metrics from database
    chat_data = get_db_chat_metrics()
    
    # Estimate agent calls (every message pair = 1 agent call)
    estimated_calls = chat_data["total_messages"] // 2
    
    return {
        "customer_support": {
            "total_calls": estimated_calls,
            "avg_response_time": 0,  # Could track this with timestamps
            "success_rate": 0   # Could track this with user feedback
        },
        "product_catalog": {
            "total_calls": 0,   # Could track specific agent calls
            "avg_response_time": 0,
            "success_rate": 0
        }
    }