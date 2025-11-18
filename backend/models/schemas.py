"""
Pydantic models for API request/response validation
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ========== MESSAGE MODELS ==========

class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")


class ChatRequest(BaseModel):
    """Request to send a message to the support agent."""
    message: str = Field(..., description="User's message", min_length=1)
    user_id: str = Field(default="guest", description="User identifier")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Response from the support agent."""
    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# ========== PRODUCT MODELS ==========

class ProductSpecs(BaseModel):
    """Product specifications (flexible schema)."""
    
    class Config:
        extra = "allow"  # Allow additional fields


class Product(BaseModel):
    """Product information."""
    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    price: float = Field(..., description="Product price")
    stock: int = Field(..., description="Stock quantity")
    specs: Dict[str, Any] = Field(..., description="Product specifications")
    description: str = Field(..., description="Product description")
    tags: List[str] = Field(default=[], description="Product tags")
    expected_restock: Optional[str] = Field(None, description="Expected restock date")


class ProductSearchRequest(BaseModel):
    """Request to search products."""
    category: Optional[str] = Field(None, description="Filter by category")
    max_price: Optional[float] = Field(None, description="Maximum price")
    min_stock: int = Field(default=1, description="Minimum stock required")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")


class ProductSearchResponse(BaseModel):
    """Response with search results."""
    count: int = Field(..., description="Number of products found")
    products: List[Dict[str, Any]] = Field(..., description="List of products")


# ========== METRICS MODELS ==========

class MetricsResponse(BaseModel):
    """Support metrics and statistics."""
    total_conversations: int = Field(..., description="Total conversation count")
    total_messages: int = Field(..., description="Total messages exchanged")
    avg_response_time: float = Field(..., description="Average response time (seconds)")
    top_products: List[Dict[str, Any]] = Field(..., description="Most queried products")
    active_sessions: int = Field(..., description="Currently active sessions")


# ========== MEMORY MODELS ==========

class CustomerMemory(BaseModel):
    """Customer preferences and memory."""
    user_id: str = Field(..., description="User identifier")
    preferences: Dict[str, Any] = Field(default={}, description="Customer preferences")
    past_queries: List[str] = Field(default=[], description="Recent queries")
    recommended_products: List[str] = Field(default=[], description="Previously recommended products")


# ========== ERROR MODELS ==========

class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    status_code: int = Field(..., description="HTTP status code")