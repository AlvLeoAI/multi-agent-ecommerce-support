"""
Products API Router
Handles product catalog endpoints backed by the deterministic SQLite catalog layer.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from database.catalog_db import (
    get_catalog_product,
    list_catalog_categories,
    list_catalog_products,
    search_catalog_products,
)
from models.schemas import ProductSearchRequest
from services.pricing import check_stock as check_catalog_stock

router = APIRouter(prefix="/products", tags=["products"])


def _validate_price_param(value: float | None, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not math.isfinite(float(value)) or float(value) < 0:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be a finite non-negative number",
        )
    return float(value)


@router.get("/")
async def list_products(
    category: str | None = Query(None, description="Filter by category (case-insensitive)"),
    in_stock_only: bool = Query(False, description="Show only in-stock products"),
    in_stock: bool | None = Query(
        None, description="Filter by stock status (True=in stock, False=out of stock)"
    ),
    min_price: float | None = Query(None, description="Minimum price filter"),
    max_price: float | None = Query(None, description="Maximum price filter"),
    search: str | None = Query(None, description="Search substring in product name or description"),
) -> list[dict[str, Any]]:
    """
    List all products with optional category, stock, price range, and text search filters.
    """
    valid_min = _validate_price_param(min_price, "min_price")
    valid_max = _validate_price_param(max_price, "max_price")

    products = list_catalog_products(category=category, in_stock_only=in_stock_only)

    if in_stock is True:
        products = [p for p in products if p["stock"] > 0]
    elif in_stock is False:
        products = [p for p in products if p["stock"] == 0]

    if valid_min is not None:
        products = [p for p in products if p["price"] >= valid_min]

    if valid_max is not None:
        products = [p for p in products if p["price"] <= valid_max]

    if search and search.strip():
        needle = search.strip().lower()
        products = [
            p
            for p in products
            if needle in p["name"].lower()
            or needle in p.get("description", "").lower()
            or needle in p["id"].lower()
        ]

    return products


@router.get("/categories")
async def list_categories() -> list[str]:
    """Get all product categories from SQLite catalog."""
    return list_catalog_categories()


@router.get("/{product_id}")
async def get_product(product_id: str) -> dict[str, Any]:
    """
    Get details for a specific product by ID.
    """
    product = get_catalog_product(product_id)
    if product is not None:
        return product

    raise HTTPException(
        status_code=404,
        detail=f"Product '{product_id}' not found",
    )


@router.post("/search")
async def search_products(
    category: str | None = Query(None, description="Filter by category"),
    max_price: float | None = Query(None, description="Maximum price filter"),
    min_stock: int | None = Query(None, description="Minimum stock filter"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    payload: ProductSearchRequest | None = Body(default=None),
) -> dict[str, Any]:
    """
    Search products with deterministic SQLite catalog filters.
    Accepts either query parameters, a JSON `ProductSearchRequest` body, or both.
    """
    eff_category = category if category is not None else (payload.category if payload else None)
    eff_max_price = max_price if max_price is not None else (payload.max_price if payload else None)
    if min_stock is not None:
        eff_min_stock = min_stock
    elif payload is not None:
        eff_min_stock = payload.min_stock
    else:
        eff_min_stock = 0
    eff_tags = tags if tags is not None else (payload.tags if payload else None)

    valid_max = _validate_price_param(eff_max_price, "max_price")
    if eff_min_stock < 0:
        raise HTTPException(status_code=422, detail="min_stock must be >= 0")

    try:
        matched = search_catalog_products(
            category=eff_category,
            max_price=valid_max,
            min_stock=eff_min_stock,
            tags=eff_tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    results = [
        {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "stock": product["stock"],
            "category": product["category"],
            "description": product["description"],
        }
        for product in matched
    ]

    return {
        "count": len(results),
        "products": results,
    }


@router.get("/{product_id}/stock")
async def check_stock(product_id: str) -> dict[str, Any]:
    """
    Check inventory status for a product by canonical product_id.
    """
    product = get_catalog_product(product_id)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{product_id}' not found",
        )

    stock_info = check_catalog_stock(product["id"], requested_qty=1)
    return {
        "product_id": stock_info["product_id"],
        "product_name": stock_info["product_name"],
        "stock_count": stock_info["stock_count"],
        "stock_status": stock_info["stock_status"],
        "message": stock_info["message"],
    }
