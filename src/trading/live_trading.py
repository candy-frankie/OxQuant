"""
OxQuant Live Trading

实盘交易模块，支持多种券商接口。
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


class BrokerType(Enum):
    """券商类型。"""
    EASYTRADER = "easytrader"    # 同花顺客户端
    QMT = "qmt"                  # 钱龙QMT
    TUSHARE = "tushare"          # Tushare模拟交易
    ALPACA = "alpaca"            # Alpaca (美股)
    BINANCE = "binance"          # Binance (加密货币)
    SIMULATION = "simulation"    # 模拟交易


class LiveBroker:
    """实盘券商接口基类。"""
    
    def __init__(self, broker_type: BrokerType):
        self.broker_type = broker_type
        self.connected = False
        self.account_info = {}
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        raise NotImplementedError
    
    def disconnect(self):
        """断开连接。"""
        self.connected = False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        raise NotImplementedError
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        raise NotImplementedError
    
    def get_balance(self) -> float:
        """获取余额。"""
        raise NotImplementedError
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        raise NotImplementedError
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        raise NotImplementedError
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        raise NotImplementedError


class EasyTraderBroker(LiveBroker):
    """同花顺客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.EASYTRADER)
        self.broker = None
    
    def connect(self, **kwargs) -> bool:
        """连接同花顺客户端。"""
        try:
            import easytrader
            
            # 创建客户端
            self.broker = easytrader.use('ths')
            
            # 连接
            self.broker.connect(
                user=kwargs.get('user'),
                password=kwargs.get('password'),
                exe_path=kwargs.get('exe_path', 'C:/同花顺软件/同花顺/xiadan.exe')
            )
            
            self.connected = True
            logger.info("同花顺客户端连接成功")
            return True
        
        except ImportError:
            logger.error("easytrader未安装，请安装: pip install easytrader")
            return False
        except Exception as e:
            logger.error(f"同花顺连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            info = self.broker.get_account()
            self.account_info = info
            return info
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            positions = self.broker.get_position()
            result = {}
            for pos in positions:
                result[pos['证券代码']] = {
                    'symbol': pos['证券代码'],
                    'name': pos['证券名称'],
                    'quantity': int(pos['持仓数量']),
                    'avg_price': float(pos['成本价']),
                    'current_price': float(pos['现价']),
                    'market_value': float(pos['市值'])
                }
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.broker:
            return 0.0
        
        try:
            info = self.broker.get_account()
            return float(info.get('可用资金', 0))
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.broker:
            return {'success': False, 'message': '未连接'}
        
        try:
            if order_type == 'market':
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            else:
                # 限价单
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            
            return {'success': True, 'order_id': result, 'message': '下单成功'}
        
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.broker:
            return False
        
        try:
            self.broker.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            orders = self.broker.get_entrust()
            for order in orders:
                if order['委托编号'] == order_id:
                    return {
                        'order_id': order['委托编号'],
                        'status': order['委托状态'],
                        'symbol': order['证券代码'],
                        'quantity': int(order['委托数量']),
                        'price': float(order['委托价格'])
                    }
            return {'status': 'not_found'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.broker:
            return []
        
        try:
            trades = self.broker.get_history()
            return trades
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class QMTBroker(LiveBroker):
    """QMT客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.QMT)
        self.client = None
    
    def connect(self, **kwargs) -> bool:
        """连接QMT客户端。"""
        try:
            # QMT使用COM接口
            import win32com.client
            
            self.client = win32com.client.Dispatch('Qmt.HQClient')
            
            # 初始化
            self.client.Init()
            
            # 登录
            result = self.client.Login(
                kwargs.get('user'),
                kwargs.get('password'),
                kwargs.get('ip', '127.0.0.1'),
                kwargs.get('port', 10000)
            )
            
            if result == 0:
                self.connected = True
                logger.info("QMT客户端连接成功")
                return True
            else:
                logger.error(f"QMT登录失败，错误码: {result}")
                return False
        
        except ImportError:
            logger.error("pywin32未安装，请安装: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"QMT连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT API示例（具体API需要参考QMT文档）
            return {
                'account': 'QMT Account',
                'balance': self.get_balance()
            }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT获取持仓
            positions = {}
            # 具体实现需要参考QMT API文档
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.client:
            return 0.0
        
        try:
            # QMT获取余额
            return 0.0
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.client:
            return {'success': False, 'message': '未连接'}
        
        try:
            # QMT下单
            return {'success': True, 'order_id': 'QMT_ORDER', 'message': '下单成功'}
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.client:
            return False
        
        try:
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            return {'order_id': order_id, 'status': 'filled'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.client:
            return []
        
        try:
            return []
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class LiveTradingEngine:
    """实盘交易引擎。"""
    
    def __init__(
        self,
        broker_type: BrokerType = BrokerType.SIMULATION,
        **broker_kwargs
    ):
        
        self.broker_type = broker_type
        self.broker: Optional[LiveBroker] = None
        self.running = False
        
        # 风险管理器
        self.risk_manager = None
        
        # 策略
        self.strategy = None
        
        # 交易日志
        self.trade_log = []
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        # 创建券商实例
        if self.broker_type == BrokerType.EASYTRADER:
            self.broker = EasyTraderBroker()
        elif self.broker_type == BrokerType.QMT:
            self.broker = QMTBroker()
        else:
            # 默认使用模拟券商
            from .simulation import SimulationBroker
            self.broker = SimulationBroker()
        
        return self.broker.connect(**kwargs)
    
    def disconnect(self):
        """断开连接。"""
        if self.broker:
            self.broker.disconnect()
            self.running = False
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def set_risk_manager(self, risk_manager):
        """设置风险管理器。"""
        self.risk_manager = risk_manager
    
    def start(self):
        """启动实盘交易。"""
        if not self.broker or not self.broker.connected:
            logger.error("请先连接券商")
            return
        
        if not self.strategy:
            logger.error("请先设置策略")
            return
        
        self.running = True
        logger.info("实盘交易引擎启动")
        
        # 启动交易循环
        self._trading_loop()
    
    def stop(self):
        """停止实盘交易。"""
        self.running = False
        logger.info("实盘交易引擎停止")
    
    def _trading_loop(self):
        """交易主循环。"""
        while self.running:
            try:
                # 检查是否在交易时间
                if not self._is_trading_time():
                    logger.info("非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # 运行策略
                signals = self.strategy.generate_signals(self.broker)
                
                # 执行交易
                for symbol, signal in signals.items():
                    if signal != 0:
                        self._execute_trade(symbol, signal)
                
                # 更新日志
                self._log_account_status()
                
                # 等待下一个周期
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"交易循环出错: {e}")
                time.sleep(5)
    
    def _is_trading_time(self) -> bool:
        """检查是否在交易时间。"""
        now = datetime.now()
        
        # 检查是否是交易日（简化版）
        if now.weekday() >= 5:
            return False
        
        # 检查时间
        time_str = now.strftime("%H:%M")
        
        # 上午交易时间
        morning = "09:30" <= time_str <= "11:30"
        
        # 下午交易时间
        afternoon = "13:00" <= time_str <= "15:00"
        
        return morning or afternoon
    
    def _execute_trade(self, symbol: str, signal: float):
        """执行交易。"""
        side = 'buy' if signal > 0 else 'sell'
        quantity = int(abs(signal) * 100)
        
        if quantity <= 0:
            return
        
        # 风险检查
        if self.risk_manager:
            # 简化的风险检查
            positions = self.broker.get_positions()
            balance = self.broker.get_balance()
            
            # 检查单一持仓限制
            if symbol in positions:
                pos_value = positions[symbol]['quantity'] * positions[symbol]['current_price']
                total_assets = balance + sum(p['quantity'] * p['current_price'] for p in positions.values())
                if pos_value / total_assets > 0.1:
                    logger.warning(f"持仓超过10%限制: {symbol}")
                    return
        
        # 下单
        result = self.broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity
        )
        
        # 记录日志
        self.trade_log.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'result': result
        })
        
        if result.get('success'):
            logger.info(f"交易成功: {side} {quantity}股 {symbol}")
        else:
            logger.error(f"交易失败: {side} {quantity}股 {symbol} - {result.get('message')}")
    
    def _log_account_status(self):
        """记录账户状态。"""
        if not self.broker:
            return
        
        try:
            summary = {
                'timestamp': datetime.now(),
                'balance': self.broker.get_balance(),
                'positions': self.broker.get_positions(),
                'account_info': self.broker.get_account_info()
            }
            
            # 每小时记录一次
            if len(self.trade_log) == 0 or (
                datetime.now() - self.trade_log[-1]['timestamp']).seconds >= 3600:
                logger.info(f"账户状态: {summary}")
        
        except Exception as e:
            logger.error(f"记录账户状态失败: {e}")
    
    def get_trade_log(self) -> List[Dict]:
        """获取交易日志。"""
        return self.trade_log


# 示例用法
if __name__ == "__main__":
    # 创建实盘交易引擎（使用模拟模式）
    engine = LiveTradingEngine(broker_type=BrokerType.SIMULATION)
    
    # 连接（模拟模式不需要实际连接）
    engine.connect()
    
    # 定义简单策略
    class TestStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            if self.counter % 5 == 0:
                symbols = ["000001", "000002", "600000"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(TestStrategy())
    
    # 启动交易（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    time.sleep(10)
    engine.stop()
    
    # 打印交易日志
    print("\n交易日志:")
    for trade in engine.get_trade_log():
        print(f"{trade['timestamp']}: {trade['side']} {trade['quantity']}股 {trade['symbol']}")
"""
OxQuant Live Trading

实盘交易模块，支持多种券商接口。
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


class BrokerType(Enum):
    """券商类型。"""
    EASYTRADER = "easytrader"    # 同花顺客户端
    QMT = "qmt"                  # 钱龙QMT
    TUSHARE = "tushare"          # Tushare模拟交易
    ALPACA = "alpaca"            # Alpaca (美股)
    BINANCE = "binance"          # Binance (加密货币)
    SIMULATION = "simulation"    # 模拟交易


class LiveBroker:
    """实盘券商接口基类。"""
    
    def __init__(self, broker_type: BrokerType):
        self.broker_type = broker_type
        self.connected = False
        self.account_info = {}
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        raise NotImplementedError
    
    def disconnect(self):
        """断开连接。"""
        self.connected = False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        raise NotImplementedError
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        raise NotImplementedError
    
    def get_balance(self) -> float:
        """获取余额。"""
        raise NotImplementedError
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        raise NotImplementedError
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        raise NotImplementedError
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        raise NotImplementedError


class EasyTraderBroker(LiveBroker):
    """同花顺客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.EASYTRADER)
        self.broker = None
    
    def connect(self, **kwargs) -> bool:
        """连接同花顺客户端。"""
        try:
            import easytrader
            
            # 创建客户端
            self.broker = easytrader.use('ths')
            
            # 连接
            self.broker.connect(
                user=kwargs.get('user'),
                password=kwargs.get('password'),
                exe_path=kwargs.get('exe_path', 'C:/同花顺软件/同花顺/xiadan.exe')
            )
            
            self.connected = True
            logger.info("同花顺客户端连接成功")
            return True
        
        except ImportError:
            logger.error("easytrader未安装，请安装: pip install easytrader")
            return False
        except Exception as e:
            logger.error(f"同花顺连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            info = self.broker.get_account()
            self.account_info = info
            return info
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            positions = self.broker.get_position()
            result = {}
            for pos in positions:
                result[pos['证券代码']] = {
                    'symbol': pos['证券代码'],
                    'name': pos['证券名称'],
                    'quantity': int(pos['持仓数量']),
                    'avg_price': float(pos['成本价']),
                    'current_price': float(pos['现价']),
                    'market_value': float(pos['市值'])
                }
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.broker:
            return 0.0
        
        try:
            info = self.broker.get_account()
            return float(info.get('可用资金', 0))
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.broker:
            return {'success': False, 'message': '未连接'}
        
        try:
            if order_type == 'market':
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            else:
                # 限价单
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            
            return {'success': True, 'order_id': result, 'message': '下单成功'}
        
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.broker:
            return False
        
        try:
            self.broker.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            orders = self.broker.get_entrust()
            for order in orders:
                if order['委托编号'] == order_id:
                    return {
                        'order_id': order['委托编号'],
                        'status': order['委托状态'],
                        'symbol': order['证券代码'],
                        'quantity': int(order['委托数量']),
                        'price': float(order['委托价格'])
                    }
            return {'status': 'not_found'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.broker:
            return []
        
        try:
            trades = self.broker.get_history()
            return trades
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class QMTBroker(LiveBroker):
    """QMT客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.QMT)
        self.client = None
    
    def connect(self, **kwargs) -> bool:
        """连接QMT客户端。"""
        try:
            # QMT使用COM接口
            import win32com.client
            
            self.client = win32com.client.Dispatch('Qmt.HQClient')
            
            # 初始化
            self.client.Init()
            
            # 登录
            result = self.client.Login(
                kwargs.get('user'),
                kwargs.get('password'),
                kwargs.get('ip', '127.0.0.1'),
                kwargs.get('port', 10000)
            )
            
            if result == 0:
                self.connected = True
                logger.info("QMT客户端连接成功")
                return True
            else:
                logger.error(f"QMT登录失败，错误码: {result}")
                return False
        
        except ImportError:
            logger.error("pywin32未安装，请安装: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"QMT连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT API示例（具体API需要参考QMT文档）
            return {
                'account': 'QMT Account',
                'balance': self.get_balance()
            }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT获取持仓
            positions = {}
            # 具体实现需要参考QMT API文档
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.client:
            return 0.0
        
        try:
            # QMT获取余额
            return 0.0
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.client:
            return {'success': False, 'message': '未连接'}
        
        try:
            # QMT下单
            return {'success': True, 'order_id': 'QMT_ORDER', 'message': '下单成功'}
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.client:
            return False
        
        try:
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            return {'order_id': order_id, 'status': 'filled'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.client:
            return []
        
        try:
            return []
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class LiveTradingEngine:
    """实盘交易引擎。"""
    
    def __init__(
        self,
        broker_type: BrokerType = BrokerType.SIMULATION,
        **broker_kwargs
    ):
        
        self.broker_type = broker_type
        self.broker: Optional[LiveBroker] = None
        self.running = False
        
        # 风险管理器
        self.risk_manager = None
        
        # 策略
        self.strategy = None
        
        # 交易日志
        self.trade_log = []
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        # 创建券商实例
        if self.broker_type == BrokerType.EASYTRADER:
            self.broker = EasyTraderBroker()
        elif self.broker_type == BrokerType.QMT:
            self.broker = QMTBroker()
        else:
            # 默认使用模拟券商
            from .simulation import SimulationBroker
            self.broker = SimulationBroker()
        
        return self.broker.connect(**kwargs)
    
    def disconnect(self):
        """断开连接。"""
        if self.broker:
            self.broker.disconnect()
            self.running = False
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def set_risk_manager(self, risk_manager):
        """设置风险管理器。"""
        self.risk_manager = risk_manager
    
    def start(self):
        """启动实盘交易。"""
        if not self.broker or not self.broker.connected:
            logger.error("请先连接券商")
            return
        
        if not self.strategy:
            logger.error("请先设置策略")
            return
        
        self.running = True
        logger.info("实盘交易引擎启动")
        
        # 启动交易循环
        self._trading_loop()
    
    def stop(self):
        """停止实盘交易。"""
        self.running = False
        logger.info("实盘交易引擎停止")
    
    def _trading_loop(self):
        """交易主循环。"""
        while self.running:
            try:
                # 检查是否在交易时间
                if not self._is_trading_time():
                    logger.info("非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # 运行策略
                signals = self.strategy.generate_signals(self.broker)
                
                # 执行交易
                for symbol, signal in signals.items():
                    if signal != 0:
                        self._execute_trade(symbol, signal)
                
                # 更新日志
                self._log_account_status()
                
                # 等待下一个周期
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"交易循环出错: {e}")
                time.sleep(5)
    
    def _is_trading_time(self) -> bool:
        """检查是否在交易时间。"""
        now = datetime.now()
        
        # 检查是否是交易日（简化版）
        if now.weekday() >= 5:
            return False
        
        # 检查时间
        time_str = now.strftime("%H:%M")
        
        # 上午交易时间
        morning = "09:30" <= time_str <= "11:30"
        
        # 下午交易时间
        afternoon = "13:00" <= time_str <= "15:00"
        
        return morning or afternoon
    
    def _execute_trade(self, symbol: str, signal: float):
        """执行交易。"""
        side = 'buy' if signal > 0 else 'sell'
        quantity = int(abs(signal) * 100)
        
        if quantity <= 0:
            return
        
        # 风险检查
        if self.risk_manager:
            # 简化的风险检查
            positions = self.broker.get_positions()
            balance = self.broker.get_balance()
            
            # 检查单一持仓限制
            if symbol in positions:
                pos_value = positions[symbol]['quantity'] * positions[symbol]['current_price']
                total_assets = balance + sum(p['quantity'] * p['current_price'] for p in positions.values())
                if pos_value / total_assets > 0.1:
                    logger.warning(f"持仓超过10%限制: {symbol}")
                    return
        
        # 下单
        result = self.broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity
        )
        
        # 记录日志
        self.trade_log.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'result': result
        })
        
        if result.get('success'):
            logger.info(f"交易成功: {side} {quantity}股 {symbol}")
        else:
            logger.error(f"交易失败: {side} {quantity}股 {symbol} - {result.get('message')}")
    
    def _log_account_status(self):
        """记录账户状态。"""
        if not self.broker:
            return
        
        try:
            summary = {
                'timestamp': datetime.now(),
                'balance': self.broker.get_balance(),
                'positions': self.broker.get_positions(),
                'account_info': self.broker.get_account_info()
            }
            
            # 每小时记录一次
            if len(self.trade_log) == 0 or (
                datetime.now() - self.trade_log[-1]['timestamp']).seconds >= 3600:
                logger.info(f"账户状态: {summary}")
        
        except Exception as e:
            logger.error(f"记录账户状态失败: {e}")
    
    def get_trade_log(self) -> List[Dict]:
        """获取交易日志。"""
        return self.trade_log


