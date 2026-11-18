"""
API Client for E-Commerce Support Backend
Handles all HTTP requests to the FastAPI backend
"""

from __future__ import annotations

import os
from typing import Any

import requests

DEFAULT_API_BASE_URL = os.getenv(
    "API_BASE_URL",
    os.getenv("API_URL", "http://localhost:8000"),
)


class EcommerceAPIClient:
    """Client for communicating with the E-Commerce Support API."""

    def __init__(self, base_url: str | None = None) -> None:
        """
        Initialize the API client.

        Args:
            base_url: Base URL of the API (default: http://localhost:8000)
        """
        self.base_url = (base_url or DEFAULT_API_BASE_URL).rstrip("/")

    def send_message(
        self,
        message: str,
        user_id: str = "streamlit_user",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a message to the customer support agent."""
        url = f"{self.base_url}/api/v1/chat/"

        payload = {
            "message": message,
            "user_id": user_id,
            "session_id": session_id,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": f"Failed to communicate with backend: {str(e)}",
            }

    def get_products(self) -> Any:
        """Get all products from the catalog (`GET /products/`)."""
        url = f"{self.base_url}/products/"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": f"Failed to fetch products: {str(e)}",
            }

    def search_products(
        self,
        category: str | None = None,
        max_price: float | None = None,
        in_stock_only: bool = False,
    ) -> dict[str, Any]:
        """Search products with filters (`POST /products/search`)."""
        url = f"{self.base_url}/products/search"

        params: dict[str, Any] = {
            "min_stock": 1 if in_stock_only else 0,
        }
        if category:
            params["category"] = category
        if max_price is not None:
            params["max_price"] = max_price

        try:
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": f"Failed to search products: {str(e)}",
            }

    def get_metrics(self) -> dict[str, Any]:
        """Get chat metrics and statistics."""
        url = f"{self.base_url}/api/v1/chat/metrics"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": f"Failed to fetch metrics: {str(e)}",
            }

    def health_check(self) -> bool:
        """Check if the backend API is healthy."""
        url = f"{self.base_url}/health"

        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False


# Singleton instance
api_client = EcommerceAPIClient()
