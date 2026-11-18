"""
Deterministic SQLite Persistence Layer for Orders, Payment/Grant Evidence,
and Verifiable Human Escalation Support Tickets (`orders`, `order_evidence`,
and `support_tickets` tables).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.schemas import (
    GrantEvidence,
    OrderRecordContract,
    PurchaseEvidence,
    SupportTicketContract,
)

# Default SQLite database path (shared with chat_memory and catalog_db)
DB_PATH = Path(__file__).resolve().parent.parent.parent / "my_agent_data.db"

# Canonical reference orders & evidence envelopes covering all cross-repo scenarios
SEED_ORDERS: list[dict[str, Any]] = [
    {
        "order_id": "ORD-1001",
        "user_id": "user_alice",
        "items": [
            {
                "product_id": "prod-dell-xps-15",
                "product_name": "Dell XPS 15",
                "quantity": 1,
                "unit_amount_cents": 129900,
                "unit_sim_usdc_micros": 1299000000,
            }
        ],
        "total_cents": 129900,
        "total_sim_usdc_micros": 1299000000,
        "order_status": "fulfilled",
        "created_at": "2026-11-08T10:00:00Z",
        "purchase_evidence": {
            "evidence_id": "EV-PAY-1001",
            "order_id": "ORD-1001",
            "tx_hash": "0xabc1001def000000000000000000000000000000000000000000000000001001",
            "protocol": "x402",
            "amount_cents": 129900,
            "sim_usdc_micros": 1299000000,
            "settlement_status": "settled",
            "charge_count": 1,
            "authorized_by_mandate": True,
            "mandate_id": "MANDATE-KYA-1001",
            "recorded_at": "2026-11-08T10:00:05Z",
        },
        "grant_evidence": {
            "grant_id": "EV-GRT-1001",
            "order_id": "ORD-1001",
            "grant_status": "delivered",
            "tracking_code": "TRK-UPS-1001",
            "delivered_at": "2026-11-10T14:30:00Z",
            "return_window_days": 30,
            "return_eligible": True,
        },
    },
    {
        # Scenario: charged_not_delivered (settled payment, pending delivery grant)
        "order_id": "ORD-1002",
        "user_id": "user_bob",
        "items": [
            {
                "product_id": "prod-iphone-15-pro",
                "product_name": "iPhone 15 Pro",
                "quantity": 1,
                "unit_amount_cents": 99900,
                "unit_sim_usdc_micros": 999000000,
            }
        ],
        "total_cents": 99900,
        "total_sim_usdc_micros": 999000000,
        "order_status": "processing",
        "created_at": "2026-11-11T12:00:00Z",
        "purchase_evidence": {
            "evidence_id": "EV-PAY-1002",
            "order_id": "ORD-1002",
            "tx_hash": "0xabc1002def000000000000000000000000000000000000000000000000001002",
            "protocol": "x402",
            "amount_cents": 99900,
            "sim_usdc_micros": 999000000,
            "settlement_status": "settled",
            "charge_count": 1,
            "authorized_by_mandate": True,
            "mandate_id": "MANDATE-KYA-1002",
            "recorded_at": "2026-11-11T12:00:04Z",
        },
        "grant_evidence": {
            "grant_id": "EV-GRT-1002",
            "order_id": "ORD-1002",
            "grant_status": "pending",
            "tracking_code": None,
            "delivered_at": None,
            "return_window_days": 30,
            "return_eligible": False,
        },
    },
    {
        # Scenario: duplicate_charge (settled payment with charge_count=2)
        "order_id": "ORD-1003",
        "user_id": "user_carol",
        "items": [
            {
                "product_id": "prod-logitech-mx-master-3s",
                "product_name": "Logitech MX Master 3S",
                "quantity": 1,
                "unit_amount_cents": 9900,
                "unit_sim_usdc_micros": 99000000,
            }
        ],
        "total_cents": 9900,
        "total_sim_usdc_micros": 99000000,
        "order_status": "fulfilled",
        "created_at": "2026-11-12T08:00:00Z",
        "purchase_evidence": {
            "evidence_id": "EV-PAY-1003",
            "order_id": "ORD-1003",
            "tx_hash": "0xabc1003def000000000000000000000000000000000000000000000000001003",
            "protocol": "x402",
            "amount_cents": 9900,
            "sim_usdc_micros": 99000000,
            "settlement_status": "settled",
            "charge_count": 2,
            "authorized_by_mandate": True,
            "mandate_id": "MANDATE-KYA-1003",
            "recorded_at": "2026-11-12T08:00:03Z",
        },
        "grant_evidence": {
            "grant_id": "EV-GRT-1003",
            "order_id": "ORD-1003",
            "grant_status": "delivered",
            "tracking_code": "TRK-FEDEX-1003",
            "delivered_at": "2026-11-14T16:15:00Z",
            "return_window_days": 30,
            "return_eligible": True,
        },
    },
    {
        # Scenario: unauthorized_purchase (settled payment without KYA mandate authorization)
        "order_id": "ORD-1004",
        "user_id": "user_dave",
        "items": [
            {
                "product_id": "prod-iphone-15-pro",
                "product_name": "iPhone 15 Pro",
                "quantity": 1,
                "unit_amount_cents": 99900,
                "unit_sim_usdc_micros": 999000000,
            }
        ],
        "total_cents": 99900,
        "total_sim_usdc_micros": 999000000,
        "order_status": "disputed",
        "created_at": "2026-11-13T18:20:00Z",
        "purchase_evidence": {
            "evidence_id": "EV-PAY-1004",
            "order_id": "ORD-1004",
            "tx_hash": "0xabc1004def000000000000000000000000000000000000000000000000001004",
            "protocol": "x402",
            "amount_cents": 99900,
            "sim_usdc_micros": 999000000,
            "settlement_status": "settled",
            "charge_count": 1,
            "authorized_by_mandate": False,
            "mandate_id": None,
            "recorded_at": "2026-11-13T18:20:02Z",
        },
        "grant_evidence": {
            "grant_id": "EV-GRT-1004",
            "order_id": "ORD-1004",
            "grant_status": "shipped",
            "tracking_code": "TRK-DHL-1004",
            "delivered_at": None,
            "return_window_days": 30,
            "return_eligible": False,
        },
    },
    {
        # Scenario: charged_but_denied (settled payment, fulfillment/access grant denied)
        "order_id": "ORD-1005",
        "user_id": "user_erin",
        "items": [
            {
                "product_id": "prod-sony-wh1000xm5",
                "product_name": "Sony WH-1000XM5",
                "quantity": 1,
                "unit_amount_cents": 39900,
                "unit_sim_usdc_micros": 399000000,
            }
        ],
        "total_cents": 39900,
        "total_sim_usdc_micros": 399000000,
        "order_status": "grant_denied",
        "created_at": "2026-11-14T09:45:00Z",
        "purchase_evidence": {
            "evidence_id": "EV-PAY-1005",
            "order_id": "ORD-1005",
            "tx_hash": "0xabc1005def000000000000000000000000000000000000000000000000001005",
            "protocol": "x402",
            "amount_cents": 39900,
            "sim_usdc_micros": 399000000,
            "settlement_status": "settled",
            "charge_count": 1,
            "authorized_by_mandate": True,
            "mandate_id": "MANDATE-KYA-1005",
            "recorded_at": "2026-11-14T09:45:03Z",
        },
        "grant_evidence": {
            "grant_id": "EV-GRT-1005",
            "order_id": "ORD-1005",
            "grant_status": "denied",
            "tracking_code": None,
            "delivered_at": None,
            "return_window_days": 30,
            "return_eligible": False,
        },
    },
    {
        # Scenario: unverifiable (order exists without settlement or grant evidence records)
        "order_id": "ORD-1006",
        "user_id": "user_frank",
        "items": [
            {
                "product_id": "prod-logitech-mx-master-3s",
                "product_name": "Logitech MX Master 3S",
                "quantity": 1,
                "unit_amount_cents": 9900,
                "unit_sim_usdc_micros": 99000000,
            }
        ],
        "total_cents": 9900,
        "total_sim_usdc_micros": 99000000,
        "order_status": "pending_verification",
        "created_at": "2026-11-15T11:10:00Z",
        "purchase_evidence": None,
        "grant_evidence": None,
    },
]


def init_orders_db(db_path: Path | str | None = None) -> None:
    """Create and idempotently seed the `orders`, `order_evidence`, and `support_tickets` tables."""
    target_db = Path(db_path) if db_path is not None else DB_PATH
    conn = sqlite3.connect(target_db)
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                items_json TEXT NOT NULL,
                total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
                total_sim_usdc_micros INTEGER NOT NULL CHECK(total_sim_usdc_micros >= 0),
                order_status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_evidence (
                order_id TEXT PRIMARY KEY,
                purchase_evidence_json TEXT,
                grant_evidence_json TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                ticket_status TEXT NOT NULL,
                reason TEXT NOT NULL,
                message TEXT NOT NULL,
                session_id TEXT,
                user_id TEXT NOT NULL,
                order_id TEXT,
                claim_type TEXT,
                verification_verdict TEXT,
                reason_code TEXT,
                priority TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        for entry in SEED_ORDERS:
            cursor.execute(
                """
                INSERT OR IGNORE INTO orders (
                    order_id, user_id, items_json, total_cents,
                    total_sim_usdc_micros, order_status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["order_id"],
                    entry["user_id"],
                    json.dumps(entry["items"]),
                    int(entry["total_cents"]),
                    int(entry["total_sim_usdc_micros"]),
                    entry["order_status"],
                    entry["created_at"],
                ),
            )

            if entry["purchase_evidence"] is not None or entry["grant_evidence"] is not None:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO order_evidence (
                        order_id, purchase_evidence_json, grant_evidence_json
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        entry["order_id"],
                        json.dumps(entry["purchase_evidence"])
                        if entry["purchase_evidence"] is not None
                        else None,
                        json.dumps(entry["grant_evidence"])
                        if entry["grant_evidence"] is not None
                        else None,
                    ),
                )

        conn.commit()
    finally:
        conn.close()