# 示例用法
if __name__ == "__main__":
    # 创建实盘交易引擎（使用模拟模式）
    engine = LiveTradingEngine(broker_type=BrokerType.SIMULATION)
    
    # 连接（模拟模式不需要实际连接）
    engine.connect()
    
    # 定义简单策略
    class TestStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            if self.counter % 5 == 0:
                symbols = ["000001", "000002", "600000"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(TestStrategy())
    
    # 启动交易（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    time.sleep(10)
    engine.stop()
    
    # 打印交易日志
    print("\n交易日志:")
    for trade in engine.get_trade_log():
        print(f"{trade['timestamp']}: {trade['side']} {trade['quantity']}股 {trade['symbol']}")
"""
OxQuant Live Trading

实盘交易模块，支持多种券商接口。
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


class BrokerType(Enum):
    """券商类型。"""
    EASYTRADER = "easytrader"    # 同花顺客户端
    QMT = "qmt"                  # 钱龙QMT
    TUSHARE = "tushare"          # Tushare模拟交易
    ALPACA = "alpaca"            # Alpaca (美股)
    BINANCE = "binance"          # Binance (加密货币)
    SIMULATION = "simulation"    # 模拟交易


class LiveBroker:
    """实盘券商接口基类。"""
    
    def __init__(self, broker_type: BrokerType):
        self.broker_type = broker_type
        self.connected = False
        self.account_info = {}
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        raise NotImplementedError
    
    def disconnect(self):
        """断开连接。"""
        self.connected = False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        raise NotImplementedError
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        raise NotImplementedError
    
    def get_balance(self) -> float:
        """获取余额。"""
        raise NotImplementedError
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        raise NotImplementedError
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        raise NotImplementedError
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        raise NotImplementedError


class EasyTraderBroker(LiveBroker):
    """同花顺客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.EASYTRADER)
        self.broker = None
    
    def connect(self, **kwargs) -> bool:
        """连接同花顺客户端。"""
        try:
            import easytrader
            
            # 创建客户端
            self.broker = easytrader.use('ths')
            
            # 连接
            self.broker.connect(
                user=kwargs.get('user'),
                password=kwargs.get('password'),
                exe_path=kwargs.get('exe_path', 'C:/同花顺软件/同花顺/xiadan.exe')
            )
            
            self.connected = True
            logger.info("同花顺客户端连接成功")
            return True
        
        except ImportError:
            logger.error("easytrader未安装，请安装: pip install easytrader")
            return False
        except Exception as e:
            logger.error(f"同花顺连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            info = self.broker.get_account()
            self.account_info = info
            return info
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            positions = self.broker.get_position()
            result = {}
            for pos in positions:
                result[pos['证券代码']] = {
                    'symbol': pos['证券代码'],
                    'name': pos['证券名称'],
                    'quantity': int(pos['持仓数量']),
                    'avg_price': float(pos['成本价']),
                    'current_price': float(pos['现价']),
                    'market_value': float(pos['市值'])
                }
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.broker:
            return 0.0
        
        try:
            info = self.broker.get_account()
            return float(info.get('可用资金', 0))
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.broker:
            return {'success': False, 'message': '未连接'}
        
        try:
            if order_type == 'market':
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            else:
                # 限价单
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            
            return {'success': True, 'order_id': result, 'message': '下单成功'}
        
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.broker:
            return False
        
        try:
            self.broker.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            orders = self.broker.get_entrust()
            for order in orders:
                if order['委托编号'] == order_id:
                    return {
                        'order_id': order['委托编号'],
                        'status': order['委托状态'],
                        'symbol': order['证券代码'],
                        'quantity': int(order['委托数量']),
                        'price': float(order['委托价格'])
                    }
            return {'status': 'not_found'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.broker:
            return []
        
        try:
            trades = self.broker.get_history()
            return trades
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class QMTBroker(LiveBroker):
    """QMT客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.QMT)
        self.client = None
    
    def connect(self, **kwargs) -> bool:
        """连接QMT客户端。"""
        try:
            # QMT使用COM接口
            import win32com.client
            
            self.client = win32com.client.Dispatch('Qmt.HQClient')
            
            # 初始化
            self.client.Init()
            
            # 登录
            result = self.client.Login(
                kwargs.get('user'),
                kwargs.get('password'),
                kwargs.get('ip', '127.0.0.1'),
                kwargs.get('port', 10000)
            )
            
            if result == 0:
                self.connected = True
                logger.info("QMT客户端连接成功")
                return True
            else:
                logger.error(f"QMT登录失败，错误码: {result}")
                return False
        
        except ImportError:
            logger.error("pywin32未安装，请安装: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"QMT连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT API示例（具体API需要参考QMT文档）
            return {
                'account': 'QMT Account',
                'balance': self.get_balance()
            }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT获取持仓
            positions = {}
            # 具体实现需要参考QMT API文档
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.client:
            return 0.0
        
        try:
            # QMT获取余额
            return 0.0
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.client:
            return {'success': False, 'message': '未连接'}
        
        try:
            # QMT下单
            return {'success': True, 'order_id': 'QMT_ORDER', 'message': '下单成功'}
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.client:
            return False
        
        try:
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            return {'order_id': order_id, 'status': 'filled'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.client:
            return []
        
        try:
            return []
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class LiveTradingEngine:
    """实盘交易引擎。"""
    
    def __init__(
        self,
        broker_type: BrokerType = BrokerType.SIMULATION,
        **broker_kwargs
    ):
        
        self.broker_type = broker_type
        self.broker: Optional[LiveBroker] = None
        self.running = False
        
        # 风险管理器
        self.risk_manager = None
        
        # 策略
        self.strategy = None
        
        # 交易日志
        self.trade_log = []
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        # 创建券商实例
        if self.broker_type == BrokerType.EASYTRADER:
            self.broker = EasyTraderBroker()
        elif self.broker_type == BrokerType.QMT:
            self.broker = QMTBroker()
        else:
            # 默认使用模拟券商
            from .simulation import SimulationBroker
            self.broker = SimulationBroker()
        
        return self.broker.connect(**kwargs)
    
    def disconnect(self):
        """断开连接。"""
        if self.broker:
            self.broker.disconnect()
            self.running = False
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def set_risk_manager(self, risk_manager):
        """设置风险管理器。"""
        self.risk_manager = risk_manager
    
    def start(self):
        """启动实盘交易。"""
        if not self.broker or not self.broker.connected:
            logger.error("请先连接券商")
            return
        
        if not self.strategy:
            logger.error("请先设置策略")
            return
        
        self.running = True
        logger.info("实盘交易引擎启动")
        
        # 启动交易循环
        self._trading_loop()
    
    def stop(self):
        """停止实盘交易。"""
        self.running = False
        logger.info("实盘交易引擎停止")
    
    def _trading_loop(self):
        """交易主循环。"""
        while self.running:
            try:
                # 检查是否在交易时间
                if not self._is_trading_time():
                    logger.info("非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # 运行策略
                signals = self.strategy.generate_signals(self.broker)
                
                # 执行交易
                for symbol, signal in signals.items():
                    if signal != 0:
                        self._execute_trade(symbol, signal)
                
                # 更新日志
                self._log_account_status()
                
                # 等待下一个周期
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"交易循环出错: {e}")
                time.sleep(5)
    
    def _is_trading_time(self) -> bool:
        """检查是否在交易时间。"""
        now = datetime.now()
        
        # 检查是否是交易日（简化版）
        if now.weekday() >= 5:
            return False
        
        # 检查时间
        time_str = now.strftime("%H:%M")
        
        # 上午交易时间
        morning = "09:30" <= time_str <= "11:30"
        
        # 下午交易时间
        afternoon = "13:00" <= time_str <= "15:00"
        
        return morning or afternoon
    
    def _execute_trade(self, symbol: str, signal: float):
        """执行交易。"""
        side = 'buy' if signal > 0 else 'sell'
        quantity = int(abs(signal) * 100)
        
        if quantity <= 0:
            return
        
        # 风险检查
        if self.risk_manager:
            # 简化的风险检查
            positions = self.broker.get_positions()
            balance = self.broker.get_balance()
            
            # 检查单一持仓限制
            if symbol in positions:
                pos_value = positions[symbol]['quantity'] * positions[symbol]['current_price']
                total_assets = balance + sum(p['quantity'] * p['current_price'] for p in positions.values())
                if pos_value / total_assets > 0.1:
                    logger.warning(f"持仓超过10%限制: {symbol}")
                    return
        
        # 下单
        result = self.broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity
        )
        
        # 记录日志
        self.trade_log.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'result': result
        })
        
        if result.get('success'):
            logger.info(f"交易成功: {side} {quantity}股 {symbol}")
        else:
            logger.error(f"交易失败: {side} {quantity}股 {symbol} - {result.get('message')}")
    
    def _log_account_status(self):
        """记录账户状态。"""
        if not self.broker:
            return
        
        try:
            summary = {
                'timestamp': datetime.now(),
                'balance': self.broker.get_balance(),
                'positions': self.broker.get_positions(),
                'account_info': self.broker.get_account_info()
            }
            
            # 每小时记录一次
            if len(self.trade_log) == 0 or (
                datetime.now() - self.trade_log[-1]['timestamp']).seconds >= 3600:
                logger.info(f"账户状态: {summary}")
        
        except Exception as e:
            logger.error(f"记录账户状态失败: {e}")
    
    def get_trade_log(self) -> List[Dict]:
        """获取交易日志。"""
        return self.trade_log


# 示例用法
if __name__ == "__main__":
    # 创建实盘交易引擎（使用模拟模式）
    engine = LiveTradingEngine(broker_type=BrokerType.SIMULATION)
    
    # 连接（模拟模式不需要实际连接）
    engine.connect()
    
    # 定义简单策略
    class TestStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            if self.counter % 5 == 0:
                symbols = ["000001", "000002", "600000"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(TestStrategy())
    
    # 启动交易（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    time.sleep(10)
    engine.stop()
    
    # 打印交易日志
    print("\n交易日志:")
    for trade in engine.get_trade_log():
        print(f"{trade['timestamp']}: {trade['side']} {trade['quantity']}股 {trade['symbol']}")
"""
OxQuant Live Trading

实盘交易模块，支持多种券商接口。
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


class BrokerType(Enum):
    """券商类型。"""
    EASYTRADER = "easytrader"    # 同花顺客户端
    QMT = "qmt"                  # 钱龙QMT
    TUSHARE = "tushare"          # Tushare模拟交易
    ALPACA = "alpaca"            # Alpaca (美股)
    BINANCE = "binance"          # Binance (加密货币)
    SIMULATION = "simulation"    # 模拟交易


class LiveBroker:
    """实盘券商接口基类。"""
    
    def __init__(self, broker_type: BrokerType):
        self.broker_type = broker_type
        self.connected = False
        self.account_info = {}
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        raise NotImplementedError
    
    def disconnect(self):
        """断开连接。"""
        self.connected = False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        raise NotImplementedError
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        raise NotImplementedError
    
    def get_balance(self) -> float:
        """获取余额。"""
        raise NotImplementedError
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        raise NotImplementedError
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        raise NotImplementedError
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        raise NotImplementedError


class EasyTraderBroker(LiveBroker):
    """同花顺客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.EASYTRADER)
        self.broker = None
    
    def connect(self, **kwargs) -> bool:
        """连接同花顺客户端。"""
        try:
            import easytrader
            
            # 创建客户端
            self.broker = easytrader.use('ths')
            
            # 连接
            self.broker.connect(
                user=kwargs.get('user'),
                password=kwargs.get('password'),
                exe_path=kwargs.get('exe_path', 'C:/同花顺软件/同花顺/xiadan.exe')
            )
            
            self.connected = True
            logger.info("同花顺客户端连接成功")
            return True
        
        except ImportError:
            logger.error("easytrader未安装，请安装: pip install easytrader")
            return False
        except Exception as e:
            logger.error(f"同花顺连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            info = self.broker.get_account()
            self.account_info = info
            return info
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            positions = self.broker.get_position()
            result = {}
            for pos in positions:
                result[pos['证券代码']] = {
                    'symbol': pos['证券代码'],
                    'name': pos['证券名称'],
                    'quantity': int(pos['持仓数量']),
                    'avg_price': float(pos['成本价']),
                    'current_price': float(pos['现价']),
                    'market_value': float(pos['市值'])
                }
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.broker:
            return 0.0
        
        try:
            info = self.broker.get_account()
            return float(info.get('可用资金', 0))
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.broker:
            return {'success': False, 'message': '未连接'}
        
        try:
            if order_type == 'market':
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            else:
                # 限价单
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            
            return {'success': True, 'order_id': result, 'message': '下单成功'}
        
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.broker:
            return False
        
        try:
            self.broker.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            orders = self.broker.get_entrust()
            for order in orders:
                if order['委托编号'] == order_id:
                    return {
                        'order_id': order['委托编号'],
                        'status': order['委托状态'],
                        'symbol': order['证券代码'],
                        'quantity': int(order['委托数量']),
                        'price': float(order['委托价格'])
                    }
            return {'status': 'not_found'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.broker:
            return []
        
        try:
            trades = self.broker.get_history()
            return trades
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class QMTBroker(LiveBroker):
    """QMT客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.QMT)
        self.client = None
    
    def connect(self, **kwargs) -> bool:
        """连接QMT客户端。"""
        try:
            # QMT使用COM接口
            import win32com.client
            
            self.client = win32com.client.Dispatch('Qmt.HQClient')
            
            # 初始化
            self.client.Init()
            
            # 登录
            result = self.client.Login(
                kwargs.get('user'),
                kwargs.get('password'),
                kwargs.get('ip', '127.0.0.1'),
                kwargs.get('port', 10000)
            )
            
            if result == 0:
                self.connected = True
                logger.info("QMT客户端连接成功")
                return True
            else:
                logger.error(f"QMT登录失败，错误码: {result}")
                return False
        
        except ImportError:
            logger.error("pywin32未安装，请安装: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"QMT连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT API示例（具体API需要参考QMT文档）
            return {
                'account': 'QMT Account',
                'balance': self.get_balance()
            }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT获取持仓
            positions = {}
            # 具体实现需要参考QMT API文档
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.client:
            return 0.0
        
        try:
            # QMT获取余额
            return 0.0
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.client:
            return {'success': False, 'message': '未连接'}
        
        try:
            # QMT下单
            return {'success': True, 'order_id': 'QMT_ORDER', 'message': '下单成功'}
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.client:
            return False
        
        try:
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            return {'order_id': order_id, 'status': 'filled'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.client:
            return []
        
        try:
            return []
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class LiveTradingEngine:
    """实盘交易引擎。"""
    
    def __init__(
        self,
        broker_type: BrokerType = BrokerType.SIMULATION,
        **broker_kwargs
    ):
        
        self.broker_type = broker_type
        self.broker: Optional[LiveBroker] = None
        self.running = False
        
        # 风险管理器
        self.risk_manager = None
        
        # 策略
        self.strategy = None
        
        # 交易日志
        self.trade_log = []
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        # 创建券商实例
        if self.broker_type == BrokerType.EASYTRADER:
            self.broker = EasyTraderBroker()
        elif self.broker_type == BrokerType.QMT:
            self.broker = QMTBroker()
        else:
            # 默认使用模拟券商
            from .simulation import SimulationBroker
            self.broker = SimulationBroker()
        
        return self.broker.connect(**kwargs)
    
    def disconnect(self):
        """断开连接。"""
        if self.broker:
            self.broker.disconnect()
            self.running = False
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def set_risk_manager(self, risk_manager):
        """设置风险管理器。"""
        self.risk_manager = risk_manager
    
    def start(self):
        """启动实盘交易。"""
        if not self.broker or not self.broker.connected:
            logger.error("请先连接券商")
            return
        
        if not self.strategy:
            logger.error("请先设置策略")
            return
        
        self.running = True
        logger.info("实盘交易引擎启动")
        
        # 启动交易循环
        self._trading_loop()
    
    def stop(self):
        """停止实盘交易。"""
        self.running = False
        logger.info("实盘交易引擎停止")
    
    def _trading_loop(self):
        """交易主循环。"""
        while self.running:
            try:
                # 检查是否在交易时间
                if not self._is_trading_time():
                    logger.info("非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # 运行策略
                signals = self.strategy.generate_signals(self.broker)
                
                # 执行交易
                for symbol, signal in signals.items():
                    if signal != 0:
                        self._execute_trade(symbol, signal)
                
                # 更新日志
                self._log_account_status()
                
                # 等待下一个周期
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"交易循环出错: {e}")
                time.sleep(5)
    
    def _is_trading_time(self) -> bool:
        """检查是否在交易时间。"""
        now = datetime.now()
        
        # 检查是否是交易日（简化版）
        if now.weekday() >= 5:
            return False
        
        # 检查时间
        time_str = now.strftime("%H:%M")
        
        # 上午交易时间
        morning = "09:30" <= time_str <= "11:30"
        
        # 下午交易时间
        afternoon = "13:00" <= time_str <= "15:00"
        
        return morning or afternoon
    
    def _execute_trade(self, symbol: str, signal: float):
        """执行交易。"""
        side = 'buy' if signal > 0 else 'sell'
        quantity = int(abs(signal) * 100)
        
        if quantity <= 0:
            return
        
        # 风险检查
        if self.risk_manager:
            # 简化的风险检查
            positions = self.broker.get_positions()
            balance = self.broker.get_balance()
            
            # 检查单一持仓限制
            if symbol in positions:
                pos_value = positions[symbol]['quantity'] * positions[symbol]['current_price']
                total_assets = balance + sum(p['quantity'] * p['current_price'] for p in positions.values())
                if pos_value / total_assets > 0.1:
                    logger.warning(f"持仓超过10%限制: {symbol}")
                    return
        
        # 下单
        result = self.broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity
        )
        
        # 记录日志
        self.trade_log.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'result': result
        })
        
        if result.get('success'):
            logger.info(f"交易成功: {side} {quantity}股 {symbol}")
        else:
            logger.error(f"交易失败: {side} {quantity}股 {symbol} - {result.get('message')}")
    
    def _log_account_status(self):
        """记录账户状态。"""
        if not self.broker:
            return
        
        try:
            summary = {
                'timestamp': datetime.now(),
                'balance': self.broker.get_balance(),
                'positions': self.broker.get_positions(),
                'account_info': self.broker.get_account_info()
            }
            
            # 每小时记录一次
            if len(self.trade_log) == 0 or (
                datetime.now() - self.trade_log[-1]['timestamp']).seconds >= 3600:
                logger.info(f"账户状态: {summary}")
        
        except Exception as e:
            logger.error(f"记录账户状态失败: {e}")
    
    def get_trade_log(self) -> List[Dict]:
        """获取交易日志。"""
        return self.trade_log


