"""
A股回测器测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.backtesting.a_stock_backtester import AStockBacktester, BacktestMode, BacktestResult
from src.strategies.a_stock_strategies import AStockMovingAverageStrategy


class TestAStockBacktester:
    """A股回测器测试类"""
    
    def setup_method(self):
        """创建测试数据"""
        dates = pd.date_range('2023-01-01', '2023-03-31', freq='D')
        np.random.seed(42)
        
        # 创建价格序列
        prices = 10 + np.cumsum(np.random.randn(len(dates)) * 0.5)
        
        self.test_data = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
        
        # 创建简单的策略函数
        def mock_strategy(data, engine, **kwargs):
            """模拟策略函数"""
            # 简单策略：价格高于10.5时买入，低于9.5时卖出
            signals = []
            for idx, row in data.iterrows():
                if row['close'] > 10.5:
                    signals.append({'action': 'buy', 'price': row['close'], 'timestamp': idx})
                elif row['close'] < 9.5:
                    signals.append({'action': 'sell', 'price': row['close'], 'timestamp': idx})
            
            # 模拟执行交易
            trade_history = []
            for signal in signals:
                if signal['action'] == 'buy':
                    result = engine.execute_buy(
                        symbol='test_stock',
                        price=signal['price'],
                        quantity=100,
                        timestamp=signal['timestamp']
                    )
                    if result['success']:
                        trade_history.append(result)
                else:
                    result = engine.execute_sell(
                        symbol='test_stock',
                        price=signal['price'],
                        quantity=100,
                        timestamp=signal['timestamp']
                    )
                    if result['success']:
                        trade_history.append(result)
            
            return {
                'trade_history': trade_history,
                'equity_curve': pd.Series([engine.initial_capital] + [engine.current_capital]),
                'metrics': engine.get_performance_metrics()
            }
        
        self.mock_strategy = mock_strategy
    
    def test_backtester_initialization(self):
        """测试回测器初始化"""
        backtester = AStockBacktester(
            initial_capital=100000,
            commission_rate=0.001,
            slippage=0.001,
            mode=BacktestMode.DAILY
        )
        
        assert backtester.initial_capital == 100000
        assert backtester.commission_rate == 0.001
        assert backtester.slippage == 0.001
        assert backtester.mode == BacktestMode.DAILY
    
    def test_run_backtest(self):
        """测试运行回测"""
        backtester = AStockBacktester(initial_capital=100000)
        
        result = backtester.run_backtest(
            data=self.test_data,
            strategy_func=self.mock_strategy,
            strategy_params={}
        )
        
        assert isinstance(result, BacktestResult)
        assert result.initial_capital == 100000
        assert result.total_trades >= 0
    
    def test_calculate_performance_no_trades(self):
        """测试无交易时的性能计算"""
        backtester = AStockBacktester(initial_capital=100000)
        
        strategy_results = {
            'trade_history': [],
            'equity_curve': pd.Series(),
            'metrics': {}
        }
        
        result = backtester.calculate_performance(strategy_results)
        
        assert result.total_return == 0.0
        assert result.total_trades == 0
        assert result.win_rate == 0.0
    
    def test_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        backtester = AStockBacktester()
        
        # 创建模拟交易历史
        trade_history = [
            {
                'action': 'buy',
                'total_cost': 1000,
                'timestamp': datetime(2023, 1, 1)
            },
            {
                'action': 'sell',
                'net_proceeds': 800,  # 亏损
                'timestamp': datetime(2023, 1, 2)
            },
            {
                'action': 'buy',
                'total_cost': 1000,
                'timestamp': datetime(2023, 1, 3)
            },
            {
                'action': 'sell',
                'net_proceeds': 1200,  # 盈利
                'timestamp': datetime(2023, 1, 4)
            }
        ]
        
        max_drawdown = backtester.calculate_max_drawdown(trade_history)
        
        assert max_drawdown > 0  # 应该有回撤
    
    def test_generate_report(self):
        """测试生成报告"""
        backtester = AStockBacktester(initial_capital=100000)
        
        # 创建模拟结果
        result = BacktestResult(
            initial_capital=100000,
            final_capital=110000,
            total_return=0.10,
            annual_return=0.15,
            sharpe_ratio=1.5,
            max_drawdown=0.05,
            win_rate=0.6,
            profit_factor=2.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            avg_win=2000,
            avg_loss=1000,
            trade_history=[],
            equity_curve=pd.Series(),
            metrics={}
        )
        
        report = backtester.generate_report(result)
        
        assert 'summary' in report
        assert '交易统计' in report
        assert '风险指标' in report
        
        # 检查报告内容
        summary = report['summary']
        assert '总收益率' in summary
        assert '年化收益率' in summary
        assert '夏普比率' in summary
    
    def test_backtest_with_real_strategy(self):
        """测试使用真实策略回测"""
        backtester = AStockBacktester(initial_capital=100000)
        
        # 使用移动平均线策略
        strategy = AStockMovingAverageStrategy(
            short_window=5,
            long_window=20,
            initial_capital=100000
        )
        
        # 定义策略函数
        def ma_strategy(data, engine, **kwargs):
            return strategy.backtest(data)
        
        result = backtester.run_backtest(
            data=self.test_data,
            strategy_func=ma_strategy,
            strategy_params={'short_window': 5, 'long_window': 20}
        )
        
        assert isinstance(result, BacktestResult)
        assert hasattr(result, 'total_return')
        assert hasattr(result, 'max_drawdown')
        
        # 检查是否有交易历史
        if result.total_trades > 0:
            assert len(result.trade_history) > 0