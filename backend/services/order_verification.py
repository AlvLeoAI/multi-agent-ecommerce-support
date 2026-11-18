"""
Deterministic Order Status, Return Eligibility & Payment/Fulfillment Claim Verification
Service (`backend/services/order_verification.py`).

Aligns with:
- `Agentic-Payments-Lab`: `PurchaseEvidence` (x402 protocol, `amount_cents`, `sim_usdc_micros`,
  KYA `authorized_by_mandate`, `charge_count`) & `GrantEvidence`.
- `ticket-prioritization-api`: Deterministic verification verdicts (`confirmed`,
  `contradicted`, `unverifiable`) and priority routing (`critical`, `high`, `medium`, `low`).
"""

from __future__ import annotations

import uuid
from typing import Any, get_args

from database.orders_db import (
    get_order_record,
    get_support_ticket,
    save_support_ticket,
    utc_now_iso,
)
from models.schemas import (
    ClaimType,
    ClaimVerificationResult,
    PriorityLevel,
    SupportTicketContract,
    VerificationVerdict,
)

VALID_CLAIM_TYPES: set[str] = set(get_args(ClaimType))


def lookup_order_status(order_id: str) -> dict[str, Any]:
    """
    Deterministically look up an order, its x402 payment evidence, fulfillment grant status,
    and return eligibility from SQLite.
    """
    raw_id = str(order_id if order_id is not None else "").strip()
    record = get_order_record(raw_id)
    if record is None:
        return {
            "status": "error",
            "error_code": "ORDER_NOT_FOUND",
            "message": f"Order '{order_id}' not found.",
        }

    data = record.model_dump()
    data["status"] = "success"
    return data


def verify_order_claim(order_id: str, claim_type: str) -> dict[str, Any]:
    """
    Deterministically evaluate a customer dispute claim (`charged_not_delivered`,
    `duplicate_charge`, `unauthorized_purchase`, `charged_but_denied`) against
    SQLite `PurchaseEvidence` and `GrantEvidence`.
    """
    normalized_claim = str(claim_type if claim_type is not None else "").strip().lower()
    if normalized_claim not in VALID_CLAIM_TYPES:
        return {
            "status": "error",
            "error_code": "INVALID_CLAIM_TYPE",
            "message": f"Unsupported claim_type '{claim_type}'.",
            "supported_claim_types": sorted(VALID_CLAIM_TYPES),
        }

    normalized_order_id = str(order_id if order_id is not None else "").strip().upper()
    record = get_order_record(normalized_order_id)

    if record is None:
        result = ClaimVerificationResult(
            order_id=normalized_order_id or "UNKNOWN",
            claim_type=normalized_claim,  # type: ignore[arg-type]
            verdict="unverifiable",
            reason_code="ORDER_NOT_FOUND",
            evidence_summary=f"Order '{normalized_order_id}' does not exist in order ledger.",
            recommended_priority="high",
            amount_cents=None,
            sim_usdc_micros=None,
        )
        return result.model_dump()

    purchase = record.purchase_evidence
    grant = record.grant_evidence

    if purchase is None or grant is None:
        result = ClaimVerificationResult(
            order_id=record.order_id,
            claim_type=normalized_claim,  # type: ignore[arg-type]
            verdict="unverifiable",
            reason_code="MISSING_EVIDENCE",
            evidence_summary=(
                f"Order '{record.order_id}' is missing settlement or fulfillment grant evidence."
            ),
            recommended_priority="high",
            amount_cents=record.total_cents,
            sim_usdc_micros=record.total_sim_usdc_micros,
        )
        return result.model_dump()

    verdict: VerificationVerdict
    reason_code: str
    summary: str
    priority: PriorityLevel

    if normalized_claim == "charged_not_delivered":
        if purchase.settlement_status == "settled" and grant.grant_status in (
            "pending",
            "denied",
            "revoked",
        ):
            verdict = "confirmed"
            reason_code = "SETTLED_WITHOUT_DELIVERY_GRANT"
            summary = (
                f"Payment {purchase.evidence_id} settled ({purchase.sim_usdc_micros} SIM-USDC micros) "
                f"but grant {grant.grant_id} status is '{grant.grant_status}'."
            )
            priority = "high"
        elif grant.grant_status == "delivered":
            verdict = "contradicted"
            reason_code = "DELIVERY_GRANT_CONFIRMED"
            summary = (
                f"Grant {grant.grant_id} confirms delivery at {grant.delivered_at} "
                f"(tracking: {grant.tracking_code})."
            )
            priority = "low"
        else:
            verdict = "unverifiable"
            reason_code = "INCONCLUSIVE_DELIVERY_STATE"
            summary = (
                f"Settlement status is '{purchase.settlement_status}' and grant status "
                f"is '{grant.grant_status}'."
            )
            priority = "medium"

    elif normalized_claim == "duplicate_charge":
        if purchase.settlement_status == "settled" and purchase.charge_count > 1:
            verdict = "confirmed"
            reason_code = "MULTIPLE_SETTLED_CHARGES"
            summary = (
                f"Purchase evidence {purchase.evidence_id} records {purchase.charge_count} "
                f"settled charges for order {record.order_id}."
            )
            priority = "high"
        else:
            verdict = "contradicted"
            reason_code = "SINGLE_CHARGE_VERIFIED"
            summary = (
                f"Purchase evidence {purchase.evidence_id} verifies charge_count="
                f"{purchase.charge_count} with status '{purchase.settlement_status}'."
            )
            priority = "low"

    elif normalized_claim == "unauthorized_purchase":
        if purchase.settlement_status == "settled" and not purchase.authorized_by_mandate:
            verdict = "confirmed"
            reason_code = "MISSING_KYA_MANDATE_AUTHORIZATION"
            summary = (
                f"Purchase {purchase.evidence_id} settled without a valid KYA mandate "
                f"(authorized_by_mandate=False)."
            )
            priority = "critical"
        elif purchase.authorized_by_mandate:
            verdict = "contradicted"
            reason_code = "VALID_MANDATE_AUTHORIZATION"
            summary = (
                f"Purchase {purchase.evidence_id} was authorized by mandate "
                f"'{purchase.mandate_id}'."
            )
            priority = "low"
        else:
            verdict = "unverifiable"
            reason_code = "UNSETTLED_AUTHORIZATION_STATE"
            summary = f"Settlement status is '{purchase.settlement_status}'."
            priority = "medium"

    else:  # charged_but_denied
        if purchase.settlement_status == "settled" and grant.grant_status in (
            "denied",
            "revoked",
        ):
            verdict = "confirmed"
            reason_code = "SETTLED_BUT_ACCESS_GRANT_DENIED"
            summary = (
                f"Payment {purchase.evidence_id} settled ({purchase.amount_cents} cents) "
                f"while fulfillment grant {grant.grant_id} was '{grant.grant_status}'."
            )
            priority = "high"
        else:
            verdict = "contradicted"
            reason_code = "GRANT_NOT_DENIED"
            summary = (
                f"Grant {grant.grant_id} status is '{grant.grant_status}' (not denied or revoked)."
            )
            priority = "low"

    result = ClaimVerificationResult(
        order_id=record.order_id,
        claim_type=normalized_claim,  # type: ignore[arg-type]
        verdict=verdict,
        reason_code=reason_code,
        evidence_summary=summary,
        recommended_priority=priority,
        amount_cents=purchase.amount_cents,
        sim_usdc_micros=purchase.sim_usdc_micros,
    )
    return result.model_dump()