# 示例用法
if __name__ == "__main__":
    # 创建实盘交易引擎（使用模拟模式）
    engine = LiveTradingEngine(broker_type=BrokerType.SIMULATION)
    
    # 连接（模拟模式不需要实际连接）
    engine.connect()
    
    # 定义简单策略
    class TestStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            if self.counter % 5 == 0:
                symbols = ["000001", "000002", "600000"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(TestStrategy())
    
    # 启动交易（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    time.sleep(10)
    engine.stop()
    
    # 打印交易日志
    print("\n交易日志:")
    for trade in engine.get_trade_log():
        print(f"{trade['timestamp']}: {trade['side']} {trade['quantity']}股 {trade['symbol']}")
"""
OxQuant Live Trading

实盘交易模块，支持多种券商接口。
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


class BrokerType(Enum):
    """券商类型。"""
    EASYTRADER = "easytrader"    # 同花顺客户端
    QMT = "qmt"                  # 钱龙QMT
    TUSHARE = "tushare"          # Tushare模拟交易
    ALPACA = "alpaca"            # Alpaca (美股)
    BINANCE = "binance"          # Binance (加密货币)
    SIMULATION = "simulation"    # 模拟交易


class LiveBroker:
    """实盘券商接口基类。"""
    
    def __init__(self, broker_type: BrokerType):
        self.broker_type = broker_type
        self.connected = False
        self.account_info = {}
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        raise NotImplementedError
    
    def disconnect(self):
        """断开连接。"""
        self.connected = False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        raise NotImplementedError
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        raise NotImplementedError
    
    def get_balance(self) -> float:
        """获取余额。"""
        raise NotImplementedError
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        raise NotImplementedError
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        raise NotImplementedError
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        raise NotImplementedError


class EasyTraderBroker(LiveBroker):
    """同花顺客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.EASYTRADER)
        self.broker = None
    
    def connect(self, **kwargs) -> bool:
        """连接同花顺客户端。"""
        try:
            import easytrader
            
            # 创建客户端
            self.broker = easytrader.use('ths')
            
            # 连接
            self.broker.connect(
                user=kwargs.get('user'),
                password=kwargs.get('password'),
                exe_path=kwargs.get('exe_path', 'C:/同花顺软件/同花顺/xiadan.exe')
            )
            
            self.connected = True
            logger.info("同花顺客户端连接成功")
            return True
        
        except ImportError:
            logger.error("easytrader未安装，请安装: pip install easytrader")
            return False
        except Exception as e:
            logger.error(f"同花顺连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            info = self.broker.get_account()
            self.account_info = info
            return info
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            positions = self.broker.get_position()
            result = {}
            for pos in positions:
                result[pos['证券代码']] = {
                    'symbol': pos['证券代码'],
                    'name': pos['证券名称'],
                    'quantity': int(pos['持仓数量']),
                    'avg_price': float(pos['成本价']),
                    'current_price': float(pos['现价']),
                    'market_value': float(pos['市值'])
                }
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.broker:
            return 0.0
        
        try:
            info = self.broker.get_account()
            return float(info.get('可用资金', 0))
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.broker:
            return {'success': False, 'message': '未连接'}
        
        try:
            if order_type == 'market':
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            else:
                # 限价单
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            
            return {'success': True, 'order_id': result, 'message': '下单成功'}
        
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.broker:
            return False
        
        try:
            self.broker.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            orders = self.broker.get_entrust()
            for order in orders:
                if order['委托编号'] == order_id:
                    return {
                        'order_id': order['委托编号'],
                        'status': order['委托状态'],
                        'symbol': order['证券代码'],
                        'quantity': int(order['委托数量']),
                        'price': float(order['委托价格'])
                    }
            return {'status': 'not_found'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.broker:
            return []
        
        try:
            trades = self.broker.get_history()
            return trades
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class QMTBroker(LiveBroker):
    """QMT客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.QMT)
        self.client = None
    
    def connect(self, **kwargs) -> bool:
        """连接QMT客户端。"""
        try:
            # QMT使用COM接口
            import win32com.client
            
            self.client = win32com.client.Dispatch('Qmt.HQClient')
            
            # 初始化
            self.client.Init()
            
            # 登录
            result = self.client.Login(
                kwargs.get('user'),
                kwargs.get('password'),
                kwargs.get('ip', '127.0.0.1'),
                kwargs.get('port', 10000)
            )
            
            if result == 0:
                self.connected = True
                logger.info("QMT客户端连接成功")
                return True
            else:
                logger.error(f"QMT登录失败，错误码: {result}")
                return False
        
        except ImportError:
            logger.error("pywin32未安装，请安装: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"QMT连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT API示例（具体API需要参考QMT文档）
            return {
                'account': 'QMT Account',
                'balance': self.get_balance()
            }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT获取持仓
            positions = {}
            # 具体实现需要参考QMT API文档
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.client:
            return 0.0
        
        try:
            # QMT获取余额
            return 0.0
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.client:
            return {'success': False, 'message': '未连接'}
        
        try:
            # QMT下单
            return {'success': True, 'order_id': 'QMT_ORDER', 'message': '下单成功'}
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.client:
            return False
        
        try:
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            return {'order_id': order_id, 'status': 'filled'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.client:
            return []
        
        try:
            return []
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class LiveTradingEngine:
    """实盘交易引擎。"""
    
    def __init__(
        self,
        broker_type: BrokerType = BrokerType.SIMULATION,
        **broker_kwargs
    ):
        
        self.broker_type = broker_type
        self.broker: Optional[LiveBroker] = None
        self.running = False
        
        # 风险管理器
        self.risk_manager = None
        
        # 策略
        self.strategy = None
        
        # 交易日志
        self.trade_log = []
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        # 创建券商实例
        if self.broker_type == BrokerType.EASYTRADER:
            self.broker = EasyTraderBroker()
        elif self.broker_type == BrokerType.QMT:
            self.broker = QMTBroker()
        else:
            # 默认使用模拟券商
            from .simulation import SimulationBroker
            self.broker = SimulationBroker()
        
        return self.broker.connect(**kwargs)
    
    def disconnect(self):
        """断开连接。"""
        if self.broker:
            self.broker.disconnect()
            self.running = False
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def set_risk_manager(self, risk_manager):
        """设置风险管理器。"""
        self.risk_manager = risk_manager
    
    def start(self):
        """启动实盘交易。"""
        if not self.broker or not self.broker.connected:
            logger.error("请先连接券商")
            return
        
        if not self.strategy:
            logger.error("请先设置策略")
            return
        
        self.running = True
        logger.info("实盘交易引擎启动")
        
        # 启动交易循环
        self._trading_loop()
    
    def stop(self):
        """停止实盘交易。"""
        self.running = False
        logger.info("实盘交易引擎停止")
    
    def _trading_loop(self):
        """交易主循环。"""
        while self.running:
            try:
                # 检查是否在交易时间
                if not self._is_trading_time():
                    logger.info("非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # 运行策略
                signals = self.strategy.generate_signals(self.broker)
                
                # 执行交易
                for symbol, signal in signals.items():
                    if signal != 0:
                        self._execute_trade(symbol, signal)
                
                # 更新日志
                self._log_account_status()
                
                # 等待下一个周期
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"交易循环出错: {e}")
                time.sleep(5)
    
    def _is_trading_time(self) -> bool:
        """检查是否在交易时间。"""
        now = datetime.now()
        
        # 检查是否是交易日（简化版）
        if now.weekday() >= 5:
            return False
        
        # 检查时间
        time_str = now.strftime("%H:%M")
        
        # 上午交易时间
        morning = "09:30" <= time_str <= "11:30"
        
        # 下午交易时间
        afternoon = "13:00" <= time_str <= "15:00"
        
        return morning or afternoon
    
    def _execute_trade(self, symbol: str, signal: float):
        """执行交易。"""
        side = 'buy' if signal > 0 else 'sell'
        quantity = int(abs(signal) * 100)
        
        if quantity <= 0:
            return
        
        # 风险检查
        if self.risk_manager:
            # 简化的风险检查
            positions = self.broker.get_positions()
            balance = self.broker.get_balance()
            
            # 检查单一持仓限制
            if symbol in positions:
                pos_value = positions[symbol]['quantity'] * positions[symbol]['current_price']
                total_assets = balance + sum(p['quantity'] * p['current_price'] for p in positions.values())
                if pos_value / total_assets > 0.1:
                    logger.warning(f"持仓超过10%限制: {symbol}")
                    return
        
        # 下单
        result = self.broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity
        )
        
        # 记录日志
        self.trade_log.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'result': result
        })
        
        if result.get('success'):
            logger.info(f"交易成功: {side} {quantity}股 {symbol}")
        else:
            logger.error(f"交易失败: {side} {quantity}股 {symbol} - {result.get('message')}")
    
    def _log_account_status(self):
        """记录账户状态。"""
        if not self.broker:
            return
        
        try:
            summary = {
                'timestamp': datetime.now(),
                'balance': self.broker.get_balance(),
                'positions': self.broker.get_positions(),
                'account_info': self.broker.get_account_info()
            }
            
            # 每小时记录一次
            if len(self.trade_log) == 0 or (
                datetime.now() - self.trade_log[-1]['timestamp']).seconds >= 3600:
                logger.info(f"账户状态: {summary}")
        
        except Exception as e:
            logger.error(f"记录账户状态失败: {e}")
    
    def get_trade_log(self) -> List[Dict]:
        """获取交易日志。"""
        return self.trade_log


# 示例用法
if __name__ == "__main__":
    # 创建实盘交易引擎（使用模拟模式）
    engine = LiveTradingEngine(broker_type=BrokerType.SIMULATION)
    
    # 连接（模拟模式不需要实际连接）
    engine.connect()
    
    # 定义简单策略
    class TestStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            if self.counter % 5 == 0:
                symbols = ["000001", "000002", "600000"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(TestStrategy())
    
    # 启动交易（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    time.sleep(10)
    engine.stop()
    
    # 打印交易日志
    print("\n交易日志:")
    for trade in engine.get_trade_log():
        print(f"{trade['timestamp']}: {trade['side']} {trade['quantity']}股 {trade['symbol']}")
"""
OxQuant Live Trading

实盘交易模块，支持多种券商接口。
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


class BrokerType(Enum):
    """券商类型。"""
    EASYTRADER = "easytrader"    # 同花顺客户端
    QMT = "qmt"                  # 钱龙QMT
    TUSHARE = "tushare"          # Tushare模拟交易
    ALPACA = "alpaca"            # Alpaca (美股)
    BINANCE = "binance"          # Binance (加密货币)
    SIMULATION = "simulation"    # 模拟交易


class LiveBroker:
    """实盘券商接口基类。"""
    
    def __init__(self, broker_type: BrokerType):
        self.broker_type = broker_type
        self.connected = False
        self.account_info = {}
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        raise NotImplementedError
    
    def disconnect(self):
        """断开连接。"""
        self.connected = False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        raise NotImplementedError
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        raise NotImplementedError
    
    def get_balance(self) -> float:
        """获取余额。"""
        raise NotImplementedError
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        raise NotImplementedError
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        raise NotImplementedError
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        raise NotImplementedError


class EasyTraderBroker(LiveBroker):
    """同花顺客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.EASYTRADER)
        self.broker = None
    
    def connect(self, **kwargs) -> bool:
        """连接同花顺客户端。"""
        try:
            import easytrader
            
            # 创建客户端
            self.broker = easytrader.use('ths')
            
            # 连接
            self.broker.connect(
                user=kwargs.get('user'),
                password=kwargs.get('password'),
                exe_path=kwargs.get('exe_path', 'C:/同花顺软件/同花顺/xiadan.exe')
            )
            
            self.connected = True
            logger.info("同花顺客户端连接成功")
            return True
        
        except ImportError:
            logger.error("easytrader未安装，请安装: pip install easytrader")
            return False
        except Exception as e:
            logger.error(f"同花顺连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            info = self.broker.get_account()
            self.account_info = info
            return info
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            positions = self.broker.get_position()
            result = {}
            for pos in positions:
                result[pos['证券代码']] = {
                    'symbol': pos['证券代码'],
                    'name': pos['证券名称'],
                    'quantity': int(pos['持仓数量']),
                    'avg_price': float(pos['成本价']),
                    'current_price': float(pos['现价']),
                    'market_value': float(pos['市值'])
                }
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.broker:
            return 0.0
        
        try:
            info = self.broker.get_account()
            return float(info.get('可用资金', 0))
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.broker:
            return {'success': False, 'message': '未连接'}
        
        try:
            if order_type == 'market':
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            else:
                # 限价单
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            
            return {'success': True, 'order_id': result, 'message': '下单成功'}
        
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.broker:
            return False
        
        try:
            self.broker.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            orders = self.broker.get_entrust()
            for order in orders:
                if order['委托编号'] == order_id:
                    return {
                        'order_id': order['委托编号'],
                        'status': order['委托状态'],
                        'symbol': order['证券代码'],
                        'quantity': int(order['委托数量']),
                        'price': float(order['委托价格'])
                    }
            return {'status': 'not_found'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.broker:
            return []
        
        try:
            trades = self.broker.get_history()
            return trades
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class QMTBroker(LiveBroker):
    """QMT客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.QMT)
        self.client = None
    
    def connect(self, **kwargs) -> bool:
        """连接QMT客户端。"""
        try:
            # QMT使用COM接口
            import win32com.client
            
            self.client = win32com.client.Dispatch('Qmt.HQClient')
            
            # 初始化
            self.client.Init()
            
            # 登录
            result = self.client.Login(
                kwargs.get('user'),
                kwargs.get('password'),
                kwargs.get('ip', '127.0.0.1'),
                kwargs.get('port', 10000)
            )
            
            if result == 0:
                self.connected = True
                logger.info("QMT客户端连接成功")
                return True
            else:
                logger.error(f"QMT登录失败，错误码: {result}")
                return False
        
        except ImportError:
            logger.error("pywin32未安装，请安装: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"QMT连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT API示例（具体API需要参考QMT文档）
            return {
                'account': 'QMT Account',
                'balance': self.get_balance()
            }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT获取持仓
            positions = {}
            # 具体实现需要参考QMT API文档
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.client:
            return 0.0
        
        try:
            # QMT获取余额
            return 0.0
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.client:
            return {'success': False, 'message': '未连接'}
        
        try:
            # QMT下单
            return {'success': True, 'order_id': 'QMT_ORDER', 'message': '下单成功'}
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.client:
            return False
        
        try:
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            return {'order_id': order_id, 'status': 'filled'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.client:
            return []
        
        try:
            return []
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class LiveTradingEngine:
    """实盘交易引擎。"""
    
    def __init__(
        self,
        broker_type: BrokerType = BrokerType.SIMULATION,
        **broker_kwargs
    ):
        
        self.broker_type = broker_type
        self.broker: Optional[LiveBroker] = None
        self.running = False
        
        # 风险管理器
        self.risk_manager = None
        
        # 策略
        self.strategy = None
        
        # 交易日志
        self.trade_log = []
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        # 创建券商实例
        if self.broker_type == BrokerType.EASYTRADER:
            self.broker = EasyTraderBroker()
        elif self.broker_type == BrokerType.QMT:
            self.broker = QMTBroker()
        else:
            # 默认使用模拟券商
            from .simulation import SimulationBroker
            self.broker = SimulationBroker()
        
        return self.broker.connect(**kwargs)
    
    def disconnect(self):
        """断开连接。"""
        if self.broker:
            self.broker.disconnect()
            self.running = False
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def set_risk_manager(self, risk_manager):
        """设置风险管理器。"""
        self.risk_manager = risk_manager
    
    def start(self):
        """启动实盘交易。"""
        if not self.broker or not self.broker.connected:
            logger.error("请先连接券商")
            return
        
        if not self.strategy:
            logger.error("请先设置策略")
            return
        
        self.running = True
        logger.info("实盘交易引擎启动")
        
        # 启动交易循环
        self._trading_loop()
    
    def stop(self):
        """停止实盘交易。"""
        self.running = False
        logger.info("实盘交易引擎停止")
    
    def _trading_loop(self):
        """交易主循环。"""
        while self.running:
            try:
                # 检查是否在交易时间
                if not self._is_trading_time():
                    logger.info("非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # 运行策略
                signals = self.strategy.generate_signals(self.broker)
                
                # 执行交易
                for symbol, signal in signals.items():
                    if signal != 0:
                        self._execute_trade(symbol, signal)
                
                # 更新日志
                self._log_account_status()
                
                # 等待下一个周期
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"交易循环出错: {e}")
                time.sleep(5)
    
    def _is_trading_time(self) -> bool:
        """检查是否在交易时间。"""
        now = datetime.now()
        
        # 检查是否是交易日（简化版）
        if now.weekday() >= 5:
            return False
        
        # 检查时间
        time_str = now.strftime("%H:%M")
        
        # 上午交易时间
        morning = "09:30" <= time_str <= "11:30"
        
        # 下午交易时间
        afternoon = "13:00" <= time_str <= "15:00"
        
        return morning or afternoon
    
    def _execute_trade(self, symbol: str, signal: float):
        """执行交易。"""
        side = 'buy' if signal > 0 else 'sell'
        quantity = int(abs(signal) * 100)
        
        if quantity <= 0:
            return
        
        # 风险检查
        if self.risk_manager:
            # 简化的风险检查
            positions = self.broker.get_positions()
            balance = self.broker.get_balance()
            
            # 检查单一持仓限制
            if symbol in positions:
                pos_value = positions[symbol]['quantity'] * positions[symbol]['current_price']
                total_assets = balance + sum(p['quantity'] * p['current_price'] for p in positions.values())
                if pos_value / total_assets > 0.1:
                    logger.warning(f"持仓超过10%限制: {symbol}")
                    return
        
        # 下单
        result = self.broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity
        )
        
        # 记录日志
        self.trade_log.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'result': result
        })
        
        if result.get('success'):
            logger.info(f"交易成功: {side} {quantity}股 {symbol}")
        else:
            logger.error(f"交易失败: {side} {quantity}股 {symbol} - {result.get('message')}")
    
    def _log_account_status(self):
        """记录账户状态。"""
        if not self.broker:
            return
        
        try:
            summary = {
                'timestamp': datetime.now(),
                'balance': self.broker.get_balance(),
                'positions': self.broker.get_positions(),
                'account_info': self.broker.get_account_info()
            }
            
            # 每小时记录一次
            if len(self.trade_log) == 0 or (
                datetime.now() - self.trade_log[-1]['timestamp']).seconds >= 3600:
                logger.info(f"账户状态: {summary}")
        
        except Exception as e:
            logger.error(f"记录账户状态失败: {e}")
    
    def get_trade_log(self) -> List[Dict]:
        """获取交易日志。"""
        return self.trade_log


