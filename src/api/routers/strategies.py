"""
Strategies API Routes

Trading strategy management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import ast
import json

from src.core.database import get_db
from src.core.models import User, Strategy, StrategyStatus
from src.api.utils.auth import get_current_user
from src.api.schemas.strategies import (
    StrategyCreate, StrategyUpdate, StrategyResponse,
    StrategyListResponse, BacktestRequest, BacktestResponse
)
from src.core.engine import BaseStrategy
from src.core.backtesting import BacktestEngine


router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("/", response_model=StrategyListResponse)
async def list_strategies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[StrategyStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List trading strategies."""
    query = db.query(Strategy).filter(Strategy.owner_id == current_user.id)
    
    if status:
        query = query.filter(Strategy.status == status)
    
    total = query.count()
    strategies = query.order_by(Strategy.created_at.desc()).offset(skip).limit(limit).all()
    
    return StrategyListResponse(
        strategies=[StrategyResponse.from_orm(s) for s in strategies],
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new trading strategy."""
    # Validate strategy code
    try:
        # Try to parse the code to check syntax
        ast.parse(strategy_data.code)
    except SyntaxError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Python code: {str(e)}"
        )
    
    # Check if strategy with same name already exists
    existing = db.query(Strategy).filter(
        Strategy.owner_id == current_user.id,
        Strategy.name == strategy_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy with this name already exists"
        )
    
    # Create strategy
    strategy = Strategy(
        name=strategy_data.name,
        description=strategy_data.description,
        code=strategy_data.code,
        parameters=json.loads(strategy_data.parameters) if strategy_data.parameters else {},
        owner_id=current_user.id,
        status=StrategyStatus.DRAFT
    )
    
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    
    return StrategyResponse.from_orm(strategy)


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific trading strategy."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.owner_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    return StrategyResponse.from_orm(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    strategy_data: StrategyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a trading strategy."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.owner_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Validate code if provided
    if strategy_data.code:
        try:
            ast.parse(strategy_data.code)
        except SyntaxError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Python code: {str(e)}"
            )
        strategy.code = strategy_data.code
    
    # Update other fields
    if strategy_data.name is not None:
        # Check if new name conflicts with existing strategy
        if strategy_data.name != strategy.name:
            existing = db.query(Strategy).filter(
                Strategy.owner_id == current_user.id,
                Strategy.name == strategy_data.name,
                Strategy.id != strategy_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Strategy with this name already exists"
                )
            strategy.name = strategy_data.name
    
    if strategy_data.description is not None:
        strategy.description = strategy_data.description
    
    if strategy_data.parameters is not None:
        strategy.parameters = json.loads(strategy_data.parameters)
    
    if strategy_data.status is not None:
        strategy.status = strategy_data.status
    
    db.commit()
    db.refresh(strategy)
    
    return StrategyResponse.from_orm(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a trading strategy."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.owner_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Check if strategy is used in any portfolio
    from src.core.models import PortfolioStrategy
    portfolio_usage = db.query(PortfolioStrategy).filter(
        PortfolioStrategy.strategy_id == strategy_id
    ).first()
    
    if portfolio_usage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete strategy that is used in a portfolio"
        )
    
    db.delete(strategy)
    db.commit()


@router.post("/{strategy_id}/backtest", response_model=BacktestResponse)
async def backtest_strategy(
    strategy_id: int,
    backtest_request: BacktestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run backtest for a strategy."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.owner_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # TODO: Load market data based on backtest_request
    # For now, we'll use dummy data
    import pandas as pd
    import numpy as np
    
    # Generate dummy data
    dates = pd.date_range(
        start=backtest_request.start_date,
        end=backtest_request.end_date,
        freq='D'
    )
    
    data = pd.DataFrame({
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 105,
        'low': np.random.randn(len(dates)).cumsum() + 95,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    # Create strategy instance from code
    # This is a simplified version - in production, you'd need to safely execute the code
    try:
        # Dynamically create strategy class
        exec_globals = {}
        exec(strategy.code, exec_globals)
        
        # Find the strategy class
        strategy_class = None
        for obj in exec_globals.values():
            if (isinstance(obj, type) and 
                issubclass(obj, BaseStrategy) and 
                obj != BaseStrategy):
                strategy_class = obj
                break
        
        if not strategy_class:
            raise ValueError("No valid strategy class found in code")
        
        # Create strategy instance
        strategy_instance = strategy_class(
            name=strategy.name,
            parameters=strategy.parameters
        )
        
        # Run backtest
        backtest_engine = BacktestEngine(
            strategy=strategy_instance,
            data=data,
            initial_capital=backtest_request.initial_capital,
            commission=backtest_request.commission_rate,
            slippage=backtest_request.slippage_rate
        )
        
        result = backtest_engine.run()
        
        # Update strategy metrics
        strategy.sharpe_ratio = result.metrics.get('sharpe_ratio')
        strategy.total_return = result.metrics.get('total_return')
        strategy.max_drawdown = result.metrics.get('max_drawdown')
        strategy.win_rate = result.metrics.get('win_rate')
        strategy.last_run_at = pd.Timestamp.now()
        
        db.commit()
        
        return BacktestResponse(
            strategy_id=strategy_id,
            metrics=result.metrics,
            equity_curve=result.equity_curve.to_dict() if result.equity_curve is not None else {},
            trades=result.trades.to_dict('records') if result.trades is not None else []
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error running backtest: {str(e)}"
        )


@router.post("/{strategy_id}/duplicate", response_model=StrategyResponse)
async def duplicate_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate a trading strategy."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.owner_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Create duplicate
    duplicate = Strategy(
        name=f"{strategy.name} (Copy)",
        description=strategy.description,
        code=strategy.code,
        parameters=strategy.parameters.copy() if strategy.parameters else {},
        owner_id=current_user.id,
        status=StrategyStatus.DRAFT
    )
    
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    
    return StrategyResponse.from_orm(duplicate)


@router.get("/{strategy_id}/validate")
async def validate_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate strategy code syntax."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.owner_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    try:
        ast.parse(strategy.code)
        return {"valid": True, "message": "Strategy code is valid"}
    except SyntaxError as e:
        return {
            "valid": False,
            "message": f"Syntax error: {str(e)}",
            "line": e.lineno,
            "offset": e.offset
        }