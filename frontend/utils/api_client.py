"""
API Client for E-Commerce Support Backend
Handles all HTTP requests to the FastAPI backend
"""

import requests
from typing import Dict, Optional, List
import os


class EcommerceAPIClient:
    """Client for communicating with the E-Commerce Support API."""
    
    def __init__(self, base_url: str = None):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the API (default: http://localhost:8000)
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "https://ecommerce-agent-backend-89106065348.southamerica-east1.run.app")
    
    def send_message(
        self,
        message: str,
        user_id: str = "streamlit_user",
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Send a message to the customer support agent.
        
        Args:
            message: User's message
            user_id: User identifier
            session_id: Optional session ID for conversation continuity
        
        Returns:
            API response with agent's reply
        """
        url = f"{self.base_url}/api/v1/chat/"
        
        payload = {
            "message": message,
            "user_id": user_id,
            "session_id": session_id
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": f"Failed to communicate with backend: {str(e)}"
            }
    
    def get_products(self) -> Dict:
        """
        Get all products from the catalog.
        
        Returns:
            List of all products with details
        """
        url = f"{self.base_url}/api/v1/products/"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": f"Failed to fetch products: {str(e)}"
            }
    
    def search_products(
        self,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = False
    ) -> Dict:
        """
        Search products with filters.
        
        Args:
            category: Filter by category
            max_price: Maximum price filter
            in_stock_only: Only show in-stock products
        
        Returns:
            Filtered list of products
        """
        url = f"{self.base_url}/api/v1/products/search"
        
        params = {}
        if category:
            params["category"] = category
        if max_price:
            params["max_price"] = max_price
        if in_stock_only:
            params["in_stock_only"] = in_stock_only
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": f"Failed to search products: {str(e)}"
            }
    
    def get_metrics(self) -> Dict:
        """
        Get chat metrics and statistics.
        
        Returns:
            Metrics data including conversation count, messages, etc.
        """
        url = f"{self.base_url}/api/v1/chat/metrics"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": f"Failed to fetch metrics: {str(e)}"
            }
    
    def health_check(self) -> bool:
        """
        Check if the backend API is healthy.
        
        Returns:
            True if API is responding, False otherwise
        """
        url = f"{self.base_url}/health"
        
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False


# Singleton instance
api_client = EcommerceAPIClient()
