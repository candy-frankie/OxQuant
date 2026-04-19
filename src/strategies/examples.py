"""
OxQuant Example Strategies

Example trading strategies for demonstration and testing.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StrategyResult:
    """Strategy execution result."""
    signals: pd.DataFrame
    positions: pd.DataFrame
    metrics: Dict[str, float]
    metadata: Dict[str, Any]


class MovingAverageCrossover:
    """
    Simple Moving Average Crossover Strategy.
    
    Buys when short MA crosses above long MA, sells when short MA crosses below long MA.
    """
    
    def __init__(self, short_window: int = 20, long_window: int = 50):
        """
        Initialize strategy.
        
        Args:
            short_window: Short moving average window
            long_window: Long moving average window
        """
        self.short_window = short_window
        self.long_window = long_window
        self.name = f"MA_Crossover_{short_window}_{long_window}"
        
    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """
        Generate trading signals from price data.
        
        Args:
            data: DataFrame with 'close' prices and datetime index
            
        Returns:
            StrategyResult with signals, positions, and metrics
        """
        # Calculate moving averages
        data['short_ma'] = data['close'].rolling(window=self.short_window).mean()
        data['long_ma'] = data['close'].rolling(window=self.long_window).mean()
        
        # Generate signals
        data['signal'] = 0
        data.loc[data['short_ma'] > data['long_ma'], 'signal'] = 1  # Buy signal
        data.loc[data['short_ma'] < data['long_ma'], 'signal'] = -1  # Sell signal
        
        # Calculate position changes (buy on signal change from -1 to 1, sell from 1 to -1)
        data['position'] = data['signal'].diff()
        data['position'] = data['position'].apply(lambda x: 1 if x == 2 else (-1 if x == -2 else 0))
        
        # Calculate returns
        data['returns'] = data['close'].pct_change()
        data['strategy_returns'] = data['position'].shift(1) * data['returns']
        
        # Calculate metrics
        total_return = (1 + data['strategy_returns'].fillna(0)).cumprod().iloc[-1] - 1
        sharpe_ratio = self._calculate_sharpe_ratio(data['strategy_returns'])
        max_drawdown = self._calculate_max_drawdown(data['strategy_returns'])
        win_rate = self._calculate_win_rate(data['strategy_returns'])
        
        metrics = {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'total_trades': int(data['position'].abs().sum()),
            'avg_trade_return': float(data['strategy_returns'].mean()),
        }
        
        metadata = {
            'strategy_name': self.name,
            'parameters': {
                'short_window': self.short_window,
                'long_window': self.long_window
            },
            'data_points': len(data)
        }
        
        return StrategyResult(
            signals=data[['signal', 'position']],
            positions=data[['position']],
            metrics=metrics,
            metadata=metadata
        )
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        if excess_returns.std() == 0:
            return 0.0
        
        sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        return float(sharpe)
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cumulative = (1 + returns.fillna(0)).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())
    
    def _calculate_win_rate(self, returns: pd.Series) -> float:
        """Calculate win rate (percentage of profitable trades)."""
        trades = returns[returns != 0]
        if len(trades) == 0:
            return 0.0
        win_rate = (trades > 0).sum() / len(trades)
        return float(win_rate)


class MeanReversion:
    """
    Mean Reversion Strategy using Bollinger Bands.
    
    Buys when price crosses below lower band, sells when price crosses above upper band.
    """
    
    def __init__(self, window: int = 20, num_std: float = 2.0):
        """
        Initialize strategy.
        
        Args:
            window: Rolling window for Bollinger Bands
            num_std: Number of standard deviations for bands
        """
        self.window = window
        self.num_std = num_std
        self.name = f"MeanReversion_BB_{window}_{num_std}"
        
    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """
        Generate trading signals using Bollinger Bands.
        
        Args:
            data: DataFrame with 'close' prices and datetime index
            
        Returns:
            StrategyResult with signals, positions, and metrics
        """
        # Calculate Bollinger Bands
        data['ma'] = data['close'].rolling(window=self.window).mean()
        data['std'] = data['close'].rolling(window=self.window).std()
        data['upper_band'] = data['ma'] + (data['std'] * self.num_std)
        data['lower_band'] = data['ma'] - (data['std'] * self.num_std)
        
        # Generate signals
        data['signal'] = 0
        data.loc[data['close'] < data['lower_band'], 'signal'] = 1  # Buy signal (oversold)
        data.loc[data['close'] > data['upper_band'], 'signal'] = -1  # Sell signal (overbought)
        
        # Calculate position changes
        data['position'] = data['signal'].diff()
        data['position'] = data['position'].apply(lambda x: 1 if x == 1 else (-1 if x == -1 else 0))
        
        # Calculate returns
        data['returns'] = data['close'].pct_change()
        data['strategy_returns'] = data['position'].shift(1) * data['returns']
        
        # Calculate metrics
        total_return = (1 + data['strategy_returns'].fillna(0)).cumprod().iloc[-1] - 1
        sharpe_ratio = self._calculate_sharpe_ratio(data['strategy_returns'])
        max_drawdown = self._calculate_max_drawdown(data['strategy_returns'])
        win_rate = self._calculate_win_rate(data['strategy_returns'])
        
        metrics = {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'total_trades': int(data['position'].abs().sum()),
            'avg_trade_return': float(data['strategy_returns'].mean()),
        }
        
        metadata = {
            'strategy_name': self.name,
            'parameters': {
                'window': self.window,
                'num_std': self.num_std
            },
            'data_points': len(data)
        }
        
        return StrategyResult(
            signals=data[['signal', 'position']],
            positions=data[['position']],
            metrics=metrics,
            metadata=metadata
        )
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        if excess_returns.std() == 0:
            return 0.0
        
        sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        return float(sharpe)
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cumulative = (1 + returns.fillna(0)).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())
    
    def _calculate_win_rate(self, returns: pd.Series) -> float:
        """Calculate win rate."""
        trades = returns[returns != 0]
        if len(trades) == 0:
            return 0.0
        win_rate = (trades > 0).sum() / len(trades)
        return float(win_rate)


# Factory function to create strategies
def create_strategy(strategy_type: str, **kwargs):
    """
    Create a strategy instance by type.
    
    Args:
        strategy_type: Type of strategy ('ma_crossover', 'mean_reversion')
        **kwargs: Strategy parameters
        
    Returns:
        Strategy instance
    """
    strategies = {
        'ma_crossover': MovingAverageCrossover,
        'mean_reversion': MeanReversion,
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"Unknown strategy type: {strategy_type}. Available: {list(strategies.keys())}")
    
    return strategies[strategy_type](**kwargs)


# Example usage
if __name__ == "__main__":
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    data = pd.DataFrame({'close': prices}, index=dates)
    
    # Test MA Crossover strategy
    print("Testing Moving Average Crossover Strategy...")
    ma_strategy = MovingAverageCrossover(short_window=10, long_window=30)
    result = ma_strategy.generate_signals(data)
    print(f"Total Return: {result.metrics['total_return']:.2%}")
    print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
    print(f"Win Rate: {result.metrics['win_rate']:.2%}")
    print(f"Total Trades: {result.metrics['total_trades']}")
    
    print("\n" + "="*50 + "\n")
    
    # Test Mean Reversion strategy
    print("Testing Mean Reversion Strategy...")
    mr_strategy = MeanReversion(window=20, num_std=2.0)
    result = mr_strategy.generate_signals(data)
    print(f"Total Return: {result.metrics['total_return']:.2%}")
    print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
    print(f"Win Rate: {result.metrics['win_rate']:.2%}")
    print(f"Total Trades: {result.metrics['total_trades']}")