def create_escalation_ticket(
    reason: str,
    session_id: str | None = None,
    user_id: str = "guest",
    order_id: str | None = None,
    claim_type: str | None = None,
) -> dict[str, Any]:
    """
    Create and durably persist a `SupportTicketContract` in SQLite (`support_tickets`).
    When `order_id` and `claim_type` are supplied, deterministically runs `verify_order_claim`
    and attaches the resulting verdict, reason_code, and priority to the persisted ticket.
    """
    ticket_id = f"TICKET-{uuid.uuid4().hex[:6]}"
    verification_verdict: str | None = None
    reason_code: str | None = None
    priority = "medium"
    raw_order = str(order_id if order_id is not None else "").strip().upper()
    raw_claim = str(claim_type if claim_type is not None else "").strip().lower()
    normalized_order_id = raw_order if raw_order else None
    normalized_claim = raw_claim if raw_claim else None

    if normalized_order_id and normalized_claim:
        verification = verify_order_claim(normalized_order_id, normalized_claim)
        if verification.get("status") == "success":
            verification_verdict = verification["verdict"]
            reason_code = verification["reason_code"]
            priority = verification["recommended_priority"]
        else:
            verification_verdict = "unverifiable"
            reason_code = verification.get("error_code", "INVALID_CLAIM_TYPE")
            priority = "high"

    ticket = SupportTicketContract(
        ticket_id=ticket_id,
        status="success",
        ticket_status="open",
        reason=str(reason),
        message="A human support agent will contact you shortly.",
        session_id=session_id,
        user_id=str(user_id or "guest"),
        order_id=normalized_order_id,
        claim_type=normalized_claim,
        verification_verdict=verification_verdict,
        reason_code=reason_code,
        priority=priority,
        created_at=utc_now_iso(),
    )
    save_support_ticket(ticket)
    return ticket.model_dump()


def lookup_support_ticket(ticket_id: str) -> dict[str, Any] | None:
    """Retrieve a persisted support ticket dictionary from SQLite."""
    ticket = get_support_ticket(ticket_id)
    return ticket.model_dump() if ticket is not None else None
