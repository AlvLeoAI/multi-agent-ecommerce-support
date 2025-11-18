"""
Products API Router
Handles product catalog endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
import json
from pathlib import Path

router = APIRouter(prefix="/products", tags=["products"])

# Load product database
DATABASE_PATH = Path(__file__).parent.parent / "database" / "products.json"

with open(DATABASE_PATH, 'r') as f:
    PRODUCT_DB = json.load(f)


@router.get("/")
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    in_stock_only: bool = Query(False, description="Show only in-stock products")
) -> List[Dict]:
    """
    List all products with optional filters.
    
    Args:
        category: Filter by category
        in_stock_only: Only show products in stock
    
    Returns:
        List of products
    """
    products = PRODUCT_DB["products"]
    
    # Apply filters
    if category:
        products = [p for p in products if p["category"] == category]
    
    if in_stock_only:
        products = [p for p in products if p["stock"] > 0]
    
    return products


@router.get("/categories")
async def list_categories() -> List[str]:
    """Get all product categories."""
    return PRODUCT_DB["categories"]


@router.get("/{product_id}")
async def get_product(product_id: str) -> Dict:
    """
    Get details for a specific product.
    
    Args:
        product_id: Product ID
    
    Returns:
        Product details
    """
    for product in PRODUCT_DB["products"]:
        if product["id"] == product_id:
            return product
    
    raise HTTPException(
        status_code=404,
        detail=f"Product '{product_id}' not found"
    )


@router.post("/search")
async def search_products(
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    min_stock: int = 0,
    tags: Optional[List[str]] = None
) -> Dict:
    """
    Search products with filters.
    
    Args:
        category: Filter by category
        max_price: Maximum price filter
        min_stock: Minimum stock filter
        tags: Filter by tags
    
    Returns:
        Search results
    """
    results = []
    
    for product in PRODUCT_DB["products"]:
        # Apply filters
        if category and product["category"] != category:
            continue
        
        if max_price and product["price"] > max_price:
            continue
        
        if product["stock"] < min_stock:
            continue
        
        if tags:
            product_tags = set(product.get("tags", []))
            search_tags = set(t.lower() for t in tags)
            if not search_tags.intersection(product_tags):
                continue
        
        # Add to results
        results.append({
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "stock": product["stock"],
            "category": product["category"],
            "description": product["description"]
        })
    
    return {
        "count": len(results),
        "products": results
    }


@router.get("/{product_id}/stock")
async def check_stock(product_id: str) -> Dict:
    """
    Check inventory status for a product.
    
    Args:
        product_id: Product ID
    
    Returns:
        Stock information
    """
    for product in PRODUCT_DB["products"]:
        if product["id"] == product_id:
            stock = product["stock"]
            
            if stock == 0:
                status = "Out of Stock"
                message = f"{product['name']} is currently out of stock."
                if "expected_restock" in product:
                    message += f" Expected restock: {product['expected_restock']}"
            elif stock < 10:
                status = "Low Stock"
                message = f"{product['name']} is in low stock ({stock} units). Order soon!"
            else:
                status = "In Stock"
                message = f"{product['name']} is in stock ({stock} units available)."
            
            return {
                "product_id": product["id"],
                "product_name": product["name"],
                "stock_count": stock,
                "stock_status": status,
                "message": message
            }
    
    raise HTTPException(
        status_code=404,
        detail=f"Product '{product_id}' not found"
    )