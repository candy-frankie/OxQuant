"""
Pydantic Schemas for Strategies

Data validation schemas for strategy management.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from src.core.models import StrategyStatus


class StrategyBase(BaseModel):
    """Base strategy schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class StrategyCreate(StrategyBase):
    """Schema for strategy creation."""
    code: str = Field(..., description="Python code for the strategy")
    parameters: Optional[str] = Field(
        None, 
        description="JSON string of strategy parameters"
    )
    
    @validator('parameters')
    def validate_parameters(cls, v):
        """Validate parameters JSON."""
        if v is None:
            return v
        
        import json
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError('Parameters must be valid JSON')


class StrategyUpdate(BaseModel):
    """Schema for strategy update."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    code: Optional[str] = None
    parameters: Optional[str] = None
    status: Optional[StrategyStatus] = None
    
    @validator('parameters')
    def validate_parameters(cls, v):
        """Validate parameters JSON."""
        if v is None:
            return v
        
        import json
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError('Parameters must be valid JSON')


class StrategyResponse(StrategyBase):
    """Schema for strategy response."""
    id: int
    code: str
    parameters: Dict[str, Any]
    status: StrategyStatus
    sharpe_ratio: Optional[float] = None
    total_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    """Schema for strategy list response."""
    strategies: List[StrategyResponse]
    total: int
    skip: int
    limit: int


class BacktestRequest(BaseModel):
    """Schema for backtest request."""
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(100000.0, gt=0)
    commission_rate: float = Field(0.001, ge=0, le=0.1)
    slippage_rate: float = Field(0.0001, ge=0, le=0.01)
    symbol: Optional[str] = None
    data_source: str = "yahoo"


class BacktestResponse(BaseModel):
    """Schema for backtest response."""
    strategy_id: int
    metrics: Dict[str, float]
    equity_curve: Dict[str, float]
    trades: List[Dict[str, Any]]


class StrategyExecutionRequest(BaseModel):
    """Schema for strategy execution request."""
    portfolio_id: int
    symbol: str
    quantity: Optional[float] = None
    amount: Optional[float] = None


class StrategyExecutionResponse(BaseModel):
    """Schema for strategy execution response."""
    order_id: str
    strategy_id: int
    portfolio_id: int
    symbol: str
    side: str
    quantity: float
    price: float
    status: str
    executed_at: datetime


class StrategyMetrics(BaseModel):
    """Schema for strategy performance metrics."""
    sharpe_ratio: Optional[float] = None
    total_return: Optional[float] = None
    annual_return: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    num_trades: Optional[int] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None


class StrategyOptimizationRequest(BaseModel):
    """Schema for strategy optimization request."""
    parameter_grid: Dict[str, List[Any]]
    optimization_metric: str = "sharpe_ratio"
    n_iter: int = Field(100, ge=1, le=1000)


class StrategyOptimizationResult(BaseModel):
    """Schema for strategy optimization result."""
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Dict[str, Any]]


class AIStrategyGenerationRequest(BaseModel):
    """Schema for AI strategy generation request."""
    description: str = Field(..., min_length=10, max_length=1000)
    asset_class: str = "equity"
    time_frame: str = "daily"
    risk_level: str = "medium"
    constraints: Optional[Dict[str, Any]] = None


class AIStrategyGenerationResponse(BaseModel):
    """Schema for AI strategy generation response."""
    strategy_code: str
    strategy_name: str
    parameters: Dict[str, Any]
    explanation: str
    assumptions: List[str]
    risks: List[str]