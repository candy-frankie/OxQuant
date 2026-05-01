"""
OxQuant Core Trading Engine

This module contains the core trading engine components for the OxQuant platform.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import pandas as pd
import numpy as np
import uuid


class AssetClass(Enum):
    """Supported asset classes."""
    EQUITY = "equity"
    FUTURE = "future"
    OPTION = "option"
    CRYPTO = "crypto"
    FOREX = "forex"
    ETF = "etf"


class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order sides."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order execution status."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Represents a trading order."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    order_id: Optional[str] = None
    timestamp: datetime = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_execution_price: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.order_id is None:
            self.order_id = f"ORD-{uuid.uuid4().hex[:8]}-{int(self.timestamp.timestamp())}"
    
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def remaining_quantity(self) -> float:
        """Calculate remaining quantity to fill."""
        return self.quantity - self.filled_quantity


@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    timestamp: datetime = None
    asset_class: Optional[AssetClass] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    @property
    def market_value(self) -> float:
        """Calculate current market value of position."""
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """Calculate total cost basis."""
        return self.quantity * self.avg_price
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """Calculate unrealized P&L as percentage of cost basis."""
        if self.cost_basis == 0:
            return 0.0
        return self.unrealized_pnl / self.cost_basis
    
    @property
    def direction(self) -> str:
        """Return position direction (long/short)."""
        if self.quantity > 0:
            return "long"
        elif self.quantity < 0:
            return "short"
        return "flat"
    
    def update_price(self, new_price: float):
        """Update current price and recalculate P&L."""
        self.current_price = new_price
        self.unrealized_pnl = (self.current_price - self.avg_price) * self.quantity
        self.timestamp = datetime.now(timezone.utc)


@dataclass
class Portfolio:
    """Represents a trading portfolio."""
    cash: float
    positions: Dict[str, Position]
    total_value: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def update_position(self, symbol: str, position: Position):
        """Update or add a position."""
        self.positions[symbol] = position
        self._recalculate_total_value()
    
    def remove_position(self, symbol: str):
        """Remove a position."""
        if symbol in self.positions:
            del self.positions[symbol]
            self._recalculate_total_value()
    
    def _recalculate_total_value(self):
        """Recalculate total portfolio value."""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        self.total_value = self.cash + positions_value


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.parameters = parameters or {}
        self._initialized = False
    
    @abstractmethod
    def initialize(self, data: pd.DataFrame) -> None:
        """Initialize the strategy with historical data."""
        pass
    
    @abstractmethod
    def calculate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate features from market data."""
        pass
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from features."""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: float, portfolio: Portfolio) -> float:
        """Calculate position size based on signal and portfolio."""
        pass
    
    def run(self, data: pd.DataFrame, portfolio: Portfolio) -> List[Order]:
        """Run the strategy and generate orders."""
        if not self._initialized:
            self.initialize(data)
            self._initialized = True
        
        # Calculate features
        data_with_features = self.calculate_features(data)
        
        # Generate signals
        data_with_signals = self.generate_signals(data_with_features)
        
        # Get latest signal
        latest_signal = data_with_signals['signal'].iloc[-1]
        
        # Generate orders based on signal
        orders = []
        if latest_signal != 0:
            position_size = self.calculate_position_size(latest_signal, portfolio)
            if position_size != 0:
                order = Order(
                    symbol=data_with_signals['symbol'].iloc[-1],
                    side=OrderSide.BUY if latest_signal > 0 else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=abs(position_size)
                )
                orders.append(order)
        
        return orders


class ExecutionResult:
    """Result of order execution."""
    success: bool
    order: Order
    message: str
    fill_price: float
    commission: float
    
    def __init__(self, success: bool, order: Order, message: str = "", 
                 fill_price: float = 0.0, commission: float = 0.0):
        self.success = success
        self.order = order
        self.message = message
        self.fill_price = fill_price
        self.commission = commission


class TradingEngine:
    """Core trading engine that executes strategies."""
    
    def __init__(self, initial_capital: float = 100000, commission_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.portfolio = Portfolio(
            cash=initial_capital,
            positions={},
            total_value=initial_capital,
            initial_capital=initial_capital
        )
        self.strategies: Dict[str, BaseStrategy] = {}
        self.order_history: List[Order] = []
        self.trade_history: List[Dict] = []
        self._equity_history: List[Dict[str, float]] = []
        self._performance_metrics: List[Dict[str, float]] = []
    
    def register_strategy(self, strategy: BaseStrategy):
        """Register a trading strategy."""
        if strategy.name in self.strategies:
            raise ValueError(f"Strategy '{strategy.name}' already registered")
        self.strategies[strategy.name] = strategy
    
    def unregister_strategy(self, strategy_name: str):
        """Unregister a trading strategy."""
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
    
    def execute_order(self, order: Order, market_price: float) -> ExecutionResult:
        """Execute a trading order."""
        # Validate order
        if order.quantity <= 0:
            order.status = OrderStatus.REJECTED
            return ExecutionResult(
                success=False, 
                order=order,
                message="Quantity must be positive"
            )
        
        # Simulate order execution
        execution_price = market_price
        
        # Calculate cost
        cost = order.quantity * execution_price
        commission = max(1.0, cost * self.commission_rate)
        
        # Check if we have enough cash for buy orders
        if order.side == OrderSide.BUY and self.portfolio.cash < (cost + commission):
            order.status = OrderStatus.REJECTED
            return ExecutionResult(
                success=False, 
                order=order,
                message="Insufficient cash"
            )
        
        # Update portfolio
        symbol = order.symbol
        
        if order.side == OrderSide.BUY:
            # Buy order
            self.portfolio.cash -= (cost + commission)
            
            if symbol in self.portfolio.positions:
                # Update existing position
                pos = self.portfolio.positions[symbol]
                total_quantity = pos.quantity + order.quantity
                total_cost = (pos.quantity * pos.avg_price) + cost
                new_avg_price = total_cost / total_quantity
                
                pos.quantity = total_quantity
                pos.avg_price = new_avg_price
                pos.current_price = execution_price
                pos.unrealized_pnl = (execution_price - new_avg_price) * total_quantity
            else:
                # New position
                position = Position(
                    symbol=symbol,
                    quantity=order.quantity,
                    avg_price=execution_price,
                    current_price=execution_price,
                    unrealized_pnl=0.0
                )
                self.portfolio.update_position(symbol, position)
        
        else:  # SELL order
            if symbol not in self.portfolio.positions:
                order.status = OrderStatus.REJECTED
                return ExecutionResult(
                    success=False, 
                    order=order,
                    message="No position to sell"
                )
            
            pos = self.portfolio.positions[symbol]
            if pos.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                return ExecutionResult(
                    success=False, 
                    order=order,
                    message="Insufficient quantity to sell"
                )
            
            # Calculate P&L
            sale_value = order.quantity * execution_price
            cost_basis = order.quantity * pos.avg_price
            realized_pnl = sale_value - cost_basis - commission
            
            # Update portfolio
            self.portfolio.cash += (sale_value - commission)
            pos.realized_pnl += realized_pnl
            
            if pos.quantity == order.quantity:
                # Close position
                self.portfolio.remove_position(symbol)
            else:
                # Reduce position
                pos.quantity -= order.quantity
                pos.unrealized_pnl = (execution_price - pos.avg_price) * pos.quantity
        
        # Update order status
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_execution_price = execution_price
        
        # Record order and trade
        self.order_history.append(order)
        
        trade = {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': order.quantity,
            'price': execution_price,
            'commission': commission,
            'timestamp': order.timestamp,
            'realized_pnl': realized_pnl if order.side == OrderSide.SELL else 0.0
        }
        self.trade_history.append(trade)
        
        return ExecutionResult(
            success=True,
            order=order,
            message="Order filled successfully",
            fill_price=execution_price,
            commission=commission
        )
    
    def run_strategies(self, market_data: Dict[str, pd.DataFrame]) -> List[ExecutionResult]:
        """Run all registered strategies and generate orders."""
        results = []
        
        for strategy_name, strategy in self.strategies.items():
            for symbol, data in market_data.items():
                if len(data) > 0:
                    orders = strategy.run(data, self.portfolio)
                    for order in orders:
                        # Get current market price
                        if 'close' in data.columns:
                            market_price = data['close'].iloc[-1]
                            result = self.execute_order(order, market_price)
                            results.append(result)
        
        # Record portfolio snapshot
        self._record_portfolio_snapshot()
        
        return results
    
    def _record_portfolio_snapshot(self):
        """Record portfolio state for performance tracking."""
        snapshot = {
            'timestamp': datetime.now(timezone.utc),
            'total_value': self.portfolio.total_value,
            'cash': self.portfolio.cash,
            'positions_value': self.portfolio.positions_value,
            'total_return': self.portfolio.total_return
        }
        self._equity_history.append(snapshot)
    
    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio performance metrics."""
        total_invested = sum(pos.cost_basis for pos in self.portfolio.positions.values())
        total_market_value = sum(pos.market_value for pos in self.portfolio.positions.values())
        
        # Calculate returns
        total_return = self.portfolio.total_return * 100
        
        # Calculate P&L
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.portfolio.positions.values())
        realized_pnl = sum(pos.realized_pnl for pos in self.portfolio.positions.values())
        total_pnl = unrealized_pnl + realized_pnl
        
        # Calculate risk metrics
        equity_values = [s['total_value'] for s in self._equity_history]
        if len(equity_values) >= 2:
            returns = np.diff(equity_values) / equity_values[:-1]
            volatility = np.std(returns) * np.sqrt(252) * 100
            sharpe_ratio = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
            
            # Calculate max drawdown
            cumulative = np.array(equity_values) / equity_values[0]
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min() * 100
        else:
            volatility = 0
            sharpe_ratio = 0
            max_drawdown = 0
        
        # Calculate win rate
        winning_trades = sum(1 for t in self.trade_history if t.get('realized_pnl', 0) > 0)
        total_sell_trades = sum(1 for t in self.trade_history if t['side'] == 'sell')
        win_rate = (winning_trades / total_sell_trades * 100) if total_sell_trades > 0 else 0
        
        metrics = {
            'total_value': self.portfolio.total_value,
            'cash': self.portfolio.cash,
            'positions_value': total_market_value,
            'num_positions': len(self.portfolio.positions),
            'total_return_pct': total_return,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': total_pnl,
            'volatility_pct': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'win_rate_pct': win_rate,
            'num_trades': len(self.trade_history),
            'exposure_pct': self.portfolio.exposure * 100
        }
        
        self._performance_metrics.append(metrics)
        
        return metrics
    
    def get_equity_curve(self) -> pd.Series:
        """Get equity curve as pandas Series."""
        if not self._equity_history:
            return pd.Series()
        
        timestamps = [s['timestamp'] for s in self._equity_history]
        values = [s['total_value'] for s in self._equity_history]
        return pd.Series(values, index=timestamps)
    
    def reset(self):
        """Reset engine to initial state."""
        self.portfolio = Portfolio(
            cash=self.initial_capital,
            positions={},
            total_value=self.initial_capital,
            initial_capital=self.initial_capital
        )
        self.order_history = []
        self.trade_history = []
        self._equity_history = []
        self._performance_metrics = []
        
        for strategy in self.strategies.values():
            strategy.reset()


