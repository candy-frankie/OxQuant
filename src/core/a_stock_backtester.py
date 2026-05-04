"""
OxQuant A股回测器

专门针对A股市场的回测引擎，支持A股市场规则。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from .engine import (
    BaseStrategy, TradingEngine, Order, Portfolio, 
    OrderSide, OrderType, OrderStatus, AssetClass,
    RiskManager, RiskCheckResult
)
from src.data.data_providers import data_manager, DataFrequency
from src.factors.factor_engine import factor_engine
from src.factors.multi_factor_model import MultiFactorModel, FactorCombinationMethod, SignalGenerator


class AStockBacktestResult:
    """A股回测结果容器。"""
    
    def __init__(self, strategy_name: str, parameters: Dict[str, Any]):
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.returns: pd.Series = None
        self.positions: pd.DataFrame = None
        self.trades: pd.DataFrame = None
        self.metrics: Dict[str, float] = {}
        self.equity_curve: pd.Series = None
        self.max_drawdown_curve: pd.Series = None
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.transaction_cost: float = 0.0
        
    def calculate_metrics(self) -> Dict[str, float]:
        """计算综合性能指标。"""
        if self.returns is None or len(self.returns) == 0:
            return {}
        
        returns = self.returns
        
        # 基础指标
        total_return = (returns + 1).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        cagr = annual_return
        
        # 风险指标
        volatility = returns.std() * np.sqrt(252)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        # 比率指标
        risk_free_rate = 0.02
        excess_returns = returns - risk_free_rate / 252
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        sortino_ratio = annual_return / downside_deviation if downside_deviation > 0 else 0
        calmar_ratio = abs(annual_return / max_drawdown) if max_drawdown != 0 else float('inf')
        
        # 回撤指标
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        avg_drawdown = drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0
        recovery_factor = abs(total_return / max_drawdown) if max_drawdown != 0 else float('inf')
        
        # 胜率指标
        if self.trades is not None and not self.trades.empty:
            winning_trades = self.trades[self.trades['pnl'] > 0]
            win_rate = len(winning_trades) / len(self.trades) if len(self.trades) > 0 else 0
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            losing_trades = self.trades[self.trades['pnl'] <= 0]
            avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
            profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if losing_trades['pnl'].sum() != 0 else float('inf')
            expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
            risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            win_rate = avg_win = avg_loss = profit_factor = expectancy = risk_reward_ratio = 0
        
        # 交易统计
        num_trades = len(self.trades) if self.trades is not None else 0
        max_win = self.trades['pnl'].max() if self.trades is not None and not self.trades.empty else 0
        max_loss = self.trades['pnl'].min() if self.trades is not None and not self.trades.empty else 0
        avg_trade_duration = self._calculate_avg_trade_duration()
        
        # 换手率
        turnover = self._calculate_turnover()
        
        self.metrics = {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'cagr': float(cagr),
            'volatility': float(volatility),
            'downside_deviation': float(downside_deviation),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'recovery_factor': float(recovery_factor),
            'max_drawdown': float(max_drawdown),
            'avg_drawdown': float(avg_drawdown),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'expectancy': float(expectancy),
            'risk_reward_ratio': float(risk_reward_ratio),
            'num_trades': num_trades,
            'max_win': float(max_win),
            'max_loss': float(max_loss),
            'avg_trade_duration_days': float(avg_trade_duration),
            'turnover': float(turnover),
            'transaction_cost': float(self.transaction_cost)
        }
        
        return self.metrics
    
    def _calculate_avg_trade_duration(self) -> float:
        """计算平均持仓天数。"""
        if self.trades is None or self.trades.empty:
            return 0.0
        
        # 简化计算：假设平均持仓1天
        return 1.0
    
    def _calculate_turnover(self) -> float:
        """计算年化换手率。"""
        if self.trades is None or self.trades.empty:
            return 0.0
        
        total_trade_value = self.trades['quantity'].mul(self.trades['price']).sum()
        avg_portfolio_value = self.equity_curve.mean() if self.equity_curve is not None else 1
        
        if avg_portfolio_value == 0:
            return 0.0
        
        return total_trade_value / avg_portfolio_value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于序列化。"""
        return {
            'strategy_name': self.strategy_name,
            'parameters': self.parameters,
            'metrics': self.metrics,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'num_trades': self.metrics.get('num_trades', 0),
            'total_return': self.metrics.get('total_return', 0),
            'sharpe_ratio': self.metrics.get('sharpe_ratio', 0),
            'max_drawdown': self.metrics.get('max_drawdown', 0)
        }


