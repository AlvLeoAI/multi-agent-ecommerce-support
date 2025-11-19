"""
E-Commerce Support API
Multi-Agent Customer Support System
"""

import uvicorn
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager  

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    logging.info("🚀 E-Commerce Agent System is starting up...")
    logging.info("✅ Database connection established (Simulated)")
    
    yield  
    
    
    logging.info("🛑 Shutting down system...")
    logging.info("💤 Connections closed")


app = FastAPI(
    lifespan=lifespan,  
    title="E-Commerce Support API",
    description="Multi-Agent Customer Support System powered by Google GenAI",
    version="1.0.0"
)


from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)


from routers import products, metrics, chat


logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="E-Commerce Support API",
    description="Multi-Agent Customer Support System powered by Google GenAI",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat.router)
app.include_router(products.router)
app.include_router(metrics.router)
logging.info("All routers included.")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "E-Commerce Support API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/v1/chat/",
            "products": "/products",
            "metrics": "/metrics",
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ecommerce-support-api"
    }

if __name__ == "__main__":
    
    try:
        # Get the port from environment variables or default to 800
        port = int(os.getenv("PORT", 8000))
        
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
    except Exception as e:
        logging.error(f"Failed to start Uvicorn server: {e}")