class RiskManager:
    """Manages trading risk and position limits."""
    
    def __init__(self, max_position_size_pct: float = 0.1,
                 max_portfolio_risk_pct: float = 0.02,
                 max_drawdown_pct: float = 0.1):
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.high_water_mark = 0.0
    
    def check_position_size(self, order: Order, portfolio: Portfolio) -> bool:
        """Check if position size is within limits."""
        position_value = order.quantity * (order.price or 0)
        portfolio_value = portfolio.total_value
        
        if portfolio_value == 0:
            return False
        
        position_size_pct = position_value / portfolio_value
        return position_size_pct <= self.max_position_size_pct
    
    def check_portfolio_risk(self, portfolio: Portfolio, new_order: Order = None) -> bool:
        """Check if portfolio risk is within limits."""
        # Simplified risk check
        total_risk = 0
        for position in portfolio.positions.values():
            position_risk = abs(position.unrealized_pnl) / position.cost_basis
            total_risk += position_risk
        
        if new_order:
            # Estimate risk for new order
            estimated_risk = 0.01  # Conservative estimate
            total_risk += estimated_risk
        
        return total_risk <= self.max_portfolio_risk_pct
    
    def check_drawdown(self, current_value: float) -> bool:
        """Check if drawdown is within limits."""
        if current_value > self.high_water_mark:
            self.high_water_mark = current_value
        
        if self.high_water_mark == 0:
            return True
        
        drawdown = (self.high_water_mark - current_value) / self.high_water_mark
        return drawdown <= self.max_drawdown_pct