"""
Configuration Module
Centralized risk parameters and application settings
"""

import os
from typing import Optional
from pydantic import BaseSettings


class RiskConfig(BaseSettings):
    """Risk management configuration"""
    
    # Position limits
    MAX_POSITION_SIZE: int = 100  # Max shares per position
    MAX_LOSS_PER_TRADE: float = 500.0  # Max allowed loss per trade ($)
    MAX_DAILY_LOSS: float = 2000.0  # Max daily loss ($)
    MAX_POSITIONS: int = 10  # Max concurrent positions
    
    # Order limits
    MAX_ORDER_VALUE: float = 10000.0  # Max order value ($)
    MIN_ORDER_SIZE: int = 1  # Min shares per order
    
    # Trading hours (ET)
    MARKET_OPEN_HOUR: int = 9
    MARKET_OPEN_MINUTE: int = 30
    MARKET_CLOSE_HOUR: int = 16
    MARKET_CLOSE_MINUTE: int = 0
    
    # Risk thresholds
    DELTA_WARNING_THRESHOLD: int = 50  # Warn if net delta exceeds
    DELTA_DANGER_THRESHOLD: int = 100  # Danger if net delta exceeds
    
    # Bot configuration
    BOT_CHECK_INTERVAL: int = 10  # Seconds between bot scans
    BOT_ICEBERG_CHUNK_SIZE: int = 25  # Shares per iceberg slice
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class AppConfig(BaseSettings):
    """Application configuration"""
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    
    # Cache settings
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    CANDLE_CACHE_TTL: int = 3600  # 1 hour
    
    # Alpaca API
    ALPACA_API_KEY: str = os.getenv("APCA_API_KEY_ID", "")
    ALPACA_API_SECRET: str = os.getenv("APCA_API_SECRET_KEY", "")
    ALPACA_ENDPOINT: str = os.getenv("APCA_ENDPOINT", "https://paper-api.alpaca.markets")
    
    # Feature flags
    ENABLE_LIVE_TRADING: bool = False
    ENABLE_MONTE_CARLO: bool = True
    ENABLE_ADVANCED_GREEKS: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global instances
risk_config = RiskConfig()
app_config = AppConfig()


def get_risk_config() -> RiskConfig:
    """Get risk configuration instance"""
    return risk_config


def get_app_config() -> AppConfig:
    """Get app configuration instance"""
    return app_config
