"""
Deterministic SQLite Product Catalog & Discount Code Layer.

Replaces raw module-import-time JSON reads with an idempotent, SQLite-backed
source of truth for products, categories, inventory counts, and allowlisted
discount codes.
"""

from __future__ import annotations

import json
import sqlite3
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

# Default SQLite database path (shared with chat_memory unless overridden in tests)
DB_PATH = Path(__file__).resolve().parent.parent.parent / "my_agent_data.db"
SEED_JSON_PATH = Path(__file__).resolve().parent / "products.json"

# Deterministic allowlist of promotional discount codes
DEFAULT_DISCOUNT_CODES: list[dict[str, Any]] = [
    {
        "code": "WELCOME10",
        "discount_percent": "10.00",
        "max_discount_cents": 20000,  # $200.00 maximum cap
        "active": 1,
        "expires_at": "2099-12-31",
    },
    {
        "code": "VIP15",
        "discount_percent": "15.00",
        "max_discount_cents": 50000,  # $500.00 maximum cap
        "active": 1,
        "expires_at": "2099-12-31",
    },
    {
        "code": "SAVE5",
        "discount_percent": "5.00",
        "max_discount_cents": 10000,  # $100.00 maximum cap
        "active": 1,
        "expires_at": "2099-12-31",
    },
    {
        "code": "EXPIRED20",
        "discount_percent": "20.00",
        "max_discount_cents": 30000,
        "active": 0,
        "expires_at": "2020-01-01",
    },
]


def _decimal_to_cents(value: Decimal) -> int:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int((quantized * 100).to_integral_value(rounding=ROUND_HALF_UP))


def _decimal_to_sim_usdc_micros(value: Decimal) -> int:
    quantized = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return int((quantized * Decimal("1000000")).to_integral_value(rounding=ROUND_HALF_UP))


