"""
OxQuant Core Trading Engine

This module contains the core trading engine components for the OxQuant platform.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np


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
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


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
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price


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


class TradingEngine:
    """Core trading engine that executes strategies."""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.portfolio = Portfolio(
            cash=initial_capital,
            positions={},
            total_value=initial_capital
        )
        self.strategies: Dict[str, BaseStrategy] = {}
        self.order_history: List[Order] = []
        self.trade_history: List[Dict] = []
    
    def register_strategy(self, strategy: BaseStrategy):
        """Register a trading strategy."""
        self.strategies[strategy.name] = strategy
    
    def execute_order(self, order: Order, market_price: float) -> bool:
        """Execute a trading order."""
        # Simulate order execution
        execution_price = market_price
        
        # Calculate cost
        cost = order.quantity * execution_price
        commission = max(1.0, cost * 0.001)  # 0.1% commission, min $1
        
        # Check if we have enough cash for buy orders
        if order.side == OrderSide.BUY and self.portfolio.cash < (cost + commission):
            return False
        
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
                return False
            
            pos = self.portfolio.positions[symbol]
            if pos.quantity < order.quantity:
                return False
            
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
        
        # Record order and trade
        order.order_id = f"order_{len(self.order_history)}"
        self.order_history.append(order)
        
        trade = {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': order.quantity,
            'price': execution_price,
            'commission': commission,
            'timestamp': order.timestamp
        }
        self.trade_history.append(trade)
        
        return True
    
    def run_strategies(self, market_data: Dict[str, pd.DataFrame]) -> List[Order]:
        """Run all registered strategies and generate orders."""
        all_orders = []
        
        for strategy_name, strategy in self.strategies.items():
            for symbol, data in market_data.items():
                if len(data) > 0:
                    orders = strategy.run(data, self.portfolio)
                    all_orders.extend(orders)
        
        return all_orders
    
    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio performance metrics."""
        total_invested = sum(pos.cost_basis for pos in self.portfolio.positions.values())
        total_market_value = sum(pos.market_value for pos in self.portfolio.positions.values())
        
        # Calculate returns
        total_return = ((self.portfolio.total_value - self.initial_capital) / 
                       self.initial_capital * 100)
        
        # Calculate P&L
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.portfolio.positions.values())
        realized_pnl = sum(pos.realized_pnl for pos in self.portfolio.positions.values())
        total_pnl = unrealized_pnl + realized_pnl
        
        # Calculate risk metrics (simplified)
        if self.trade_history:
            returns = []
            for trade in self.trade_history[-20:]:  # Last 20 trades
                if trade['side'] == 'sell':
                    returns.append(trade['price'] / 100)  # Simplified
            
            if returns:
                returns_array = np.array(returns)
                volatility = np.std(returns_array) * np.sqrt(252) * 100  # Annualized
                sharpe_ratio = (np.mean(returns_array) / np.std(returns_array) * 
                               np.sqrt(252)) if np.std(returns_array) > 0 else 0
            else:
                volatility = 0
                sharpe_ratio = 0
        else:
            volatility = 0
            sharpe_ratio = 0
        
        return {
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
            'num_trades': len(self.trade_history)
        }


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