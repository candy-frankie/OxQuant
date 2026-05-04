"""
OxQuant Risk Management

风控模块，支持多种风险控制策略。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskType(Enum):
    """风险类型。"""
    MARKET_RISK = "market_risk"           # 市场风险
    CREDIT_RISK = "credit_risk"           # 信用风险
    LIQUIDITY_RISK = "liquidity_risk"     # 流动性风险
    OPERATIONAL_RISK = "operational_risk" # 操作风险
    CONCENTRATION_RISK = "concentration_risk" # 集中度风险
    DRAWDOWN_RISK = "drawdown_risk"       # 回撤风险
    DAILY_LOSS_RISK = "daily_loss_risk"   # 单日亏损风险


class RiskLevel(Enum):
    """风险等级。"""
    LOW = "low"       # 低风险
    MEDIUM = "medium" # 中等风险
    HIGH = "high"     # 高风险
    CRITICAL = "critical" # 严重风险


class RiskCheckResult:
    """风险检查结果。"""
    
    def __init__(
        self,
        passed: bool,
        reason: str = "",
        risk_type: RiskType = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        details: Optional[Dict] = None
    ):
        self.passed = passed
        self.reason = reason
        self.risk_type = risk_type
        self.risk_level = risk_level
        self.details = details or {}
    
    def __bool__(self):
        return self.passed
    
    def __repr__(self):
        return f"RiskCheckResult(passed={self.passed}, reason={self.reason}, risk_type={self.risk_type})"


class RiskManager:
    """风险管理器。"""
    
    def __init__(
        self,
        max_position_size_pct: float = 0.1,      # 单一持仓最大比例
        max_portfolio_risk_pct: float = 0.02,    # 组合最大风险
        max_drawdown_pct: float = 0.1,           # 最大回撤
        max_daily_loss_pct: float = 0.05,        # 单日最大亏损
        max_concentration_pct: float = 0.2,      # 行业/板块最大集中度
        max_open_positions: int = 20,            # 最大持仓数量
        max_single_stock_risk: float = 0.01,     # 单只股票最大风险贡献
        max_gross_exposure: float = 1.0,         # 最大总敞口
        max_leverage: float = 1.0,               # 最大杠杆
        volatility_target: float = 0.15          # 目标波动率
    ):
        
        # 风险参数
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_concentration_pct = max_concentration_pct
        self.max_open_positions = max_open_positions
        self.max_single_stock_risk = max_single_stock_risk
        self.max_gross_exposure = max_gross_exposure
        self.max_leverage = max_leverage
        self.volatility_target = volatility_target
        
        # 风险状态
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.running_max = 0.0
        self.daily_high = 0.0
        
        # 风控事件记录
        self.risk_events = []
    
    def reset_daily(self):
        """重置每日统计。"""
        self.daily_pnl = 0.0
        self.daily_high = 0.0
    
    def record_pnl(self, pnl: float, portfolio_value: float):
        """记录盈亏。"""
        self.daily_pnl += pnl
        
        # 更新最大回撤
        self.running_max = max(self.running_max, portfolio_value)
        current_drawdown = (self.running_max - portfolio_value) / self.running_max
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # 更新当日高点
        self.daily_high = max(self.daily_high, portfolio_value)
    
    def check_position_size(
        self,
        order_value: float,
        portfolio_value: float,
        existing_position_value: float = 0.0
    ) -> RiskCheckResult:
        """检查单一持仓大小限制。"""
        new_position_value = existing_position_value + order_value
        position_pct = new_position_value / portfolio_value
        
        if position_pct > self.max_position_size_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"持仓比例超过限制: {position_pct:.1%} > {self.max_position_size_pct:.1%}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'position_pct': position_pct,
                    'max_allowed': self.max_position_size_pct,
                    'order_value': order_value,
                    'existing_value': existing_position_value
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_portfolio_concentration(
        self,
        sector: str,
        sector_exposure: float,
        portfolio_value: float
    ) -> RiskCheckResult:
        """检查行业/板块集中度。"""
        sector_pct = sector_exposure / portfolio_value
        
        if sector_pct > self.max_concentration_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"{sector}板块持仓超过限制: {sector_pct:.1%} > {self.max_concentration_pct:.1%}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'sector': sector,
                    'sector_pct': sector_pct,
                    'max_allowed': self.max_concentration_pct
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_drawdown(self, portfolio_value: float) -> RiskCheckResult:
        """检查最大回撤。"""
        current_drawdown = (self.running_max - portfolio_value) / self.running_max if self.running_max > 0 else 0
        
        if current_drawdown > self.max_drawdown_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"回撤超过限制: {current_drawdown:.1%} > {self.max_drawdown_pct:.1%}",
                risk_type=RiskType.DRAWDOWN_RISK,
                risk_level=RiskLevel.CRITICAL,
                details={
                    'current_drawdown': current_drawdown,
                    'max_allowed': self.max_drawdown_pct,
                    'running_max': self.running_max
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_daily_loss(self, portfolio_value: float) -> RiskCheckResult:
        """检查单日亏损。"""
        daily_return = self.daily_pnl / (portfolio_value - self.daily_pnl) if (portfolio_value - self.daily_pnl) > 0 else 0
        
        if daily_return < -self.max_daily_loss_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"单日亏损超过限制: {daily_return:.1%} < -{self.max_daily_loss_pct:.1%}",
                risk_type=RiskType.DAILY_LOSS_RISK,
                risk_level=RiskLevel.CRITICAL,
                details={
                    'daily_return': daily_return,
                    'max_allowed': -self.max_daily_loss_pct,
                    'daily_pnl': self.daily_pnl
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_open_positions(self, num_positions: int) -> RiskCheckResult:
        """检查持仓数量限制。"""
        if num_positions >= self.max_open_positions:
            return RiskCheckResult(
                passed=False,
                reason=f"持仓数量超过限制: {num_positions} >= {self.max_open_positions}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.MEDIUM,
                details={
                    'num_positions': num_positions,
                    'max_allowed': self.max_open_positions
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_leverage(self, gross_exposure: float, net_exposure: float) -> RiskCheckResult:
        """检查杠杆限制。"""
        leverage = gross_exposure / net_exposure if net_exposure > 0 else 0
        
        if leverage > self.max_leverage:
            return RiskCheckResult(
                passed=False,
                reason=f"杠杆超过限制: {leverage:.2f}x > {self.max_leverage:.2f}x",
                risk_type=RiskType.MARKET_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'leverage': leverage,
                    'gross_exposure': gross_exposure,
                    'net_exposure': net_exposure,
                    'max_allowed': self.max_leverage
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_all(
        self,
        order_value: float,
        portfolio_value: float,
        existing_position_value: float = 0.0,
        num_positions: int = 0,
        sector: str = "",
        sector_exposure: float = 0.0,
        gross_exposure: float = 0.0,
        net_exposure: float = 0.0
    ) -> RiskCheckResult:
        """执行所有风险检查。"""
        checks = [
            ('drawdown', lambda: self.check_drawdown(portfolio_value)),
            ('daily_loss', lambda: self.check_daily_loss(portfolio_value)),
            ('open_positions', lambda: self.check_open_positions(num_positions)),
            ('position_size', lambda: self.check_position_size(order_value, portfolio_value, existing_position_value)),
        ]
        
        if sector:
            checks.append(('concentration', lambda: self.check_portfolio_concentration(sector, sector_exposure, portfolio_value)))
        
        if gross_exposure > 0 and net_exposure > 0:
            checks.append(('leverage', lambda: self.check_leverage(gross_exposure, net_exposure)))
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                if not result:
                    # 记录风控事件
                    self._record_risk_event(result)
                    return result
            except Exception as e:
                logger.error(f"风险检查 {check_name} 出错: {e}")
        
        return RiskCheckResult(passed=True)
    
    def _record_risk_event(self, result: RiskCheckResult):
        """记录风控事件。"""
        event = {
            'timestamp': datetime.now(),
            'risk_type': result.risk_type.value,
            'risk_level': result.risk_level.value,
            'reason': result.reason,
            'details': result.details
        }
        
        self.risk_events.append(event)
        
        # 严重风险发送告警
        if result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._send_alert(event)
    
    def _send_alert(self, event: Dict):
        """发送风险告警。"""
        logger.critical(f"风险告警 [{event['risk_level'].upper()}]: {event['reason']}")
        
        # 可以扩展：发送邮件、短信、企业微信等
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        horizon_days: int = 1
    ) -> float:
        """计算VaR（在险价值）。"""
        if len(returns) < 2:
            return 0.0
        
        # 简单的参数法VaR
        mean_return = returns.mean()
        std_return = returns.std()
        
        # 使用正态分布
        from scipy.stats import norm
        z_score = norm.ppf(1 - confidence_level)
        
        var = -(mean_return + z_score * std_return) * np.sqrt(horizon_days)
        
        return var
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """计算CVaR（条件在险价值）。"""
        if len(returns) < 2:
            return 0.0
        
        var = self.calculate_var(returns, confidence_level)
        
        # 找到所有超过VaR的损失
        tail_returns = returns[returns < -var]
        
        if len(tail_returns) == 0:
            return var
        
        cvar = -tail_returns.mean()
        
        return cvar
    
    def calculate_risk_contribution(
        self,
        weights: pd.Series,
        covariance_matrix: pd.DataFrame
    ) -> pd.Series:
        """计算各资产的风险贡献。"""
        portfolio_std = np.sqrt(weights @ covariance_matrix @ weights.T)
        risk_contributions = (weights * (covariance_matrix @ weights)) / portfolio_std
        
        return risk_contributions
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要。"""
        return {
            'max_drawdown': self.max_drawdown,
            'daily_pnl': self.daily_pnl,
            'num_risk_events': len(self.risk_events),
            'recent_events': self.risk_events[-5:] if len(self.risk_events) > 0 else []
        }


