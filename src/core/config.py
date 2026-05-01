"""
OxQuant Configuration Settings

Application configuration using Pydantic settings management.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "OxQuant"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8501",
    ]
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/oxquant"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # JWT
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    # Data
    DATA_DIR: str = "./data"
    CACHE_DIR: str = "./cache"
    
    # ML/AI
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Trading
    DEFAULT_INITIAL_CAPITAL: float = 100000.0
    DEFAULT_COMMISSION_RATE: float = 0.001
    
    # A股市场配置
    A_STOCK_MARKET_OPEN_TIME: str = "09:30"
    A_STOCK_MARKET_CLOSE_TIME: str = "15:00"
    A_STOCK_LUNCH_BREAK_START: str = "11:30"
    A_STOCK_LUNCH_BREAK_END: str = "13:00"
    
    # 数据源配置
    DATA_SOURCE_AKSHARE_ENABLED: bool = True
    DATA_SOURCE_TUSHARE_ENABLED: bool = True
    DATA_SOURCE_BAOSTOCK_ENABLED: bool = True
    
    # 交易接口配置
    TRADING_BROKER: str = "simulation"  # simulation, easytrader, qmt, etc.
    TRADING_SIMULATION_MODE: bool = True
    
    # 风控配置
    RISK_MAX_POSITION_SIZE_PCT: float = 0.1
    RISK_MAX_PORTFOLIO_RISK_PCT: float = 0.02
    RISK_MAX_DRAWDOWN_PCT: float = 0.1
    RISK_MAX_DAILY_LOSS_PCT: float = 0.05
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()