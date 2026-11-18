"""
Products API Router
Handles product catalog endpoints backed by the deterministic SQLite catalog layer.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from database.catalog_db import (
    get_catalog_product,
    list_catalog_categories,
    list_catalog_products,
    search_catalog_products,
)
from services.pricing import check_stock as check_catalog_stock

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/")
async def list_products(
    category: str | None = Query(None, description="Filter by category"),
    in_stock_only: bool = Query(False, description="Show only in-stock products"),
) -> list[dict[str, Any]]:
    """
    List all products with optional filters from SQLite catalog.
    """
    return list_catalog_products(category=category, in_stock_only=in_stock_only)


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
    category: str | None = None,
    max_price: float | None = None,
    min_stock: int = 0,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Search products with deterministic SQLite catalog filters.
    """
    matched = search_catalog_products(
        category=category,
        max_price=max_price,
        min_stock=min_stock,
        tags=tags,
    )
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
