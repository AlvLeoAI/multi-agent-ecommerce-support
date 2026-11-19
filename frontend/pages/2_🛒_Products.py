"""
Products Page - Deterministic SQLite Product Catalog Browser
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    os.getenv("API_URL", "http://localhost:8000"),
).rstrip("/")

DEFAULT_CATEGORIES = ["All", "Laptops", "Smartphones", "Audio", "Accessories"]

CATEGORY_ICONS: dict[str, str] = {
    "Laptops": "💻",
    "Smartphones": "📱",
    "Audio": "🎧",
    "Accessories": "🖱️",
}

st.set_page_config(
    page_title="Products - E-Commerce Support",
    page_icon="🛒",
    layout="wide",
)


@st.cache_data(ttl=60)
def fetch_categories() -> list[str]:
    """Fetch product categories dynamically from the backend with 60s cache and safe fallback."""
    try:
        response = requests.get(f"{API_BASE_URL}/products/categories", timeout=5)
        response.raise_for_status()
        cats = response.json()
        if isinstance(cats, list) and cats:
            return ["All"] + [str(c) for c in cats]
    except requests.exceptions.RequestException:
        pass
    return DEFAULT_CATEGORIES


def get_products(
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    in_stock: bool | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch products from the API with filters."""
    try:
        params: dict[str, object] = {}
        if category:
            params["category"] = category
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if in_stock is not None:
            params["in_stock"] = in_stock
        if search:
            params["search"] = search

        response = requests.get(f"{API_BASE_URL}/products/", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching products: {str(e)}")
        return []


def reset_filters() -> None:
    """Reset all sidebar filter widget states to their default values."""
    st.session_state["filter_search"] = ""
    st.session_state["filter_category"] = "All"
    st.session_state["filter_min_price"] = 0.0
    st.session_state["filter_max_price"] = 2000.0
    st.session_state["filter_stock"] = "All Products"


def display_product_card(product: dict[str, Any]) -> None:
    """Display a theme-adaptive product card using native Streamlit containers."""
    category = str(product.get("category", "N/A"))
    icon = CATEGORY_ICONS.get(category, "📦")
    name = str(product.get("name", "Unnamed Product"))
    description = str(product.get("description", "No description available"))
    price = float(product.get("price", 0.0))
    stock = int(product.get("stock", 0))
    expected_restock = product.get("expected_restock")
    specs = product.get("specs") or {}
    product_id = str(product.get("id", name))

    with st.container(border=True):
        st.markdown(f"### {icon} {name}")
        st.caption(f"Category: **{category}** · SKU: `{product_id}`")

        st.markdown(f"#### ${price:,.2f}")

        if stock <= 0:
            restock_note = f" (Restock: {expected_restock})" if expected_restock else ""
            st.error(f"Out of Stock{restock_note}")
        elif stock < 10:
            st.warning(f"Low Stock · {stock} units remaining")
        else:
            st.success(f"In Stock · {stock} units available")

        st.write(description)

        if isinstance(specs, dict) and specs:
            spec_items = [
                f"**{str(k).replace('_', ' ').title()}:** {v}" for k, v in list(specs.items())[:4]
            ]
            st.caption(" · ".join(spec_items))

        if st.button(
            "💬 Quote / Ask Agent",
            key=f"quote_btn_{product_id}",
            use_container_width=True,
        ):
            st.session_state["temp_message"] = (
                f"Tell me about {name} and quote 1 unit with tax in US-STANDARD."
            )
            st.switch_page("pages/1_💬_Chat.py")


# Initialize filter session state defaults
st.session_state.setdefault("filter_search", "")
st.session_state.setdefault("filter_category", "All")
st.session_state.setdefault("filter_min_price", 0.0)
st.session_state.setdefault("filter_max_price", 2000.0)
st.session_state.setdefault("filter_stock", "All Products")

# Main UI
st.title("🛒 Product Catalog")
st.markdown("Browse the deterministic SQLite product catalog with live stock verification.")

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")

    search_query = st.text_input(
        "Search products",
        key="filter_search",
        placeholder="Enter product name...",
        help="Search by product name or description",
    )

    st.divider()

    categories = fetch_categories()
    if st.session_state["filter_category"] not in categories:
        st.session_state["filter_category"] = "All"
    selected_category = st.selectbox("Category", categories, key="filter_category")

    st.subheader("Price Range")
    col1, col2 = st.columns(2)
    with col1:
        min_price = st.number_input("Min $", min_value=0.0, step=10.0, key="filter_min_price")
    with col2:
        max_price = st.number_input("Max $", min_value=0.0, step=10.0, key="filter_max_price")

    st.subheader("Availability")
    stock_filter = st.radio(
        "Stock Status",
        ["All Products", "In Stock Only", "Out of Stock"],
        key="filter_stock",
        help="Filter by stock availability",
    )

    st.button("🔄 Clear Filters", on_click=reset_filters, use_container_width=True)

# Convert filters to API parameters
category_param = None if selected_category == "All" else selected_category
stock_param: bool | None = None
if stock_filter == "In Stock Only":
    stock_param = True
elif stock_filter == "Out of Stock":
    stock_param = False

search_param = search_query if search_query else None

# Fetch products
with st.spinner("Loading products..."):
    products = get_products(
        category=category_param,
        min_price=min_price,
        max_price=max_price,
        in_stock=stock_param,
        search=search_param,
    )

# Display results summary
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Products", len(products))
with col2:
    in_stock_count = sum(1 for p in products if int(p.get("stock", 0)) > 0)
    st.metric("In Stock", in_stock_count)
with col3:
    out_of_stock_count = len(products) - in_stock_count
    st.metric("Out of Stock", out_of_stock_count)

st.divider()

# Display products in grid layout
if products:
    cols_per_row = 2
    rows = [products[i : i + cols_per_row] for i in range(0, len(products), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for idx, product in enumerate(row):
            with cols[idx]:
                display_product_card(product)
else:
    st.info("No products found matching your filters. Try adjusting your search criteria.")

st.divider()
st.caption(
    "💡 Use the sidebar filters to narrow results, or click **Quote / Ask Agent** "
    "on any product card to calculate a deterministic quote in Chat."
)
