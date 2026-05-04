"""
OxQuant Simulation Trading

模拟交易模块，用于策略验证和测试。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimulationMode(Enum):
    """模拟模式。"""
    HISTORICAL = "historical"    # 历史数据回放
    REALTIME_SIM = "realtime_sim" # 实时模拟（使用实时数据）
    PAPER_TRADING = "paper_trading" # 纸盘交易


class SimulationBroker:
    """模拟券商。"""
    
    def __init__(
        self,
        initial_balance: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.0001,
        stamp_tax: float = 0.001,
        min_commission: float = 5.0
    ):
        
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage = slippage
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        
        # 持仓
        self.positions: Dict[str, dict] = {}  # symbol -> {quantity, avg_price, current_price}
        
        # 订单历史
        self.order_history = []
        
        # 交易历史
        self.trade_history = []
        
        # 账户历史
        self.account_history = []
    
    def get_balance(self) -> float:
        """获取当前余额。"""
        return self.balance
    
    def get_positions(self) -> Dict[str, dict]:
        """获取当前持仓。"""
        return self.positions
    
    def get_total_assets(self) -> float:
        """获取总资产。"""
        position_value = sum(
            pos['quantity'] * pos['current_price'] 
            for pos in self.positions.values()
        )
        return self.balance + position_value
    
    def place_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        order_id = f"SIM-{int(time.time())}-{np.random.randint(1000, 9999)}"
        
        # 模拟市场价格
        if price is None:
            price = self._get_simulated_price(symbol, side)
        
        # 计算执行价格（考虑滑点）
        execution_price = price
        if side == 'buy':
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)
        
        # 计算成本
        cost = quantity * execution_price
        commission = max(self.min_commission, cost * self.commission)
        
        if side == 'sell':
            commission += cost * self.stamp_tax
        
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'execution_price': execution_price,
            'order_type': order_type,
            'status': 'pending',
            'timestamp': datetime.now(),
            'commission': commission
        }
        
        # 执行订单
        success, message = self._execute_order(order)
        
        order['status'] = 'filled' if success else 'rejected'
        order['message'] = message
        
        self.order_history.append(order)
        
        if success:
            trade = {
                'trade_id': f"TRD-{int(time.time())}-{np.random.randint(1000, 9999)}",
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': execution_price,
                'commission': commission,
                'timestamp': datetime.now(),
                'pnl': 0.0
            }
            
            # 计算已实现盈亏（卖出时）
            if side == 'sell' and symbol in self.positions:
                pos = self.positions[symbol]
                trade['pnl'] = (execution_price - pos['avg_price']) * quantity
                pos['realized_pnl'] = pos.get('realized_pnl', 0) + trade['pnl']
            
            self.trade_history.append(trade)
        
        # 记录账户状态
        self._record_account_status()
        
        return order
    
    def _execute_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """执行订单。"""
        symbol = order['symbol']
        side = order['side']
        quantity = order['quantity']
        execution_price = order['execution_price']
        commission = order['commission']
        
        cost = quantity * execution_price
        total_cost = cost + commission
        
        if side == 'buy':
            # 买入
            if self.balance < total_cost:
                return False, "余额不足"
            
            self.balance -= total_cost
            
            if symbol in self.positions:
                # 更新持仓
                pos = self.positions[symbol]
                total_qty = pos['quantity'] + quantity
                total_cost_basis = pos['quantity'] * pos['avg_price'] + cost
                pos['quantity'] = total_qty
                pos['avg_price'] = total_cost_basis / total_qty
                pos['current_price'] = execution_price
            else:
                # 新建持仓
                self.positions[symbol] = {
                    'quantity': quantity,
                    'avg_price': execution_price,
                    'current_price': execution_price,
                    'realized_pnl': 0.0
                }
            
            return True, "买入成功"
        
        else:
            # 卖出
            if symbol not in self.positions:
                return False, "没有持仓"
            
            pos = self.positions[symbol]
            if pos['quantity'] < quantity:
                return False, "持仓不足"
            
            # 更新持仓
            pos['quantity'] -= quantity
            self.balance += (quantity * execution_price) - commission
            
            if pos['quantity'] == 0:
                del self.positions[symbol]
            
            return True, "卖出成功"
    
    def _get_simulated_price(self, symbol: str, side: str) -> float:
        """模拟获取市场价格。"""
        # 从数据提供商获取最新价格
        from src.data.data_providers import data_manager
        
        try:
            # 获取最近的历史数据
            today = datetime.now().strftime("%Y%m%d")
            data = data_manager.get_price_data(symbol, today, today)
            
            if not data.empty:
                return data['close'].iloc[-1]
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
        
        # 如果获取失败，使用随机价格
        return 100 + np.random.randn() * 10
    
    def _record_account_status(self):
        """记录账户状态。"""
        self.account_history.append({
            'timestamp': datetime.now(),
            'balance': self.balance,
            'total_assets': self.get_total_assets(),
            'num_positions': len(self.positions)
        })
    
    def update_prices(self):
        """更新持仓价格。"""
        for symbol, pos in self.positions.items():
            new_price = self._get_simulated_price(symbol, 'buy')
            pos['current_price'] = new_price
    
    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户摘要。"""
        total_assets = self.get_total_assets()
        total_return = (total_assets - self.initial_balance) / self.initial_balance
        
        # 计算未实现盈亏
        unrealized_pnl = 0
        for pos in self.positions.values():
            unrealized_pnl += (pos['current_price'] - pos['avg_price']) * pos['quantity']
        
        realized_pnl = sum(pos.get('realized_pnl', 0) for pos in self.positions.values())
        
        return {
            'balance': self.balance,
            'total_assets': total_assets,
            'total_return': total_return,
            'num_positions': len(self.positions),
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': unrealized_pnl + realized_pnl,
            'num_trades': len(self.trade_history)
        }


