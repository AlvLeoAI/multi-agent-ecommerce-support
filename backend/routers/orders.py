"""
Orders, Evidence Verification & Support Tickets API Router (`/api/v1/orders`, `/api/v1/tickets`).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from database.orders_db import get_order_record, get_support_ticket
from models.schemas import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    OrderRecordContract,
    SupportTicketContract,
)
from services.order_verification import verify_order_claim

router = APIRouter(prefix="/api/v1", tags=["orders-and-tickets"])


@router.get("/orders/{order_id}", response_model=OrderRecordContract)
async def get_order_endpoint(order_id: str) -> OrderRecordContract:
    """Retrieve a deterministic OrderRecordContract (with x402 payment and grant evidence)."""
    record = get_order_record(order_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Order '{order_id}' not found",
        )
    return record


@router.post(
    "/orders/{order_id}/verify-claim",
    response_model=ClaimVerificationResult,
)
async def verify_order_claim_endpoint(
    order_id: str,
    payload: ClaimVerificationRequest,
) -> ClaimVerificationResult:
    """
    Deterministically evaluate a dispute claim against SQLite PurchaseEvidence and GrantEvidence.
    """
    result = verify_order_claim(order_id=order_id, claim_type=payload.claim_type)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Invalid claim verification request"),
        )
    return ClaimVerificationResult(**result)


@router.get("/tickets/{ticket_id}", response_model=SupportTicketContract)
async def get_ticket_endpoint(ticket_id: str) -> SupportTicketContract:
    """Retrieve a persisted human escalation support ticket from SQLite."""
    ticket = get_support_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail=f"Support ticket '{ticket_id}' not found",
        )
    return ticket