class AStockBacktestEngine:
    """A股专用回测引擎。"""
    
    def __init__(
        self,
        strategy: Optional[BaseStrategy] = None,
        initial_capital: float = 1000000,
        commission: float = 0.0003,  # A股佣金约万3
        slippage: float = 0.0001,    # 滑点
        stamp_tax: float = 0.001,     # 印花税千1（仅卖出）
        min_commission: float = 5.0   # 最低佣金5元
    ):
        
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        
        # A股市场规则
        self.market_open_time = '09:30'
        self.market_close_time = '15:00'
        self.lunch_break_start = '11:30'
        self.lunch_break_end = '13:00'
        
        # 交易引擎
        self.trading_engine = TradingEngine(
            initial_capital=initial_capital,
            commission_rate=commission
        )
        
        # 风险管理器
        self.risk_manager = RiskManager(
            max_position_size_pct=0.1,    # 单一持仓不超过10%
            max_portfolio_risk_pct=0.02,
            max_drawdown_pct=0.1,
            max_daily_loss_pct=0.05,
            max_concentration_pct=0.2,
            max_open_positions=20
        )
        
        # 结果存储
        self.results = None
        
        # 持仓历史
        self.position_history = []
    
    def load_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        frequency: str = "daily"
    ) -> Dict[str, pd.DataFrame]:
        """加载A股数据。"""
        return data_manager.get_multi_stock_data(
            symbols, start_date, end_date, frequency
        )
    
    def run(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        strategy_type: str = "multi_factor",
        strategy_params: Optional[Dict] = None
    ) -> AStockBacktestResult:
        """运行回测。"""
        print(f"\n{'='*60}")
        print(f"A股回测引擎启动")
        print(f"{'='*60}")
        print(f"策略类型: {strategy_type}")
        print(f"股票池: {len(symbols)} 只股票")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_capital:,.2f} 元")
        
        # 加载数据
        print(f"\n正在加载数据...")
        data_dict = self.load_data(symbols, start_date, end_date)
        
        if not data_dict:
            print("错误: 未能加载任何股票数据")
            return AStockBacktestResult("NoData", {})
        
        print(f"成功加载 {len(data_dict)} 只股票的数据")
        
        # 准备数据
        all_dates = sorted(set([date for data in data_dict.values() for date in data.index]))
        
        # 初始化结果
        self.results = AStockBacktestResult(
            strategy_name=strategy_type,
            parameters=strategy_params or {}
        )
        self.results.start_date = all_dates[0]
        self.results.end_date = all_dates[-1]
        
        # 初始化多因子模型
        if strategy_type == "multi_factor":
            print("\n正在训练多因子模型...")
            self._init_multi_factor_model(data_dict)
        
        # 主回测循环
        print("\n开始回测...")
        portfolio_values = []
        trade_list = []
        
        for date in tqdm(all_dates, desc="回测进度"):
            # 获取当日数据
            daily_data = {}
            for symbol, data in data_dict.items():
                if date in data.index:
                    daily_data[symbol] = data.loc[[date]]
            
            if not daily_data:
                continue
            
            # 生成信号
            signals = self._generate_signals(daily_data, date)
            
            # 执行交易
            for symbol, signal in signals.items():
                if signal != 0:
                    self._execute_trade(symbol, signal, daily_data[symbol])
            
            # 更新持仓价格
            self._update_position_prices(daily_data)
            
            # 记录组合价值
            portfolio_values.append({
                'date': date,
                'total_value': self.trading_engine.portfolio.total_value,
                'cash': self.trading_engine.portfolio.cash,
                'num_positions': len(self.trading_engine.portfolio.positions)
            })
            
            # 记录持仓
            self.position_history.append({
                'date': date,
                'positions': {k: v.__dict__.copy() for k, v in self.trading_engine.portfolio.positions.items()}
            })
        
        # 处理交易历史
        if self.trading_engine.trade_history:
            trades_df = pd.DataFrame(self.trading_engine.trade_history)
            trades_df['date'] = pd.to_datetime(trades_df['timestamp'])
            self.results.trades = trades_df
            self.results.transaction_cost = trades_df['commission'].sum()
        
        # 构建权益曲线
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_df.set_index('date', inplace=True)
        self.results.equity_curve = portfolio_df['total_value']
        
        # 计算收益
        self.results.returns = self.results.equity_curve.pct_change().dropna()
        
        # 计算指标
        self.results.calculate_metrics()
        
        # 打印结果
        self._print_summary()
        
        return self.results
    
    def _init_multi_factor_model(self, data_dict: Dict[str, pd.DataFrame]):
        """初始化多因子模型。"""
        # 合并所有股票数据用于训练
        all_factors = []
        all_returns = []
        
        for symbol, data in data_dict.items():
            # 计算因子
            factors = factor_engine.compute_all_factors(data)
            factors['symbol'] = symbol
            factors['date'] = factors.index
            all_factors.append(factors)
            
            # 计算未来收益
            returns = data['close'].pct_change().shift(-1).dropna()
            returns.name = symbol
            all_returns.append(returns)
        
        if all_factors:
            combined_factors = pd.concat(all_factors)
            
            # 简单的时序因子模型
            self.multi_factor_model = MultiFactorModel(
                factors=combined_factors.drop(['symbol', 'date'], axis=1),
                returns=pd.concat(all_returns),
                method=FactorCombinationMethod.IC_WEIGHTED
            )
            self.multi_factor_model.fit()
            
            self.signal_generator = SignalGenerator(self.multi_factor_model)
            print(f"多因子模型训练完成，因子权重:")
            print(self.multi_factor_model.get_factor_weights().sort_values(ascending=False)[:5])
    
    def _generate_signals(
        self,
        daily_data: Dict[str, pd.DataFrame],
        date: datetime
    ) -> Dict[str, float]:
        """生成交易信号。"""
        signals = {}
        
        if hasattr(self, 'signal_generator') and self.signal_generator:
            # 计算当日因子
            factors_list = []
            symbols = []
            
            for symbol, data in daily_data.items():
                try:
                    factors = factor_engine.compute_all_factors(data)
                    factors_list.append(factors.iloc[-1])
                    symbols.append(symbol)
                except Exception as e:
                    continue
            
            if factors_list:
                factors_df = pd.DataFrame(factors_list, index=symbols)
                
                # 生成信号
                signal_weights = self.signal_generator.generate_position_weights(
                    factors_df,
                    top_n=10,
                    long_only=True
                )
                
                signals = signal_weights.to_dict()
        
        return signals
    
    def _execute_trade(self, symbol: str, weight: float, data: pd.DataFrame):
        """执行交易。"""
        current_price = data['close'].iloc[-1]
        
        # 计算目标持仓数量
        target_value = self.trading_engine.portfolio.total_value * weight
        target_quantity = int(target_value / current_price / 100) * 100  # A股必须是100股的整数倍
        
        # 获取当前持仓
        current_quantity = 0
        if symbol in self.trading_engine.portfolio.positions:
            current_quantity = self.trading_engine.portfolio.positions[symbol].quantity
        
        # 计算需要交易的数量
        quantity_to_trade = target_quantity - current_quantity
        
        if quantity_to_trade == 0:
            return
        
        # 创建订单
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY if quantity_to_trade > 0 else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=abs(quantity_to_trade),
            price=current_price
        )
        
        # 风险检查
        risk_check = self.risk_manager.check_all(order, self.trading_engine.portfolio)
        if not risk_check:
            return
        
        # 计算执行价格（考虑滑点）
        execution_price = current_price
        if order.side == OrderSide.BUY:
            execution_price = current_price * (1 + self.slippage)
        else:
            execution_price = current_price * (1 - self.slippage)
        
        # 计算成本
        cost = order.quantity * execution_price
        commission = max(self.min_commission, cost * self.commission)
        
        # 卖出时扣除印花税
        if order.side == OrderSide.SELL:
            commission += cost * self.stamp_tax
        
        # 执行订单
        result = self.trading_engine.execute_order(order, execution_price)
        
        # 更新佣金
        if result.success:
            self.trading_engine.portfolio.cash -= commission
            self.trading_engine.portfolio._recalculate_total_value()
    
    def _update_position_prices(self, daily_data: Dict[str, pd.DataFrame]):
        """更新持仓价格。"""
        for symbol, position in self.trading_engine.portfolio.positions.items():
            if symbol in daily_data:
                new_price = daily_data[symbol]['close'].iloc[-1]
                position.update_price(new_price)
    
    def _print_summary(self):
        """打印回测摘要。"""
        metrics = self.results.metrics
        
        print(f"\n{'='*60}")
        print("回测结果摘要")
        print(f"{'='*60}")
        print(f"\n策略名称: {self.results.strategy_name}")
        print(f"参数: {self.results.parameters}")
        print(f"\n时间范围: {self.results.start_date.date()} ~ {self.results.end_date.date()}")
        print(f"交易天数: {len(self.results.equity_curve)}")
        
        print(f"\n{'='*40}")
        print("收益指标")
        print(f"{'='*40}")
        print(f"总收益率: {metrics.get('total_return', 0):.2%}")
        print(f"年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"CAGR: {metrics.get('cagr', 0):.2%}")
        
        print(f"\n{'='*40}")
        print("风险指标")
        print(f"{'='*40}")
        print(f"年化波动率: {metrics.get('volatility', 0):.2%}")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"索提诺比率: {metrics.get('sortino_ratio', 0):.2f}")
        print(f"最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        
        print(f"\n{'='*40}")
        print("交易统计")
        print(f"{'='*40}")
        print(f"交易次数: {metrics.get('num_trades', 0)}")
        print(f"胜率: {metrics.get('win_rate', 0):.1%}")
        print(f"盈亏比: {metrics.get('risk_reward_ratio', 0):.2f}")
        print(f"利润因子: {metrics.get('profit_factor', 0):.2f}")
        print(f"年化换手率: {metrics.get('turnover', 0):.2f}x")
        print(f"总交易成本: {metrics.get('transaction_cost', 0):,.2f} 元")
        
        final_value = self.results.equity_curve.iloc[-1] if self.results.equity_curve is not None else self.initial_capital
        print(f"\n{'='*40}")
        print(f"最终组合价值: {final_value:,.2f} 元")
        print(f"总盈亏: {(final_value - self.initial_capital):,.2f} 元")


# 示例用法
if __name__ == "__main__":
    # 获取沪深300成分股
    universe = data_manager.get_universe("000300")
    
    # 选取前20只股票进行回测
    symbols = universe[:20]
    
    # 创建回测引擎
    backtester = AStockBacktestEngine(
        initial_capital=1000000,
        commission=0.0003,
        slippage=0.0001,
        stamp_tax=0.001
    )
    
    # 运行回测
    result = backtester.run(
        symbols=symbols,
        start_date="20230101",
        end_date="20231231",
        strategy_type="multi_factor"
    )
    
    # 保存结果
    import json
    with open('backtest_result.json', 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    print("\n结果已保存到 backtest_result.json")
"""
OxQuant A股回测器

专门针对A股市场的回测引擎，支持A股市场规则。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from .engine import (
    BaseStrategy, TradingEngine, Order, Portfolio, 
    OrderSide, OrderType, OrderStatus, AssetClass,
    RiskManager, RiskCheckResult
)
from src.data.data_providers import data_manager, DataFrequency
from src.factors.factor_engine import factor_engine
from src.factors.multi_factor_model import MultiFactorModel, FactorCombinationMethod, SignalGenerator


class AStockBacktestResult:
    """A股回测结果容器。"""
    
    def __init__(self, strategy_name: str, parameters: Dict[str, Any]):
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.returns: pd.Series = None
        self.positions: pd.DataFrame = None
        self.trades: pd.DataFrame = None
        self.metrics: Dict[str, float] = {}
        self.equity_curve: pd.Series = None
        self.max_drawdown_curve: pd.Series = None
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.transaction_cost: float = 0.0
        
    def calculate_metrics(self) -> Dict[str, float]:
        """计算综合性能指标。"""
        if self.returns is None or len(self.returns) == 0:
            return {}
        
        returns = self.returns
        
        # 基础指标
        total_return = (returns + 1).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        cagr = annual_return
        
        # 风险指标
        volatility = returns.std() * np.sqrt(252)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        # 比率指标
        risk_free_rate = 0.02
        excess_returns = returns - risk_free_rate / 252
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        sortino_ratio = annual_return / downside_deviation if downside_deviation > 0 else 0
        calmar_ratio = abs(annual_return / max_drawdown) if max_drawdown != 0 else float('inf')
        
        # 回撤指标
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        avg_drawdown = drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0
        recovery_factor = abs(total_return / max_drawdown) if max_drawdown != 0 else float('inf')
        
        # 胜率指标
        if self.trades is not None and not self.trades.empty:
            winning_trades = self.trades[self.trades['pnl'] > 0]
            win_rate = len(winning_trades) / len(self.trades) if len(self.trades) > 0 else 0
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            losing_trades = self.trades[self.trades['pnl'] <= 0]
            avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
            profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if losing_trades['pnl'].sum() != 0 else float('inf')
            expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
            risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            win_rate = avg_win = avg_loss = profit_factor = expectancy = risk_reward_ratio = 0
        
        # 交易统计
        num_trades = len(self.trades) if self.trades is not None else 0
        max_win = self.trades['pnl'].max() if self.trades is not None and not self.trades.empty else 0
        max_loss = self.trades['pnl'].min() if self.trades is not None and not self.trades.empty else 0
        avg_trade_duration = self._calculate_avg_trade_duration()
        
        # 换手率
        turnover = self._calculate_turnover()
        
        self.metrics = {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'cagr': float(cagr),
            'volatility': float(volatility),
            'downside_deviation': float(downside_deviation),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'recovery_factor': float(recovery_factor),
            'max_drawdown': float(max_drawdown),
            'avg_drawdown': float(avg_drawdown),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'expectancy': float(expectancy),
            'risk_reward_ratio': float(risk_reward_ratio),
            'num_trades': num_trades,
            'max_win': float(max_win),
            'max_loss': float(max_loss),
            'avg_trade_duration_days': float(avg_trade_duration),
            'turnover': float(turnover),
            'transaction_cost': float(self.transaction_cost)
        }
        
        return self.metrics
    
    def _calculate_avg_trade_duration(self) -> float:
        """计算平均持仓天数。"""
        if self.trades is None or self.trades.empty:
            return 0.0
        
        # 简化计算：假设平均持仓1天
        return 1.0
    
    def _calculate_turnover(self) -> float:
        """计算年化换手率。"""
        if self.trades is None or self.trades.empty:
            return 0.0
        
        total_trade_value = self.trades['quantity'].mul(self.trades['price']).sum()
        avg_portfolio_value = self.equity_curve.mean() if self.equity_curve is not None else 1
        
        if avg_portfolio_value == 0:
            return 0.0
        
        return total_trade_value / avg_portfolio_value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于序列化。"""
        return {
            'strategy_name': self.strategy_name,
            'parameters': self.parameters,
            'metrics': self.metrics,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'num_trades': self.metrics.get('num_trades', 0),
            'total_return': self.metrics.get('total_return', 0),
            'sharpe_ratio': self.metrics.get('sharpe_ratio', 0),
            'max_drawdown': self.metrics.get('max_drawdown', 0)
        }


class AStockBacktestEngine:
    """A股专用回测引擎。"""
    
    def __init__(
        self,
        strategy: Optional[BaseStrategy] = None,
        initial_capital: float = 1000000,
        commission: float = 0.0003,  # A股佣金约万3
        slippage: float = 0.0001,    # 滑点
        stamp_tax: float = 0.001,     # 印花税千1（仅卖出）
        min_commission: float = 5.0   # 最低佣金5元
    ):
        
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        
        # A股市场规则
        self.market_open_time = '09:30'
        self.market_close_time = '15:00'
        self.lunch_break_start = '11:30'
        self.lunch_break_end = '13:00'
        
        # 交易引擎
        self.trading_engine = TradingEngine(
            initial_capital=initial_capital,
            commission_rate=commission
        )
        
        # 风险管理器
        self.risk_manager = RiskManager(
            max_position_size_pct=0.1,    # 单一持仓不超过10%
            max_portfolio_risk_pct=0.02,
            max_drawdown_pct=0.1,
            max_daily_loss_pct=0.05,
            max_concentration_pct=0.2,
            max_open_positions=20
        )
        
        # 结果存储
        self.results = None
        
        # 持仓历史
        self.position_history = []
    
    def load_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        frequency: str = "daily"
    ) -> Dict[str, pd.DataFrame]:
        """加载A股数据。"""
        return data_manager.get_multi_stock_data(
            symbols, start_date, end_date, frequency
        )
    
    def run(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        strategy_type: str = "multi_factor",
        strategy_params: Optional[Dict] = None
    ) -> AStockBacktestResult:
        """运行回测。"""
        print(f"\n{'='*60}")
        print(f"A股回测引擎启动")
        print(f"{'='*60}")
        print(f"策略类型: {strategy_type}")
        print(f"股票池: {len(symbols)} 只股票")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_capital:,.2f} 元")
        
        # 加载数据
        print(f"\n正在加载数据...")
        data_dict = self.load_data(symbols, start_date, end_date)
        
        if not data_dict:
            print("错误: 未能加载任何股票数据")
            return AStockBacktestResult("NoData", {})
        
        print(f"成功加载 {len(data_dict)} 只股票的数据")
        
        # 准备数据
        all_dates = sorted(set([date for data in data_dict.values() for date in data.index]))
        
        # 初始化结果
        self.results = AStockBacktestResult(
            strategy_name=strategy_type,
            parameters=strategy_params or {}
        )
        self.results.start_date = all_dates[0]
        self.results.end_date = all_dates[-1]
        
        # 初始化多因子模型
        if strategy_type == "multi_factor":
            print("\n正在训练多因子模型...")
            self._init_multi_factor_model(data_dict)
        
        # 主回测循环
        print("\n开始回测...")
        portfolio_values = []
        trade_list = []
        
        for date in tqdm(all_dates, desc="回测进度"):
            # 获取当日数据
            daily_data = {}
            for symbol, data in data_dict.items():
                if date in data.index:
                    daily_data[symbol] = data.loc[[date]]
            
            if not daily_data:
                continue
            
            # 生成信号
            signals = self._generate_signals(daily_data, date)
            
            # 执行交易
            for symbol, signal in signals.items():
                if signal != 0:
                    self._execute_trade(symbol, signal, daily_data[symbol])
            
            # 更新持仓价格
            self._update_position_prices(daily_data)
            
            # 记录组合价值
            portfolio_values.append({
                'date': date,
                'total_value': self.trading_engine.portfolio.total_value,
                'cash': self.trading_engine.portfolio.cash,
                'num_positions': len(self.trading_engine.portfolio.positions)
            })
            
            # 记录持仓
            self.position_history.append({
                'date': date,
                'positions': {k: v.__dict__.copy() for k, v in self.trading_engine.portfolio.positions.items()}
            })
        
        # 处理交易历史
        if self.trading_engine.trade_history:
            trades_df = pd.DataFrame(self.trading_engine.trade_history)
            trades_df['date'] = pd.to_datetime(trades_df['timestamp'])
            self.results.trades = trades_df
            self.results.transaction_cost = trades_df['commission'].sum()
        
        # 构建权益曲线
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_df.set_index('date', inplace=True)
        self.results.equity_curve = portfolio_df['total_value']
        
        # 计算收益
        self.results.returns = self.results.equity_curve.pct_change().dropna()
        
        # 计算指标
        self.results.calculate_metrics()
        
        # 打印结果
        self._print_summary()
        
        return self.results
    
    def _init_multi_factor_model(self, data_dict: Dict[str, pd.DataFrame]):
        """初始化多因子模型。"""
        # 合并所有股票数据用于训练
        all_factors = []
        all_returns = []
        
        for symbol, data in data_dict.items():
            # 计算因子
            factors = factor_engine.compute_all_factors(data)
            factors['symbol'] = symbol
            factors['date'] = factors.index
            all_factors.append(factors)
            
            # 计算未来收益
            returns = data['close'].pct_change().shift(-1).dropna()
            returns.name = symbol
            all_returns.append(returns)
        
        if all_factors:
            combined_factors = pd.concat(all_factors)
            
            # 简单的时序因子模型
            self.multi_factor_model = MultiFactorModel(
                factors=combined_factors.drop(['symbol', 'date'], axis=1),
                returns=pd.concat(all_returns),
                method=FactorCombinationMethod.IC_WEIGHTED
            )
            self.multi_factor_model.fit()
            
            self.signal_generator = SignalGenerator(self.multi_factor_model)
            print(f"多因子模型训练完成，因子权重:")
            print(self.multi_factor_model.get_factor_weights().sort_values(ascending=False)[:5])
    
    def _generate_signals(
        self,
        daily_data: Dict[str, pd.DataFrame],
        date: datetime
    ) -> Dict[str, float]:
        """生成交易信号。"""
        signals = {}
        
        if hasattr(self, 'signal_generator') and self.signal_generator:
            # 计算当日因子
            factors_list = []
            symbols = []
            
            for symbol, data in daily_data.items():
                try:
                    factors = factor_engine.compute_all_factors(data)
                    factors_list.append(factors.iloc[-1])
                    symbols.append(symbol)
                except Exception as e:
                    continue
            
            if factors_list:
                factors_df = pd.DataFrame(factors_list, index=symbols)
                
                # 生成信号
                signal_weights = self.signal_generator.generate_position_weights(
                    factors_df,
                    top_n=10,
                    long_only=True
                )
                
                signals = signal_weights.to_dict()
        
        return signals
    
    def _execute_trade(self, symbol: str, weight: float, data: pd.DataFrame):
        """执行交易。"""
        current_price = data['close'].iloc[-1]
        
        # 计算目标持仓数量
        target_value = self.trading_engine.portfolio.total_value * weight
        target_quantity = int(target_value / current_price / 100) * 100  # A股必须是100股的整数倍
        
        # 获取当前持仓
        current_quantity = 0
        if symbol in self.trading_engine.portfolio.positions:
            current_quantity = self.trading_engine.portfolio.positions[symbol].quantity
        
        # 计算需要交易的数量
        quantity_to_trade = target_quantity - current_quantity
        
        if quantity_to_trade == 0:
            return
        
        # 创建订单
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY if quantity_to_trade > 0 else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=abs(quantity_to_trade),
            price=current_price
        )
        
        # 风险检查
        risk_check = self.risk_manager.check_all(order, self.trading_engine.portfolio)
        if not risk_check:
            return
        
        # 计算执行价格（考虑滑点）
        execution_price = current_price
        if order.side == OrderSide.BUY:
            execution_price = current_price * (1 + self.slippage)
        else:
            execution_price = current_price * (1 - self.slippage)
        
        # 计算成本
        cost = order.quantity * execution_price
        commission = max(self.min_commission, cost * self.commission)
        
        # 卖出时扣除印花税
        if order.side == OrderSide.SELL:
            commission += cost * self.stamp_tax
        
        # 执行订单
        result = self.trading_engine.execute_order(order, execution_price)
        
        # 更新佣金
        if result.success:
            self.trading_engine.portfolio.cash -= commission
            self.trading_engine.portfolio._recalculate_total_value()
    
    def _update_position_prices(self, daily_data: Dict[str, pd.DataFrame]):
        """更新持仓价格。"""
        for symbol, position in self.trading_engine.portfolio.positions.items():
            if symbol in daily_data:
                new_price = daily_data[symbol]['close'].iloc[-1]
                position.update_price(new_price)
    
    def _print_summary(self):
        """打印回测摘要。"""
        metrics = self.results.metrics
        
        print(f"\n{'='*60}")
        print("回测结果摘要")
        print(f"{'='*60}")
        print(f"\n策略名称: {self.results.strategy_name}")
        print(f"参数: {self.results.parameters}")
        print(f"\n时间范围: {self.results.start_date.date()} ~ {self.results.end_date.date()}")
        print(f"交易天数: {len(self.results.equity_curve)}")
        
        print(f"\n{'='*40}")
        print("收益指标")
        print(f"{'='*40}")
        print(f"总收益率: {metrics.get('total_return', 0):.2%}")
        print(f"年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"CAGR: {metrics.get('cagr', 0):.2%}")
        
        print(f"\n{'='*40}")
        print("风险指标")
        print(f"{'='*40}")
        print(f"年化波动率: {metrics.get('volatility', 0):.2%}")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"索提诺比率: {metrics.get('sortino_ratio', 0):.2f}")
        print(f"最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        
        print(f"\n{'='*40}")
        print("交易统计")
        print(f"{'='*40}")
        print(f"交易次数: {metrics.get('num_trades', 0)}")
        print(f"胜率: {metrics.get('win_rate', 0):.1%}")
        print(f"盈亏比: {metrics.get('risk_reward_ratio', 0):.2f}")
        print(f"利润因子: {metrics.get('profit_factor', 0):.2f}")
        print(f"年化换手率: {metrics.get('turnover', 0):.2f}x")
        print(f"总交易成本: {metrics.get('transaction_cost', 0):,.2f} 元")
        
        final_value = self.results.equity_curve.iloc[-1] if self.results.equity_curve is not None else self.initial_capital
        print(f"\n{'='*40}")
        print(f"最终组合价值: {final_value:,.2f} 元")
        print(f"总盈亏: {(final_value - self.initial_capital):,.2f} 元")


# 示例用法
if __name__ == "__main__":
    # 获取沪深300成分股
    universe = data_manager.get_universe("000300")
    
    # 选取前20只股票进行回测
    symbols = universe[:20]
    
    # 创建回测引擎
    backtester = AStockBacktestEngine(
        initial_capital=1000000,
        commission=0.0003,
        slippage=0.0001,
        stamp_tax=0.001
    )
    
    # 运行回测
    result = backtester.run(
        symbols=symbols,
        start_date="20230101",
        end_date="20231231",
        strategy_type="multi_factor"
    )
    
    # 保存结果
    import json
    with open('backtest_result.json', 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    print("\n结果已保存到 backtest_result.json")
"""
OxQuant A股回测器

专门针对A股市场的回测引擎，支持A股市场规则。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from .engine import (
    BaseStrategy, TradingEngine, Order, Portfolio, 
    OrderSide, OrderType, OrderStatus, AssetClass,
    RiskManager, RiskCheckResult
)
from src.data.data_providers import data_manager, DataFrequency
from src.factors.factor_engine import factor_engine
from src.factors.multi_factor_model import MultiFactorModel, FactorCombinationMethod, SignalGenerator


class AStockBacktestResult:
    """A股回测结果容器。"""
    
    def __init__(self, strategy_name: str, parameters: Dict[str, Any]):
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.returns: pd.Series = None
        self.positions: pd.DataFrame = None
        self.trades: pd.DataFrame = None
        self.metrics: Dict[str, float] = {}
        self.equity_curve: pd.Series = None
        self.max_drawdown_curve: pd.Series = None
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.transaction_cost: float = 0.0
        
    def calculate_metrics(self) -> Dict[str, float]:
        """计算综合性能指标。"""
        if self.returns is None or len(self.returns) == 0:
            return {}
        
        returns = self.returns
        
        # 基础指标
        total_return = (returns + 1).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        cagr = annual_return
        
        # 风险指标
        volatility = returns.std() * np.sqrt(252)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        # 比率指标
        risk_free_rate = 0.02
        excess_returns = returns - risk_free_rate / 252
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        sortino_ratio = annual_return / downside_deviation if downside_deviation > 0 else 0
        calmar_ratio = abs(annual_return / max_drawdown) if max_drawdown != 0 else float('inf')
        
        # 回撤指标
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        avg_drawdown = drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0
        recovery_factor = abs(total_return / max_drawdown) if max_drawdown != 0 else float('inf')
        
        # 胜率指标
        if self.trades is not None and not self.trades.empty:
            winning_trades = self.trades[self.trades['pnl'] > 0]
            win_rate = len(winning_trades) / len(self.trades) if len(self.trades) > 0 else 0
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            losing_trades = self.trades[self.trades['pnl'] <= 0]
            avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
            profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if losing_trades['pnl'].sum() != 0 else float('inf')
            expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
            risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            win_rate = avg_win = avg_loss = profit_factor = expectancy = risk_reward_ratio = 0
        
        # 交易统计
        num_trades = len(self.trades) if self.trades is not None else 0
        max_win = self.trades['pnl'].max() if self.trades is not None and not self.trades.empty else 0
        max_loss = self.trades['pnl'].min() if self.trades is not None and not self.trades.empty else 0
        avg_trade_duration = self._calculate_avg_trade_duration()
        
        # 换手率
        turnover = self._calculate_turnover()
        
        self.metrics = {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'cagr': float(cagr),
            'volatility': float(volatility),
            'downside_deviation': float(downside_deviation),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'recovery_factor': float(recovery_factor),
            'max_drawdown': float(max_drawdown),
            'avg_drawdown': float(avg_drawdown),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'expectancy': float(expectancy),
            'risk_reward_ratio': float(risk_reward_ratio),
            'num_trades': num_trades,
            'max_win': float(max_win),
            'max_loss': float(max_loss),
            'avg_trade_duration_days': float(avg_trade_duration),
            'turnover': float(turnover),
            'transaction_cost': float(self.transaction_cost)
        }
        
        return self.metrics
    
    def _calculate_avg_trade_duration(self) -> float:
        """计算平均持仓天数。"""
        if self.trades is None or self.trades.empty:
            return 0.0
        
        # 简化计算：假设平均持仓1天
        return 1.0
    
    def _calculate_turnover(self) -> float:
        """计算年化换手率。"""
        if self.trades is None or self.trades.empty:
            return 0.0
        
        total_trade_value = self.trades['quantity'].mul(self.trades['price']).sum()
        avg_portfolio_value = self.equity_curve.mean() if self.equity_curve is not None else 1
        
        if avg_portfolio_value == 0:
            return 0.0
        
        return total_trade_value / avg_portfolio_value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于序列化。"""
        return {
            'strategy_name': self.strategy_name,
            'parameters': self.parameters,
            'metrics': self.metrics,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'num_trades': self.metrics.get('num_trades', 0),
            'total_return': self.metrics.get('total_return', 0),
            'sharpe_ratio': self.metrics.get('sharpe_ratio', 0),
            'max_drawdown': self.metrics.get('max_drawdown', 0)
        }


class AStockBacktestEngine:
    """A股专用回测引擎。"""
    
    def __init__(
        self,
        strategy: Optional[BaseStrategy] = None,
        initial_capital: float = 1000000,
        commission: float = 0.0003,  # A股佣金约万3
        slippage: float = 0.0001,    # 滑点
        stamp_tax: float = 0.001,     # 印花税千1（仅卖出）
        min_commission: float = 5.0   # 最低佣金5元
    ):
        
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        
        # A股市场规则
        self.market_open_time = '09:30'
        self.market_close_time = '15:00'
        self.lunch_break_start = '11:30'
        self.lunch_break_end = '13:00'
        
        # 交易引擎
        self.trading_engine = TradingEngine(
            initial_capital=initial_capital,
            commission_rate=commission
        )
        
        # 风险管理器
        self.risk_manager = RiskManager(
            max_position_size_pct=0.1,    # 单一持仓不超过10%
            max_portfolio_risk_pct=0.02,
            max_drawdown_pct=0.1,
            max_daily_loss_pct=0.05,
            max_concentration_pct=0.2,
            max_open_positions=20
        )
        
        # 结果存储
        self.results = None
        
        # 持仓历史
        self.position_history = []
    
    def load_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        frequency: str = "daily"
    ) -> Dict[str, pd.DataFrame]:
        """加载A股数据。"""
        return data_manager.get_multi_stock_data(
            symbols, start_date, end_date, frequency
        )
    
    def run(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        strategy_type: str = "multi_factor",
        strategy_params: Optional[Dict] = None
    ) -> AStockBacktestResult:
        """运行回测。"""
        print(f"\n{'='*60}")
        print(f"A股回测引擎启动")
        print(f"{'='*60}")
        print(f"策略类型: {strategy_type}")
        print(f"股票池: {len(symbols)} 只股票")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_capital:,.2f} 元")
        
        # 加载数据
        print(f"\n正在加载数据...")
        data_dict = self.load_data(symbols, start_date, end_date)
        
        if not data_dict:
            print("错误: 未能加载任何股票数据")
            return AStockBacktestResult("NoData", {})
        
        print(f"成功加载 {len(data_dict)} 只股票的数据")
        
        # 准备数据
        all_dates = sorted(set([date for data in data_dict.values() for date in data.index]))
        
        # 初始化结果
        self.results = AStockBacktestResult(
            strategy_name=strategy_type,
            parameters=strategy_params or {}
        )
        self.results.start_date = all_dates[0]
        self.results.end_date = all_dates[-1]
        
        # 初始化多因子模型
        if strategy_type == "multi_factor":
            print("\n正在训练多因子模型...")
            self._init_multi_factor_model(data_dict)
        
        # 主回测循环
        print("\n开始回测...")
        portfolio_values = []
        trade_list = []
        
        for date in tqdm(all_dates, desc="回测进度"):
            # 获取当日数据
            daily_data = {}
            for symbol, data in data_dict.items():
                if date in data.index:
                    daily_data[symbol] = data.loc[[date]]
            
            if not daily_data:
                continue
            
            # 生成信号
            signals = self._generate_signals(daily_data, date)
            
            # 执行交易
            for symbol, signal in signals.items():
                if signal != 0:
                    self._execute_trade(symbol, signal, daily_data[symbol])
            
            # 更新持仓价格
            self._update_position_prices(daily_data)
            
            # 记录组合价值
            portfolio_values.append({
                'date': date,
                'total_value': self.trading_engine.portfolio.total_value,
                'cash': self.trading_engine.portfolio.cash,
                'num_positions': len(self.trading_engine.portfolio.positions)
            })
            
            # 记录持仓
            self.position_history.append({
                'date': date,
                'positions': {k: v.__dict__.copy() for k, v in self.trading_engine.portfolio.positions.items()}
            })
        
        # 处理交易历史
        if self.trading_engine.trade_history:
            trades_df = pd.DataFrame(self.trading_engine.trade_history)
            trades_df['date'] = pd.to_datetime(trades_df['timestamp'])
            self.results.trades = trades_df
            self.results.transaction_cost = trades_df['commission'].sum()
        
        # 构建权益曲线
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_df.set_index('date', inplace=True)
        self.results.equity_curve = portfolio_df['total_value']
        
        # 计算收益
        self.results.returns = self.results.equity_curve.pct_change().dropna()
        
        # 计算指标
        self.results.calculate_metrics()
        
        # 打印结果
        self._print_summary()
        
        return self.results
    
    def _init_multi_factor_model(self, data_dict: Dict[str, pd.DataFrame]):
        """初始化多因子模型。"""
        # 合并所有股票数据用于训练
        all_factors = []
        all_returns = []
        
        for symbol, data in data_dict.items():
            # 计算因子
            factors = factor_engine.compute_all_factors(data)
            factors['symbol'] = symbol
            factors['date'] = factors.index
            all_factors.append(factors)
            
            # 计算未来收益
            returns = data['close'].pct_change().shift(-1).dropna()
            returns.name = symbol
            all_returns.append(returns)
        
        if all_factors:
            combined_factors = pd.concat(all_factors)
            
            # 简单的时序因子模型
            self.multi_factor_model = MultiFactorModel(
                factors=combined_factors.drop(['symbol', 'date'], axis=1),
                returns=pd.concat(all_returns),
                method=FactorCombinationMethod.IC_WEIGHTED
            )
            self.multi_factor_model.fit()
            
            self.signal_generator = SignalGenerator(self.multi_factor_model)
            print(f"多因子模型训练完成，因子权重:")
            print(self.multi_factor_model.get_factor_weights().sort_values(ascending=False)[:5])
    
    def _generate_signals(
        self,
        daily_data: Dict[str, pd.DataFrame],
        date: datetime
    ) -> Dict[str, float]:
        """生成交易信号。"""
        signals = {}
        
        if hasattr(self, 'signal_generator') and self.signal_generator:
            # 计算当日因子
            factors_list = []
            symbols = []
            
            for symbol, data in daily_data.items():
                try:
                    factors = factor_engine.compute_all_factors(data)
                    factors_list.append(factors.iloc[-1])
                    symbols.append(symbol)
                except Exception as e:
                    continue
            
            if factors_list:
                factors_df = pd.DataFrame(factors_list, index=symbols)
                
                # 生成信号
                signal_weights = self.signal_generator.generate_position_weights(
                    factors_df,
                    top_n=10,
                    long_only=True
                )
                
                signals = signal_weights.to_dict()
        
        return signals
    
    def _execute_trade(self, symbol: str, weight: float, data: pd.DataFrame):
        """执行交易。"""
        current_price = data['close'].iloc[-1]
        
        # 计算目标持仓数量
        target_value = self.trading_engine.portfolio.total_value * weight
        target_quantity = int(target_value / current_price / 100) * 100  # A股必须是100股的整数倍
        
        # 获取当前持仓
        current_quantity = 0
        if symbol in self.trading_engine.portfolio.positions:
            current_quantity = self.trading_engine.portfolio.positions[symbol].quantity
        
        # 计算需要交易的数量
        quantity_to_trade = target_quantity - current_quantity
        
        if quantity_to_trade == 0:
            return
        
        # 创建订单
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY if quantity_to_trade > 0 else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=abs(quantity_to_trade),
            price=current_price
        )
        
        # 风险检查
        risk_check = self.risk_manager.check_all(order, self.trading_engine.portfolio)
        if not risk_check:
            return
        
        # 计算执行价格（考虑滑点）
        execution_price = current_price
        if order.side == OrderSide.BUY:
            execution_price = current_price * (1 + self.slippage)
        else:
            execution_price = current_price * (1 - self.slippage)
        
        # 计算成本
        cost = order.quantity * execution_price
        commission = max(self.min_commission, cost * self.commission)
        
        # 卖出时扣除印花税
        if order.side == OrderSide.SELL:
            commission += cost * self.stamp_tax
        
        # 执行订单
        result = self.trading_engine.execute_order(order, execution_price)
        
        # 更新佣金
        if result.success:
            self.trading_engine.portfolio.cash -= commission
            self.trading_engine.portfolio._recalculate_total_value()
    
    def _update_position_prices(self, daily_data: Dict[str, pd.DataFrame]):
        """更新持仓价格。"""
        for symbol, position in self.trading_engine.portfolio.positions.items():
            if symbol in daily_data:
                new_price = daily_data[symbol]['close'].iloc[-1]
                position.update_price(new_price)
    
    def _print_summary(self):
        """打印回测摘要。"""
        metrics = self.results.metrics
        
        print(f"\n{'='*60}")
        print("回测结果摘要")
        print(f"{'='*60}")
        print(f"\n策略名称: {self.results.strategy_name}")
        print(f"参数: {self.results.parameters}")
        print(f"\n时间范围: {self.results.start_date.date()} ~ {self.results.end_date.date()}")
        print(f"交易天数: {len(self.results.equity_curve)}")
        
        print(f"\n{'='*40}")
        print("收益指标")
        print(f"{'='*40}")
        print(f"总收益率: {metrics.get('total_return', 0):.2%}")
        print(f"年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"CAGR: {metrics.get('cagr', 0):.2%}")
        
        print(f"\n{'='*40}")
        print("风险指标")
        print(f"{'='*40}")
        print(f"年化波动率: {metrics.get('volatility', 0):.2%}")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"索提诺比率: {metrics.get('sortino_ratio', 0):.2f}")
        print(f"最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        
        print(f"\n{'='*40}")
        print("交易统计")
        print(f"{'='*40}")
        print(f"交易次数: {metrics.get('num_trades', 0)}")
        print(f"胜率: {metrics.get('win_rate', 0):.1%}")
        print(f"盈亏比: {metrics.get('risk_reward_ratio', 0):.2f}")
        print(f"利润因子: {metrics.get('profit_factor', 0):.2f}")
        print(f"年化换手率: {metrics.get('turnover', 0):.2f}x")
        print(f"总交易成本: {metrics.get('transaction_cost', 0):,.2f} 元")
        
        final_value = self.results.equity_curve.iloc[-1] if self.results.equity_curve is not None else self.initial_capital
        print(f"\n{'='*40}")
        print(f"最终组合价值: {final_value:,.2f} 元")
        print(f"总盈亏: {(final_value - self.initial_capital):,.2f} 元")


# 示例用法
if __name__ == "__main__":
    # 获取沪深300成分股
    universe = data_manager.get_universe("000300")
    
    # 选取前20只股票进行回测
    symbols = universe[:20]
    
    # 创建回测引擎
    backtester = AStockBacktestEngine(
        initial_capital=1000000,
        commission=0.0003,
        slippage=0.0001,
        stamp_tax=0.001
    )
    
    # 运行回测
    result = backtester.run(
        symbols=symbols,
        start_date="20230101",
        end_date="20231231",
        strategy_type="multi_factor"
    )
    
    # 保存结果
    import json
    with open('backtest_result.json', 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    print("\n结果已保存到 backtest_result.json")
"""
OxQuant A股回测器

专门针对A股市场的回测引擎，支持A股市场规则。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from .engine import (
    BaseStrategy, TradingEngine, Order, Portfolio, 
    OrderSide, OrderType, OrderStatus, AssetClass,
    RiskManager, RiskCheckResult
)
from src.data.data_providers import data_manager, DataFrequency
from src.factors.factor_engine import factor_engine
from src.factors.multi_factor_model import MultiFactorModel, FactorCombinationMethod, SignalGenerator


class AStockBacktestResult:
    """A股回测结果容器。"""
    
    def __init__(self, strategy_name: str, parameters: Dict[str, Any]):
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.returns: pd.Series = None
        self.positions: pd.DataFrame = None
        self.trades: pd.DataFrame = None
        self.metrics: Dict[str, float] = {}
        self.equity_curve: pd.Series = None
        self.max_drawdown_curve: pd.Series = None
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.transaction_cost: float = 0.0
        
    def calculate_metrics(self) -> Dict[str, float]:
        """计算综合性能指标。"""
        if self.returns is None or len(self.returns) == 0:
            return {}
        
        returns = self.returns
        
        # 基础指标
        total_return = (returns + 1).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        cagr = annual_return
        
        # 风险指标
        volatility = returns.std() * np.sqrt(252)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        # 比率指标
        risk_free_rate = 0.02
        excess_returns = returns - risk_free_rate / 252
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        sortino_ratio = annual_return / downside_deviation if downside_deviation > 0 else 0
        calmar_ratio = abs(annual_return / max_drawdown) if max_drawdown != 0 else float('inf')
        
        # 回撤指标
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        avg_drawdown = drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0
        recovery_factor = abs(total_return / max_drawdown) if max_drawdown != 0 else float('inf')
        
        # 胜率指标
        if self.trades is not None and not self.trades.empty:
            winning_trades = self.trades[self.trades['pnl'] > 0]
            win_rate = len(winning_trades) / len(self.trades) if len(self.trades) > 0 else 0
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            losing_trades = self.trades[self.trades['pnl'] <= 0]
            avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
            profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if losing_trades['pnl'].sum() != 0 else float('inf')
            expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
            risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            win_rate = avg_win = avg_loss = profit_factor = expectancy = risk_reward_ratio = 0
        
        # 交易统计
        num_trades = len(self.trades) if self.trades is not None else 0
        max_win = self.trades['pnl'].max() if self.trades is not None and not self.trades.empty else 0
        max_loss = self.trades['pnl'].min() if self.trades is not None and not self.trades.empty else 0
        avg_trade_duration = self._calculate_avg_trade_duration()
        
        # 换手率
        turnover = self._calculate_turnover()
        
        self.metrics = {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'cagr': float(cagr),
            'volatility': float(volatility),
            'downside_deviation': float(downside_deviation),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'recovery_factor': float(recovery_factor),
            'max_drawdown': float(max_drawdown),
            'avg_drawdown': float(avg_drawdown),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'expectancy': float(expectancy),
            'risk_reward_ratio': float(risk_reward_ratio),
            'num_trades': num_trades,
            'max_win': float(max_win),
            'max_loss': float(max_loss),
            'avg_trade_duration_days': float(avg_trade_duration),
            'turnover': float(turnover),
            'transaction_cost': float(self.transaction_cost)
        }
        
        return self.metrics
    
    def _calculate_avg_trade_duration(self) -> float:
        """计算平均持仓天数。"""
        if self.trades is None or self.trades.empty:
            return 0.0
        
        # 简化计算：假设平均持仓1天
        return 1.0
    
    def _calculate_turnover(self) -> float:
        """计算年化换手率。"""
        if self.trades is None or self.trades.empty:
            return 0.0
        
        total_trade_value = self.trades['quantity'].mul(self.trades['price']).sum()
        avg_portfolio_value = self.equity_curve.mean() if self.equity_curve is not None else 1
        
        if avg_portfolio_value == 0:
            return 0.0
        
        return total_trade_value / avg_portfolio_value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于序列化。"""
        return {
            'strategy_name': self.strategy_name,
            'parameters': self.parameters,
            'metrics': self.metrics,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'num_trades': self.metrics.get('num_trades', 0),
            'total_return': self.metrics.get('total_return', 0),
            'sharpe_ratio': self.metrics.get('sharpe_ratio', 0),
            'max_drawdown': self.metrics.get('max_drawdown', 0)
        }


class AStockBacktestEngine:
    """A股专用回测引擎。"""
    
    def __init__(
        self,
        strategy: Optional[BaseStrategy] = None,
        initial_capital: float = 1000000,
        commission: float = 0.0003,  # A股佣金约万3
        slippage: float = 0.0001,    # 滑点
        stamp_tax: float = 0.001,     # 印花税千1（仅卖出）
        min_commission: float = 5.0   # 最低佣金5元
    ):
        
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        
        # A股市场规则
        self.market_open_time = '09:30'
        self.market_close_time = '15:00'
        self.lunch_break_start = '11:30'
        self.lunch_break_end = '13:00'
        
        # 交易引擎
        self.trading_engine = TradingEngine(
            initial_capital=initial_capital,
            commission_rate=commission
        )
        
        # 风险管理器
        self.risk_manager = RiskManager(
            max_position_size_pct=0.1,    # 单一持仓不超过10%
            max_portfolio_risk_pct=0.02,
            max_drawdown_pct=0.1,
            max_daily_loss_pct=0.05,
            max_concentration_pct=0.2,
            max_open_positions=20
        )
        
        # 结果存储
        self.results = None
        
        # 持仓历史
        self.position_history = []
    
    def load_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        frequency: str = "daily"
    ) -> Dict[str, pd.DataFrame]:
        """加载A股数据。"""
        return data_manager.get_multi_stock_data(
            symbols, start_date, end_date, frequency
        )
    
    def run(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        strategy_type: str = "multi_factor",
        strategy_params: Optional[Dict] = None
    ) -> AStockBacktestResult:
        """运行回测。"""
        print(f"\n{'='*60}")
        print(f"A股回测引擎启动")
        print(f"{'='*60}")
        print(f"策略类型: {strategy_type}")
        print(f"股票池: {len(symbols)} 只股票")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_capital:,.2f} 元")
        
        # 加载数据
        print(f"\n正在加载数据...")
        data_dict = self.load_data(symbols, start_date, end_date)
        
        if not data_dict:
            print("错误: 未能加载任何股票数据")
            return AStockBacktestResult("NoData", {})
        
        print(f"成功加载 {len(data_dict)} 只股票的数据")
        
        # 准备数据
        all_dates = sorted(set([date for data in data_dict.values() for date in data.index]))
        
        # 初始化结果
        self.results = AStockBacktestResult(
            strategy_name=strategy_type,
            parameters=strategy_params or {}
        )
        self.results.start_date = all_dates[0]
        self.results.end_date = all_dates[-1]
        
        # 初始化多因子模型
        if strategy_type == "multi_factor":
            print("\n正在训练多因子模型...")
            self._init_multi_factor_model(data_dict)
        
        # 主回测循环
        print("\n开始回测...")
        portfolio_values = []
        trade_list = []
        
        for date in tqdm(all_dates, desc="回测进度"):
            # 获取当日数据
            daily_data = {}
            for symbol, data in data_dict.items():
                if date in data.index:
                    daily_data[symbol] = data.loc[[date]]
            
            if not daily_data:
                continue
            
            # 生成信号
            signals = self._generate_signals(daily_data, date)
            
            # 执行交易
            for symbol, signal in signals.items():
                if signal != 0:
                    self._execute_trade(symbol, signal, daily_data[symbol])
            
            # 更新持仓价格
            self._update_position_prices(daily_data)
            
            # 记录组合价值
            portfolio_values.append({
                'date': date,
                'total_value': self.trading_engine.portfolio.total_value,
                'cash': self.trading_engine.portfolio.cash,
                'num_positions': len(self.trading_engine.portfolio.positions)
            })
            
            # 记录持仓
            self.position_history.append({
                'date': date,
                'positions': {k: v.__dict__.copy() for k, v in self.trading_engine.portfolio.positions.items()}
            })
        
        # 处理交易历史
        if self.trading_engine.trade_history:
            trades_df = pd.DataFrame(self.trading_engine.trade_history)
            trades_df['date'] = pd.to_datetime(trades_df['timestamp'])
            self.results.trades = trades_df
            self.results.transaction_cost = trades_df['commission'].sum()
        
        # 构建权益曲线
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_df.set_index('date', inplace=True)
        self.results.equity_curve = portfolio_df['total_value']
        
        # 计算收益
        self.results.returns = self.results.equity_curve.pct_change().dropna()
        
        # 计算指标
        self.results.calculate_metrics()
        
        # 打印结果
        self._print_summary()
        
        return self.results
    
    def _init_multi_factor_model(self, data_dict: Dict[str, pd.DataFrame]):
        """初始化多因子模型。"""
        # 合并所有股票数据用于训练
        all_factors = []
        all_returns = []
        
        for symbol, data in data_dict.items():
            # 计算因子
            factors = factor_engine.compute_all_factors(data)
            factors['symbol'] = symbol
            factors['date'] = factors.index
            all_factors.append(factors)
            
            # 计算未来收益
            returns = data['close'].pct_change().shift(-1).dropna()
            returns.name = symbol
            all_returns.append(returns)
        
        if all_factors:
            combined_factors = pd.concat(all_factors)
            
            # 简单的时序因子模型
            self.multi_factor_model = MultiFactorModel(
                factors=combined_factors.drop(['symbol', 'date'], axis=1),
                returns=pd.concat(all_returns),
                method=FactorCombinationMethod.IC_WEIGHTED
            )
            self.multi_factor_model.fit()
            
            self.signal_generator = SignalGenerator(self.multi_factor_model)
            print(f"多因子模型训练完成，因子权重:")
            print(self.multi_factor_model.get_factor_weights().sort_values(ascending=False)[:5])
    
    def _generate_signals(
        self,
        daily_data: Dict[str, pd.DataFrame],
        date: datetime
    ) -> Dict[str, float]:
        """生成交易信号。"""
        signals = {}
        
        if hasattr(self, 'signal_generator') and self.signal_generator:
            # 计算当日因子
            factors_list = []
            symbols = []
            
            for symbol, data in daily_data.items():
                try:
                    factors = factor_engine.compute_all_factors(data)
                    factors_list.append(factors.iloc[-1])
                    symbols.append(symbol)
                except Exception as e:
                    continue
            
            if factors_list:
                factors_df = pd.DataFrame(factors_list, index=symbols)
                
                # 生成信号
                signal_weights = self.signal_generator.generate_position_weights(
                    factors_df,
                    top_n=10,
                    long_only=True
                )
                
                signals = signal_weights.to_dict()
        
        return signals
    
    def _execute_trade(self, symbol: str, weight: float, data: pd.DataFrame):
        """执行交易。"""
        current_price = data['close'].iloc[-1]
        
        # 计算目标持仓数量
        target_value = self.trading_engine.portfolio.total_value * weight
        target_quantity = int(target_value / current_price / 100) * 100  # A股必须是100股的整数倍
        
        # 获取当前持仓
        current_quantity = 0
        if symbol in self.trading_engine.portfolio.positions:
            current_quantity = self.trading_engine.portfolio.positions[symbol].quantity
        
        # 计算需要交易的数量
        quantity_to_trade = target_quantity - current_quantity
        
        if quantity_to_trade == 0:
            return
        
        # 创建订单
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY if quantity_to_trade > 0 else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=abs(quantity_to_trade),
            price=current_price
        )
        
        # 风险检查
        risk_check = self.risk_manager.check_all(order, self.trading_engine.portfolio)
        if not risk_check:
            return
        
        # 计算执行价格（考虑滑点）
        execution_price = current_price
        if order.side == OrderSide.BUY:
            execution_price = current_price * (1 + self.slippage)
        else:
            execution_price = current_price * (1 - self.slippage)
        
        # 计算成本
        cost = order.quantity * execution_price
        commission = max(self.min_commission, cost * self.commission)
        
        # 卖出时扣除印花税
        if order.side == OrderSide.SELL:
            commission += cost * self.stamp_tax
        
        # 执行订单
        result = self.trading_engine.execute_order(order, execution_price)
        
        # 更新佣金
        if result.success:
            self.trading_engine.portfolio.cash -= commission
            self.trading_engine.portfolio._recalculate_total_value()
    
    def _update_position_prices(self, daily_data: Dict[str, pd.DataFrame]):
        """更新持仓价格。"""
        for symbol, position in self.trading_engine.portfolio.positions.items():
            if symbol in daily_data:
                new_price = daily_data[symbol]['close'].iloc[-1]
                position.update_price(new_price)
    
    def _print_summary(self):
        """打印回测摘要。"""
        metrics = self.results.metrics
        
        print(f"\n{'='*60}")
        print("回测结果摘要")
        print(f"{'='*60}")
        print(f"\n策略名称: {self.results.strategy_name}")
        print(f"参数: {self.results.parameters}")
        print(f"\n时间范围: {self.results.start_date.date()} ~ {self.results.end_date.date()}")
        print(f"交易天数: {len(self.results.equity_curve)}")
        
        print(f"\n{'='*40}")
        print("收益指标")
        print(f"{'='*40}")
        print(f"总收益率: {metrics.get('total_return', 0):.2%}")
        print(f"年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"CAGR: {metrics.get('cagr', 0):.2%}")
        
        print(f"\n{'='*40}")
        print("风险指标")
        print(f"{'='*40}")
        print(f"年化波动率: {metrics.get('volatility', 0):.2%}")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"索提诺比率: {metrics.get('sortino_ratio', 0):.2f}")
        print(f"最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        
        print(f"\n{'='*40}")
        print("交易统计")
        print(f"{'='*40}")
        print(f"交易次数: {metrics.get('num_trades', 0)}")
        print(f"胜率: {metrics.get('win_rate', 0):.1%}")
        print(f"盈亏比: {metrics.get('risk_reward_ratio', 0):.2f}")
        print(f"利润因子: {metrics.get('profit_factor', 0):.2f}")
        print(f"年化换手率: {metrics.get('turnover', 0):.2f}x")
        print(f"总交易成本: {metrics.get('transaction_cost', 0):,.2f} 元")
        
        final_value = self.results.equity_curve.iloc[-1] if self.results.equity_curve is not None else self.initial_capital
        print(f"\n{'='*40}")
        print(f"最终组合价值: {final_value:,.2f} 元")
        print(f"总盈亏: {(final_value - self.initial_capital):,.2f} 元")


# 示例用法
if __name__ == "__main__":
    # 获取沪深300成分股
    universe = data_manager.get_universe("000300")
    
    # 选取前20只股票进行回测
    symbols = universe[:20]
    
    # 创建回测引擎
    backtester = AStockBacktestEngine(
        initial_capital=1000000,
        commission=0.0003,
        slippage=0.0001,
        stamp_tax=0.001
    )
    
    # 运行回测
    result = backtester.run(
        symbols=symbols,
        start_date="20230101",
        end_date="20231231",
        strategy_type="multi_factor"
    )
    
    # 保存结果
    import json
    with open('backtest_result.json', 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    print("\n结果已保存到 backtest_result.json")