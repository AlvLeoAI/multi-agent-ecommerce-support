"""
Product Catalog Agent & Deterministic Catalog Tooling.
Backed by the SQLite catalog (`backend/database/catalog_db.py`) and pure pricing
service (`backend/services/pricing.py`).
"""

from __future__ import annotations

import functools
import logging
import os
from decimal import Decimal
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import types

from database.catalog_db import search_catalog_products
from services.pricing import check_stock, lookup_product

logger = logging.getLogger(__name__)

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

model_name = os.getenv("AGENT_MODEL", "gemini-3.8-flash")


def _make_json_safe(obj: Any) -> Any:
    """Recursively convert Decimal values to str so ADK FunctionResponse JSON serialization succeeds."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_make_json_safe(v) for v in obj)
    return obj


def _wrap_json_safe_tool(func: Any) -> Any:
    @functools.wraps(func)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        return _make_json_safe(func(*args, **kwargs))

    return _wrapped


def get_product_info(product_name: str) -> dict[str, Any]:
    """Get deterministic details, unit price, and stock for a specific product from SQLite."""
    return lookup_product(product_name)


def search_products(
    category: str | None = None,
    max_price: float | None = None,
    min_stock: int = 1,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Search the SQLite product catalog with deterministic filters."""
    try:
        matched = search_catalog_products(
            category=category,
            max_price=max_price,
            min_stock=min_stock,
            tags=tags,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "error_code": "INVALID_PRICE_FILTER",
            "message": str(exc),
            "count": 0,
            "products": [],
        }

    results = [
        {
            "id": product["id"],
            "name": product["name"],
            "price": f"${product['price_decimal']}",
            "amount_cents": product["price_cents"],
            "sim_usdc_micros": product["sim_usdc_micros"],
            "stock": product["stock"],
            "category": product["category"],
            "description": product["description"],
        }
        for product in matched
    ]
    return {"status": "success", "count": len(results), "products": results}


def check_inventory(product_name: str, requested_qty: int = 1) -> dict[str, Any]:
    """Check deterministic inventory availability in SQLite for a product."""
    return check_stock(product_name, requested_qty=requested_qty)


get_product_info_tool = FunctionTool(func=_wrap_json_safe_tool(get_product_info))
search_products_tool = FunctionTool(func=_wrap_json_safe_tool(search_products))
check_inventory_tool = FunctionTool(func=_wrap_json_safe_tool(check_inventory))

PRODUCT_AGENT_INSTRUCTION = """You are a product catalog specialist for an e-commerce store.

Your responsibilities:
1. Provide accurate product details by calling `get_product_info`.
2. Help customers discover products using `search_products`.
3. Verify exact stock availability using `check_inventory`.
4. If an item is out of stock, report the exact `expected_restock` date returned by the tool and search for in-stock alternatives.

Strict Grounding Rules:
- Never guess, fabricate, or extrapolate product SKUs, prices, specifications, or stock counts.
- Only cite products and prices returned by `get_product_info`, `search_products`, or `check_inventory`.
"""

product_catalog_agent = LlmAgent(
    model=Gemini(model=model_name, retry_options=retry_config),
    name="product_catalog_agent",
    description="Deterministic product catalog specialist backed by the local SQLite inventory.",
    instruction=PRODUCT_AGENT_INSTRUCTION,
    tools=[get_product_info_tool, search_products_tool, check_inventory_tool],
)

logger.info(f"✅ Product Catalog Agent created using model: {model_name}")
