"""
Metrics API Router
Handles analytics and performance metrics backed by SQLite chat memory and catalog.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.catalog_db import list_catalog_categories, list_catalog_products  # noqa: E402
from database.chat_memory import get_chat_metrics as get_db_chat_metrics  # noqa: E402


@router.get("/overview")
async def get_metrics_overview() -> dict[str, Any]:
    """
    Get high-level metrics overview combining SQLite chat memory and SQLite product catalog.
    """
    chat_data = get_db_chat_metrics()
    products = list_catalog_products()

    total_products = len(products)
    in_stock = sum(1 for p in products if p["stock"] > 0)
    out_of_stock = total_products - in_stock
    low_stock = sum(1 for p in products if 0 < p["stock"] < 10)

    return {
        "conversations": {
            "total": chat_data["total_conversations"],
            "total_messages": chat_data["total_messages"],
            "avg_messages_per_conversation": chat_data["avg_messages_per_conversation"],
            "active_sessions_24h": chat_data["active_sessions"],
        },
        "products": {
            "total": total_products,
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "total_queries": 0,
        },
        "agents": {
            "total_calls": chat_data["total_messages"] // 2,
            "customer_support_calls": 0,
            "product_catalog_calls": 0,
        },
    }


@router.get("/products/top-queried")
async def get_top_queried_products(limit: int = 10) -> list[dict[str, Any]]:
    """Get most queried products from SQLite catalog."""
    products = list_catalog_products()[:limit]
    return [
        {
            "product_id": p["id"],
            "product_name": p["name"],
            "category": p["category"],
            "query_count": 0,
            "price": p["price"],
            "stock": p["stock"],
        }
        for p in products
    ]


@router.get("/products/by-category")
async def get_product_distribution() -> dict[str, Any]:
    """Get product distribution by category from SQLite catalog."""
    products = list_catalog_products()
    categories = list_catalog_categories()

    category_counts = Counter(p["category"] for p in products)
    total = len(products)

    distribution = []
    for category in categories:
        count = category_counts.get(category, 0)
        distribution.append(
            {
                "category": category,
                "count": count,
                "percentage": round((count / total * 100) if total > 0 else 0, 1),
                "in_stock": sum(
                    1 for p in products if p["category"] == category and p["stock"] > 0
                ),
            }
        )

    return {
        "total_products": total,
        "categories": distribution,
    }


@router.get("/agents/performance")
async def get_agent_performance() -> dict[str, Any]:
    """Get agent performance metrics."""
    chat_data = get_db_chat_metrics()
    estimated_calls = chat_data["total_messages"] // 2

    return {
        "customer_support": {
            "total_calls": estimated_calls,
            "avg_response_time": 0,
            "success_rate": 0,
        },
        "product_catalog": {
            "total_calls": 0,
            "avg_response_time": 0,
            "success_rate": 0,
        },
    }
