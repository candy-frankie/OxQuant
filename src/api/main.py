"""
OxQuant - Main API Application

FastAPI application for the OxQuant trading platform.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn
import os

from src.api.routers import strategies, backtesting, portfolio, data, auth
from src.core.config import settings


security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    print("Starting OxQuant API server...")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database: {settings.DATABASE_URL[:20]}...")
    
    # Initialize services
    from src.core.database import init_db
    await init_db()
    
    yield
    
    # Shutdown
    print("Shutting down OxQuant API server...")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="OxQuant API",
        description="Next-generation AI quantitative trading platform",
        version="0.1.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
    app.include_router(strategies.router, prefix="/api/v1", tags=["strategies"])
    app.include_router(backtesting.router, prefix="/api/v1", tags=["backtesting"])
    app.include_router(portfolio.router, prefix="/api/v1", tags=["portfolio"])
    app.include_router(data.router, prefix="/api/v1", tags=["data"])
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "oxquant-api",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "Welcome to OxQuant API",
            "documentation": "/docs" if settings.ENVIRONMENT != "production" else None,
            "version": "0.1.0",
            "description": "Next-generation AI quantitative trading platform"
        }
    
    return app


app = create_application()


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )