"""
OxQuant Backtesting Engine

High-performance backtesting framework for quantitative trading strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from .engine import BaseStrategy, TradingEngine, Order, Portfolio


class BacktestResult:
    """Container for backtest results."""
    
    def __init__(self, strategy_name: str, parameters: Dict[str, Any]):
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.returns: pd.Series = None
        self.positions: pd.DataFrame = None
        self.trades: pd.DataFrame = None
        self.metrics: Dict[str, float] = {}
        self.equity_curve: pd.Series = None
        
    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate comprehensive performance metrics."""
        if self.returns is None or len(self.returns) == 0:
            return {}
        
        returns = self.returns
        
        # Basic metrics
        total_return = (returns + 1).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # Risk metrics
        volatility = returns.std() * np.sqrt(252)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        # Ratio metrics
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        sortino_ratio = annual_return / downside_deviation if downside_deviation > 0 else 0
        
        # Drawdown metrics
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Win metrics
        if self.trades is not None and not self.trades.empty:
            winning_trades = self.trades[self.trades['pnl'] > 0]
            win_rate = len(winning_trades) / len(self.trades) if len(self.trades) > 0 else 0
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            losing_trades = self.trades[self.trades['pnl'] <= 0]
            avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
            profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if losing_trades['pnl'].sum() != 0 else float('inf')
        else:
            win_rate = avg_win = avg_loss = profit_factor = 0
        
        self.metrics = {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'num_trades': len(self.trades) if self.trades is not None else 0
        }
        
        return self.metrics
    
    def plot(self, show: bool = True):
        """Plot backtest results."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            fig, axes = plt.subplots(3, 1, figsize=(12, 10))
            
            # Equity curve
            if self.equity_curve is not None:
                axes[0].plot(self.equity_curve.index, self.equity_curve.values, linewidth=2)
                axes[0].set_title('Equity Curve')
                axes[0].set_ylabel('Portfolio Value')
                axes[0].grid(True, alpha=0.3)
            
            # Drawdown
            if self.equity_curve is not None:
                cumulative = (self.equity_curve / self.equity_curve.iloc[0])
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                
                axes[1].fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
                axes[1].plot(drawdown.index, drawdown.values, color='red', linewidth=1)
                axes[1].set_title('Drawdown')
                axes[1].set_ylabel('Drawdown (%)')
                axes[1].grid(True, alpha=0.3)
            
            # Returns distribution
            if self.returns is not None and len(self.returns) > 0:
                axes[2].hist(self.returns.values, bins=50, alpha=0.7, edgecolor='black')
                axes[2].axvline(self.returns.mean(), color='red', linestyle='--', label=f'Mean: {self.returns.mean():.4f}')
                axes[2].set_title('Returns Distribution')
                axes[2].set_xlabel('Daily Returns')
                axes[2].set_ylabel('Frequency')
                axes[2].legend()
                axes[2].grid(True, alpha=0.3)
            
            plt.tight_layout()
            if show:
                plt.show()
            
            return fig
            
        except ImportError:
            print("Matplotlib not installed. Install with: pip install matplotlib")
            return None


class BacktestEngine:
    """High-performance backtesting engine."""
    
    def __init__(self, 
                 strategy: BaseStrategy,
                 data: pd.DataFrame,
                 initial_capital: float = 100000,
                 commission: float = 0.001,  # 0.1%
                 slippage: float = 0.0001,   # 0.01%
                 data_frequency: str = 'daily'):
        
        self.strategy = strategy
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.data_frequency = data_frequency
        
        # Initialize trading engine
        self.trading_engine = TradingEngine(initial_capital=initial_capital)
        self.trading_engine.register_strategy(strategy)
        
        # Results storage
        self.results = BacktestResult(
            strategy_name=strategy.name,
            parameters=strategy.parameters
        )
        
    def run(self) -> BacktestResult:
        """Run the backtest."""
        print(f"Running backtest for strategy: {self.strategy.name}")
        print(f"Period: {self.data.index[0]} to {self.data.index[-1]}")
        print(f"Initial capital: ${self.initial_capital:,.2f}")
        
        # Prepare data
        self._prepare_data()
        
        # Initialize portfolio history
        portfolio_values = []
        dates = []
        
        # Main backtest loop
        for i in range(len(self.data)):
            current_date = self.data.index[i]
            current_data = self.data.iloc[:i+1]
            
            # Get current market prices
            market_prices = {
                symbol: current_data['close'].iloc[-1]
                for symbol in ['AAPL']  # Simplified for single symbol
            }
            
            # Run strategy
            market_data = {'AAPL': current_data}  # Simplified
            orders = self.trading_engine.run_strategies(market_data)
            
            # Execute orders
            for order in orders:
                market_price = market_prices.get(order.symbol)
                if market_price:
                    # Apply slippage
                    if order.side.value == 'buy':
                        execution_price = market_price * (1 + self.slippage)
                    else:
                        execution_price = market_price * (1 - self.slippage)
                    
                    order.price = execution_price
                    self.trading_engine.execute_order(order, execution_price)
            
            # Record portfolio value
            portfolio_values.append(self.trading_engine.portfolio.total_value)
            dates.append(current_date)
        
        # Store results
        self.results.equity_curve = pd.Series(portfolio_values, index=dates)
        
        # Calculate returns
        self.results.returns = self.results.equity_curve.pct_change().dropna()
        
        # Prepare trades dataframe
        if self.trading_engine.trade_history:
            self.results.trades = pd.DataFrame(self.trading_engine.trade_history)
        
        # Calculate metrics
        self.results.calculate_metrics()
        
        print("\n" + "="*50)
        print("BACKTEST COMPLETE")
        print("="*50)
        self._print_summary()
        
        return self.results
    
    def _prepare_data(self):
        """Prepare data for backtesting."""
        # Ensure datetime index
        if not isinstance(self.data.index, pd.DatetimeIndex):
            self.data.index = pd.to_datetime(self.data.index)
        
        # Sort by date
        self.data = self.data.sort_index()
        
        # Ensure required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in self.data.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add symbol column if not present
        if 'symbol' not in self.data.columns:
            self.data['symbol'] = 'AAPL'  # Default symbol
    
    def _print_summary(self):
        """Print backtest summary."""
        metrics = self.results.metrics
        
        print(f"\nStrategy: {self.results.strategy_name}")
        print(f"Parameters: {self.results.parameters}")
        print("\nPerformance Metrics:")
        print("-" * 40)
        print(f"Total Return: {metrics.get('total_return', 0):.2%}")
        print(f"Annual Return: {metrics.get('annual_return', 0):.2%}")
        print(f"Volatility: {metrics.get('volatility', 0):.2%}")
        print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}")
        print(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
        print(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
        print(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        print(f"Number of Trades: {metrics.get('num_trades', 0)}")
        
        final_value = self.results.equity_curve.iloc[-1] if self.results.equity_curve is not None else self.initial_capital
        print(f"\nFinal Portfolio Value: ${final_value:,.2f}")
        print(f"Total P&L: ${final_value - self.initial_capital:,.2f}")
    
    def optimize_parameters(self, 
                           param_grid: Dict[str, List[Any]],
                           metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """Optimize strategy parameters using grid search."""
        from itertools import product
        
        best_params = None
        best_score = -float('inf')
        results = []
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        print(f"\nParameter Optimization")
        print(f"Grid size: {np.prod([len(v) for v in param_values])} combinations")
        print(f"Optimization metric: {metric}")
        
        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            
            # Update strategy parameters
            self.strategy.parameters.update(params)
            
            # Run backtest
            self.trading_engine = TradingEngine(initial_capital=self.initial_capital)
            self.trading_engine.register_strategy(self.strategy)
            
            result = self.run()
            score = result.metrics.get(metric, 0)
            
            results.append({
                'params': params.copy(),
                'score': score,
                'total_return': result.metrics.get('total_return', 0),
                'max_drawdown': result.metrics.get('max_drawdown', 0)
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
            
            print(f"  Params: {params} -> {metric}: {score:.4f}")
        
        # Sort results by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\nBest Parameters: {best_params}")
        print(f"Best {metric}: {best_score:.4f}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': results
        }


class WalkForwardAnalyzer:
    """Walk-forward analysis for strategy validation."""
    
    def __init__(self, 
                 strategy_class,
                 data: pd.DataFrame,
                 initial_capital: float = 100000,
                 train_size: int = 252,  # 1 year of daily data
                 test_size: int = 63,    # 3 months
                 step_size: int = 21):   # 1 month
        
        self.strategy_class = strategy_class
        self.data = data
        self.initial_capital = initial_capital
        self.train_size = train_size
        self.test_size = test_size
        self.step_size = step_size
        
    def run(self) -> Dict[str, Any]:
        """Run walk-forward analysis."""
        n_periods = len(self.data)
        results = []
        
        print(f"Running Walk-Forward Analysis")
        print(f"Train size: {self.train_size} periods")
        print(f"Test size: {self.test_size} periods")
        print(f"Step size: {self.step_size} periods")
        
        for start in range(0, n_periods - self.train_size - self.test_size, self.step_size):
            train_end = start + self.train_size
            test_end = train_end + self.test_size
            
            train_data = self.data.iloc[start:train_end]
            test_data = self.data.iloc[train_end:test_end]
            
            # Create and train strategy on training data
            strategy = self.strategy_class(name=f"walkforward_{len(results)}")
            
            # Run backtest on test data
            backtest = BacktestEngine(
                strategy=strategy,
                data=test_data,
                initial_capital=self.initial_capital
            )
            
            result = backtest.run()
            
            results.append({
                'train_period': (self.data.index[start], self.data.index[train_end-1]),
                'test_period': (self.data.index[train_end], self.data.index[test_end-1]),
                'metrics': result.metrics,
                'equity_curve': result.equity_curve
            })
            
            print(f"  Fold {len(results)}: Test period {result.equity_curve.index[0].date()} to {result.equity_curve.index[-1].date()} -> Sharpe: {result.metrics.get('sharpe_ratio', 0):.2f}")
        
        # Aggregate results
        aggregated = self._aggregate_results(results)
        
        print(f"\nWalk-Forward Analysis Complete")
        print(f"Number of folds: {len(results)}")
        print(f"Average Sharpe Ratio: {aggregated['avg_sharpe']:.2f}")
        print(f"Average Annual Return: {aggregated['avg_annual_return']:.2%}")
        
        return {
            'folds': results,
            'aggregated': aggregated
        }
    
    def _aggregate_results(self, results: List[Dict]) -> Dict[str, float]:
        """Aggregate results across all folds."""
        if not results:
            return {}
        
        metrics_list = [r['metrics'] for r in results]
        
        aggregated = {
            'avg_sharpe': np.mean([m.get('sharpe_ratio', 0) for m in metrics_list]),
            'avg_annual_return': np.mean([m.get('annual_return', 0) for m in metrics_list]),
            'avg_volatility': np.mean([m.get('volatility', 0) for m in metrics_list]),
            'avg_max_drawdown': np.mean([m.get('max_drawdown', 0) for m in metrics_list]),
            'avg_win_rate': np.mean([m.get('win_rate', 0) for m in metrics_list]),
            'std_sharpe': np.std([m.get('sharpe_ratio', 0) for m in metrics_list]),
            'min_sharpe': np.min([m.get('sharpe_ratio', 0) for m in metrics_list]),
            'max_sharpe': np.max([m.get('sharpe_ratio', 0) for m in metrics_list])
        }
        
        return aggregated