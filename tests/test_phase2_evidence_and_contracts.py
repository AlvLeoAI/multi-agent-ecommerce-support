"""
Phase 2 Typed Output Contracts & Order/Payment Evidence Integration Test Suite.

Covers:
1. All 4 confirmed claim types aligned with `Agentic-Payments-Lab` (`x402`, `sim_usdc_micros`,
   KYA `authorized_by_mandate`, `charge_count`) and `ticket-prioritization-api`
   (`charged_not_delivered`, `duplicate_charge`, `unauthorized_purchase`, `charged_but_denied`).
2. Contradicted claim scenarios against clean fulfilled order `ORD-1001`.
3. Unverifiable scenarios (`ORD-1006` missing evidence -> `MISSING_EVIDENCE`, and
   nonexistent order `ORD-9999` -> `ORDER_NOT_FOUND`).
4. SQLite persistence and retrieval of escalation tickets via `escalate_to_human_support`
   and `GET /api/v1/tickets/{ticket_id}`, both standalone and linked to order claims.
5. FastAPI contracts for `GET /api/v1/orders/{order_id}` and
   `POST /api/v1/orders/{order_id}/verify-claim`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main as backend_main
from routers import chat as chat_router
from services.order_verification import (
    create_escalation_ticket,
    lookup_order_status,
    verify_order_claim,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(backend_main.app)


# ============================================================================
# 1. CONFIRMED CLAIM VERIFICATION SCENARIOS (CROSS-REPO ALIGNMENT)
# ============================================================================


@pytest.mark.parametrize(
    ("order_id", "claim_type", "expected_reason_code", "expected_priority", "expected_micros"),
    [
        (
            "ORD-1002",
            "charged_not_delivered",
            "SETTLED_WITHOUT_DELIVERY_GRANT",
            "high",
            999_000_000,
        ),
        (
            "ORD-1003",
            "duplicate_charge",
            "MULTIPLE_SETTLED_CHARGES",
            "high",
            99_000_000,
        ),
        (
            "ORD-1004",
            "unauthorized_purchase",
            "MISSING_KYA_MANDATE_AUTHORIZATION",
            "critical",
            999_000_000,
        ),
        (
            "ORD-1005",
            "charged_but_denied",
            "SETTLED_BUT_ACCESS_GRANT_DENIED",
            "high",
            399_000_000,
        ),
    ],
)
def test_confirmed_claims_against_purchase_and_grant_evidence(
    order_id: str,
    claim_type: str,
    expected_reason_code: str,
    expected_priority: str,
    expected_micros: int,
) -> None:
    """
    Verify all 4 canonical claim types produce deterministic `confirmed` verdicts,
    exact `reason_code`, `recommended_priority`, and `sim_usdc_micros` (10^6).
    """
    res = verify_order_claim(order_id=order_id, claim_type=claim_type)
    assert res["status"] == "success"
    assert res["order_id"] == order_id
    assert res["claim_type"] == claim_type
    assert res["verdict"] == "confirmed"
    assert res["reason_code"] == expected_reason_code
    assert res["recommended_priority"] == expected_priority
    assert res["sim_usdc_micros"] == expected_micros
    assert res["amount_cents"] == expected_micros // 10_000


# ============================================================================
# 2. CONTRADICTED CLAIM SCENARIOS (CLEAN FULFILLED ORDER ORD-1001)
# ============================================================================


@pytest.mark.parametrize(
    ("claim_type", "expected_reason_code"),
    [
        ("charged_not_delivered", "DELIVERY_GRANT_CONFIRMED"),
        ("duplicate_charge", "SINGLE_CHARGE_VERIFIED"),
        ("unauthorized_purchase", "VALID_MANDATE_AUTHORIZATION"),
        ("charged_but_denied", "GRANT_NOT_DENIED"),
    ],
)
def test_contradicted_claims_on_fulfilled_order_ord_1001(
    claim_type: str,
    expected_reason_code: str,
) -> None:
    """
    Verify false customer claims against clean fulfilled order `ORD-1001`
    deterministically yield `verdict == 'contradicted'` and `recommended_priority == 'low'`.
    """
    res = verify_order_claim(order_id="ORD-1001", claim_type=claim_type)
    assert res["status"] == "success"
    assert res["order_id"] == "ORD-1001"
    assert res["verdict"] == "contradicted"
    assert res["reason_code"] == expected_reason_code
    assert res["recommended_priority"] == "low"
    assert res["amount_cents"] == 129_900
    assert res["sim_usdc_micros"] == 1_299_000_000


# ============================================================================
# 3. UNVERIFIABLE & INVALID CLAIM SCENARIOS
# ============================================================================


def test_unverifiable_claims_for_missing_evidence_and_unknown_order() -> None:
    """
    Verify `ORD-1006` (missing PurchaseEvidence/GrantEvidence) yields `unverifiable`
    with `MISSING_EVIDENCE`, and nonexistent `ORD-9999` yields `unverifiable` with
    `ORDER_NOT_FOUND`.
    """
    missing_ev = verify_order_claim(order_id="ORD-1006", claim_type="charged_not_delivered")
    assert missing_ev["status"] == "success"
    assert missing_ev["verdict"] == "unverifiable"
    assert missing_ev["reason_code"] == "MISSING_EVIDENCE"
    assert missing_ev["recommended_priority"] == "high"
    assert missing_ev["amount_cents"] == 9_900
    assert missing_ev["sim_usdc_micros"] == 99_000_000

    unknown_ord = verify_order_claim(order_id="ORD-9999", claim_type="duplicate_charge")
    assert unknown_ord["status"] == "success"
    assert unknown_ord["verdict"] == "unverifiable"
    assert unknown_ord["reason_code"] == "ORDER_NOT_FOUND"
    assert unknown_ord["recommended_priority"] == "high"
    assert unknown_ord["amount_cents"] is None
    assert unknown_ord["sim_usdc_micros"] is None

    invalid_claim = verify_order_claim(order_id="ORD-1001", claim_type="made_up_claim")
    assert invalid_claim["status"] == "error"
    assert invalid_claim["error_code"] == "INVALID_CLAIM_TYPE"


# ============================================================================
# 4. PERSISTENT SUPPORT TICKET ESCALATION & EVIDENCE LINKING (RESOLVES F-05)
# ============================================================================


def test_escalation_ticket_linked_to_order_claim_and_retrieved_via_api(
    client: TestClient,
) -> None:
    """
    Verify `escalate_to_human_support` / `create_escalation_ticket` persists tickets
    with automatic claim verification and exposes them via `GET /api/v1/tickets/{ticket_id}`.
    """
    ticket_data = create_escalation_ticket(
        reason="Customer reports unauthorized charge on ORD-1004",
        session_id="sess_dispute_1004",
        user_id="user_dave",
        order_id="ord-1004",
        claim_type="unauthorized_purchase",
    )

    assert ticket_data["status"] == "success"
    ticket_id = ticket_data["ticket_id"]
    assert ticket_id.startswith("TICKET-")
    assert ticket_data["order_id"] == "ORD-1004"
    assert ticket_data["claim_type"] == "unauthorized_purchase"
    assert ticket_data["verification_verdict"] == "confirmed"
    assert ticket_data["reason_code"] == "MISSING_KYA_MANDATE_AUTHORIZATION"
    assert ticket_data["priority"] == "critical"

    # Fetch via FastAPI endpoint
    get_resp = client.get(f"/api/v1/tickets/{ticket_id}")
    assert get_resp.status_code == 200
    persisted = get_resp.json()
    assert persisted["ticket_id"] == ticket_id
    assert persisted["verification_verdict"] == "confirmed"
    assert persisted["priority"] == "critical"

    # 404 for unknown ticket
    missing_resp = client.get("/api/v1/tickets/TICKET-000000")
    assert missing_resp.status_code == 404


# ============================================================================
# 5. FASTAPI ORDER & CLAIM VERIFICATION ENDPOINT CONTRACTS & AGENT TOOLS
# ============================================================================


def test_order_lookup_and_verify_claim_api_endpoints(client: TestClient) -> None:
    """
    Verify `GET /api/v1/orders/{order_id}` and `POST /api/v1/orders/{order_id}/verify-claim`.
    """
    ord_resp = client.get("/api/v1/orders/ORD-1001")
    assert ord_resp.status_code == 200
    ord_data = ord_resp.json()
    assert ord_data["order_id"] == "ORD-1001"
    assert ord_data["total_cents"] == 129_900
    assert ord_data["total_sim_usdc_micros"] == 1_299_000_000
    assert ord_data["purchase_evidence"]["protocol"] == "x402"
    assert ord_data["purchase_evidence"]["authorized_by_mandate"] is True
    assert ord_data["grant_evidence"]["grant_status"] == "delivered"
    assert ord_data["grant_evidence"]["return_eligible"] is True

    not_found_ord = client.get("/api/v1/orders/ORD-DOES-NOT-EXIST")
    assert not_found_ord.status_code == 404

    verify_resp = client.post(
        "/api/v1/orders/ORD-1003/verify-claim",
        json={"claim_type": "duplicate_charge"},
    )
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["verdict"] == "confirmed"
    assert verify_data["reason_code"] == "MULTIPLE_SETTLED_CHARGES"
    assert verify_data["recommended_priority"] == "high"

    bad_claim_resp = client.post(
        "/api/v1/orders/ORD-1003/verify-claim",
        json={"claim_type": "invalid_claim_kind"},
    )
    assert bad_claim_resp.status_code == 400


def test_agents_register_deterministic_order_and_claim_tools() -> None:
    """Verify `general_agent` and `order_support_agent` expose deterministic order tools."""
    lookup_res = lookup_order_status("ORD-9999")
    assert lookup_res["status"] == "error"
    assert lookup_res["error_code"] == "ORDER_NOT_FOUND"

    for agent in (chat_router.general_agent, chat_router.order_support_agent):
        tool_names = {getattr(t, "name", getattr(t, "__name__", str(t))) for t in agent.tools or []}
        assert {
            "lookup_order_status",
            "verify_order_claim",
            "escalate_to_human_support",
        }.issubset(tool_names)