class RiskMonitor:
    """风险监控器。"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        self.monitoring = False
    
    def start(self):
        """开始监控。"""
        self.monitoring = True
        logger.info("风险监控器启动")
    
    def stop(self):
        """停止监控。"""
        self.monitoring = False
        logger.info("风险监控器停止")
    
    def monitor(
        self,
        portfolio_value: float,
        positions: Dict[str, dict],
        daily_pnl: float = 0.0
    ) -> Dict[str, Any]:
        """执行监控。"""
        if not self.monitoring:
            return {}
        
        # 更新风险管理器
        self.risk_manager.record_pnl(daily_pnl, portfolio_value)
        
        # 检查各项风险
        checks = {
            'drawdown': self.risk_manager.check_drawdown(portfolio_value),
            'daily_loss': self.risk_manager.check_daily_loss(portfolio_value),
            'open_positions': self.risk_manager.check_open_positions(len(positions))
        }
        
        # 检查单一持仓风险
        for symbol, pos in positions.items():
            pos_value = pos['quantity'] * pos.get('current_price', pos.get('avg_price', 0))
            check = self.risk_manager.check_position_size(pos_value, portfolio_value)
            checks[f'position_{symbol}'] = check
        
        # 汇总结果
        passed = all(check.passed for check in checks.values())
        
        return {
            'overall_passed': passed,
            'checks': {k: {'passed': v.passed, 'reason': v.reason, 'risk_level': v.risk_level.value} for k, v in checks.items()},
            'risk_summary': self.risk_manager.get_risk_summary()
        }


# 示例用法
if __name__ == "__main__":
    # 创建风险管理器
    risk_manager = RiskManager(
        max_position_size_pct=0.1,
        max_drawdown_pct=0.1,
        max_daily_loss_pct=0.05,
        max_open_positions=10
    )
    
    # 模拟组合数据
    portfolio_value = 1000000
    order_value = 150000  # 15%的持仓
    existing_position_value = 0
    num_positions = 5
    
    # 执行风险检查
    result = risk_manager.check_all(
        order_value=order_value,
        portfolio_value=portfolio_value,
        existing_position_value=existing_position_value,
        num_positions=num_positions
    )
    
    print(f"风险检查结果: {result.passed}")
    print(f"原因: {result.reason}")
    print(f"风险类型: {result.risk_type}")
    print(f"风险等级: {result.risk_level}")
    
    # 计算VaR
    returns = pd.Series(np.random.randn(252) * 0.01)  # 模拟一年的日收益
    var = risk_manager.calculate_var(returns)
    cvar = risk_manager.calculate_cvar(returns)
    
    print(f"\nVaR (95%): {var:.2%}")
    print(f"CVaR (95%): {cvar:.2%}")
    
    # 获取风险摘要
    print(f"\n风险摘要:")
    print(risk_manager.get_risk_summary())
"""
OxQuant Risk Management