def get_order_record(order_id: str) -> OrderRecordContract | None:
    """Retrieve a validated `OrderRecordContract` (with evidence) from SQLite."""
    if not order_id or not str(order_id).strip():
        return None

    normalized_id = str(order_id).strip().upper()
    init_orders_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT o.order_id, o.user_id, o.items_json, o.total_cents,
                   o.total_sim_usdc_micros, o.order_status, o.created_at,
                   e.purchase_evidence_json, e.grant_evidence_json
            FROM orders o
            LEFT JOIN order_evidence e ON o.order_id = e.order_id
            WHERE o.order_id = ?
            """,
            (normalized_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        (
            ord_id,
            user_id,
            items_json,
            total_cents,
            total_sim_usdc_micros,
            order_status,
            created_at,
            purchase_json,
            grant_json,
        ) = row

        purchase_ev = PurchaseEvidence(**json.loads(purchase_json)) if purchase_json else None
        grant_ev = GrantEvidence(**json.loads(grant_json)) if grant_json else None

        return OrderRecordContract(
            order_id=ord_id,
            user_id=user_id,
            items=json.loads(items_json),
            total_cents=int(total_cents),
            total_sim_usdc_micros=int(total_sim_usdc_micros),
            order_status=order_status,
            created_at=created_at,
            purchase_evidence=purchase_ev,
            grant_evidence=grant_ev,
        )
    finally:
        conn.close()


def save_support_ticket(ticket: SupportTicketContract) -> SupportTicketContract:
    """Persist a `SupportTicketContract` row into SQLite `support_tickets`."""
    init_orders_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO support_tickets (
                ticket_id, status, ticket_status, reason, message,
                session_id, user_id, order_id, claim_type,
                verification_verdict, reason_code, priority, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket.ticket_id,
                ticket.status,
                ticket.ticket_status,
                ticket.reason,
                ticket.message,
                ticket.session_id,
                ticket.user_id,
                ticket.order_id,
                ticket.claim_type,
                ticket.verification_verdict,
                ticket.reason_code,
                ticket.priority,
                ticket.created_at,
            ),
        )
        conn.commit()
        return ticket
    finally:
        conn.close()


def get_support_ticket(ticket_id: str) -> SupportTicketContract | None:
    """Look up a persisted `SupportTicketContract` by `ticket_id`."""
    if not ticket_id or not str(ticket_id).strip():
        return None

    normalized_id = str(ticket_id).strip().upper()
    init_orders_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ticket_id, status, ticket_status, reason, message,
                   session_id, user_id, order_id, claim_type,
                   verification_verdict, reason_code, priority, created_at
            FROM support_tickets
            WHERE UPPER(ticket_id) = ?
            """,
            (normalized_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return SupportTicketContract(
            ticket_id=row[0],
            status=row[1],
            ticket_status=row[2],
            reason=row[3],
            message=row[4],
            session_id=row[5],
            user_id=row[6],
            order_id=row[7],
            claim_type=row[8],
            verification_verdict=row[9],
            reason_code=row[10],
            priority=row[11],
            created_at=row[12],
        )
    finally:
        conn.close()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


# Ensure tables exist on import
init_orders_db()