class SimulationEngine:
    """模拟交易引擎。"""
    
    def __init__(
        self,
        initial_capital: float = 1000000,
        mode: SimulationMode = SimulationMode.REALTIME_SIM
    ):
        
        self.mode = mode
        self.broker = SimulationBroker(initial_balance=initial_capital)
        self.running = False
        self.paused = False
        
        # 策略
        self.strategy = None
        
        # 性能统计
        self.stats = {
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'total_profit': 0,
            'total_loss': 0
        }
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def start(self):
        """启动模拟。"""
        self.running = True
        logger.info("模拟交易引擎启动")
        
        if self.mode == SimulationMode.REALTIME_SIM:
            self._run_realtime_sim()
        elif self.mode == SimulationMode.HISTORICAL:
            self._run_historical()
    
    def stop(self):
        """停止模拟。"""
        self.running = False
        logger.info("模拟交易引擎停止")
    
    def pause(self):
        """暂停模拟。"""
        self.paused = True
        logger.info("模拟交易引擎暂停")
    
    def resume(self):
        """恢复模拟。"""
        self.paused = False
        logger.info("模拟交易引擎恢复")
    
    def _run_realtime_sim(self):
        """运行实时模拟。"""
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            try:
                # 更新价格
                self.broker.update_prices()
                
                # 运行策略
                if self.strategy:
                    signals = self.strategy.generate_signals(self.broker)
                    
                    for symbol, signal in signals.items():
                        if signal != 0:
                            side = 'buy' if signal > 0 else 'sell'
                            quantity = int(abs(signal) * 100)
                            
                            if quantity > 0:
                                result = self.broker.place_order(
                                    symbol=symbol,
                                    side=side,
                                    quantity=quantity
                                )
                                
                                self.stats['orders_placed'] += 1
                                if result['status'] == 'filled':
                                    self.stats['orders_filled'] += 1
                                else:
                                    self.stats['orders_rejected'] += 1
                
                # 打印账户状态
                summary = self.broker.get_account_summary()
                logger.info(f"账户资产: {summary['total_assets']:,.2f} 元, 
                          收益率: {summary['total_return']:.2%}, 
                          持仓数: {summary['num_positions']}")
                
                # 每秒更新一次
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"模拟运行出错: {e}")
                time.sleep(5)
    
    def _run_historical(self):
        """运行历史回放。"""
        # 历史回放模式需要更多参数
        logger.info("历史回放模式尚未实现完整功能")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计。"""
        return self.stats
    
    def get_report(self) -> Dict[str, Any]:
        """获取交易报告。"""
        return {
            'account_summary': self.broker.get_account_summary(),
            'performance_stats': self.get_performance_stats(),
            'recent_trades': self.broker.trade_history[-10:],
            'positions': self.broker.get_positions()
        }


# 示例用法
if __name__ == "__main__":
    # 创建模拟引擎
    engine = SimulationEngine(
        initial_capital=100000,
        mode=SimulationMode.REALTIME_SIM
    )
    
    # 定义简单策略
    class SimpleStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            # 每10秒发出一个随机信号
            if self.counter % 10 == 0:
                symbols = ["000001", "000002", "000003", "000004", "000005"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(SimpleStrategy())
    
    # 启动模拟（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    # 运行10秒后停止
    time.sleep(10)
    engine.stop()
    
    # 打印报告
    report = engine.get_report()
    print("\n交易报告:")
    print(json.dumps(report, ensure_ascii=False, indent=2))
"""
OxQuant Simulation Trading