风控模块，支持多种风险控制策略。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskType(Enum):
    """风险类型。"""
    MARKET_RISK = "market_risk"           # 市场风险
    CREDIT_RISK = "credit_risk"           # 信用风险
    LIQUIDITY_RISK = "liquidity_risk"     # 流动性风险
    OPERATIONAL_RISK = "operational_risk" # 操作风险
    CONCENTRATION_RISK = "concentration_risk" # 集中度风险
    DRAWDOWN_RISK = "drawdown_risk"       # 回撤风险
    DAILY_LOSS_RISK = "daily_loss_risk"   # 单日亏损风险


class RiskLevel(Enum):
    """风险等级。"""
    LOW = "low"       # 低风险
    MEDIUM = "medium" # 中等风险
    HIGH = "high"     # 高风险
    CRITICAL = "critical" # 严重风险


class RiskCheckResult:
    """风险检查结果。"""
    
    def __init__(
        self,
        passed: bool,
        reason: str = "",
        risk_type: RiskType = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        details: Optional[Dict] = None
    ):
        self.passed = passed
        self.reason = reason
        self.risk_type = risk_type
        self.risk_level = risk_level
        self.details = details or {}
    
    def __bool__(self):
        return self.passed
    
    def __repr__(self):
        return f"RiskCheckResult(passed={self.passed}, reason={self.reason}, risk_type={self.risk_type})"


