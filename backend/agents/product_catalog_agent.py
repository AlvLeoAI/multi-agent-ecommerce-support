"""
Product Catalog Agent
Handles product information, search, and inventory queries
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

# Configure logger
logger = logging.getLogger(__name__)

# --- FIX: Robust Database Loading ---
# We use a function to load the database, allowing reloading if necessary.
def load_product_db():
    try:
        # Try searching in common paths (Docker vs Local)
        base_dir = Path(__file__).resolve().parent.parent # backend/
        db_path = base_dir / "database" / "products.json"
        
        if not db_path.exists():
             # Fallback for when we run from the root
             db_path = Path("ecommerce_support/backend/database/products.json")

        with open(db_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"🔥 Error loading product database: {e}")
        return {"products": []} # Return empty DB to avoid crash

PRODUCT_DB = load_product_db()

# Retry configuration
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504]
)

# Load model from env
model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp")

# --- Tools Definitions (Misma lógica, solo quitando prints innecesarios) ---

def get_product_info(product_name: str) -> Dict:
    """Get detailed information about a specific product."""
    product_name_lower = product_name.lower()
    
    # Refresh DB on search (Opcional: si quisieras actualizaciones en vivo)
    # global PRODUCT_DB; PRODUCT_DB = load_product_db() 

    for product in PRODUCT_DB.get("products", []):
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
    
    # Product not found logic...
    available_products = [p["name"] for p in PRODUCT_DB.get("products", [])]
    return {
        "status": "error",
        "message": f"Product '{product_name}' not found.",
        "available_products": available_products[:5]
    }


def search_products(category: Optional[str] = None, max_price: Optional[float] = None, min_stock: int = 1, tags: Optional[List[str]] = None) -> Dict:

    results = []
    for product in PRODUCT_DB.get("products", []):
        # ... (Tu lógica de filtrado) ...
        if category and product["category"] != category: continue
        if max_price and product["price"] > max_price: continue
        if product["stock"] < min_stock: continue
        
        if tags:
            product_tags = set(product.get("tags", []))
            search_tags = set(t.lower() for t in tags)
            if not search_tags.intersection(product_tags): continue

        results.append({
            "name": product["name"],
            "price": f"${product['price']}",
            "stock": product["stock"],
            "category": product["category"]
        })
    
    return {"status": "success", "count": len(results), "products": results}

def check_inventory(product_name: str) -> Dict:
    
    product_name_lower = product_name.lower()
    for product in PRODUCT_DB.get("products", []):
        if product_name_lower in product["name"].lower():
            stock = product["stock"]
            status = "Out of Stock" if stock == 0 else "Low Stock" if stock < 10 else "In Stock"
            message = f"{product['name']} is {status.lower()} ({stock} units)."
            
            return {
                "status": "success",
                "product_name": product["name"],
                "stock_count": stock,
                "stock_status": status,
                "message": message
            }
    return {"status": "error", "message": f"Product '{product_name}' not found."}


# Create Product Catalog Agent
product_catalog_agent = LlmAgent(
    model=Gemini(model=model_name, retry_options=retry_config),
    name="product_catalog_agent",
    description="Product catalog specialist that provides product information, search, and inventory data.",
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

logger.info(f"✅ Product Catalog Agent created using model: {model_name}")
