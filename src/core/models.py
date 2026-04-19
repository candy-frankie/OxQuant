"""
OxQuant Database Models

SQLAlchemy models for the OxQuant platform.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Enum, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.core.database import Base


class UserRole(str, enum.Enum):
    """User roles."""
    ADMIN = "admin"
    TRADER = "trader"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.TRADER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    strategies = relationship("Strategy", back_populates="owner")
    portfolios = relationship("Portfolio", back_populates="owner")
    backtests = relationship("Backtest", back_populates="owner")


class StrategyStatus(str, enum.Enum):
    """Strategy status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Strategy(Base):
    """Trading strategy model."""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    code = Column(Text, nullable=False)  # Python code for the strategy
    parameters = Column(JSON, default=dict)  # Strategy parameters
    status = Column(Enum(StrategyStatus), default=StrategyStatus.DRAFT)
    
    # Performance metrics (cached)
    sharpe_ratio = Column(Float)
    total_return = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="strategies")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_run_at = Column(DateTime(timezone=True))
    
    # Relationships
    backtests = relationship("Backtest", back_populates="strategy")
    portfolio_strategies = relationship("PortfolioStrategy", back_populates="strategy")


class Portfolio(Base):
    """Portfolio model."""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    initial_capital = Column(Float, default=100000.0)
    current_value = Column(Float)
    
    # Risk parameters
    max_position_size_pct = Column(Float, default=0.1)
    max_portfolio_risk_pct = Column(Float, default=0.02)
    max_drawdown_pct = Column(Float, default=0.1)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="portfolios")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    strategies = relationship("PortfolioStrategy", back_populates="portfolio")
    positions = relationship("Position", back_populates="portfolio")
    trades = relationship("Trade", back_populates="portfolio")


class PortfolioStrategy(Base):
    """Many-to-many relationship between portfolios and strategies."""
    __tablename__ = "portfolio_strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    weight = Column(Float, default=1.0)  # Weight in portfolio
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="strategies")
    strategy = relationship("Strategy", back_populates="portfolio_strategies")


class Position(Base):
    """Portfolio position model."""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String(50), nullable=False)
    asset_class = Column(String(50))  # equity, crypto, forex, etc.
    quantity = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    current_price = Column(Float)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")


class Trade(Base):
    """Trade execution model."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    
    # Trade details
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)  # buy/sell
    order_type = Column(String(20))  # market/limit/stop
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    pnl = Column(Float)
    
    # Execution details
    order_id = Column(String(100))
    broker = Column(String(50))
    status = Column(String(20), default="filled")
    
    # Timestamps
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="trades")
    strategy = relationship("Strategy")


class Backtest(Base):
    """Backtest result model."""
    __tablename__ = "backtests"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    
    # Configuration
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    initial_capital = Column(Float, default=100000.0)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    commission_rate = Column(Float, default=0.001)
    slippage_rate = Column(Float, default=0.0001)
    
    # Results
    results = Column(JSON)  # Full backtest results
    metrics = Column(JSON)  # Performance metrics
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="backtests")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="backtests")


class MarketData(Base):
    """Market data model."""
    __tablename__ = "market_data"
    
    id = Column(BigInteger, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    interval = Column(String(10))  # 1m, 5m, 1h, 1d, etc.
    
    # OHLCV data
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    
    # Additional data
    vwap = Column(Float)  # Volume Weighted Average Price
    trades = Column(Integer)  # Number of trades
    
    # Index
    __table_args__ = (
        Index('ix_market_data_symbol_timestamp', 'symbol', 'timestamp', unique=True),
    )


class AIRequest(Base):
    """AI/ML request logging."""
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    endpoint = Column(String(255))
    prompt = Column(Text)
    response = Column(Text)
    tokens_used = Column(Integer)
    cost = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")