"""
Product Catalog Agent
Handles product information, search, and inventory queries
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

# Load product database
DATABASE_PATH = Path(__file__).parent.parent / "database" / "products.json"

with open(DATABASE_PATH, 'r') as f:
    PRODUCT_DB = json.load(f)

# Retry configuration
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504]
)

def get_product_info(product_name: str) -> Dict:
    """
    Get detailed information about a specific product.
    
    Args:
        product_name: Name of the product (e.g., "iPhone 15 Pro", "Dell XPS 15")
    
    Returns:
        Dictionary with product information or error message
    """
    product_name_lower = product_name.lower()
    
    # Search for product
    for product in PRODUCT_DB["products"]:
        if product_name_lower in product["name"].lower():
            return {
                "status": "success",
                "product": {
                    "name": product["name"],
                    "price": f"${product['price']}",
                    "stock": product["stock"],
                    "stock_status": "In Stock" if product["stock"] > 0 else "Out of Stock",
                    "category": product["category"],
                    "specs": product["specs"],
                    "description": product["description"],
                    "expected_restock": product.get("expected_restock", None)
                }
            }
    
    # Product not found
    available_products = [p["name"] for p in PRODUCT_DB["products"]]
    return {
        "status": "error",
        "message": f"Product '{product_name}' not found.",
        "available_products": available_products[:5]  # Show first 5
    }


def search_products(
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    min_stock: int = 1,
    tags: Optional[List[str]] = None
) -> Dict:
    """
    Search products with filters.
    
    Args:
        category: Filter by category (e.g., "Laptops", "Audio")
        max_price: Maximum price filter
        min_stock: Minimum stock required (default: 1, i.e., in stock)
        tags: Filter by tags (e.g., ["video editing", "professional"])
    
    Returns:
        Dictionary with matching products
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
            "name": product["name"],
            "price": f"${product['price']}",
            "stock": product["stock"],
            "category": product["category"],
            "description": product["description"]
        })
    
    return {
        "status": "success",
        "count": len(results),
        "products": results
    }


def check_inventory(product_name: str) -> Dict:
    """
    Check inventory status for a product.
    
    Args:
        product_name: Name of the product
    
    Returns:
        Dictionary with inventory information
    """
    product_name_lower = product_name.lower()
    
    for product in PRODUCT_DB["products"]:
        if product_name_lower in product["name"].lower():
            stock = product["stock"]
            
            if stock == 0:
                status = "Out of Stock"
                message = f"{product['name']} is currently out of stock."
                if "expected_restock" in product:
                    message += f" Expected restock: {product['expected_restock']}"
            elif stock < 10:
                status = "Low Stock"
                message = f"{product['name']} is in low stock ({stock} units remaining). Order soon!"
            else:
                status = "In Stock"
                message = f"{product['name']} is in stock ({stock} units available)."
            
            return {
                "status": "success",
                "product_name": product["name"],
                "stock_count": stock,
                "stock_status": status,
                "message": message
            }
    
    return {
        "status": "error",
        "message": f"Product '{product_name}' not found in inventory."
    }


# Create Product Catalog Agent
product_catalog_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="product_catalog_agent",
    description="Product catalog specialist that provides product information, search, and inventory data for an e-commerce store.",
    instruction="""
    You are a product catalog specialist for an e-commerce store.
    
    Your responsibilities:
    1. Provide detailed product information when asked
    2. Help customers find products based on their needs
    3. Check inventory and stock status
    4. Suggest alternatives if products are out of stock
    
    Available tools:
    - get_product_info: Get details about a specific product
    - search_products: Search with filters (category, price, tags)
    - check_inventory: Check stock availability
    
    Always:
    - Be accurate with product details
    - Mention stock status clearly
    - Suggest alternatives for out-of-stock items
    - Be professional and helpful
    """,
    tools=[get_product_info, search_products, check_inventory]
)

print("✅ Product Catalog Agent created!")