def init_catalog_db(
    db_path: Path | str | None = None,
    seed_json_path: Path | str | None = None,
) -> None:
    """Create and idempotently seed the SQLite catalog and discount_codes tables."""
    target_db = Path(db_path) if db_path is not None else DB_PATH
    target_seed = Path(seed_json_path) if seed_json_path is not None else SEED_JSON_PATH

    conn = sqlite3.connect(target_db)
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalog_categories (
                name TEXT PRIMARY KEY,
                sort_order INTEGER NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                price TEXT NOT NULL,
                price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
                sim_usdc_micros INTEGER NOT NULL CHECK(sim_usdc_micros >= 0),
                stock INTEGER NOT NULL CHECK(stock >= 0),
                specs TEXT NOT NULL,
                description TEXT NOT NULL,
                tags TEXT NOT NULL,
                expected_restock TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discount_codes (
                code TEXT PRIMARY KEY,
                discount_percent TEXT NOT NULL,
                max_discount_cents INTEGER NOT NULL CHECK(max_discount_cents >= 0),
                active INTEGER NOT NULL DEFAULT 1,
                expires_at TEXT
            )
        """)

        if target_seed.exists():
            with open(target_seed) as f:
                seed_data = json.load(f)

            for idx, category in enumerate(seed_data.get("categories", [])):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO catalog_categories (name, sort_order)
                    VALUES (?, ?)
                    """,
                    (category, idx),
                )

            for product in seed_data.get("products", []):
                price_dec = Decimal(str(product["price"])).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                price_cents = _decimal_to_cents(price_dec)
                sim_usdc_micros = _decimal_to_sim_usdc_micros(price_dec)
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO products (
                        id, name, category, price, price_cents, sim_usdc_micros,
                        stock, specs, description, tags, expected_restock
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product["id"],
                        product["name"],
                        product["category"],
                        str(price_dec),
                        price_cents,
                        sim_usdc_micros,
                        int(product["stock"]),
                        json.dumps(product.get("specs", {})),
                        product.get("description", ""),
                        json.dumps([str(t).lower() for t in product.get("tags", [])]),
                        product.get("expected_restock"),
                    ),
                )

        for code_entry in DEFAULT_DISCOUNT_CODES:
            cursor.execute(
                """
                INSERT OR IGNORE INTO discount_codes (
                    code, discount_percent, max_discount_cents, active, expires_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    code_entry["code"].upper(),
                    code_entry["discount_percent"],
                    int(code_entry["max_discount_cents"]),
                    int(code_entry["active"]),
                    code_entry["expires_at"],
                ),
            )

        conn.commit()
    finally:
        conn.close()


def _row_to_product_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        prod_id,
        name,
        category,
        price_str,
        price_cents,
        sim_usdc_micros,
        stock,
        specs_json,
        description,
        tags_json,
        expected_restock,
    ) = row
    price_dec = Decimal(price_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    product_dict: dict[str, Any] = {
        "id": prod_id,
        "name": name,
        "category": category,
        "price": float(price_dec),
        "price_decimal": str(price_dec),
        "price_cents": int(price_cents),
        "sim_usdc_micros": int(sim_usdc_micros),
        "stock": int(stock),
        "specs": json.loads(specs_json) if specs_json else {},
        "description": description,
        "tags": json.loads(tags_json) if tags_json else [],
    }
    if expected_restock is not None:
        product_dict["expected_restock"] = expected_restock
    return product_dict


def list_catalog_products(
    category: str | None = None,
    in_stock_only: bool = False,
) -> list[dict[str, Any]]:
    """Return all catalog products from SQLite with optional category and stock filtering."""
    init_catalog_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        query = """
            SELECT id, name, category, price, price_cents, sim_usdc_micros,
                   stock, specs, description, tags, expected_restock
            FROM products
            WHERE 1=1
        """
        params: list[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if in_stock_only:
            query += " AND stock > 0"
        query += " ORDER BY rowid ASC"

        cursor.execute(query, params)
        return [_row_to_product_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def list_catalog_categories() -> list[str]:
    """Return ordered list of product categories from SQLite."""
    init_catalog_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM catalog_categories ORDER BY sort_order ASC")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def get_catalog_product(product_id: str) -> dict[str, Any] | None:
    """Look up a single product by its exact canonical `product_id`."""
    init_catalog_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, category, price, price_cents, sim_usdc_micros,
                   stock, specs, description, tags, expected_restock
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        )
        row = cursor.fetchone()
        return _row_to_product_dict(row) if row else None
    finally:
        conn.close()


def find_catalog_product(product_id_or_name: str) -> dict[str, Any] | None:
    """
    Deterministic lookup by canonical ID or normalized product name.
    1. Exact match on `id` (case-insensitive).
    2. Exact match on `name` (case-insensitive).
    3. Unambiguous substring match on `name` (only if exactly 1 product matches).
    """
    if not product_id_or_name or not product_id_or_name.strip():
        return None

    needle = product_id_or_name.strip().lower()
    products = list_catalog_products()

    for prod in products:
        if prod["id"].lower() == needle:
            return prod

    for prod in products:
        if prod["name"].lower() == needle:
            return prod

    substring_matches = [prod for prod in products if needle in prod["name"].lower()]
    if len(substring_matches) == 1:
        return substring_matches[0]

    return None


def search_catalog_products(
    category: str | None = None,
    max_price: float | Decimal | None = None,
    min_stock: int = 0,
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Deterministically filter products in SQLite by category, max_price, min_stock, and tags."""
    products = list_catalog_products()
    max_price_cents: int | None = None
    if max_price is not None:
        max_price_dec = Decimal(str(max_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        max_price_cents = _decimal_to_cents(max_price_dec)

    normalized_tags = {t.strip().lower() for t in tags if t and t.strip()} if tags else set()

    results: list[dict[str, Any]] = []
    for prod in products:
        if category and prod["category"].lower() != category.strip().lower():
            continue
        if max_price_cents is not None and prod["price_cents"] > max_price_cents:
            continue
        if prod["stock"] < min_stock:
            continue
        if normalized_tags:
            prod_tags = {t.lower() for t in prod.get("tags", [])}
            if not normalized_tags.intersection(prod_tags):
                continue
        results.append(prod)

    return results


def get_discount_code_record(code: str) -> dict[str, Any] | None:
    """Look up an allowlisted discount code in SQLite."""
    if not code or not code.strip():
        return None
    init_catalog_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT code, discount_percent, max_discount_cents, active, expires_at
            FROM discount_codes
            WHERE code = ?
            """,
            (code.strip().upper(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "code": row[0],
            "discount_percent": Decimal(row[1]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "max_discount_cents": int(row[2]),
            "active": bool(row[3]),
            "expires_at": row[4],
        }
    finally:
        conn.close()


# Ensure catalog tables exist on module import
init_catalog_db()
