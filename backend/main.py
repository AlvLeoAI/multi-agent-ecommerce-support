"""
E-Commerce Support API
Multi-Agent Customer Support System
"""

import uvicorn
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- FIX: Cargar variables de entorno ---
from dotenv import load_dotenv
# Asumimos que .env está en la raíz del proyecto (dos niveles arriba de main.py)
# Ruta: backend/ -> ecommerce_support/ -> multi-agent-ecommerce/
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)
# --- Fin del Fix ---

# Importa correctamente todos los routers usando importaciones absolutas simples.
# Esto funciona si Uvicorn se ejecuta desde la carpeta que contiene el paquete 'routers'.
from routers import products, metrics, chat

# Configura logging para mejor diagnóstico
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="E-Commerce Support API",
    description="Multi-Agent Customer Support System powered by Google GenAI",
    version="1.0.0"
)

# CORS middleware
# Usando allow_origins=["*"] para máxima flexibilidad en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# El router de chat ya tiene el prefijo /api/v1/chat/ definido
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
    # La ejecución directa de main.py debe usar el nombre del módulo
    try:
        # Get the port from environment variables or default to 8000
        port = int(os.getenv("PORT", 8000))
        # Nota: Usamos "main:app" ya que es una convención de Uvicorn que funciona con importaciones simples
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
    except Exception as e:
        logging.error(f"Failed to start Uvicorn server: {e}")