模拟交易模块，用于策略验证和测试。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimulationMode(Enum):
    """模拟模式。"""
    HISTORICAL = "historical"    # 历史数据回放
    REALTIME_SIM = "realtime_sim" # 实时模拟（使用实时数据）
    PAPER_TRADING = "paper_trading" # 纸盘交易


class SimulationBroker:
    """模拟券商。"""
    
    def __init__(
        self,
        initial_balance: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.0001,
        stamp_tax: float = 0.001,
        min_commission: float = 5.0
    ):
        
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage = slippage
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        
        # 持仓
        self.positions: Dict[str, dict] = {}  # symbol -> {quantity, avg_price, current_price}
        
        # 订单历史
        self.order_history = []
        
        # 交易历史
        self.trade_history = []
        
        # 账户历史
        self.account_history = []
    
    def get_balance(self) -> float:
        """获取当前余额。"""
        return self.balance
    
    def get_positions(self) -> Dict[str, dict]:
        """获取当前持仓。"""
        return self.positions
    
    def get_total_assets(self) -> float:
        """获取总资产。"""
        position_value = sum(
            pos['quantity'] * pos['current_price'] 
            for pos in self.positions.values()
        )
        return self.balance + position_value
    
    def place_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        order_id = f"SIM-{int(time.time())}-{np.random.randint(1000, 9999)}"
        
        # 模拟市场价格
        if price is None:
            price = self._get_simulated_price(symbol, side)
        
        # 计算执行价格（考虑滑点）
        execution_price = price
        if side == 'buy':
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)
        
        # 计算成本
        cost = quantity * execution_price
        commission = max(self.min_commission, cost * self.commission)
        
        if side == 'sell':
            commission += cost * self.stamp_tax
        
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'execution_price': execution_price,
            'order_type': order_type,
            'status': 'pending',
            'timestamp': datetime.now(),
            'commission': commission
        }
        
        # 执行订单
        success, message = self._execute_order(order)
        
        order['status'] = 'filled' if success else 'rejected'
        order['message'] = message
        
        self.order_history.append(order)
        
        if success:
            trade = {
                'trade_id': f"TRD-{int(time.time())}-{np.random.randint(1000, 9999)}",
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': execution_price,
                'commission': commission,
                'timestamp': datetime.now(),
                'pnl': 0.0
            }
            
            # 计算已实现盈亏（卖出时）
            if side == 'sell' and symbol in self.positions:
                pos = self.positions[symbol]
                trade['pnl'] = (execution_price - pos['avg_price']) * quantity
                pos['realized_pnl'] = pos.get('realized_pnl', 0) + trade['pnl']
            
            self.trade_history.append(trade)
        
        # 记录账户状态
        self._record_account_status()
        
        return order
    
    def _execute_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """执行订单。"""
        symbol = order['symbol']
        side = order['side']
        quantity = order['quantity']
        execution_price = order['execution_price']
        commission = order['commission']
        
        cost = quantity * execution_price
        total_cost = cost + commission
        
        if side == 'buy':
            # 买入
            if self.balance < total_cost:
                return False, "余额不足"
            
            self.balance -= total_cost
            
            if symbol in self.positions:
                # 更新持仓
                pos = self.positions[symbol]
                total_qty = pos['quantity'] + quantity
                total_cost_basis = pos['quantity'] * pos['avg_price'] + cost
                pos['quantity'] = total_qty
                pos['avg_price'] = total_cost_basis / total_qty
                pos['current_price'] = execution_price
            else:
                # 新建持仓
                self.positions[symbol] = {
                    'quantity': quantity,
                    'avg_price': execution_price,
                    'current_price': execution_price,
                    'realized_pnl': 0.0
                }
            
            return True, "买入成功"
        
        else:
            # 卖出
            if symbol not in self.positions:
                return False, "没有持仓"
            
            pos = self.positions[symbol]
            if pos['quantity'] < quantity:
                return False, "持仓不足"
            
            # 更新持仓
            pos['quantity'] -= quantity
            self.balance += (quantity * execution_price) - commission
            
            if pos['quantity'] == 0:
                del self.positions[symbol]
            
            return True, "卖出成功"
    
    def _get_simulated_price(self, symbol: str, side: str) -> float:
        """模拟获取市场价格。"""
        # 从数据提供商获取最新价格
        from src.data.data_providers import data_manager
        
        try:
            # 获取最近的历史数据
            today = datetime.now().strftime("%Y%m%d")
            data = data_manager.get_price_data(symbol, today, today)
            
            if not data.empty:
                return data['close'].iloc[-1]
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
        
        # 如果获取失败，使用随机价格
        return 100 + np.random.randn() * 10
    
    def _record_account_status(self):
        """记录账户状态。"""
        self.account_history.append({
            'timestamp': datetime.now(),
            'balance': self.balance,
            'total_assets': self.get_total_assets(),
            'num_positions': len(self.positions)
        })
    
    def update_prices(self):
        """更新持仓价格。"""
        for symbol, pos in self.positions.items():
            new_price = self._get_simulated_price(symbol, 'buy')
            pos['current_price'] = new_price
    
    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户摘要。"""
        total_assets = self.get_total_assets()
        total_return = (total_assets - self.initial_balance) / self.initial_balance
        
        # 计算未实现盈亏
        unrealized_pnl = 0
        for pos in self.positions.values():
            unrealized_pnl += (pos['current_price'] - pos['avg_price']) * pos['quantity']
        
        realized_pnl = sum(pos.get('realized_pnl', 0) for pos in self.positions.values())
        
        return {
            'balance': self.balance,
            'total_assets': total_assets,
            'total_return': total_return,
            'num_positions': len(self.positions),
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': unrealized_pnl + realized_pnl,
            'num_trades': len(self.trade_history)
        }


class SimulationEngine:
    """模拟交易引擎。"""
    
    def __init__(
        self,
        initial_capital: float = 1000000,
        mode: SimulationMode = SimulationMode.REALTIME_SIM
    ):
        
        self.mode = mode
        self.broker = SimulationBroker(initial_balance=initial_capital)
        self.running = False
        self.paused = False
        
        # 策略
        self.strategy = None
        
        # 性能统计
        self.stats = {
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'total_profit': 0,
            'total_loss': 0
        }
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def start(self):
        """启动模拟。"""
        self.running = True
        logger.info("模拟交易引擎启动")
        
        if self.mode == SimulationMode.REALTIME_SIM:
            self._run_realtime_sim()
        elif self.mode == SimulationMode.HISTORICAL:
            self._run_historical()
    
    def stop(self):
        """停止模拟。"""
        self.running = False
        logger.info("模拟交易引擎停止")
    
    def pause(self):
        """暂停模拟。"""
        self.paused = True
        logger.info("模拟交易引擎暂停")
    
    def resume(self):
        """恢复模拟。"""
        self.paused = False
        logger.info("模拟交易引擎恢复")
    
    def _run_realtime_sim(self):
        """运行实时模拟。"""
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            try:
                # 更新价格
                self.broker.update_prices()
                
                # 运行策略
                if self.strategy:
                    signals = self.strategy.generate_signals(self.broker)
                    
                    for symbol, signal in signals.items():
                        if signal != 0:
                            side = 'buy' if signal > 0 else 'sell'
                            quantity = int(abs(signal) * 100)
                            
                            if quantity > 0:
                                result = self.broker.place_order(
                                    symbol=symbol,
                                    side=side,
                                    quantity=quantity
                                )
                                
                                self.stats['orders_placed'] += 1
                                if result['status'] == 'filled':
                                    self.stats['orders_filled'] += 1
                                else:
                                    self.stats['orders_rejected'] += 1
                
                # 打印账户状态
                summary = self.broker.get_account_summary()
                logger.info(f"账户资产: {summary['total_assets']:,.2f} 元, 
                          收益率: {summary['total_return']:.2%}, 
                          持仓数: {summary['num_positions']}")
                
                # 每秒更新一次
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"模拟运行出错: {e}")
                time.sleep(5)
    
    def _run_historical(self):
        """运行历史回放。"""
        # 历史回放模式需要更多参数
        logger.info("历史回放模式尚未实现完整功能")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计。"""
        return self.stats
    
    def get_report(self) -> Dict[str, Any]:
        """获取交易报告。"""
        return {
            'account_summary': self.broker.get_account_summary(),
            'performance_stats': self.get_performance_stats(),
            'recent_trades': self.broker.trade_history[-10:],
            'positions': self.broker.get_positions()
        }


