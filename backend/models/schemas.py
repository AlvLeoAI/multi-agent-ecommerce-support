"""
Pydantic models for API request/response validation and deterministic
Order, Payment Evidence (`Agentic-Payments-Lab`), and Claim Verification
(`ticket-prioritization-api`) contracts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ========== MESSAGE MODELS ==========


class ChatMessage(BaseModel):
    """Single chat message."""

    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: str | None = Field(None, description="ISO timestamp")


class ChatRequest(BaseModel):
    """Request to send a message to the support agent."""

    message: str = Field(..., description="User's message", min_length=1)
    user_id: str = Field(default="guest", description="User identifier")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Response from the support agent."""

    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


# ========== PRODUCT MODELS ==========


class ProductSpecs(BaseModel):
    """Product specifications (flexible schema)."""

    model_config = ConfigDict(extra="allow")


class Product(BaseModel):
    """Product information."""

    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    price: float = Field(..., description="Product price")
    stock: int = Field(..., description="Stock quantity")
    specs: dict[str, Any] = Field(..., description="Product specifications")
    description: str = Field(..., description="Product description")
    tags: list[str] = Field(default=[], description="Product tags")
    expected_restock: str | None = Field(None, description="Expected restock date")


class ProductSearchRequest(BaseModel):
    """Request to search products."""

    category: str | None = Field(None, description="Filter by category")
    max_price: float | None = Field(None, description="Maximum price")
    min_stock: int = Field(default=1, description="Minimum stock required")
    tags: list[str] | None = Field(None, description="Filter by tags")


class ProductSearchResponse(BaseModel):
    """Response with search results."""

    count: int = Field(..., description="Number of products found")
    products: list[dict[str, Any]] = Field(..., description="List of products")


# ========== METRICS MODELS ==========


class MetricsResponse(BaseModel):
    """Support metrics and statistics."""

    total_conversations: int = Field(..., description="Total conversation count")
    total_messages: int = Field(..., description="Total messages exchanged")
    avg_response_time: float = Field(..., description="Average response time (seconds)")
    top_products: list[dict[str, Any]] = Field(..., description="Most queried products")
    active_sessions: int = Field(..., description="Currently active sessions")


# ========== MEMORY MODELS ==========


class CustomerMemory(BaseModel):
    """Customer preferences and memory."""

    user_id: str = Field(..., description="User identifier")
    preferences: dict[str, Any] = Field(default={}, description="Customer preferences")
    past_queries: list[str] = Field(default=[], description="Recent queries")
    recommended_products: list[str] = Field(default=[], description="Previously recommended products")


# ========== PHASE 2: ORDER, EVIDENCE & CLAIM VERIFICATION CONTRACTS ==========

ClaimType = Literal[
    "charged_not_delivered",
    "duplicate_charge",
    "unauthorized_purchase",
    "charged_but_denied",
]

VerificationVerdict = Literal["confirmed", "contradicted", "unverifiable"]

PriorityLevel = Literal["critical", "high", "medium", "low"]


class PurchaseEvidence(BaseModel):
    """
    Deterministic payment settlement evidence envelope aligned with `Agentic-Payments-Lab`.
    Stores both USD cents (10^2) and simulated USDC atomic units (10^6).
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(..., description="Unique purchase evidence identifier")
    order_id: str = Field(..., description="Canonical order identifier")
    tx_hash: str = Field(..., description="Settlement transaction hash")
    protocol: str = Field(default="x402", description="Payment settlement protocol")
    amount_cents: int = Field(..., ge=0, description="Settled amount in USD cents (10^2)")
    sim_usdc_micros: int = Field(
        ..., ge=0, description="Settled amount in SIM-USDC micro-units (10^6)"
    )
    settlement_status: Literal["settled", "pending", "failed", "refunded"] = Field(
        ..., description="On-chain / payment gateway settlement status"
    )
    charge_count: int = Field(..., ge=0, description="Number of settled charges recorded")
    authorized_by_mandate: bool = Field(
        ..., description="Whether purchase was authorized by a valid KYA mandate"
    )
    mandate_id: str | None = Field(default=None, description="KYA Mandate ID if authorized")
    recorded_at: str = Field(..., description="ISO-8601 timestamp when settlement was recorded")


class GrantEvidence(BaseModel):
    """
    Deterministic fulfillment and access grant evidence envelope.
    """

    model_config = ConfigDict(extra="forbid")

    grant_id: str = Field(..., description="Unique fulfillment/grant identifier")
    order_id: str = Field(..., description="Canonical order identifier")
    grant_status: Literal["delivered", "shipped", "pending", "denied", "revoked"] = Field(
        ..., description="Current fulfillment or entitlement grant status"
    )
    tracking_code: str | None = Field(default=None, description="Carrier tracking code")
    delivered_at: str | None = Field(default=None, description="ISO-8601 delivery timestamp")
    return_window_days: int = Field(default=30, ge=0, description="Return window in days")
    return_eligible: bool = Field(..., description="Deterministic return policy eligibility")


class OrderRecordContract(BaseModel):
    """
    Complete order contract combining order items, dual atomic amounts,
    `PurchaseEvidence`, and `GrantEvidence`.
    """

    model_config = ConfigDict(extra="forbid")

    order_id: str
    user_id: str
    items: list[dict[str, Any]]
    total_cents: int = Field(..., ge=0)
    total_sim_usdc_micros: int = Field(..., ge=0)
    order_status: str
    created_at: str
    purchase_evidence: PurchaseEvidence | None = None
    grant_evidence: GrantEvidence | None = None


class ClaimVerificationRequest(BaseModel):
    """Request payload for `POST /api/v1/orders/{order_id}/verify-claim`."""

    model_config = ConfigDict(extra="forbid")

    claim_type: str = Field(..., description="Canonical dispute claim type")


class ClaimVerificationResult(BaseModel):
    """
    Deterministic dispute verification result aligned with `ticket-prioritization-api`.
    """

    model_config = ConfigDict(extra="forbid")

    status: str = "success"
    order_id: str
    claim_type: ClaimType
    verdict: VerificationVerdict
    reason_code: str
    evidence_summary: str
    recommended_priority: PriorityLevel
    amount_cents: int | None = None
    sim_usdc_micros: int | None = None


class SupportTicketContract(BaseModel):
    """
    Persisted human escalation support ticket contract (resolves F-05).
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    status: str = "success"
    ticket_status: str = "open"
    reason: str
    message: str = "A human support agent will contact you shortly."
    session_id: str | None = None
    user_id: str = "guest"
    order_id: str | None = None
    claim_type: str | None = None
    verification_verdict: str | None = None
    reason_code: str | None = None
    priority: str = "medium"
    created_at: str


# ========== ERROR MODELS ==========


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Error details")
    status_code: int = Field(..., description="HTTP status code")
