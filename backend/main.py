"""
E-Commerce Support API
Multi-Agent Customer Support System
"""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- 1. Load environment variables at startup ---
# Path: backend/ -> ecommerce_support/ -> multi-agent-ecommerce/ (.env)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

# Import routers (after loading .env in case the routers need variables)
from request_limits import RequestBodyLimitMiddleware, parse_cors_origins  # noqa: E402
from routers import chat, metrics, orders, products  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO)


# --- 2. Define Lifespan (Life Cycle) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logging.info("🚀 E-Commerce Agent System is starting up...")
    logging.info("✅ Database connection established (Simulated)")

    yield  # <--- The app runs here

    # Shutdown logic
    logging.info("🛑 Shutting down system...")
    logging.info("💤 Connections closed")


# --- 3. Create the App (ONLY ONCE) ---
app = FastAPI(
    lifespan=lifespan,
    title="E-Commerce Support API",
    description="Multi-Agent Customer Support System powered by Google GenAI",
    version="1.0.0",
)

# --- 4. Middlewares ---
# Exact-origin allowlist from CORS_ALLOWED_ORIGINS (comma-separated); wildcards are
# ignored. The API uses no cookies, so credentialed cross-origin requests stay off.
CORS_ALLOWED_ORIGINS = parse_cors_origins(os.getenv("CORS_ALLOWED_ORIGINS"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
# Added last so it runs first: oversized bodies are refused before CORS or routing.
app.add_middleware(RequestBodyLimitMiddleware)

# --- 5. Routers ---
app.include_router(chat.router)
app.include_router(products.router)
app.include_router(metrics.router)
app.include_router(orders.router)
logging.info("All routers included.")


# --- 6. Endpoints Base ---
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "E-Commerce Support API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/v1/chat/",
            "orders": "/api/v1/orders/",
            "tickets": "/api/v1/tickets/",
            "products": "/products",
            "metrics": "/metrics",
            "docs": "/docs",
            "health": "/health",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ecommerce-support-api",
    }


# --- 7. Entry Point ---
if __name__ == "__main__":
    try:
        port = int(os.getenv("PORT", 8000))
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
    except Exception as e:
        logging.error(f"Failed to start Uvicorn server: {e}")