# 示例用法
if __name__ == "__main__":
    # 创建模拟引擎
    engine = SimulationEngine(
        initial_capital=100000,
        mode=SimulationMode.REALTIME_SIM
    )
    
    # 定义简单策略
    class SimpleStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            # 每10秒发出一个随机信号
            if self.counter % 10 == 0:
                symbols = ["000001", "000002", "000003", "000004", "000005"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(SimpleStrategy())
    
    # 启动模拟（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    # 运行10秒后停止
    time.sleep(10)
    engine.stop()
    
    # 打印报告
    report = engine.get_report()
    print("\n交易报告:")
    print(json.dumps(report, ensure_ascii=False, indent=2))
"""
OxQuant Simulation Trading

模拟交易模块，用于策略验证和测试。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimulationMode(Enum):
    """模拟模式。"""
    HISTORICAL = "historical"    # 历史数据回放
    REALTIME_SIM = "realtime_sim" # 实时模拟（使用实时数据）
    PAPER_TRADING = "paper_trading" # 纸盘交易


class SimulationBroker:
    """模拟券商。"""
    
    def __init__(
        self,
        initial_balance: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.0001,
        stamp_tax: float = 0.001,
        min_commission: float = 5.0
    ):
        
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage = slippage
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        
        # 持仓
        self.positions: Dict[str, dict] = {}  # symbol -> {quantity, avg_price, current_price}
        
        # 订单历史
        self.order_history = []
        
        # 交易历史
        self.trade_history = []
        
        # 账户历史
        self.account_history = []
    
    def get_balance(self) -> float:
        """获取当前余额。"""
        return self.balance
    
    def get_positions(self) -> Dict[str, dict]:
        """获取当前持仓。"""
        return self.positions
    
    def get_total_assets(self) -> float:
        """获取总资产。"""
        position_value = sum(
            pos['quantity'] * pos['current_price'] 
            for pos in self.positions.values()
        )
        return self.balance + position_value
    
    def place_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        order_id = f"SIM-{int(time.time())}-{np.random.randint(1000, 9999)}"
        
        # 模拟市场价格
        if price is None:
            price = self._get_simulated_price(symbol, side)
        
        # 计算执行价格（考虑滑点）
        execution_price = price
        if side == 'buy':
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)
        
        # 计算成本
        cost = quantity * execution_price
        commission = max(self.min_commission, cost * self.commission)
        
        if side == 'sell':
            commission += cost * self.stamp_tax
        
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'execution_price': execution_price,
            'order_type': order_type,
            'status': 'pending',
            'timestamp': datetime.now(),
            'commission': commission
        }
        
        # 执行订单
        success, message = self._execute_order(order)
        
        order['status'] = 'filled' if success else 'rejected'
        order['message'] = message
        
        self.order_history.append(order)
        
        if success:
            trade = {
                'trade_id': f"TRD-{int(time.time())}-{np.random.randint(1000, 9999)}",
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': execution_price,
                'commission': commission,
                'timestamp': datetime.now(),
                'pnl': 0.0
            }
            
            # 计算已实现盈亏（卖出时）
            if side == 'sell' and symbol in self.positions:
                pos = self.positions[symbol]
                trade['pnl'] = (execution_price - pos['avg_price']) * quantity
                pos['realized_pnl'] = pos.get('realized_pnl', 0) + trade['pnl']
            
            self.trade_history.append(trade)
        
        # 记录账户状态
        self._record_account_status()
        
        return order
    
    def _execute_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """执行订单。"""
        symbol = order['symbol']
        side = order['side']
        quantity = order['quantity']
        execution_price = order['execution_price']
        commission = order['commission']
        
        cost = quantity * execution_price
        total_cost = cost + commission
        
        if side == 'buy':
            # 买入
            if self.balance < total_cost:
                return False, "余额不足"
            
            self.balance -= total_cost
            
            if symbol in self.positions:
                # 更新持仓
                pos = self.positions[symbol]
                total_qty = pos['quantity'] + quantity
                total_cost_basis = pos['quantity'] * pos['avg_price'] + cost
                pos['quantity'] = total_qty
                pos['avg_price'] = total_cost_basis / total_qty
                pos['current_price'] = execution_price
            else:
                # 新建持仓
                self.positions[symbol] = {
                    'quantity': quantity,
                    'avg_price': execution_price,
                    'current_price': execution_price,
                    'realized_pnl': 0.0
                }
            
            return True, "买入成功"
        
        else:
            # 卖出
            if symbol not in self.positions:
                return False, "没有持仓"
            
            pos = self.positions[symbol]
            if pos['quantity'] < quantity:
                return False, "持仓不足"
            
            # 更新持仓
            pos['quantity'] -= quantity
            self.balance += (quantity * execution_price) - commission
            
            if pos['quantity'] == 0:
                del self.positions[symbol]
            
            return True, "卖出成功"
    
    def _get_simulated_price(self, symbol: str, side: str) -> float:
        """模拟获取市场价格。"""
        # 从数据提供商获取最新价格
        from src.data.data_providers import data_manager
        
        try:
            # 获取最近的历史数据
            today = datetime.now().strftime("%Y%m%d")
            data = data_manager.get_price_data(symbol, today, today)
            
            if not data.empty:
                return data['close'].iloc[-1]
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
        
        # 如果获取失败，使用随机价格
        return 100 + np.random.randn() * 10
    
    def _record_account_status(self):
        """记录账户状态。"""
        self.account_history.append({
            'timestamp': datetime.now(),
            'balance': self.balance,
            'total_assets': self.get_total_assets(),
            'num_positions': len(self.positions)
        })
    
    def update_prices(self):
        """更新持仓价格。"""
        for symbol, pos in self.positions.items():
            new_price = self._get_simulated_price(symbol, 'buy')
            pos['current_price'] = new_price
    
    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户摘要。"""
        total_assets = self.get_total_assets()
        total_return = (total_assets - self.initial_balance) / self.initial_balance
        
        # 计算未实现盈亏
        unrealized_pnl = 0
        for pos in self.positions.values():
            unrealized_pnl += (pos['current_price'] - pos['avg_price']) * pos['quantity']
        
        realized_pnl = sum(pos.get('realized_pnl', 0) for pos in self.positions.values())
        
        return {
            'balance': self.balance,
            'total_assets': total_assets,
            'total_return': total_return,
            'num_positions': len(self.positions),
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': unrealized_pnl + realized_pnl,
            'num_trades': len(self.trade_history)
        }


class SimulationEngine:
    """模拟交易引擎。"""
    
    def __init__(
        self,
        initial_capital: float = 1000000,
        mode: SimulationMode = SimulationMode.REALTIME_SIM
    ):
        
        self.mode = mode
        self.broker = SimulationBroker(initial_balance=initial_capital)
        self.running = False
        self.paused = False
        
        # 策略
        self.strategy = None
        
        # 性能统计
        self.stats = {
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'total_profit': 0,
            'total_loss': 0
        }
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def start(self):
        """启动模拟。"""
        self.running = True
        logger.info("模拟交易引擎启动")
        
        if self.mode == SimulationMode.REALTIME_SIM:
            self._run_realtime_sim()
        elif self.mode == SimulationMode.HISTORICAL:
            self._run_historical()
    
    def stop(self):
        """停止模拟。"""
        self.running = False
        logger.info("模拟交易引擎停止")
    
    def pause(self):
        """暂停模拟。"""
        self.paused = True
        logger.info("模拟交易引擎暂停")
    
    def resume(self):
        """恢复模拟。"""
        self.paused = False
        logger.info("模拟交易引擎恢复")
    
    def _run_realtime_sim(self):
        """运行实时模拟。"""
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            try:
                # 更新价格
                self.broker.update_prices()
                
                # 运行策略
                if self.strategy:
                    signals = self.strategy.generate_signals(self.broker)
                    
                    for symbol, signal in signals.items():
                        if signal != 0:
                            side = 'buy' if signal > 0 else 'sell'
                            quantity = int(abs(signal) * 100)
                            
                            if quantity > 0:
                                result = self.broker.place_order(
                                    symbol=symbol,
                                    side=side,
                                    quantity=quantity
                                )
                                
                                self.stats['orders_placed'] += 1
                                if result['status'] == 'filled':
                                    self.stats['orders_filled'] += 1
                                else:
                                    self.stats['orders_rejected'] += 1
                
                # 打印账户状态
                summary = self.broker.get_account_summary()
                logger.info(f"账户资产: {summary['total_assets']:,.2f} 元, 
                          收益率: {summary['total_return']:.2%}, 
                          持仓数: {summary['num_positions']}")
                
                # 每秒更新一次
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"模拟运行出错: {e}")
                time.sleep(5)
    
    def _run_historical(self):
        """运行历史回放。"""
        # 历史回放模式需要更多参数
        logger.info("历史回放模式尚未实现完整功能")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计。"""
        return self.stats
    
    def get_report(self) -> Dict[str, Any]:
        """获取交易报告。"""
        return {
            'account_summary': self.broker.get_account_summary(),
            'performance_stats': self.get_performance_stats(),
            'recent_trades': self.broker.trade_history[-10:],
            'positions': self.broker.get_positions()
        }


# 示例用法
if __name__ == "__main__":
    # 创建模拟引擎
    engine = SimulationEngine(
        initial_capital=100000,
        mode=SimulationMode.REALTIME_SIM
    )
    
    # 定义简单策略
    class SimpleStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            # 每10秒发出一个随机信号
            if self.counter % 10 == 0:
                symbols = ["000001", "000002", "000003", "000004", "000005"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(SimpleStrategy())
    
    # 启动模拟（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    # 运行10秒后停止
    time.sleep(10)
    engine.stop()
    
    # 打印报告
    report = engine.get_report()
    print("\n交易报告:")
    print(json.dumps(report, ensure_ascii=False, indent=2))
"""
OxQuant Simulation Trading

模拟交易模块，用于策略验证和测试。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimulationMode(Enum):
    """模拟模式。"""
    HISTORICAL = "historical"    # 历史数据回放
    REALTIME_SIM = "realtime_sim" # 实时模拟（使用实时数据）
    PAPER_TRADING = "paper_trading" # 纸盘交易


class SimulationBroker:
    """模拟券商。"""
    
    def __init__(
        self,
        initial_balance: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.0001,
        stamp_tax: float = 0.001,
        min_commission: float = 5.0
    ):
        
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage = slippage
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        
        # 持仓
        self.positions: Dict[str, dict] = {}  # symbol -> {quantity, avg_price, current_price}
        
        # 订单历史
        self.order_history = []
        
        # 交易历史
        self.trade_history = []
        
        # 账户历史
        self.account_history = []
    
    def get_balance(self) -> float:
        """获取当前余额。"""
        return self.balance
    
    def get_positions(self) -> Dict[str, dict]:
        """获取当前持仓。"""
        return self.positions
    
    def get_total_assets(self) -> float:
        """获取总资产。"""
        position_value = sum(
            pos['quantity'] * pos['current_price'] 
            for pos in self.positions.values()
        )
        return self.balance + position_value
    
    def place_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        order_id = f"SIM-{int(time.time())}-{np.random.randint(1000, 9999)}"
        
        # 模拟市场价格
        if price is None:
            price = self._get_simulated_price(symbol, side)
        
        # 计算执行价格（考虑滑点）
        execution_price = price
        if side == 'buy':
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)
        
        # 计算成本
        cost = quantity * execution_price
        commission = max(self.min_commission, cost * self.commission)
        
        if side == 'sell':
            commission += cost * self.stamp_tax
        
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'execution_price': execution_price,
            'order_type': order_type,
            'status': 'pending',
            'timestamp': datetime.now(),
            'commission': commission
        }
        
        # 执行订单
        success, message = self._execute_order(order)
        
        order['status'] = 'filled' if success else 'rejected'
        order['message'] = message
        
        self.order_history.append(order)
        
        if success:
            trade = {
                'trade_id': f"TRD-{int(time.time())}-{np.random.randint(1000, 9999)}",
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': execution_price,
                'commission': commission,
                'timestamp': datetime.now(),
                'pnl': 0.0
            }
            
            # 计算已实现盈亏（卖出时）
            if side == 'sell' and symbol in self.positions:
                pos = self.positions[symbol]
                trade['pnl'] = (execution_price - pos['avg_price']) * quantity
                pos['realized_pnl'] = pos.get('realized_pnl', 0) + trade['pnl']
            
            self.trade_history.append(trade)
        
        # 记录账户状态
        self._record_account_status()
        
        return order
    
    def _execute_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """执行订单。"""
        symbol = order['symbol']
        side = order['side']
        quantity = order['quantity']
        execution_price = order['execution_price']
        commission = order['commission']
        
        cost = quantity * execution_price
        total_cost = cost + commission
        
        if side == 'buy':
            # 买入
            if self.balance < total_cost:
                return False, "余额不足"
            
            self.balance -= total_cost
            
            if symbol in self.positions:
                # 更新持仓
                pos = self.positions[symbol]
                total_qty = pos['quantity'] + quantity
                total_cost_basis = pos['quantity'] * pos['avg_price'] + cost
                pos['quantity'] = total_qty
                pos['avg_price'] = total_cost_basis / total_qty
                pos['current_price'] = execution_price
            else:
                # 新建持仓
                self.positions[symbol] = {
                    'quantity': quantity,
                    'avg_price': execution_price,
                    'current_price': execution_price,
                    'realized_pnl': 0.0
                }
            
            return True, "买入成功"
        
        else:
            # 卖出
            if symbol not in self.positions:
                return False, "没有持仓"
            
            pos = self.positions[symbol]
            if pos['quantity'] < quantity:
                return False, "持仓不足"
            
            # 更新持仓
            pos['quantity'] -= quantity
            self.balance += (quantity * execution_price) - commission
            
            if pos['quantity'] == 0:
                del self.positions[symbol]
            
            return True, "卖出成功"
    
    def _get_simulated_price(self, symbol: str, side: str) -> float:
        """模拟获取市场价格。"""
        # 从数据提供商获取最新价格
        from src.data.data_providers import data_manager
        
        try:
            # 获取最近的历史数据
            today = datetime.now().strftime("%Y%m%d")
            data = data_manager.get_price_data(symbol, today, today)
            
            if not data.empty:
                return data['close'].iloc[-1]
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
        
        # 如果获取失败，使用随机价格
        return 100 + np.random.randn() * 10
    
    def _record_account_status(self):
        """记录账户状态。"""
        self.account_history.append({
            'timestamp': datetime.now(),
            'balance': self.balance,
            'total_assets': self.get_total_assets(),
            'num_positions': len(self.positions)
        })
    
    def update_prices(self):
        """更新持仓价格。"""
        for symbol, pos in self.positions.items():
            new_price = self._get_simulated_price(symbol, 'buy')
            pos['current_price'] = new_price
    
    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户摘要。"""
        total_assets = self.get_total_assets()
        total_return = (total_assets - self.initial_balance) / self.initial_balance
        
        # 计算未实现盈亏
        unrealized_pnl = 0
        for pos in self.positions.values():
            unrealized_pnl += (pos['current_price'] - pos['avg_price']) * pos['quantity']
        
        realized_pnl = sum(pos.get('realized_pnl', 0) for pos in self.positions.values())
        
        return {
            'balance': self.balance,
            'total_assets': total_assets,
            'total_return': total_return,
            'num_positions': len(self.positions),
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': unrealized_pnl + realized_pnl,
            'num_trades': len(self.trade_history)
        }


class SimulationEngine:
    """模拟交易引擎。"""
    
    def __init__(
        self,
        initial_capital: float = 1000000,
        mode: SimulationMode = SimulationMode.REALTIME_SIM
    ):
        
        self.mode = mode
        self.broker = SimulationBroker(initial_balance=initial_capital)
        self.running = False
        self.paused = False
        
        # 策略
        self.strategy = None
        
        # 性能统计
        self.stats = {
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'total_profit': 0,
            'total_loss': 0
        }
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def start(self):
        """启动模拟。"""
        self.running = True
        logger.info("模拟交易引擎启动")
        
        if self.mode == SimulationMode.REALTIME_SIM:
            self._run_realtime_sim()
        elif self.mode == SimulationMode.HISTORICAL:
            self._run_historical()
    
    def stop(self):
        """停止模拟。"""
        self.running = False
        logger.info("模拟交易引擎停止")
    
    def pause(self):
        """暂停模拟。"""
        self.paused = True
        logger.info("模拟交易引擎暂停")
    
    def resume(self):
        """恢复模拟。"""
        self.paused = False
        logger.info("模拟交易引擎恢复")
    
    def _run_realtime_sim(self):
        """运行实时模拟。"""
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            try:
                # 更新价格
                self.broker.update_prices()
                
                # 运行策略
                if self.strategy:
                    signals = self.strategy.generate_signals(self.broker)
                    
                    for symbol, signal in signals.items():
                        if signal != 0:
                            side = 'buy' if signal > 0 else 'sell'
                            quantity = int(abs(signal) * 100)
                            
                            if quantity > 0:
                                result = self.broker.place_order(
                                    symbol=symbol,
                                    side=side,
                                    quantity=quantity
                                )
                                
                                self.stats['orders_placed'] += 1
                                if result['status'] == 'filled':
                                    self.stats['orders_filled'] += 1
                                else:
                                    self.stats['orders_rejected'] += 1
                
                # 打印账户状态
                summary = self.broker.get_account_summary()
                logger.info(f"账户资产: {summary['total_assets']:,.2f} 元, 
                          收益率: {summary['total_return']:.2%}, 
                          持仓数: {summary['num_positions']}")
                
                # 每秒更新一次
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"模拟运行出错: {e}")
                time.sleep(5)
    
    def _run_historical(self):
        """运行历史回放。"""
        # 历史回放模式需要更多参数
        logger.info("历史回放模式尚未实现完整功能")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计。"""
        return self.stats
    
    def get_report(self) -> Dict[str, Any]:
        """获取交易报告。"""
        return {
            'account_summary': self.broker.get_account_summary(),
            'performance_stats': self.get_performance_stats(),
            'recent_trades': self.broker.trade_history[-10:],
            'positions': self.broker.get_positions()
        }


# 示例用法
if __name__ == "__main__":
    # 创建模拟引擎
    engine = SimulationEngine(
        initial_capital=100000,
        mode=SimulationMode.REALTIME_SIM
    )
    
    # 定义简单策略
    class SimpleStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            # 每10秒发出一个随机信号
            if self.counter % 10 == 0:
                symbols = ["000001", "000002", "000003", "000004", "000005"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(SimpleStrategy())
    
    # 启动模拟（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    # 运行10秒后停止
    time.sleep(10)
    engine.stop()
    
    # 打印报告
    report = engine.get_report()
    print("\n交易报告:")
    print(json.dumps(report, ensure_ascii=False, indent=2))