"""
Customer Support Agent
Canonical support agent definition sharing deterministic catalog and pricing tools.
"""

from __future__ import annotations

import logging
import os

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from .product_catalog_agent import product_catalog_agent

logger = logging.getLogger(__name__)

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

model_name = os.getenv("AGENT_MODEL", "gemini-3.8-flash")

CUSTOMER_SUPPORT_INSTRUCTION = """You are a professional customer support assistant for an e-commerce store.

Your role:
1. Help customers find products matching their requirements via `product_catalog_agent`.
2. Provide verified product information, pricing, and stock status strictly from catalog tools.
3. Suggest in-stock alternatives from the catalog when a requested item is out of stock.

Strict Grounding Rules:
- Never fabricate product names, SKUs, prices, stock counts, or restock dates.
- Always delegate product and inventory lookups to `product_catalog_agent`.
"""

customer_support_agent = LlmAgent(
    model=Gemini(model=model_name, retry_options=retry_config),
    name="customer_support_agent",
    description=(
        "Customer support assistant for e-commerce inquiries using deterministic catalog tools."
    ),
    instruction=CUSTOMER_SUPPORT_INSTRUCTION,
    sub_agents=[product_catalog_agent],
)

logger.info(f"✅ Customer Support Agent created using model: {model_name}")
