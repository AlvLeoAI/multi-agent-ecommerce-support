"""
Deterministic Pricing, Inventory Validation & Quote Calculation Engine.

Enforces the core architectural invariant:
1. Zero LLM-supplied prices, discount percentages, or tax rates.
2. Dual financial representation: `decimal.Decimal` (quantized with `ROUND_HALF_UP`)
   plus integer atomic units (`amount_cents` at 10^2 scale and `sim_usdc_micros` at 10^6 scale).
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from database.catalog_db import (
    find_catalog_product,
    get_discount_code_record,
    list_catalog_products,
)

USD_QUANT = Decimal("0.01")
MICROS_SCALE = Decimal("1000000")
CENTS_SCALE = Decimal("100")

# Deterministic allowlist of tax jurisdictions
TAX_JURISDICTIONS: dict[str, Decimal] = {
    "US-STANDARD": Decimal("0.08"),
    "US-CA": Decimal("0.0725"),
    "US-NY": Decimal("0.08875"),
    "US-OR": Decimal("0.00"),
    "EU-VAT": Decimal("0.20"),
}


def quantize_usd(amount: Decimal | str | int | float) -> Decimal:
    """Quantize a monetary value to 2 decimal places using ROUND_HALF_UP."""
    return Decimal(str(amount)).quantize(USD_QUANT, rounding=ROUND_HALF_UP)


def usd_to_cents(amount: Decimal) -> int:
    """Convert a quantized USD Decimal to integer cents (10^2 scale)."""
    q = quantize_usd(amount)
    return int((q * CENTS_SCALE).to_integral_value(rounding=ROUND_HALF_UP))


def usd_to_sim_usdc_micros(amount: Decimal) -> int:
    """Convert a quantized USD Decimal to simulated USDC micro-units (10^6 scale)."""
    q = quantize_usd(amount)
    return int((q * MICROS_SCALE).to_integral_value(rounding=ROUND_HALF_UP))


def _stock_status_label(stock: int) -> str:
    if stock <= 0:
        return "Out of Stock"
    if stock < 10:
        return "Low Stock"
    return "In Stock"


class QuoteLineItemModel(BaseModel):
    """Validated, deterministic line item breakdown."""

    model_config = ConfigDict(extra="forbid")

    product_id: str
    product_name: str
    quantity: int = Field(..., ge=1)
    unit_price: Decimal
    unit_amount_cents: int = Field(..., ge=0)
    unit_sim_usdc_micros: int = Field(..., ge=0)
    line_subtotal: Decimal
    line_subtotal_cents: int = Field(..., ge=0)
    line_subtotal_sim_usdc_micros: int = Field(..., ge=0)


class QuoteCalculationModel(BaseModel):
    """Validated, deterministic cart quote output with dual representations."""

    model_config = ConfigDict(extra="forbid")

    status: str = "success"
    currency: str = "USD"
    items: list[QuoteLineItemModel]
    discount_code: str | None = None
    discount_percent: Decimal = Decimal("0.00")
    tax_jurisdiction: str
    tax_rate: Decimal
    subtotal: Decimal
    subtotal_cents: int = Field(..., ge=0)
    discount_amount: Decimal
    discount_amount_cents: int = Field(..., ge=0)
    taxable_amount: Decimal
    taxable_amount_cents: int = Field(..., ge=0)
    tax_amount: Decimal
    tax_amount_cents: int = Field(..., ge=0)
    total: Decimal
    total_cents: int = Field(..., ge=0)
    total_sim_usdc_micros: int = Field(..., ge=0)


def lookup_product(product_id_or_name: str) -> dict[str, Any]:
    """
    Deterministic lookup of a product's price, stock, and specifications from SQLite.
    Returns a structured error dictionary if the product is not found.
    """
    product = find_catalog_product(product_id_or_name)
    if product is None:
        available = [p["name"] for p in list_catalog_products()[:5]]
        return {
            "status": "error",
            "error_code": "PRODUCT_NOT_FOUND",
            "message": f"Product '{product_id_or_name}' not found.",
            "available_products": available,
        }

    unit_price = quantize_usd(product["price_decimal"])
    amount_cents = usd_to_cents(unit_price)
    sim_usdc_micros = usd_to_sim_usdc_micros(unit_price)
    stock = int(product["stock"])

    return {
        "status": "success",
        "product": {
            "id": product["id"],
            "name": product["name"],
            "category": product["category"],
            "price": f"${unit_price}",
            "unit_price": unit_price,
            "amount_cents": amount_cents,
            "sim_usdc_micros": sim_usdc_micros,
            "stock": stock,
            "stock_status": _stock_status_label(stock),
            "specs": product["specs"],
            "description": product["description"],
            "expected_restock": product.get("expected_restock"),
        },
    }


def check_stock(product_id: str, requested_qty: int = 1) -> dict[str, Any]:
    """
    Deterministic stock verification against SQLite inventory.
    Validates `requested_qty >= 1` and returns exact availability status and `expected_restock`.
    """
    if isinstance(requested_qty, bool) or not isinstance(requested_qty, int) or requested_qty < 1:
        return {
            "status": "error",
            "error_code": "INVALID_QUANTITY",
            "message": f"Requested quantity must be an integer >= 1 (got {requested_qty!r}).",
        }

    product = find_catalog_product(product_id)
    if product is None:
        return {
            "status": "error",
            "error_code": "PRODUCT_NOT_FOUND",
            "message": f"Product '{product_id}' not found.",
        }

    stock = int(product["stock"])
    status_label = _stock_status_label(stock)
    expected_restock = product.get("expected_restock")
    is_available = stock >= requested_qty and stock > 0

    if stock == 0:
        message = f"{product['name']} is currently out of stock."
        if expected_restock:
            message += f" Expected restock: {expected_restock}"
    elif not is_available:
        message = (
            f"{product['name']} has insufficient stock for {requested_qty} units "
            f"(only {stock} available)."
        )
    elif stock < 10:
        message = f"{product['name']} is in low stock ({stock} units). Order soon!"
    else:
        message = f"{product['name']} is in stock ({stock} units available)."

    return {
        "status": "success",
        "product_id": product["id"],
        "product_name": product["name"],
        "stock_count": stock,
        "requested_qty": requested_qty,
        "available": is_available,
        "stock_status": status_label,
        "expected_restock": expected_restock,
        "message": message,
    }


def calculate_quote(
    items: list[dict[str, Any]],
    discount_code: str | None = None,
    tax_jurisdiction: str = "US-STANDARD",
) -> dict[str, Any]:
    """
    Deterministic cart quote engine.
    - Looks up all unit prices and stock directly from SQLite.
    - Rejects any caller-supplied price overrides, invalid quantities, unknown SKUs,
      insufficient inventory, or unauthorized/expired discount codes.
    - Computes subtotal, discount_amount, taxable_amount, tax_amount, and total
      using `Decimal` (`ROUND_HALF_UP`) and returns integer `total_cents` and
      `total_sim_usdc_micros` (10^6 atomic units).
    """
    if not items or not isinstance(items, list):
        return {
            "status": "error",
            "error_code": "EMPTY_CART",
            "message": "Cart items list cannot be empty.",
        }

    # Validate tax jurisdiction first
    normalized_jurisdiction = (tax_jurisdiction or "US-STANDARD").strip().upper()
    if normalized_jurisdiction not in TAX_JURISDICTIONS:
        return {
            "status": "error",
            "error_code": "INVALID_TAX_JURISDICTION",
            "message": f"Unsupported tax jurisdiction '{tax_jurisdiction}'.",
            "supported_jurisdictions": sorted(TAX_JURISDICTIONS.keys()),
        }
    tax_rate = TAX_JURISDICTIONS[normalized_jurisdiction]

    # Validate discount code if provided
    normalized_discount_code: str | None = None
    discount_percent = Decimal("0.00")
    max_discount_cents = 0

    if discount_code is not None and str(discount_code).strip() != "":
        normalized_discount_code = str(discount_code).strip().upper()
        disc_record = get_discount_code_record(normalized_discount_code)
        if disc_record is None:
            return {
                "status": "error",
                "error_code": "INVALID_DISCOUNT_CODE",
                "message": f"Discount code '{discount_code}' is not allowlisted.",
            }

        expires_at = disc_record.get("expires_at")
        is_expired = bool(expires_at and str(expires_at) < date.today().isoformat())
        if not disc_record["active"] or is_expired:
            return {
                "status": "error",
                "error_code": "EXPIRED_DISCOUNT_CODE",
                "message": f"Discount code '{normalized_discount_code}' is expired or inactive.",
            }

        discount_percent = quantize_usd(disc_record["discount_percent"])
        if discount_percent < Decimal("0.00") or discount_percent > Decimal("100.00"):
            return {
                "status": "error",
                "error_code": "INVALID_DISCOUNT_CODE",
                "message": "Discount percentage out of valid bounds.",
            }
        max_discount_cents = int(disc_record["max_discount_cents"])

    # Aggregate quantities per canonical product_id to prevent split-line stock bypass
    aggregated_quantities: dict[str, int] = {}
    resolved_products: dict[str, dict[str, Any]] = {}
    line_items: list[QuoteLineItemModel] = []

    for raw_item in items:
        if not isinstance(raw_item, dict):
            return {
                "status": "error",
                "error_code": "INVALID_ITEM_FORMAT",
                "message": "Each cart item must be a dictionary with 'product_id' and 'quantity'.",
            }

        # Explicitly reject attempts to inject custom unit prices or discounts in item payloads
        if any(k in raw_item for k in ("unit_price", "price", "discount_percent", "discount")):
            return {
                "status": "error",
                "error_code": "UNAUTHORIZED_PRICE_OVERRIDE",
                "message": (
                    "Caller-supplied prices or discounts are forbidden; "
                    "all prices are resolved deterministically from the catalog."
                ),
            }

        identifier = (
            raw_item.get("product_id")
            or raw_item.get("id")
            or raw_item.get("product_name")
            or raw_item.get("name")
        )
        if not identifier or not str(identifier).strip():
            return {
                "status": "error",
                "error_code": "PRODUCT_NOT_FOUND",
                "message": "Each cart item must specify a non-empty 'product_id'.",
            }

        qty = raw_item.get("quantity", 1)
        if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
            return {
                "status": "error",
                "error_code": "INVALID_QUANTITY",
                "message": f"Item quantity must be an integer >= 1 (got {qty!r}).",
            }

        product = find_catalog_product(str(identifier))
        if product is None:
            return {
                "status": "error",
                "error_code": "PRODUCT_NOT_FOUND",
                "message": f"Product '{identifier}' not found in catalog.",
            }

        canonical_id = product["id"]
        resolved_products[canonical_id] = product
        new_total_qty = aggregated_quantities.get(canonical_id, 0) + qty
        stock = int(product["stock"])

        if stock == 0:
            return {
                "status": "error",
                "error_code": "OUT_OF_STOCK",
                "product_id": canonical_id,
                "product_name": product["name"],
                "expected_restock": product.get("expected_restock"),
                "message": f"Product '{product['name']}' is out of stock.",
            }

        if new_total_qty > stock:
            return {
                "status": "error",
                "error_code": "INSUFFICIENT_STOCK",
                "product_id": canonical_id,
                "product_name": product["name"],
                "available_stock": stock,
                "requested_quantity": new_total_qty,
                "message": (
                    f"Insufficient stock for '{product['name']}': "
                    f"requested {new_total_qty}, available {stock}."
                ),
            }

        aggregated_quantities[canonical_id] = new_total_qty

        unit_price = quantize_usd(product["price_decimal"])
        unit_cents = usd_to_cents(unit_price)
        unit_micros = usd_to_sim_usdc_micros(unit_price)
        line_sub = quantize_usd(unit_price * Decimal(qty))

        line_items.append(
            QuoteLineItemModel(
                product_id=canonical_id,
                product_name=product["name"],
                quantity=qty,
                unit_price=unit_price,
                unit_amount_cents=unit_cents,
                unit_sim_usdc_micros=unit_micros,
                line_subtotal=line_sub,
                line_subtotal_cents=usd_to_cents(line_sub),
                line_subtotal_sim_usdc_micros=usd_to_sim_usdc_micros(line_sub),
            )
        )

    subtotal = quantize_usd(sum((li.line_subtotal for li in line_items), Decimal("0.00")))

    if normalized_discount_code and discount_percent > Decimal("0.00"):
        raw_discount = quantize_usd(subtotal * (discount_percent / Decimal("100")))
        max_cap_usd = quantize_usd(Decimal(max_discount_cents) / CENTS_SCALE)
        discount_amount = min(raw_discount, max_cap_usd, subtotal)
    else:
        discount_amount = Decimal("0.00")

    taxable_amount = quantize_usd(subtotal - discount_amount)
    tax_amount = quantize_usd(taxable_amount * tax_rate)
    total = quantize_usd(taxable_amount + tax_amount)

    quote_model = QuoteCalculationModel(
        items=line_items,
        discount_code=normalized_discount_code,
        discount_percent=discount_percent,
        tax_jurisdiction=normalized_jurisdiction,
        tax_rate=tax_rate,
        subtotal=subtotal,
        subtotal_cents=usd_to_cents(subtotal),
        discount_amount=discount_amount,
        discount_amount_cents=usd_to_cents(discount_amount),
        taxable_amount=taxable_amount,
        taxable_amount_cents=usd_to_cents(taxable_amount),
        tax_amount=tax_amount,
        tax_amount_cents=usd_to_cents(tax_amount),
        total=total,
        total_cents=usd_to_cents(total),
        total_sim_usdc_micros=usd_to_sim_usdc_micros(total),
    )

    return quote_model.model_dump()