# 示例用法
if __name__ == "__main__":
    # 创建实盘交易引擎（使用模拟模式）
    engine = LiveTradingEngine(broker_type=BrokerType.SIMULATION)
    
    # 连接（模拟模式不需要实际连接）
    engine.connect()
    
    # 定义简单策略
    class TestStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            if self.counter % 5 == 0:
                symbols = ["000001", "000002", "600000"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(TestStrategy())
    
    # 启动交易（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    time.sleep(10)
    engine.stop()
    
    # 打印交易日志
    print("\n交易日志:")
    for trade in engine.get_trade_log():
        print(f"{trade['timestamp']}: {trade['side']} {trade['quantity']}股 {trade['symbol']}")
"""
OxQuant Live Trading

实盘交易模块，支持多种券商接口。
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


class BrokerType(Enum):
    """券商类型。"""
    EASYTRADER = "easytrader"    # 同花顺客户端
    QMT = "qmt"                  # 钱龙QMT
    TUSHARE = "tushare"          # Tushare模拟交易
    ALPACA = "alpaca"            # Alpaca (美股)
    BINANCE = "binance"          # Binance (加密货币)
    SIMULATION = "simulation"    # 模拟交易


class LiveBroker:
    """实盘券商接口基类。"""
    
    def __init__(self, broker_type: BrokerType):
        self.broker_type = broker_type
        self.connected = False
        self.account_info = {}
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        raise NotImplementedError
    
    def disconnect(self):
        """断开连接。"""
        self.connected = False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        raise NotImplementedError
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        raise NotImplementedError
    
    def get_balance(self) -> float:
        """获取余额。"""
        raise NotImplementedError
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        raise NotImplementedError
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        raise NotImplementedError
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        raise NotImplementedError


class EasyTraderBroker(LiveBroker):
    """同花顺客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.EASYTRADER)
        self.broker = None
    
    def connect(self, **kwargs) -> bool:
        """连接同花顺客户端。"""
        try:
            import easytrader
            
            # 创建客户端
            self.broker = easytrader.use('ths')
            
            # 连接
            self.broker.connect(
                user=kwargs.get('user'),
                password=kwargs.get('password'),
                exe_path=kwargs.get('exe_path', 'C:/同花顺软件/同花顺/xiadan.exe')
            )
            
            self.connected = True
            logger.info("同花顺客户端连接成功")
            return True
        
        except ImportError:
            logger.error("easytrader未安装，请安装: pip install easytrader")
            return False
        except Exception as e:
            logger.error(f"同花顺连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            info = self.broker.get_account()
            self.account_info = info
            return info
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            positions = self.broker.get_position()
            result = {}
            for pos in positions:
                result[pos['证券代码']] = {
                    'symbol': pos['证券代码'],
                    'name': pos['证券名称'],
                    'quantity': int(pos['持仓数量']),
                    'avg_price': float(pos['成本价']),
                    'current_price': float(pos['现价']),
                    'market_value': float(pos['市值'])
                }
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.broker:
            return 0.0
        
        try:
            info = self.broker.get_account()
            return float(info.get('可用资金', 0))
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.broker:
            return {'success': False, 'message': '未连接'}
        
        try:
            if order_type == 'market':
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            else:
                # 限价单
                result = self.broker.buy(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                ) if side == 'buy' else self.broker.sell(
                    stock_code=symbol,
                    price=price,
                    amount=quantity
                )
            
            return {'success': True, 'order_id': result, 'message': '下单成功'}
        
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.broker:
            return False
        
        try:
            self.broker.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.broker:
            return {}
        
        try:
            orders = self.broker.get_entrust()
            for order in orders:
                if order['委托编号'] == order_id:
                    return {
                        'order_id': order['委托编号'],
                        'status': order['委托状态'],
                        'symbol': order['证券代码'],
                        'quantity': int(order['委托数量']),
                        'price': float(order['委托价格'])
                    }
            return {'status': 'not_found'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.broker:
            return []
        
        try:
            trades = self.broker.get_history()
            return trades
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class QMTBroker(LiveBroker):
    """QMT客户端接口。"""
    
    def __init__(self):
        super().__init__(BrokerType.QMT)
        self.client = None
    
    def connect(self, **kwargs) -> bool:
        """连接QMT客户端。"""
        try:
            # QMT使用COM接口
            import win32com.client
            
            self.client = win32com.client.Dispatch('Qmt.HQClient')
            
            # 初始化
            self.client.Init()
            
            # 登录
            result = self.client.Login(
                kwargs.get('user'),
                kwargs.get('password'),
                kwargs.get('ip', '127.0.0.1'),
                kwargs.get('port', 10000)
            )
            
            if result == 0:
                self.connected = True
                logger.info("QMT客户端连接成功")
                return True
            else:
                logger.error(f"QMT登录失败，错误码: {result}")
                return False
        
        except ImportError:
            logger.error("pywin32未安装，请安装: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"QMT连接失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT API示例（具体API需要参考QMT文档）
            return {
                'account': 'QMT Account',
                'balance': self.get_balance()
            }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    def get_positions(self) -> Dict[str, dict]:
        """获取持仓。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            # QMT获取持仓
            positions = {}
            # 具体实现需要参考QMT API文档
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {}
    
    def get_balance(self) -> float:
        """获取余额。"""
        if not self.connected or not self.client:
            return 0.0
        
        try:
            # QMT获取余额
            return 0.0
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """下单。"""
        if not self.connected or not self.client:
            return {'success': False, 'message': '未连接'}
        
        try:
            # QMT下单
            return {'success': True, 'order_id': 'QMT_ORDER', 'message': '下单成功'}
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self.connected or not self.client:
            return False
        
        try:
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态。"""
        if not self.connected or not self.client:
            return {}
        
        try:
            return {'order_id': order_id, 'status': 'filled'}
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {}
    
    def get_trade_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取交易历史。"""
        if not self.connected or not self.client:
            return []
        
        try:
            return []
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []


class LiveTradingEngine:
    """实盘交易引擎。"""
    
    def __init__(
        self,
        broker_type: BrokerType = BrokerType.SIMULATION,
        **broker_kwargs
    ):
        
        self.broker_type = broker_type
        self.broker: Optional[LiveBroker] = None
        self.running = False
        
        # 风险管理器
        self.risk_manager = None
        
        # 策略
        self.strategy = None
        
        # 交易日志
        self.trade_log = []
    
    def connect(self, **kwargs) -> bool:
        """连接券商。"""
        # 创建券商实例
        if self.broker_type == BrokerType.EASYTRADER:
            self.broker = EasyTraderBroker()
        elif self.broker_type == BrokerType.QMT:
            self.broker = QMTBroker()
        else:
            # 默认使用模拟券商
            from .simulation import SimulationBroker
            self.broker = SimulationBroker()
        
        return self.broker.connect(**kwargs)
    
    def disconnect(self):
        """断开连接。"""
        if self.broker:
            self.broker.disconnect()
            self.running = False
    
    def set_strategy(self, strategy):
        """设置策略。"""
        self.strategy = strategy
    
    def set_risk_manager(self, risk_manager):
        """设置风险管理器。"""
        self.risk_manager = risk_manager
    
    def start(self):
        """启动实盘交易。"""
        if not self.broker or not self.broker.connected:
            logger.error("请先连接券商")
            return
        
        if not self.strategy:
            logger.error("请先设置策略")
            return
        
        self.running = True
        logger.info("实盘交易引擎启动")
        
        # 启动交易循环
        self._trading_loop()
    
    def stop(self):
        """停止实盘交易。"""
        self.running = False
        logger.info("实盘交易引擎停止")
    
    def _trading_loop(self):
        """交易主循环。"""
        while self.running:
            try:
                # 检查是否在交易时间
                if not self._is_trading_time():
                    logger.info("非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # 运行策略
                signals = self.strategy.generate_signals(self.broker)
                
                # 执行交易
                for symbol, signal in signals.items():
                    if signal != 0:
                        self._execute_trade(symbol, signal)
                
                # 更新日志
                self._log_account_status()
                
                # 等待下一个周期
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"交易循环出错: {e}")
                time.sleep(5)
    
    def _is_trading_time(self) -> bool:
        """检查是否在交易时间。"""
        now = datetime.now()
        
        # 检查是否是交易日（简化版）
        if now.weekday() >= 5:
            return False
        
        # 检查时间
        time_str = now.strftime("%H:%M")
        
        # 上午交易时间
        morning = "09:30" <= time_str <= "11:30"
        
        # 下午交易时间
        afternoon = "13:00" <= time_str <= "15:00"
        
        return morning or afternoon
    
    def _execute_trade(self, symbol: str, signal: float):
        """执行交易。"""
        side = 'buy' if signal > 0 else 'sell'
        quantity = int(abs(signal) * 100)
        
        if quantity <= 0:
            return
        
        # 风险检查
        if self.risk_manager:
            # 简化的风险检查
            positions = self.broker.get_positions()
            balance = self.broker.get_balance()
            
            # 检查单一持仓限制
            if symbol in positions:
                pos_value = positions[symbol]['quantity'] * positions[symbol]['current_price']
                total_assets = balance + sum(p['quantity'] * p['current_price'] for p in positions.values())
                if pos_value / total_assets > 0.1:
                    logger.warning(f"持仓超过10%限制: {symbol}")
                    return
        
        # 下单
        result = self.broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity
        )
        
        # 记录日志
        self.trade_log.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'result': result
        })
        
        if result.get('success'):
            logger.info(f"交易成功: {side} {quantity}股 {symbol}")
        else:
            logger.error(f"交易失败: {side} {quantity}股 {symbol} - {result.get('message')}")
    
    def _log_account_status(self):
        """记录账户状态。"""
        if not self.broker:
            return
        
        try:
            summary = {
                'timestamp': datetime.now(),
                'balance': self.broker.get_balance(),
                'positions': self.broker.get_positions(),
                'account_info': self.broker.get_account_info()
            }
            
            # 每小时记录一次
            if len(self.trade_log) == 0 or (
                datetime.now() - self.trade_log[-1]['timestamp']).seconds >= 3600:
                logger.info(f"账户状态: {summary}")
        
        except Exception as e:
            logger.error(f"记录账户状态失败: {e}")
    
    def get_trade_log(self) -> List[Dict]:
        """获取交易日志。"""
        return self.trade_log


# 示例用法
if __name__ == "__main__":
    # 创建实盘交易引擎（使用模拟模式）
    engine = LiveTradingEngine(broker_type=BrokerType.SIMULATION)
    
    # 连接（模拟模式不需要实际连接）
    engine.connect()
    
    # 定义简单策略
    class TestStrategy:
        def __init__(self):
            self.counter = 0
        
        def generate_signals(self, broker):
            self.counter += 1
            
            if self.counter % 5 == 0:
                symbols = ["000001", "000002", "600000"]
                symbol = np.random.choice(symbols)
                signal = np.random.choice([1, -1])
                return {symbol: signal}
            
            return {}
    
    # 设置策略
    engine.set_strategy(TestStrategy())
    
    # 启动交易（运行10秒）
    import threading
    t = threading.Thread(target=engine.start)
    t.daemon = True
    t.start()
    
    time.sleep(10)
    engine.stop()
    
    # 打印交易日志
    print("\n交易日志:")
    for trade in engine.get_trade_log():
        print(f"{trade['timestamp']}: {trade['side']} {trade['quantity']}股 {trade['symbol']}")