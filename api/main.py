"""
Supergraph Pro - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers import market, strategy, backtest
from services.cache import init_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    await init_database()
    yield

app = FastAPI(
    title="Supergraph Pro API",
    description="Professional Options Trading Dashboard Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(market.router, prefix="/api/market", tags=["Market Data"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["Strategy"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtest"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root redirect to docs"""
    return {"message": "Supergraph Pro API", "docs": "/docs"}
