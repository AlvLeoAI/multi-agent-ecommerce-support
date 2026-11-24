"""
Metrics API Router
Handles analytics and performance metrics backed by SQLite chat memory,
catalog_db, and live QualityTracker telemetry.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.catalog_db import list_catalog_categories, list_catalog_products  # noqa: E402
from database.chat_memory import get_chat_metrics as get_db_chat_metrics  # noqa: E402
from routers import chat as chat_router  # noqa: E402


@router.get("/")
@router.get("/overview")
async def get_metrics_overview() -> dict[str, Any]:
    """
    Get high-level metrics overview combining SQLite chat memory, SQLite product catalog,
    and live QualityTracker agent execution telemetry.
    """
    chat_data = get_db_chat_metrics()
    products = list_catalog_products()
    quality_summary = chat_router.quality_tracker.get_metrics_summary(days=30)
    by_agent_df = chat_router.quality_tracker.get_metrics_by_agent(days=30)
    by_agent_records = by_agent_df.to_dict("records") if not by_agent_df.empty else []
    agent_map = {str(r["agent_used"]): r for r in by_agent_records}

    total_products = len(products)
    in_stock = sum(1 for p in products if p["stock"] > 0)
    out_of_stock = total_products - in_stock
    low_stock = sum(1 for p in products if 0 < p["stock"] < 10)

    tracked_calls = int(quality_summary.get("total_conversations", 0))
    total_calls = max(tracked_calls, chat_data["total_messages"] // 2)
    product_calls = int(agent_map.get("ProductAgent", {}).get("conversations", 0))
    support_calls = max(total_calls - product_calls, 0)

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
            "total_queries": product_calls,
        },
        "agents": {
            "total_calls": total_calls,
            "customer_support_calls": support_calls,
            "product_catalog_calls": product_calls,
        },
    }


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


@router.get("/agents")
@router.get("/performance")
@router.get("/agents/performance")
async def get_agent_performance(
    days: int = Query(30, ge=1, le=365, description="Lookback window in days (1-365)"),
) -> dict[str, Any]:
    """Get live agent performance metrics from QualityTracker and chat memory."""
    chat_data = get_db_chat_metrics()
    quality_summary = chat_router.quality_tracker.get_metrics_summary(days=days)
    by_agent_df = chat_router.quality_tracker.get_metrics_by_agent(days=days)
    by_agent_records = by_agent_df.to_dict("records") if not by_agent_df.empty else []
    agent_map = {str(r["agent_used"]): r for r in by_agent_records}

    tracked_calls = int(quality_summary.get("total_conversations", 0))
    estimated_calls = max(tracked_calls, chat_data["total_messages"] // 2)
    avg_resp_time = round(float(quality_summary.get("avg_response_time", 0.0)), 4)
    overall_success = round(float(quality_summary.get("success_rate", 0.0)), 2)

    prod_row = agent_map.get("ProductAgent", {})
    prod_calls = int(prod_row.get("conversations", 0))
    prod_resp_time = round(float(prod_row.get("avg_response_time", 0.0) or 0.0), 4)
    prod_success = round(float(prod_row.get("success_rate", 0.0) or 0.0), 2)

    return {
        "customer_support": {
            "total_calls": max(estimated_calls - prod_calls, 0),
            "avg_response_time": avg_resp_time,
            "success_rate": overall_success,
        },
        "product_catalog": {
            "total_calls": prod_calls,
            "avg_response_time": prod_resp_time,
            "success_rate": prod_success,
        },
        "summary": quality_summary,
        "by_agent": by_agent_records,
    }
