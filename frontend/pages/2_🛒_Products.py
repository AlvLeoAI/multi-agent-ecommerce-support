import html
import os

import requests
import streamlit as st

# Unified API Base URL configuration
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    os.getenv("API_URL", "http://localhost:8000"),
).rstrip("/")

DEFAULT_CATEGORIES = ["All", "Laptops", "Smartphones", "Audio", "Accessories"]

st.set_page_config(
    page_title="Products - E-Commerce Support",
    page_icon="🛒",
    layout="wide",
)


def fetch_categories() -> list[str]:
    """Fetch product categories dynamically from the backend with safe fallback."""
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
) -> list[dict]:
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


def get_stock_badge(stock: int) -> str:
    """Generate stock status badge HTML."""
    safe_stock = int(stock)
    if safe_stock <= 0:
        return (
            '<span style="background-color: #ff4444; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 12px; font-weight: bold;">OUT OF STOCK</span>'
        )
    if safe_stock < 10:
        return (
            f'<span style="background-color: #ffaa00; color: white; padding: 4px 12px; '
            f'border-radius: 12px; font-size: 12px; font-weight: bold;">LOW STOCK ({safe_stock})</span>'
        )
    return (
        f'<span style="background-color: #00aa44; color: white; padding: 4px 12px; '
        f'border-radius: 12px; font-size: 12px; font-weight: bold;">IN STOCK ({safe_stock})</span>'
    )


def display_product_card(product: dict) -> None:
    """Display a single product card with HTML escaping on all dynamic fields."""
    safe_image = html.escape(str(product.get("image", "📦")))
    safe_name = html.escape(str(product.get("name", "Unnamed Product")))
    safe_desc = html.escape(str(product.get("description", "No description available")))
    safe_cat = html.escape(str(product.get("category", "N/A")))
    safe_price = float(product.get("price", 0.0))
    safe_stock = int(product.get("stock", 0))

    with st.container():
        card_html = f"""
        <div style="
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 16px;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            height: 100%;
            transition: transform 0.2s;
        ">
            <div style="text-align: center; margin-bottom: 12px;">
                <div style="
                    width: 100%;
                    height: 200px;
                    background-color: #f5f5f5;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 48px;
                    margin-bottom: 12px;
                ">
                    {safe_image}
                </div>
            </div>
            <h3 style="margin: 8px 0; font-size: 18px; color: #333;">{safe_name}</h3>
            <p style="color: #666; font-size: 14px; margin: 8px 0; min-height: 60px;">{safe_desc}</p>
            <div style="margin: 12px 0;">
                <p style="font-size: 24px; font-weight: bold; color: #2e7d32; margin: 8px 0;">
                    ${safe_price:.2f}
                </p>
                <p style="font-size: 14px; color: #666; margin: 4px 0;">
                    Category: <strong>{safe_cat}</strong>
                </p>
            </div>
            <div style="margin-top: 12px;">
                {get_stock_badge(safe_stock)}
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)


# Main UI
st.title("🛒 Product Catalog")
st.markdown("Browse our complete product catalog with advanced filtering options")

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")

    search_query = st.text_input(
        "Search products",
        placeholder="Enter product name...",
        help="Search by product name",
    )

    st.divider()

    categories = fetch_categories()
    selected_category = st.selectbox("Category", categories)

    st.subheader("Price Range")
    col1, col2 = st.columns(2)
    with col1:
        min_price = st.number_input("Min $", min_value=0.0, value=0.0, step=10.0)
    with col2:
        max_price = st.number_input("Max $", min_value=0.0, value=2000.0, step=10.0)

    st.subheader("Availability")
    stock_filter = st.radio(
        "Stock Status",
        ["All Products", "In Stock Only", "Out of Stock"],
        help="Filter by stock availability",
    )

    if st.button("🔄 Clear Filters", use_container_width=True):
        st.rerun()

# Convert filters to API parameters
category_param = None if selected_category == "All" else selected_category
stock_param = None
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
    in_stock_count = sum(1 for p in products if p["stock"] > 0)
    st.metric("In Stock", in_stock_count)
with col3:
    out_of_stock_count = len(products) - in_stock_count
    st.metric("Out of Stock", out_of_stock_count)

st.divider()

# Display products in grid layout
if products:
    cols_per_row = 3
    rows = [products[i : i + cols_per_row] for i in range(0, len(products), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for idx, product in enumerate(row):
            with cols[idx]:
                display_product_card(product)
else:
    st.info("No products found matching your filters. Try adjusting your search criteria.")

# Footer
st.divider()
st.markdown(
    """
<div style="text-align: center; color: #666; padding: 20px;">
    <p>💡 <strong>Tip:</strong> Use the filters in the sidebar to narrow down your search</p>
    <p>Need help finding a product? Visit the <strong>Chat</strong> page to talk with our support agent!</p>
</div>
""",
    unsafe_allow_html=True,
)