class RiskManager:
    """风险管理器。"""
    
    def __init__(
        self,
        max_position_size_pct: float = 0.1,      # 单一持仓最大比例
        max_portfolio_risk_pct: float = 0.02,    # 组合最大风险
        max_drawdown_pct: float = 0.1,           # 最大回撤
        max_daily_loss_pct: float = 0.05,        # 单日最大亏损
        max_concentration_pct: float = 0.2,      # 行业/板块最大集中度
        max_open_positions: int = 20,            # 最大持仓数量
        max_single_stock_risk: float = 0.01,     # 单只股票最大风险贡献
        max_gross_exposure: float = 1.0,         # 最大总敞口
        max_leverage: float = 1.0,               # 最大杠杆
        volatility_target: float = 0.15          # 目标波动率
    ):
        
        # 风险参数
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_concentration_pct = max_concentration_pct
        self.max_open_positions = max_open_positions
        self.max_single_stock_risk = max_single_stock_risk
        self.max_gross_exposure = max_gross_exposure
        self.max_leverage = max_leverage
        self.volatility_target = volatility_target
        
        # 风险状态
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.running_max = 0.0
        self.daily_high = 0.0
        
        # 风控事件记录
        self.risk_events = []
    
    def reset_daily(self):
        """重置每日统计。"""
        self.daily_pnl = 0.0
        self.daily_high = 0.0
    
    def record_pnl(self, pnl: float, portfolio_value: float):
        """记录盈亏。"""
        self.daily_pnl += pnl
        
        # 更新最大回撤
        self.running_max = max(self.running_max, portfolio_value)
        current_drawdown = (self.running_max - portfolio_value) / self.running_max
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # 更新当日高点
        self.daily_high = max(self.daily_high, portfolio_value)
    
    def check_position_size(
        self,
        order_value: float,
        portfolio_value: float,
        existing_position_value: float = 0.0
    ) -> RiskCheckResult:
        """检查单一持仓大小限制。"""
        new_position_value = existing_position_value + order_value
        position_pct = new_position_value / portfolio_value
        
        if position_pct > self.max_position_size_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"持仓比例超过限制: {position_pct:.1%} > {self.max_position_size_pct:.1%}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'position_pct': position_pct,
                    'max_allowed': self.max_position_size_pct,
                    'order_value': order_value,
                    'existing_value': existing_position_value
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_portfolio_concentration(
        self,
        sector: str,
        sector_exposure: float,
        portfolio_value: float
    ) -> RiskCheckResult:
        """检查行业/板块集中度。"""
        sector_pct = sector_exposure / portfolio_value
        
        if sector_pct > self.max_concentration_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"{sector}板块持仓超过限制: {sector_pct:.1%} > {self.max_concentration_pct:.1%}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'sector': sector,
                    'sector_pct': sector_pct,
                    'max_allowed': self.max_concentration_pct
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_drawdown(self, portfolio_value: float) -> RiskCheckResult:
        """检查最大回撤。"""
        current_drawdown = (self.running_max - portfolio_value) / self.running_max if self.running_max > 0 else 0
        
        if current_drawdown > self.max_drawdown_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"回撤超过限制: {current_drawdown:.1%} > {self.max_drawdown_pct:.1%}",
                risk_type=RiskType.DRAWDOWN_RISK,
                risk_level=RiskLevel.CRITICAL,
                details={
                    'current_drawdown': current_drawdown,
                    'max_allowed': self.max_drawdown_pct,
                    'running_max': self.running_max
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_daily_loss(self, portfolio_value: float) -> RiskCheckResult:
        """检查单日亏损。"""
        daily_return = self.daily_pnl / (portfolio_value - self.daily_pnl) if (portfolio_value - self.daily_pnl) > 0 else 0
        
        if daily_return < -self.max_daily_loss_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"单日亏损超过限制: {daily_return:.1%} < -{self.max_daily_loss_pct:.1%}",
                risk_type=RiskType.DAILY_LOSS_RISK,
                risk_level=RiskLevel.CRITICAL,
                details={
                    'daily_return': daily_return,
                    'max_allowed': -self.max_daily_loss_pct,
                    'daily_pnl': self.daily_pnl
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_open_positions(self, num_positions: int) -> RiskCheckResult:
        """检查持仓数量限制。"""
        if num_positions >= self.max_open_positions:
            return RiskCheckResult(
                passed=False,
                reason=f"持仓数量超过限制: {num_positions} >= {self.max_open_positions}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.MEDIUM,
                details={
                    'num_positions': num_positions,
                    'max_allowed': self.max_open_positions
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_leverage(self, gross_exposure: float, net_exposure: float) -> RiskCheckResult:
        """检查杠杆限制。"""
        leverage = gross_exposure / net_exposure if net_exposure > 0 else 0
        
        if leverage > self.max_leverage:
            return RiskCheckResult(
                passed=False,
                reason=f"杠杆超过限制: {leverage:.2f}x > {self.max_leverage:.2f}x",
                risk_type=RiskType.MARKET_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'leverage': leverage,
                    'gross_exposure': gross_exposure,
                    'net_exposure': net_exposure,
                    'max_allowed': self.max_leverage
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_all(
        self,
        order_value: float,
        portfolio_value: float,
        existing_position_value: float = 0.0,
        num_positions: int = 0,
        sector: str = "",
        sector_exposure: float = 0.0,
        gross_exposure: float = 0.0,
        net_exposure: float = 0.0
    ) -> RiskCheckResult:
        """执行所有风险检查。"""
        checks = [
            ('drawdown', lambda: self.check_drawdown(portfolio_value)),
            ('daily_loss', lambda: self.check_daily_loss(portfolio_value)),
            ('open_positions', lambda: self.check_open_positions(num_positions)),
            ('position_size', lambda: self.check_position_size(order_value, portfolio_value, existing_position_value)),
        ]
        
        if sector:
            checks.append(('concentration', lambda: self.check_portfolio_concentration(sector, sector_exposure, portfolio_value)))
        
        if gross_exposure > 0 and net_exposure > 0:
            checks.append(('leverage', lambda: self.check_leverage(gross_exposure, net_exposure)))
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                if not result:
                    # 记录风控事件
                    self._record_risk_event(result)
                    return result
            except Exception as e:
                logger.error(f"风险检查 {check_name} 出错: {e}")
        
        return RiskCheckResult(passed=True)
    
    def _record_risk_event(self, result: RiskCheckResult):
        """记录风控事件。"""
        event = {
            'timestamp': datetime.now(),
            'risk_type': result.risk_type.value,
            'risk_level': result.risk_level.value,
            'reason': result.reason,
            'details': result.details
        }
        
        self.risk_events.append(event)
        
        # 严重风险发送告警
        if result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._send_alert(event)
    
    def _send_alert(self, event: Dict):
        """发送风险告警。"""
        logger.critical(f"风险告警 [{event['risk_level'].upper()}]: {event['reason']}")
        
        # 可以扩展：发送邮件、短信、企业微信等
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        horizon_days: int = 1
    ) -> float:
        """计算VaR（在险价值）。"""
        if len(returns) < 2:
            return 0.0
        
        # 简单的参数法VaR
        mean_return = returns.mean()
        std_return = returns.std()
        
        # 使用正态分布
        from scipy.stats import norm
        z_score = norm.ppf(1 - confidence_level)
        
        var = -(mean_return + z_score * std_return) * np.sqrt(horizon_days)
        
        return var
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """计算CVaR（条件在险价值）。"""
        if len(returns) < 2:
            return 0.0
        
        var = self.calculate_var(returns, confidence_level)
        
        # 找到所有超过VaR的损失
        tail_returns = returns[returns < -var]
        
        if len(tail_returns) == 0:
            return var
        
        cvar = -tail_returns.mean()
        
        return cvar
    
    def calculate_risk_contribution(
        self,
        weights: pd.Series,
        covariance_matrix: pd.DataFrame
    ) -> pd.Series:
        """计算各资产的风险贡献。"""
        portfolio_std = np.sqrt(weights @ covariance_matrix @ weights.T)
        risk_contributions = (weights * (covariance_matrix @ weights)) / portfolio_std
        
        return risk_contributions
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要。"""
        return {
            'max_drawdown': self.max_drawdown,
            'daily_pnl': self.daily_pnl,
            'num_risk_events': len(self.risk_events),
            'recent_events': self.risk_events[-5:] if len(self.risk_events) > 0 else []
        }


class RiskMonitor:
    """风险监控器。"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        self.monitoring = False
    
    def start(self):
        """开始监控。"""
        self.monitoring = True
        logger.info("风险监控器启动")
    
    def stop(self):
        """停止监控。"""
        self.monitoring = False
        logger.info("风险监控器停止")
    
    def monitor(
        self,
        portfolio_value: float,
        positions: Dict[str, dict],
        daily_pnl: float = 0.0
    ) -> Dict[str, Any]:
        """执行监控。"""
        if not self.monitoring:
            return {}
        
        # 更新风险管理器
        self.risk_manager.record_pnl(daily_pnl, portfolio_value)
        
        # 检查各项风险
        checks = {
            'drawdown': self.risk_manager.check_drawdown(portfolio_value),
            'daily_loss': self.risk_manager.check_daily_loss(portfolio_value),
            'open_positions': self.risk_manager.check_open_positions(len(positions))
        }
        
        # 检查单一持仓风险
        for symbol, pos in positions.items():
            pos_value = pos['quantity'] * pos.get('current_price', pos.get('avg_price', 0))
            check = self.risk_manager.check_position_size(pos_value, portfolio_value)
            checks[f'position_{symbol}'] = check
        
        # 汇总结果
        passed = all(check.passed for check in checks.values())
        
        return {
            'overall_passed': passed,
            'checks': {k: {'passed': v.passed, 'reason': v.reason, 'risk_level': v.risk_level.value} for k, v in checks.items()},
            'risk_summary': self.risk_manager.get_risk_summary()
        }


# 示例用法
if __name__ == "__main__":
    # 创建风险管理器
    risk_manager = RiskManager(
        max_position_size_pct=0.1,
        max_drawdown_pct=0.1,
        max_daily_loss_pct=0.05,
        max_open_positions=10
    )
    
    # 模拟组合数据
    portfolio_value = 1000000
    order_value = 150000  # 15%的持仓
    existing_position_value = 0
    num_positions = 5
    
    # 执行风险检查
    result = risk_manager.check_all(
        order_value=order_value,
        portfolio_value=portfolio_value,
        existing_position_value=existing_position_value,
        num_positions=num_positions
    )
    
    print(f"风险检查结果: {result.passed}")
    print(f"原因: {result.reason}")
    print(f"风险类型: {result.risk_type}")
    print(f"风险等级: {result.risk_level}")
    
    # 计算VaR
    returns = pd.Series(np.random.randn(252) * 0.01)  # 模拟一年的日收益
    var = risk_manager.calculate_var(returns)
    cvar = risk_manager.calculate_cvar(returns)
    
    print(f"\nVaR (95%): {var:.2%}")
    print(f"CVaR (95%): {cvar:.2%}")
    
    # 获取风险摘要
    print(f"\n风险摘要:")
    print(risk_manager.get_risk_summary())
"""
OxQuant Risk Management

风控模块，支持多种风险控制策略。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskType(Enum):
    """风险类型。"""
    MARKET_RISK = "market_risk"           # 市场风险
    CREDIT_RISK = "credit_risk"           # 信用风险
    LIQUIDITY_RISK = "liquidity_risk"     # 流动性风险
    OPERATIONAL_RISK = "operational_risk" # 操作风险
    CONCENTRATION_RISK = "concentration_risk" # 集中度风险
    DRAWDOWN_RISK = "drawdown_risk"       # 回撤风险
    DAILY_LOSS_RISK = "daily_loss_risk"   # 单日亏损风险


class RiskLevel(Enum):
    """风险等级。"""
    LOW = "low"       # 低风险
    MEDIUM = "medium" # 中等风险
    HIGH = "high"     # 高风险
    CRITICAL = "critical" # 严重风险


class RiskCheckResult:
    """风险检查结果。"""
    
    def __init__(
        self,
        passed: bool,
        reason: str = "",
        risk_type: RiskType = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        details: Optional[Dict] = None
    ):
        self.passed = passed
        self.reason = reason
        self.risk_type = risk_type
        self.risk_level = risk_level
        self.details = details or {}
    
    def __bool__(self):
        return self.passed
    
    def __repr__(self):
        return f"RiskCheckResult(passed={self.passed}, reason={self.reason}, risk_type={self.risk_type})"


class RiskManager:
    """风险管理器。"""
    
    def __init__(
        self,
        max_position_size_pct: float = 0.1,      # 单一持仓最大比例
        max_portfolio_risk_pct: float = 0.02,    # 组合最大风险
        max_drawdown_pct: float = 0.1,           # 最大回撤
        max_daily_loss_pct: float = 0.05,        # 单日最大亏损
        max_concentration_pct: float = 0.2,      # 行业/板块最大集中度
        max_open_positions: int = 20,            # 最大持仓数量
        max_single_stock_risk: float = 0.01,     # 单只股票最大风险贡献
        max_gross_exposure: float = 1.0,         # 最大总敞口
        max_leverage: float = 1.0,               # 最大杠杆
        volatility_target: float = 0.15          # 目标波动率
    ):
        
        # 风险参数
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_concentration_pct = max_concentration_pct
        self.max_open_positions = max_open_positions
        self.max_single_stock_risk = max_single_stock_risk
        self.max_gross_exposure = max_gross_exposure
        self.max_leverage = max_leverage
        self.volatility_target = volatility_target
        
        # 风险状态
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.running_max = 0.0
        self.daily_high = 0.0
        
        # 风控事件记录
        self.risk_events = []
    
    def reset_daily(self):
        """重置每日统计。"""
        self.daily_pnl = 0.0
        self.daily_high = 0.0
    
    def record_pnl(self, pnl: float, portfolio_value: float):
        """记录盈亏。"""
        self.daily_pnl += pnl
        
        # 更新最大回撤
        self.running_max = max(self.running_max, portfolio_value)
        current_drawdown = (self.running_max - portfolio_value) / self.running_max
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # 更新当日高点
        self.daily_high = max(self.daily_high, portfolio_value)
    
    def check_position_size(
        self,
        order_value: float,
        portfolio_value: float,
        existing_position_value: float = 0.0
    ) -> RiskCheckResult:
        """检查单一持仓大小限制。"""
        new_position_value = existing_position_value + order_value
        position_pct = new_position_value / portfolio_value
        
        if position_pct > self.max_position_size_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"持仓比例超过限制: {position_pct:.1%} > {self.max_position_size_pct:.1%}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'position_pct': position_pct,
                    'max_allowed': self.max_position_size_pct,
                    'order_value': order_value,
                    'existing_value': existing_position_value
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_portfolio_concentration(
        self,
        sector: str,
        sector_exposure: float,
        portfolio_value: float
    ) -> RiskCheckResult:
        """检查行业/板块集中度。"""
        sector_pct = sector_exposure / portfolio_value
        
        if sector_pct > self.max_concentration_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"{sector}板块持仓超过限制: {sector_pct:.1%} > {self.max_concentration_pct:.1%}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'sector': sector,
                    'sector_pct': sector_pct,
                    'max_allowed': self.max_concentration_pct
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_drawdown(self, portfolio_value: float) -> RiskCheckResult:
        """检查最大回撤。"""
        current_drawdown = (self.running_max - portfolio_value) / self.running_max if self.running_max > 0 else 0
        
        if current_drawdown > self.max_drawdown_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"回撤超过限制: {current_drawdown:.1%} > {self.max_drawdown_pct:.1%}",
                risk_type=RiskType.DRAWDOWN_RISK,
                risk_level=RiskLevel.CRITICAL,
                details={
                    'current_drawdown': current_drawdown,
                    'max_allowed': self.max_drawdown_pct,
                    'running_max': self.running_max
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_daily_loss(self, portfolio_value: float) -> RiskCheckResult:
        """检查单日亏损。"""
        daily_return = self.daily_pnl / (portfolio_value - self.daily_pnl) if (portfolio_value - self.daily_pnl) > 0 else 0
        
        if daily_return < -self.max_daily_loss_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"单日亏损超过限制: {daily_return:.1%} < -{self.max_daily_loss_pct:.1%}",
                risk_type=RiskType.DAILY_LOSS_RISK,
                risk_level=RiskLevel.CRITICAL,
                details={
                    'daily_return': daily_return,
                    'max_allowed': -self.max_daily_loss_pct,
                    'daily_pnl': self.daily_pnl
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_open_positions(self, num_positions: int) -> RiskCheckResult:
        """检查持仓数量限制。"""
        if num_positions >= self.max_open_positions:
            return RiskCheckResult(
                passed=False,
                reason=f"持仓数量超过限制: {num_positions} >= {self.max_open_positions}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.MEDIUM,
                details={
                    'num_positions': num_positions,
                    'max_allowed': self.max_open_positions
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_leverage(self, gross_exposure: float, net_exposure: float) -> RiskCheckResult:
        """检查杠杆限制。"""
        leverage = gross_exposure / net_exposure if net_exposure > 0 else 0
        
        if leverage > self.max_leverage:
            return RiskCheckResult(
                passed=False,
                reason=f"杠杆超过限制: {leverage:.2f}x > {self.max_leverage:.2f}x",
                risk_type=RiskType.MARKET_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'leverage': leverage,
                    'gross_exposure': gross_exposure,
                    'net_exposure': net_exposure,
                    'max_allowed': self.max_leverage
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_all(
        self,
        order_value: float,
        portfolio_value: float,
        existing_position_value: float = 0.0,
        num_positions: int = 0,
        sector: str = "",
        sector_exposure: float = 0.0,
        gross_exposure: float = 0.0,
        net_exposure: float = 0.0
    ) -> RiskCheckResult:
        """执行所有风险检查。"""
        checks = [
            ('drawdown', lambda: self.check_drawdown(portfolio_value)),
            ('daily_loss', lambda: self.check_daily_loss(portfolio_value)),
            ('open_positions', lambda: self.check_open_positions(num_positions)),
            ('position_size', lambda: self.check_position_size(order_value, portfolio_value, existing_position_value)),
        ]
        
        if sector:
            checks.append(('concentration', lambda: self.check_portfolio_concentration(sector, sector_exposure, portfolio_value)))
        
        if gross_exposure > 0 and net_exposure > 0:
            checks.append(('leverage', lambda: self.check_leverage(gross_exposure, net_exposure)))
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                if not result:
                    # 记录风控事件
                    self._record_risk_event(result)
                    return result
            except Exception as e:
                logger.error(f"风险检查 {check_name} 出错: {e}")
        
        return RiskCheckResult(passed=True)
    
    def _record_risk_event(self, result: RiskCheckResult):
        """记录风控事件。"""
        event = {
            'timestamp': datetime.now(),
            'risk_type': result.risk_type.value,
            'risk_level': result.risk_level.value,
            'reason': result.reason,
            'details': result.details
        }
        
        self.risk_events.append(event)
        
        # 严重风险发送告警
        if result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._send_alert(event)
    
    def _send_alert(self, event: Dict):
        """发送风险告警。"""
        logger.critical(f"风险告警 [{event['risk_level'].upper()}]: {event['reason']}")
        
        # 可以扩展：发送邮件、短信、企业微信等
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        horizon_days: int = 1
    ) -> float:
        """计算VaR（在险价值）。"""
        if len(returns) < 2:
            return 0.0
        
        # 简单的参数法VaR
        mean_return = returns.mean()
        std_return = returns.std()
        
        # 使用正态分布
        from scipy.stats import norm
        z_score = norm.ppf(1 - confidence_level)
        
        var = -(mean_return + z_score * std_return) * np.sqrt(horizon_days)
        
        return var
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """计算CVaR（条件在险价值）。"""
        if len(returns) < 2:
            return 0.0
        
        var = self.calculate_var(returns, confidence_level)
        
        # 找到所有超过VaR的损失
        tail_returns = returns[returns < -var]
        
        if len(tail_returns) == 0:
            return var
        
        cvar = -tail_returns.mean()
        
        return cvar
    
    def calculate_risk_contribution(
        self,
        weights: pd.Series,
        covariance_matrix: pd.DataFrame
    ) -> pd.Series:
        """计算各资产的风险贡献。"""
        portfolio_std = np.sqrt(weights @ covariance_matrix @ weights.T)
        risk_contributions = (weights * (covariance_matrix @ weights)) / portfolio_std
        
        return risk_contributions
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要。"""
        return {
            'max_drawdown': self.max_drawdown,
            'daily_pnl': self.daily_pnl,
            'num_risk_events': len(self.risk_events),
            'recent_events': self.risk_events[-5:] if len(self.risk_events) > 0 else []
        }


class RiskMonitor:
    """风险监控器。"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        self.monitoring = False
    
    def start(self):
        """开始监控。"""
        self.monitoring = True
        logger.info("风险监控器启动")
    
    def stop(self):
        """停止监控。"""
        self.monitoring = False
        logger.info("风险监控器停止")
    
    def monitor(
        self,
        portfolio_value: float,
        positions: Dict[str, dict],
        daily_pnl: float = 0.0
    ) -> Dict[str, Any]:
        """执行监控。"""
        if not self.monitoring:
            return {}
        
        # 更新风险管理器
        self.risk_manager.record_pnl(daily_pnl, portfolio_value)
        
        # 检查各项风险
        checks = {
            'drawdown': self.risk_manager.check_drawdown(portfolio_value),
            'daily_loss': self.risk_manager.check_daily_loss(portfolio_value),
            'open_positions': self.risk_manager.check_open_positions(len(positions))
        }
        
        # 检查单一持仓风险
        for symbol, pos in positions.items():
            pos_value = pos['quantity'] * pos.get('current_price', pos.get('avg_price', 0))
            check = self.risk_manager.check_position_size(pos_value, portfolio_value)
            checks[f'position_{symbol}'] = check
        
        # 汇总结果
        passed = all(check.passed for check in checks.values())
        
        return {
            'overall_passed': passed,
            'checks': {k: {'passed': v.passed, 'reason': v.reason, 'risk_level': v.risk_level.value} for k, v in checks.items()},
            'risk_summary': self.risk_manager.get_risk_summary()
        }


# 示例用法
if __name__ == "__main__":
    # 创建风险管理器
    risk_manager = RiskManager(
        max_position_size_pct=0.1,
        max_drawdown_pct=0.1,
        max_daily_loss_pct=0.05,
        max_open_positions=10
    )
    
    # 模拟组合数据
    portfolio_value = 1000000
    order_value = 150000  # 15%的持仓
    existing_position_value = 0
    num_positions = 5
    
    # 执行风险检查
    result = risk_manager.check_all(
        order_value=order_value,
        portfolio_value=portfolio_value,
        existing_position_value=existing_position_value,
        num_positions=num_positions
    )
    
    print(f"风险检查结果: {result.passed}")
    print(f"原因: {result.reason}")
    print(f"风险类型: {result.risk_type}")
    print(f"风险等级: {result.risk_level}")
    
    # 计算VaR
    returns = pd.Series(np.random.randn(252) * 0.01)  # 模拟一年的日收益
    var = risk_manager.calculate_var(returns)
    cvar = risk_manager.calculate_cvar(returns)
    
    print(f"\nVaR (95%): {var:.2%}")
    print(f"CVaR (95%): {cvar:.2%}")
    
    # 获取风险摘要
    print(f"\n风险摘要:")
    print(risk_manager.get_risk_summary())
"""
OxQuant Risk Management

风控模块，支持多种风险控制策略。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskType(Enum):
    """风险类型。"""
    MARKET_RISK = "market_risk"           # 市场风险
    CREDIT_RISK = "credit_risk"           # 信用风险
    LIQUIDITY_RISK = "liquidity_risk"     # 流动性风险
    OPERATIONAL_RISK = "operational_risk" # 操作风险
    CONCENTRATION_RISK = "concentration_risk" # 集中度风险
    DRAWDOWN_RISK = "drawdown_risk"       # 回撤风险
    DAILY_LOSS_RISK = "daily_loss_risk"   # 单日亏损风险


class RiskLevel(Enum):
    """风险等级。"""
    LOW = "low"       # 低风险
    MEDIUM = "medium" # 中等风险
    HIGH = "high"     # 高风险
    CRITICAL = "critical" # 严重风险


class RiskCheckResult:
    """风险检查结果。"""
    
    def __init__(
        self,
        passed: bool,
        reason: str = "",
        risk_type: RiskType = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        details: Optional[Dict] = None
    ):
        self.passed = passed
        self.reason = reason
        self.risk_type = risk_type
        self.risk_level = risk_level
        self.details = details or {}
    
    def __bool__(self):
        return self.passed
    
    def __repr__(self):
        return f"RiskCheckResult(passed={self.passed}, reason={self.reason}, risk_type={self.risk_type})"


class RiskManager:
    """风险管理器。"""
    
    def __init__(
        self,
        max_position_size_pct: float = 0.1,      # 单一持仓最大比例
        max_portfolio_risk_pct: float = 0.02,    # 组合最大风险
        max_drawdown_pct: float = 0.1,           # 最大回撤
        max_daily_loss_pct: float = 0.05,        # 单日最大亏损
        max_concentration_pct: float = 0.2,      # 行业/板块最大集中度
        max_open_positions: int = 20,            # 最大持仓数量
        max_single_stock_risk: float = 0.01,     # 单只股票最大风险贡献
        max_gross_exposure: float = 1.0,         # 最大总敞口
        max_leverage: float = 1.0,               # 最大杠杆
        volatility_target: float = 0.15          # 目标波动率
    ):
        
        # 风险参数
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_concentration_pct = max_concentration_pct
        self.max_open_positions = max_open_positions
        self.max_single_stock_risk = max_single_stock_risk
        self.max_gross_exposure = max_gross_exposure
        self.max_leverage = max_leverage
        self.volatility_target = volatility_target
        
        # 风险状态
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.running_max = 0.0
        self.daily_high = 0.0
        
        # 风控事件记录
        self.risk_events = []
    
    def reset_daily(self):
        """重置每日统计。"""
        self.daily_pnl = 0.0
        self.daily_high = 0.0
    
    def record_pnl(self, pnl: float, portfolio_value: float):
        """记录盈亏。"""
        self.daily_pnl += pnl
        
        # 更新最大回撤
        self.running_max = max(self.running_max, portfolio_value)
        current_drawdown = (self.running_max - portfolio_value) / self.running_max
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # 更新当日高点
        self.daily_high = max(self.daily_high, portfolio_value)
    
    def check_position_size(
        self,
        order_value: float,
        portfolio_value: float,
        existing_position_value: float = 0.0
    ) -> RiskCheckResult:
        """检查单一持仓大小限制。"""
        new_position_value = existing_position_value + order_value
        position_pct = new_position_value / portfolio_value
        
        if position_pct > self.max_position_size_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"持仓比例超过限制: {position_pct:.1%} > {self.max_position_size_pct:.1%}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'position_pct': position_pct,
                    'max_allowed': self.max_position_size_pct,
                    'order_value': order_value,
                    'existing_value': existing_position_value
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_portfolio_concentration(
        self,
        sector: str,
        sector_exposure: float,
        portfolio_value: float
    ) -> RiskCheckResult:
        """检查行业/板块集中度。"""
        sector_pct = sector_exposure / portfolio_value
        
        if sector_pct > self.max_concentration_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"{sector}板块持仓超过限制: {sector_pct:.1%} > {self.max_concentration_pct:.1%}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'sector': sector,
                    'sector_pct': sector_pct,
                    'max_allowed': self.max_concentration_pct
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_drawdown(self, portfolio_value: float) -> RiskCheckResult:
        """检查最大回撤。"""
        current_drawdown = (self.running_max - portfolio_value) / self.running_max if self.running_max > 0 else 0
        
        if current_drawdown > self.max_drawdown_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"回撤超过限制: {current_drawdown:.1%} > {self.max_drawdown_pct:.1%}",
                risk_type=RiskType.DRAWDOWN_RISK,
                risk_level=RiskLevel.CRITICAL,
                details={
                    'current_drawdown': current_drawdown,
                    'max_allowed': self.max_drawdown_pct,
                    'running_max': self.running_max
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_daily_loss(self, portfolio_value: float) -> RiskCheckResult:
        """检查单日亏损。"""
        daily_return = self.daily_pnl / (portfolio_value - self.daily_pnl) if (portfolio_value - self.daily_pnl) > 0 else 0
        
        if daily_return < -self.max_daily_loss_pct:
            return RiskCheckResult(
                passed=False,
                reason=f"单日亏损超过限制: {daily_return:.1%} < -{self.max_daily_loss_pct:.1%}",
                risk_type=RiskType.DAILY_LOSS_RISK,
                risk_level=RiskLevel.CRITICAL,
                details={
                    'daily_return': daily_return,
                    'max_allowed': -self.max_daily_loss_pct,
                    'daily_pnl': self.daily_pnl
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_open_positions(self, num_positions: int) -> RiskCheckResult:
        """检查持仓数量限制。"""
        if num_positions >= self.max_open_positions:
            return RiskCheckResult(
                passed=False,
                reason=f"持仓数量超过限制: {num_positions} >= {self.max_open_positions}",
                risk_type=RiskType.CONCENTRATION_RISK,
                risk_level=RiskLevel.MEDIUM,
                details={
                    'num_positions': num_positions,
                    'max_allowed': self.max_open_positions
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_leverage(self, gross_exposure: float, net_exposure: float) -> RiskCheckResult:
        """检查杠杆限制。"""
        leverage = gross_exposure / net_exposure if net_exposure > 0 else 0
        
        if leverage > self.max_leverage:
            return RiskCheckResult(
                passed=False,
                reason=f"杠杆超过限制: {leverage:.2f}x > {self.max_leverage:.2f}x",
                risk_type=RiskType.MARKET_RISK,
                risk_level=RiskLevel.HIGH,
                details={
                    'leverage': leverage,
                    'gross_exposure': gross_exposure,
                    'net_exposure': net_exposure,
                    'max_allowed': self.max_leverage
                }
            )
        
        return RiskCheckResult(passed=True)
    
    def check_all(
        self,
        order_value: float,
        portfolio_value: float,
        existing_position_value: float = 0.0,
        num_positions: int = 0,
        sector: str = "",
        sector_exposure: float = 0.0,
        gross_exposure: float = 0.0,
        net_exposure: float = 0.0
    ) -> RiskCheckResult:
        """执行所有风险检查。"""
        checks = [
            ('drawdown', lambda: self.check_drawdown(portfolio_value)),
            ('daily_loss', lambda: self.check_daily_loss(portfolio_value)),
            ('open_positions', lambda: self.check_open_positions(num_positions)),
            ('position_size', lambda: self.check_position_size(order_value, portfolio_value, existing_position_value)),
        ]
        
        if sector:
            checks.append(('concentration', lambda: self.check_portfolio_concentration(sector, sector_exposure, portfolio_value)))
        
        if gross_exposure > 0 and net_exposure > 0:
            checks.append(('leverage', lambda: self.check_leverage(gross_exposure, net_exposure)))
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                if not result:
                    # 记录风控事件
                    self._record_risk_event(result)
                    return result
            except Exception as e:
                logger.error(f"风险检查 {check_name} 出错: {e}")
        
        return RiskCheckResult(passed=True)
    
    def _record_risk_event(self, result: RiskCheckResult):
        """记录风控事件。"""
        event = {
            'timestamp': datetime.now(),
            'risk_type': result.risk_type.value,
            'risk_level': result.risk_level.value,
            'reason': result.reason,
            'details': result.details
        }
        
        self.risk_events.append(event)
        
        # 严重风险发送告警
        if result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._send_alert(event)
    
    def _send_alert(self, event: Dict):
        """发送风险告警。"""
        logger.critical(f"风险告警 [{event['risk_level'].upper()}]: {event['reason']}")
        
        # 可以扩展：发送邮件、短信、企业微信等
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        horizon_days: int = 1
    ) -> float:
        """计算VaR（在险价值）。"""
        if len(returns) < 2:
            return 0.0
        
        # 简单的参数法VaR
        mean_return = returns.mean()
        std_return = returns.std()
        
        # 使用正态分布
        from scipy.stats import norm
        z_score = norm.ppf(1 - confidence_level)
        
        var = -(mean_return + z_score * std_return) * np.sqrt(horizon_days)
        
        return var
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """计算CVaR（条件在险价值）。"""
        if len(returns) < 2:
            return 0.0
        
        var = self.calculate_var(returns, confidence_level)
        
        # 找到所有超过VaR的损失
        tail_returns = returns[returns < -var]
        
        if len(tail_returns) == 0:
            return var
        
        cvar = -tail_returns.mean()
        
        return cvar
    
    def calculate_risk_contribution(
        self,
        weights: pd.Series,
        covariance_matrix: pd.DataFrame
    ) -> pd.Series:
        """计算各资产的风险贡献。"""
        portfolio_std = np.sqrt(weights @ covariance_matrix @ weights.T)
        risk_contributions = (weights * (covariance_matrix @ weights)) / portfolio_std
        
        return risk_contributions
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要。"""
        return {
            'max_drawdown': self.max_drawdown,
            'daily_pnl': self.daily_pnl,
            'num_risk_events': len(self.risk_events),
            'recent_events': self.risk_events[-5:] if len(self.risk_events) > 0 else []
        }


class RiskMonitor:
    """风险监控器。"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        self.monitoring = False
    
    def start(self):
        """开始监控。"""
        self.monitoring = True
        logger.info("风险监控器启动")
    
    def stop(self):
        """停止监控。"""
        self.monitoring = False
        logger.info("风险监控器停止")
    
    def monitor(
        self,
        portfolio_value: float,
        positions: Dict[str, dict],
        daily_pnl: float = 0.0
    ) -> Dict[str, Any]:
        """执行监控。"""
        if not self.monitoring:
            return {}
        
        # 更新风险管理器
        self.risk_manager.record_pnl(daily_pnl, portfolio_value)
        
        # 检查各项风险
        checks = {
            'drawdown': self.risk_manager.check_drawdown(portfolio_value),
            'daily_loss': self.risk_manager.check_daily_loss(portfolio_value),
            'open_positions': self.risk_manager.check_open_positions(len(positions))
        }
        
        # 检查单一持仓风险
        for symbol, pos in positions.items():
            pos_value = pos['quantity'] * pos.get('current_price', pos.get('avg_price', 0))
            check = self.risk_manager.check_position_size(pos_value, portfolio_value)
            checks[f'position_{symbol}'] = check
        
        # 汇总结果
        passed = all(check.passed for check in checks.values())
        
        return {
            'overall_passed': passed,
            'checks': {k: {'passed': v.passed, 'reason': v.reason, 'risk_level': v.risk_level.value} for k, v in checks.items()},
            'risk_summary': self.risk_manager.get_risk_summary()
        }


# 示例用法
if __name__ == "__main__":
    # 创建风险管理器
    risk_manager = RiskManager(
        max_position_size_pct=0.1,
        max_drawdown_pct=0.1,
        max_daily_loss_pct=0.05,
        max_open_positions=10
    )
    
    # 模拟组合数据
    portfolio_value = 1000000
    order_value = 150000  # 15%的持仓
    existing_position_value = 0
    num_positions = 5
    
    # 执行风险检查
    result = risk_manager.check_all(
        order_value=order_value,
        portfolio_value=portfolio_value,
        existing_position_value=existing_position_value,
        num_positions=num_positions
    )
    
    print(f"风险检查结果: {result.passed}")
    print(f"原因: {result.reason}")
    print(f"风险类型: {result.risk_type}")
    print(f"风险等级: {result.risk_level}")
    
    # 计算VaR
    returns = pd.Series(np.random.randn(252) * 0.01)  # 模拟一年的日收益
    var = risk_manager.calculate_var(returns)
    cvar = risk_manager.calculate_cvar(returns)
    
    print(f"\nVaR (95%): {var:.2%}")
    print(f"CVaR (95%): {cvar:.2%}")
    
    # 获取风险摘要
    print(f"\n风险摘要:")
    print(risk_manager.get_risk_summary())