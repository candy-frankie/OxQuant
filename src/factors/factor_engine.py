"""
OxQuant Factor Engine

因子挖掘模块，借鉴微软QLib框架的设计思路。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorType(Enum):
    """因子类型。"""
    ALPHA = "alpha"          # 阿尔法因子
    BETA = "beta"            # 贝塔因子
    VALUATION = "valuation"  # 估值因子
    QUALITY = "quality"      # 质量因子
    MOMENTUM = "momentum"    # 动量因子
    VOLATILITY = "volatility" # 波动率因子
    LIQUIDITY = "liquidity"  # 流动性因子


class FactorDirection(Enum):
    """因子方向。"""
    LONG = "long"            # 正向因子（因子值越高预期收益越高）
    SHORT = "short"          # 反向因子（因子值越高预期收益越低）
    NEUTRAL = "neutral"      # 中性因子


class FactorInfo:
    """因子信息类。"""
    
    def __init__(
        self,
        name: str,
        description: str,
        factor_type: FactorType,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        self.name = name
        self.description = description
        self.factor_type = factor_type
        self.direction = direction
        self.is_standardized = is_standardized
        self.window = window
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'factor_type': self.factor_type.value,
            'direction': self.direction.value,
            'is_standardized': self.is_standardized,
            'window': self.window
        }


class FactorEngine:
    """因子计算引擎。"""
    
    def __init__(self):
        self.factors: Dict[str, Callable] = {}
        self.factor_info: Dict[str, FactorInfo] = {}
    
    def register_factor(
        self,
        name: str,
        func: Callable,
        description: str = "",
        factor_type: FactorType = FactorType.ALPHA,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        """注册因子计算函数。"""
        self.factors[name] = func
        self.factor_info[name] = FactorInfo(
            name=name,
            description=description,
            factor_type=factor_type,
            direction=direction,
            is_standardized=is_standardized,
            window=window
        )
    
    def compute_factor(self, name: str, data: pd.DataFrame) -> pd.Series:
        """计算单个因子。"""
        if name not in self.factors:
            raise ValueError(f"Unknown factor: {name}")
        
        factor = self.factors[name](data)
        
        # 如果需要标准化
        if self.factor_info[name].is_standardized:
            factor = self._standardize(factor)
        
        return factor
    
    def compute_all_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有已注册因子。"""
        results = {}
        for name in self.factors:
            try:
                results[name] = self.compute_factor(name, data)
            except Exception as e:
                logger.error(f"Failed to compute factor {name}: {e}")
                results[name] = pd.Series([np.nan] * len(data), index=data.index)
        
        return pd.DataFrame(results)
    
    def _standardize(self, factor: pd.Series) -> pd.Series:
        """标准化因子（Z-score）。"""
        return (factor - factor.mean()) / factor.std()
    
    def get_factor_info(self, name: str) -> Optional[FactorInfo]:
        """获取因子信息。"""
        return self.factor_info.get(name)
    
    def list_factors(self) -> List[Dict[str, Any]]:
        """列出所有已注册因子。"""
        return [info.to_dict() for info in self.factor_info.values()]


# ==================== 常用因子实现 ====================

def factor_close_to_ma_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """收盘价相对均线比率。"""
    ma = data['close'].rolling(window=window).mean()
    return data['close'] / ma


def factor_momentum(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """动量因子：过去N日收益率。"""
    return data['close'].pct_change(window).fillna(0)


def factor_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """相对强弱指数。"""
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def factor_macd_signal(data: pd.DataFrame) -> pd.Series:
    """MACD信号因子。"""
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal


def factor_bollinger_band_width(data: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """布林带宽度。"""
    ma = data['close'].rolling(window=window).mean()
    std = data['close'].rolling(window=window).std()
    upper = ma + std * num_std
    lower = ma - std * num_std
    return (upper - lower) / ma


def factor_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """平均真实波动。"""
    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift()).abs()
    low_close = (data['low'] - data['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=window).mean()


def factor_volume_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """成交量相对均值比率。"""
    avg_volume = data['volume'].rolling(window=window).mean()
    return data['volume'] / avg_volume


def factor_turnover(data: pd.DataFrame) -> pd.Series:
    """换手率（如果数据中有）。"""
    if 'turnover' in data.columns:
        return data['turnover']
    return pd.Series([0.0] * len(data), index=data.index)


def factor_price_to_earnings(data: pd.DataFrame) -> pd.Series:
    """市盈率因子。"""
    if 'pe' in data.columns:
        return data['pe']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_price_to_book(data: pd.DataFrame) -> pd.Series:
    """市净率因子。"""
    if 'pb' in data.columns:
        return data['pb']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_earnings_growth(data: pd.DataFrame, window: int = 4) -> pd.Series:
    """盈利增长率。"""
    if 'eps' in data.columns:
        return data['eps'].pct_change(window).fillna(0)
    return pd.Series([0.0] * len(data), index=data.index)


def factor_sharpe_ratio(data: pd.DataFrame, window: int = 60) -> pd.Series:
    """滚动夏普比率。"""
    returns = data['close'].pct_change()
    return returns.rolling(window=window).mean() / returns.rolling(window=window).std() * np.sqrt(252)


# 创建全局因子引擎实例
factor_engine = FactorEngine()

# 注册常用因子
factor_engine.register_factor(
    'close_to_ma_20',
    lambda df: factor_close_to_ma_ratio(df, 20),
    description='收盘价相对20日均线比率',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_20',
    lambda df: factor_momentum(df, 20),
    description='20日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_60',
    lambda df: factor_momentum(df, 60),
    description='60日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=60
)

factor_engine.register_factor(
    'rsi_14',
    lambda df: factor_rsi(df, 14),
    description='14日RSI指标',
    factor_type=FactorType.MOMENTUM,
    direction=FactorDirection.SHORT,
    window=14
)

factor_engine.register_factor(
    'macd_signal',
    factor_macd_signal,
    description='MACD信号线',
    factor_type=FactorType.MOMENTUM
)

factor_engine.register_factor(
    'bollinger_width',
    factor_bollinger_band_width,
    description='布林带宽度',
    factor_type=FactorType.VOLATILITY,
    window=20
)

factor_engine.register_factor(
    'atr_14',
    lambda df: factor_atr(df, 14),
    description='14日ATR',
    factor_type=FactorType.VOLATILITY,
    window=14
)

factor_engine.register_factor(
    'volume_ratio_20',
    lambda df: factor_volume_ratio(df, 20),
    description='成交量相对20日均值比率',
    factor_type=FactorType.LIQUIDITY,
    window=20
)

factor_engine.register_factor(
    'turnover',
    factor_turnover,
    description='换手率',
    factor_type=FactorType.LIQUIDITY
)

factor_engine.register_factor(
    'pe',
    factor_price_to_earnings,
    description='市盈率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'pb',
    factor_price_to_book,
    description='市净率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'eps_growth',
    factor_earnings_growth,
    description='EPS增长率',
    factor_type=FactorType.QUALITY
)

factor_engine.register_factor(
    'sharpe_60',
    lambda df: factor_sharpe_ratio(df, 60),
    description='60日滚动夏普比率',
    factor_type=FactorType.QUALITY,
    window=60
)


class FactorAnalyzer:
    """因子分析器。"""
    
    def __init__(self):
        pass
    
    def calculate_ic(self, factor: pd.Series, returns: pd.Series, lag: int = 1) -> float:
        """计算信息系数（IC）。"""
        factor_shifted = factor.shift(lag)
        combined = pd.concat([factor_shifted, returns], axis=1).dropna()
        
        if len(combined) < 2:
            return 0.0
        
        return combined.corr().iloc[0, 1]
    
    def calculate_ic_series(self, factor: pd.Series, returns: pd.Series, window: int = 60) -> pd.Series:
        """计算滚动IC序列。"""
        ic_values = []
        dates = []
        
        for i in range(window, len(factor)):
            factor_window = factor.iloc[i-window:i]
            returns_window = returns.iloc[i-window:i]
            ic = self.calculate_ic(factor_window, returns_window)
            ic_values.append(ic)
            dates.append(factor.index[i])
        
        return pd.Series(ic_values, index=dates)
    
    def calculate_ic_ir(self, factor: pd.Series, returns: pd.Series) -> Tuple[float, float]:
        """计算IC均值和IR（信息比率）。"""
        ic_series = self.calculate_ic_series(factor, returns)
        
        if len(ic_series) == 0:
            return 0.0, 0.0
        
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return ic_mean, ir
    
    def factor_return_analysis(self, factor: pd.Series, returns: pd.Series, n_bins: int = 5) -> pd.DataFrame:
        """因子分组收益分析。"""
        factor_quantile = pd.qcut(factor, n_bins, labels=False, duplicates='drop')
        
        grouped = pd.DataFrame({
            'factor': factor,
            'return': returns,
            'group': factor_quantile
        }).groupby('group')
        
        analysis = grouped.agg({
            'return': ['mean', 'std', 'count'],
            'factor': ['mean', 'min', 'max']
        })
        
        if len(analysis) >= 2:
            long_return = analysis['return']['mean'].iloc[-1]
            short_return = analysis['return']['mean'].iloc[0]
            analysis.loc['long_short_diff'] = [long_return - short_return, np.nan, np.nan, np.nan, np.nan, np.nan]
        
        return analysis
    
    def calculate_factor_autocorrelation(self, factor: pd.Series, lag: int = 1) -> float:
        """计算因子自相关系数。"""
        return factor.autocorr(lag=lag)
    
    def analyze_all_factors(self, factors: pd.DataFrame, returns: pd.Series) -> Dict[str, Dict[str, float]]:
        """批量分析所有因子。"""
        results = {}
        
        for factor_name in factors.columns:
            factor = factors[factor_name].dropna()
            aligned_returns = returns.loc[factor.index]
            
            if len(factor) < 20:
                continue
            
            ic_mean, ir = self.calculate_ic_ir(factor, aligned_returns)
            autocorr = self.calculate_factor_autocorrelation(factor)
            
            results[factor_name] = {
                'ic_mean': ic_mean,
                'ir': ir,
                'autocorrelation': autocorr,
                'observations': len(factor),
                'mean': float(factor.mean()),
                'std': float(factor.std())
            }
        
        return results


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    print(f"数据量: {len(data)}")
    
    # 计算所有因子
    factors = factor_engine.compute_all_factors(data)
    print(f"\n计算的因子数量: {len(factors.columns)}")
    print(factors.columns.tolist())
    print(factors.head())
    
    # 分析因子
    analyzer = FactorAnalyzer()
    returns = data['close'].pct_change().dropna()
    
    # 分析单个因子
    ic_mean, ir = analyzer.calculate_ic_ir(factors['momentum_20'], returns)
    print(f"\nmomentum_20 - IC均值: {ic_mean:.4f}, IR: {ir:.4f}")
    
    # 批量分析
    analysis_results = analyzer.analyze_all_factors(factors, returns)
    print("\n所有因子分析结果:")
    for name, stats in analysis_results.items():
        print(f"{name}: IC={stats['ic_mean']:.3f}, IR={stats['ir']:.3f}")
"""
OxQuant Factor Engine

因子挖掘模块，借鉴微软QLib框架的设计思路。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorType(Enum):
    """因子类型。"""
    ALPHA = "alpha"          # 阿尔法因子
    BETA = "beta"            # 贝塔因子
    VALUATION = "valuation"  # 估值因子
    QUALITY = "quality"      # 质量因子
    MOMENTUM = "momentum"    # 动量因子
    VOLATILITY = "volatility" # 波动率因子
    LIQUIDITY = "liquidity"  # 流动性因子


class FactorDirection(Enum):
    """因子方向。"""
    LONG = "long"            # 正向因子（因子值越高预期收益越高）
    SHORT = "short"          # 反向因子（因子值越高预期收益越低）
    NEUTRAL = "neutral"      # 中性因子


class FactorInfo:
    """因子信息类。"""
    
    def __init__(
        self,
        name: str,
        description: str,
        factor_type: FactorType,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        self.name = name
        self.description = description
        self.factor_type = factor_type
        self.direction = direction
        self.is_standardized = is_standardized
        self.window = window
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'factor_type': self.factor_type.value,
            'direction': self.direction.value,
            'is_standardized': self.is_standardized,
            'window': self.window
        }


class FactorEngine:
    """因子计算引擎。"""
    
    def __init__(self):
        self.factors: Dict[str, Callable] = {}
        self.factor_info: Dict[str, FactorInfo] = {}
    
    def register_factor(
        self,
        name: str,
        func: Callable,
        description: str = "",
        factor_type: FactorType = FactorType.ALPHA,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        """注册因子计算函数。"""
        self.factors[name] = func
        self.factor_info[name] = FactorInfo(
            name=name,
            description=description,
            factor_type=factor_type,
            direction=direction,
            is_standardized=is_standardized,
            window=window
        )
    
    def compute_factor(self, name: str, data: pd.DataFrame) -> pd.Series:
        """计算单个因子。"""
        if name not in self.factors:
            raise ValueError(f"Unknown factor: {name}")
        
        factor = self.factors[name](data)
        
        # 如果需要标准化
        if self.factor_info[name].is_standardized:
            factor = self._standardize(factor)
        
        return factor
    
    def compute_all_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有已注册因子。"""
        results = {}
        for name in self.factors:
            try:
                results[name] = self.compute_factor(name, data)
            except Exception as e:
                logger.error(f"Failed to compute factor {name}: {e}")
                results[name] = pd.Series([np.nan] * len(data), index=data.index)
        
        return pd.DataFrame(results)
    
    def _standardize(self, factor: pd.Series) -> pd.Series:
        """标准化因子（Z-score）。"""
        return (factor - factor.mean()) / factor.std()
    
    def get_factor_info(self, name: str) -> Optional[FactorInfo]:
        """获取因子信息。"""
        return self.factor_info.get(name)
    
    def list_factors(self) -> List[Dict[str, Any]]:
        """列出所有已注册因子。"""
        return [info.to_dict() for info in self.factor_info.values()]


# ==================== 常用因子实现 ====================

def factor_close_to_ma_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """收盘价相对均线比率。"""
    ma = data['close'].rolling(window=window).mean()
    return data['close'] / ma


def factor_momentum(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """动量因子：过去N日收益率。"""
    return data['close'].pct_change(window).fillna(0)


def factor_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """相对强弱指数。"""
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def factor_macd_signal(data: pd.DataFrame) -> pd.Series:
    """MACD信号因子。"""
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal


def factor_bollinger_band_width(data: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """布林带宽度。"""
    ma = data['close'].rolling(window=window).mean()
    std = data['close'].rolling(window=window).std()
    upper = ma + std * num_std
    lower = ma - std * num_std
    return (upper - lower) / ma


def factor_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """平均真实波动。"""
    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift()).abs()
    low_close = (data['low'] - data['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=window).mean()


def factor_volume_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """成交量相对均值比率。"""
    avg_volume = data['volume'].rolling(window=window).mean()
    return data['volume'] / avg_volume


def factor_turnover(data: pd.DataFrame) -> pd.Series:
    """换手率（如果数据中有）。"""
    if 'turnover' in data.columns:
        return data['turnover']
    return pd.Series([0.0] * len(data), index=data.index)


def factor_price_to_earnings(data: pd.DataFrame) -> pd.Series:
    """市盈率因子。"""
    if 'pe' in data.columns:
        return data['pe']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_price_to_book(data: pd.DataFrame) -> pd.Series:
    """市净率因子。"""
    if 'pb' in data.columns:
        return data['pb']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_earnings_growth(data: pd.DataFrame, window: int = 4) -> pd.Series:
    """盈利增长率。"""
    if 'eps' in data.columns:
        return data['eps'].pct_change(window).fillna(0)
    return pd.Series([0.0] * len(data), index=data.index)


def factor_sharpe_ratio(data: pd.DataFrame, window: int = 60) -> pd.Series:
    """滚动夏普比率。"""
    returns = data['close'].pct_change()
    return returns.rolling(window=window).mean() / returns.rolling(window=window).std() * np.sqrt(252)


# 创建全局因子引擎实例
factor_engine = FactorEngine()

# 注册常用因子
factor_engine.register_factor(
    'close_to_ma_20',
    lambda df: factor_close_to_ma_ratio(df, 20),
    description='收盘价相对20日均线比率',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_20',
    lambda df: factor_momentum(df, 20),
    description='20日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_60',
    lambda df: factor_momentum(df, 60),
    description='60日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=60
)

factor_engine.register_factor(
    'rsi_14',
    lambda df: factor_rsi(df, 14),
    description='14日RSI指标',
    factor_type=FactorType.MOMENTUM,
    direction=FactorDirection.SHORT,
    window=14
)

factor_engine.register_factor(
    'macd_signal',
    factor_macd_signal,
    description='MACD信号线',
    factor_type=FactorType.MOMENTUM
)

factor_engine.register_factor(
    'bollinger_width',
    factor_bollinger_band_width,
    description='布林带宽度',
    factor_type=FactorType.VOLATILITY,
    window=20
)

factor_engine.register_factor(
    'atr_14',
    lambda df: factor_atr(df, 14),
    description='14日ATR',
    factor_type=FactorType.VOLATILITY,
    window=14
)

factor_engine.register_factor(
    'volume_ratio_20',
    lambda df: factor_volume_ratio(df, 20),
    description='成交量相对20日均值比率',
    factor_type=FactorType.LIQUIDITY,
    window=20
)

factor_engine.register_factor(
    'turnover',
    factor_turnover,
    description='换手率',
    factor_type=FactorType.LIQUIDITY
)

factor_engine.register_factor(
    'pe',
    factor_price_to_earnings,
    description='市盈率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'pb',
    factor_price_to_book,
    description='市净率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'eps_growth',
    factor_earnings_growth,
    description='EPS增长率',
    factor_type=FactorType.QUALITY
)

factor_engine.register_factor(
    'sharpe_60',
    lambda df: factor_sharpe_ratio(df, 60),
    description='60日滚动夏普比率',
    factor_type=FactorType.QUALITY,
    window=60
)


class FactorAnalyzer:
    """因子分析器。"""
    
    def __init__(self):
        pass
    
    def calculate_ic(self, factor: pd.Series, returns: pd.Series, lag: int = 1) -> float:
        """计算信息系数（IC）。"""
        factor_shifted = factor.shift(lag)
        combined = pd.concat([factor_shifted, returns], axis=1).dropna()
        
        if len(combined) < 2:
            return 0.0
        
        return combined.corr().iloc[0, 1]
    
    def calculate_ic_series(self, factor: pd.Series, returns: pd.Series, window: int = 60) -> pd.Series:
        """计算滚动IC序列。"""
        ic_values = []
        dates = []
        
        for i in range(window, len(factor)):
            factor_window = factor.iloc[i-window:i]
            returns_window = returns.iloc[i-window:i]
            ic = self.calculate_ic(factor_window, returns_window)
            ic_values.append(ic)
            dates.append(factor.index[i])
        
        return pd.Series(ic_values, index=dates)
    
    def calculate_ic_ir(self, factor: pd.Series, returns: pd.Series) -> Tuple[float, float]:
        """计算IC均值和IR（信息比率）。"""
        ic_series = self.calculate_ic_series(factor, returns)
        
        if len(ic_series) == 0:
            return 0.0, 0.0
        
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return ic_mean, ir
    
    def factor_return_analysis(self, factor: pd.Series, returns: pd.Series, n_bins: int = 5) -> pd.DataFrame:
        """因子分组收益分析。"""
        factor_quantile = pd.qcut(factor, n_bins, labels=False, duplicates='drop')
        
        grouped = pd.DataFrame({
            'factor': factor,
            'return': returns,
            'group': factor_quantile
        }).groupby('group')
        
        analysis = grouped.agg({
            'return': ['mean', 'std', 'count'],
            'factor': ['mean', 'min', 'max']
        })
        
        if len(analysis) >= 2:
            long_return = analysis['return']['mean'].iloc[-1]
            short_return = analysis['return']['mean'].iloc[0]
            analysis.loc['long_short_diff'] = [long_return - short_return, np.nan, np.nan, np.nan, np.nan, np.nan]
        
        return analysis
    
    def calculate_factor_autocorrelation(self, factor: pd.Series, lag: int = 1) -> float:
        """计算因子自相关系数。"""
        return factor.autocorr(lag=lag)
    
    def analyze_all_factors(self, factors: pd.DataFrame, returns: pd.Series) -> Dict[str, Dict[str, float]]:
        """批量分析所有因子。"""
        results = {}
        
        for factor_name in factors.columns:
            factor = factors[factor_name].dropna()
            aligned_returns = returns.loc[factor.index]
            
            if len(factor) < 20:
                continue
            
            ic_mean, ir = self.calculate_ic_ir(factor, aligned_returns)
            autocorr = self.calculate_factor_autocorrelation(factor)
            
            results[factor_name] = {
                'ic_mean': ic_mean,
                'ir': ir,
                'autocorrelation': autocorr,
                'observations': len(factor),
                'mean': float(factor.mean()),
                'std': float(factor.std())
            }
        
        return results


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    print(f"数据量: {len(data)}")
    
    # 计算所有因子
    factors = factor_engine.compute_all_factors(data)
    print(f"\n计算的因子数量: {len(factors.columns)}")
    print(factors.columns.tolist())
    print(factors.head())
    
    # 分析因子
    analyzer = FactorAnalyzer()
    returns = data['close'].pct_change().dropna()
    
    # 分析单个因子
    ic_mean, ir = analyzer.calculate_ic_ir(factors['momentum_20'], returns)
    print(f"\nmomentum_20 - IC均值: {ic_mean:.4f}, IR: {ir:.4f}")
    
    # 批量分析
    analysis_results = analyzer.analyze_all_factors(factors, returns)
    print("\n所有因子分析结果:")
    for name, stats in analysis_results.items():
        print(f"{name}: IC={stats['ic_mean']:.3f}, IR={stats['ir']:.3f}")
"""
OxQuant Factor Engine

因子挖掘模块，借鉴微软QLib框架的设计思路。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorType(Enum):
    """因子类型。"""
    ALPHA = "alpha"          # 阿尔法因子
    BETA = "beta"            # 贝塔因子
    VALUATION = "valuation"  # 估值因子
    QUALITY = "quality"      # 质量因子
    MOMENTUM = "momentum"    # 动量因子
    VOLATILITY = "volatility" # 波动率因子
    LIQUIDITY = "liquidity"  # 流动性因子


class FactorDirection(Enum):
    """因子方向。"""
    LONG = "long"            # 正向因子（因子值越高预期收益越高）
    SHORT = "short"          # 反向因子（因子值越高预期收益越低）
    NEUTRAL = "neutral"      # 中性因子


class FactorInfo:
    """因子信息类。"""
    
    def __init__(
        self,
        name: str,
        description: str,
        factor_type: FactorType,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        self.name = name
        self.description = description
        self.factor_type = factor_type
        self.direction = direction
        self.is_standardized = is_standardized
        self.window = window
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'factor_type': self.factor_type.value,
            'direction': self.direction.value,
            'is_standardized': self.is_standardized,
            'window': self.window
        }


class FactorEngine:
    """因子计算引擎。"""
    
    def __init__(self):
        self.factors: Dict[str, Callable] = {}
        self.factor_info: Dict[str, FactorInfo] = {}
    
    def register_factor(
        self,
        name: str,
        func: Callable,
        description: str = "",
        factor_type: FactorType = FactorType.ALPHA,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        """注册因子计算函数。"""
        self.factors[name] = func
        self.factor_info[name] = FactorInfo(
            name=name,
            description=description,
            factor_type=factor_type,
            direction=direction,
            is_standardized=is_standardized,
            window=window
        )
    
    def compute_factor(self, name: str, data: pd.DataFrame) -> pd.Series:
        """计算单个因子。"""
        if name not in self.factors:
            raise ValueError(f"Unknown factor: {name}")
        
        factor = self.factors[name](data)
        
        # 如果需要标准化
        if self.factor_info[name].is_standardized:
            factor = self._standardize(factor)
        
        return factor
    
    def compute_all_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有已注册因子。"""
        results = {}
        for name in self.factors:
            try:
                results[name] = self.compute_factor(name, data)
            except Exception as e:
                logger.error(f"Failed to compute factor {name}: {e}")
                results[name] = pd.Series([np.nan] * len(data), index=data.index)
        
        return pd.DataFrame(results)
    
    def _standardize(self, factor: pd.Series) -> pd.Series:
        """标准化因子（Z-score）。"""
        return (factor - factor.mean()) / factor.std()
    
    def get_factor_info(self, name: str) -> Optional[FactorInfo]:
        """获取因子信息。"""
        return self.factor_info.get(name)
    
    def list_factors(self) -> List[Dict[str, Any]]:
        """列出所有已注册因子。"""
        return [info.to_dict() for info in self.factor_info.values()]


# ==================== 常用因子实现 ====================

def factor_close_to_ma_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """收盘价相对均线比率。"""
    ma = data['close'].rolling(window=window).mean()
    return data['close'] / ma


def factor_momentum(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """动量因子：过去N日收益率。"""
    return data['close'].pct_change(window).fillna(0)


def factor_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """相对强弱指数。"""
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def factor_macd_signal(data: pd.DataFrame) -> pd.Series:
    """MACD信号因子。"""
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal


def factor_bollinger_band_width(data: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """布林带宽度。"""
    ma = data['close'].rolling(window=window).mean()
    std = data['close'].rolling(window=window).std()
    upper = ma + std * num_std
    lower = ma - std * num_std
    return (upper - lower) / ma


def factor_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """平均真实波动。"""
    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift()).abs()
    low_close = (data['low'] - data['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=window).mean()


def factor_volume_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """成交量相对均值比率。"""
    avg_volume = data['volume'].rolling(window=window).mean()
    return data['volume'] / avg_volume


def factor_turnover(data: pd.DataFrame) -> pd.Series:
    """换手率（如果数据中有）。"""
    if 'turnover' in data.columns:
        return data['turnover']
    return pd.Series([0.0] * len(data), index=data.index)


def factor_price_to_earnings(data: pd.DataFrame) -> pd.Series:
    """市盈率因子。"""
    if 'pe' in data.columns:
        return data['pe']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_price_to_book(data: pd.DataFrame) -> pd.Series:
    """市净率因子。"""
    if 'pb' in data.columns:
        return data['pb']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_earnings_growth(data: pd.DataFrame, window: int = 4) -> pd.Series:
    """盈利增长率。"""
    if 'eps' in data.columns:
        return data['eps'].pct_change(window).fillna(0)
    return pd.Series([0.0] * len(data), index=data.index)


def factor_sharpe_ratio(data: pd.DataFrame, window: int = 60) -> pd.Series:
    """滚动夏普比率。"""
    returns = data['close'].pct_change()
    return returns.rolling(window=window).mean() / returns.rolling(window=window).std() * np.sqrt(252)


# 创建全局因子引擎实例
factor_engine = FactorEngine()

# 注册常用因子
factor_engine.register_factor(
    'close_to_ma_20',
    lambda df: factor_close_to_ma_ratio(df, 20),
    description='收盘价相对20日均线比率',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_20',
    lambda df: factor_momentum(df, 20),
    description='20日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_60',
    lambda df: factor_momentum(df, 60),
    description='60日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=60
)

factor_engine.register_factor(
    'rsi_14',
    lambda df: factor_rsi(df, 14),
    description='14日RSI指标',
    factor_type=FactorType.MOMENTUM,
    direction=FactorDirection.SHORT,
    window=14
)

factor_engine.register_factor(
    'macd_signal',
    factor_macd_signal,
    description='MACD信号线',
    factor_type=FactorType.MOMENTUM
)

factor_engine.register_factor(
    'bollinger_width',
    factor_bollinger_band_width,
    description='布林带宽度',
    factor_type=FactorType.VOLATILITY,
    window=20
)

factor_engine.register_factor(
    'atr_14',
    lambda df: factor_atr(df, 14),
    description='14日ATR',
    factor_type=FactorType.VOLATILITY,
    window=14
)

factor_engine.register_factor(
    'volume_ratio_20',
    lambda df: factor_volume_ratio(df, 20),
    description='成交量相对20日均值比率',
    factor_type=FactorType.LIQUIDITY,
    window=20
)

factor_engine.register_factor(
    'turnover',
    factor_turnover,
    description='换手率',
    factor_type=FactorType.LIQUIDITY
)

factor_engine.register_factor(
    'pe',
    factor_price_to_earnings,
    description='市盈率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'pb',
    factor_price_to_book,
    description='市净率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'eps_growth',
    factor_earnings_growth,
    description='EPS增长率',
    factor_type=FactorType.QUALITY
)

factor_engine.register_factor(
    'sharpe_60',
    lambda df: factor_sharpe_ratio(df, 60),
    description='60日滚动夏普比率',
    factor_type=FactorType.QUALITY,
    window=60
)


class FactorAnalyzer:
    """因子分析器。"""
    
    def __init__(self):
        pass
    
    def calculate_ic(self, factor: pd.Series, returns: pd.Series, lag: int = 1) -> float:
        """计算信息系数（IC）。"""
        factor_shifted = factor.shift(lag)
        combined = pd.concat([factor_shifted, returns], axis=1).dropna()
        
        if len(combined) < 2:
            return 0.0
        
        return combined.corr().iloc[0, 1]
    
    def calculate_ic_series(self, factor: pd.Series, returns: pd.Series, window: int = 60) -> pd.Series:
        """计算滚动IC序列。"""
        ic_values = []
        dates = []
        
        for i in range(window, len(factor)):
            factor_window = factor.iloc[i-window:i]
            returns_window = returns.iloc[i-window:i]
            ic = self.calculate_ic(factor_window, returns_window)
            ic_values.append(ic)
            dates.append(factor.index[i])
        
        return pd.Series(ic_values, index=dates)
    
    def calculate_ic_ir(self, factor: pd.Series, returns: pd.Series) -> Tuple[float, float]:
        """计算IC均值和IR（信息比率）。"""
        ic_series = self.calculate_ic_series(factor, returns)
        
        if len(ic_series) == 0:
            return 0.0, 0.0
        
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return ic_mean, ir
    
    def factor_return_analysis(self, factor: pd.Series, returns: pd.Series, n_bins: int = 5) -> pd.DataFrame:
        """因子分组收益分析。"""
        factor_quantile = pd.qcut(factor, n_bins, labels=False, duplicates='drop')
        
        grouped = pd.DataFrame({
            'factor': factor,
            'return': returns,
            'group': factor_quantile
        }).groupby('group')
        
        analysis = grouped.agg({
            'return': ['mean', 'std', 'count'],
            'factor': ['mean', 'min', 'max']
        })
        
        if len(analysis) >= 2:
            long_return = analysis['return']['mean'].iloc[-1]
            short_return = analysis['return']['mean'].iloc[0]
            analysis.loc['long_short_diff'] = [long_return - short_return, np.nan, np.nan, np.nan, np.nan, np.nan]
        
        return analysis
    
    def calculate_factor_autocorrelation(self, factor: pd.Series, lag: int = 1) -> float:
        """计算因子自相关系数。"""
        return factor.autocorr(lag=lag)
    
    def analyze_all_factors(self, factors: pd.DataFrame, returns: pd.Series) -> Dict[str, Dict[str, float]]:
        """批量分析所有因子。"""
        results = {}
        
        for factor_name in factors.columns:
            factor = factors[factor_name].dropna()
            aligned_returns = returns.loc[factor.index]
            
            if len(factor) < 20:
                continue
            
            ic_mean, ir = self.calculate_ic_ir(factor, aligned_returns)
            autocorr = self.calculate_factor_autocorrelation(factor)
            
            results[factor_name] = {
                'ic_mean': ic_mean,
                'ir': ir,
                'autocorrelation': autocorr,
                'observations': len(factor),
                'mean': float(factor.mean()),
                'std': float(factor.std())
            }
        
        return results


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    print(f"数据量: {len(data)}")
    
    # 计算所有因子
    factors = factor_engine.compute_all_factors(data)
    print(f"\n计算的因子数量: {len(factors.columns)}")
    print(factors.columns.tolist())
    print(factors.head())
    
    # 分析因子
    analyzer = FactorAnalyzer()
    returns = data['close'].pct_change().dropna()
    
    # 分析单个因子
    ic_mean, ir = analyzer.calculate_ic_ir(factors['momentum_20'], returns)
    print(f"\nmomentum_20 - IC均值: {ic_mean:.4f}, IR: {ir:.4f}")
    
    # 批量分析
    analysis_results = analyzer.analyze_all_factors(factors, returns)
    print("\n所有因子分析结果:")
    for name, stats in analysis_results.items():
        print(f"{name}: IC={stats['ic_mean']:.3f}, IR={stats['ir']:.3f}")
"""
OxQuant Factor Engine

因子挖掘模块，借鉴微软QLib框架的设计思路。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorType(Enum):
    """因子类型。"""
    ALPHA = "alpha"          # 阿尔法因子
    BETA = "beta"            # 贝塔因子
    VALUATION = "valuation"  # 估值因子
    QUALITY = "quality"      # 质量因子
    MOMENTUM = "momentum"    # 动量因子
    VOLATILITY = "volatility" # 波动率因子
    LIQUIDITY = "liquidity"  # 流动性因子


class FactorDirection(Enum):
    """因子方向。"""
    LONG = "long"            # 正向因子（因子值越高预期收益越高）
    SHORT = "short"          # 反向因子（因子值越高预期收益越低）
    NEUTRAL = "neutral"      # 中性因子


class FactorInfo:
    """因子信息类。"""
    
    def __init__(
        self,
        name: str,
        description: str,
        factor_type: FactorType,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        self.name = name
        self.description = description
        self.factor_type = factor_type
        self.direction = direction
        self.is_standardized = is_standardized
        self.window = window
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'factor_type': self.factor_type.value,
            'direction': self.direction.value,
            'is_standardized': self.is_standardized,
            'window': self.window
        }


class FactorEngine:
    """因子计算引擎。"""
    
    def __init__(self):
        self.factors: Dict[str, Callable] = {}
        self.factor_info: Dict[str, FactorInfo] = {}
    
    def register_factor(
        self,
        name: str,
        func: Callable,
        description: str = "",
        factor_type: FactorType = FactorType.ALPHA,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        """注册因子计算函数。"""
        self.factors[name] = func
        self.factor_info[name] = FactorInfo(
            name=name,
            description=description,
            factor_type=factor_type,
            direction=direction,
            is_standardized=is_standardized,
            window=window
        )
    
    def compute_factor(self, name: str, data: pd.DataFrame) -> pd.Series:
        """计算单个因子。"""
        if name not in self.factors:
            raise ValueError(f"Unknown factor: {name}")
        
        factor = self.factors[name](data)
        
        # 如果需要标准化
        if self.factor_info[name].is_standardized:
            factor = self._standardize(factor)
        
        return factor
    
    def compute_all_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有已注册因子。"""
        results = {}
        for name in self.factors:
            try:
                results[name] = self.compute_factor(name, data)
            except Exception as e:
                logger.error(f"Failed to compute factor {name}: {e}")
                results[name] = pd.Series([np.nan] * len(data), index=data.index)
        
        return pd.DataFrame(results)
    
    def _standardize(self, factor: pd.Series) -> pd.Series:
        """标准化因子（Z-score）。"""
        return (factor - factor.mean()) / factor.std()
    
    def get_factor_info(self, name: str) -> Optional[FactorInfo]:
        """获取因子信息。"""
        return self.factor_info.get(name)
    
    def list_factors(self) -> List[Dict[str, Any]]:
        """列出所有已注册因子。"""
        return [info.to_dict() for info in self.factor_info.values()]


# ==================== 常用因子实现 ====================

def factor_close_to_ma_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """收盘价相对均线比率。"""
    ma = data['close'].rolling(window=window).mean()
    return data['close'] / ma


def factor_momentum(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """动量因子：过去N日收益率。"""
    return data['close'].pct_change(window).fillna(0)


def factor_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """相对强弱指数。"""
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def factor_macd_signal(data: pd.DataFrame) -> pd.Series:
    """MACD信号因子。"""
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal


def factor_bollinger_band_width(data: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """布林带宽度。"""
    ma = data['close'].rolling(window=window).mean()
    std = data['close'].rolling(window=window).std()
    upper = ma + std * num_std
    lower = ma - std * num_std
    return (upper - lower) / ma


def factor_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """平均真实波动。"""
    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift()).abs()
    low_close = (data['low'] - data['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=window).mean()


def factor_volume_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """成交量相对均值比率。"""
    avg_volume = data['volume'].rolling(window=window).mean()
    return data['volume'] / avg_volume


def factor_turnover(data: pd.DataFrame) -> pd.Series:
    """换手率（如果数据中有）。"""
    if 'turnover' in data.columns:
        return data['turnover']
    return pd.Series([0.0] * len(data), index=data.index)


def factor_price_to_earnings(data: pd.DataFrame) -> pd.Series:
    """市盈率因子。"""
    if 'pe' in data.columns:
        return data['pe']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_price_to_book(data: pd.DataFrame) -> pd.Series:
    """市净率因子。"""
    if 'pb' in data.columns:
        return data['pb']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_earnings_growth(data: pd.DataFrame, window: int = 4) -> pd.Series:
    """盈利增长率。"""
    if 'eps' in data.columns:
        return data['eps'].pct_change(window).fillna(0)
    return pd.Series([0.0] * len(data), index=data.index)


def factor_sharpe_ratio(data: pd.DataFrame, window: int = 60) -> pd.Series:
    """滚动夏普比率。"""
    returns = data['close'].pct_change()
    return returns.rolling(window=window).mean() / returns.rolling(window=window).std() * np.sqrt(252)


# 创建全局因子引擎实例
factor_engine = FactorEngine()

# 注册常用因子
factor_engine.register_factor(
    'close_to_ma_20',
    lambda df: factor_close_to_ma_ratio(df, 20),
    description='收盘价相对20日均线比率',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_20',
    lambda df: factor_momentum(df, 20),
    description='20日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_60',
    lambda df: factor_momentum(df, 60),
    description='60日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=60
)

factor_engine.register_factor(
    'rsi_14',
    lambda df: factor_rsi(df, 14),
    description='14日RSI指标',
    factor_type=FactorType.MOMENTUM,
    direction=FactorDirection.SHORT,
    window=14
)

factor_engine.register_factor(
    'macd_signal',
    factor_macd_signal,
    description='MACD信号线',
    factor_type=FactorType.MOMENTUM
)

factor_engine.register_factor(
    'bollinger_width',
    factor_bollinger_band_width,
    description='布林带宽度',
    factor_type=FactorType.VOLATILITY,
    window=20
)

factor_engine.register_factor(
    'atr_14',
    lambda df: factor_atr(df, 14),
    description='14日ATR',
    factor_type=FactorType.VOLATILITY,
    window=14
)

factor_engine.register_factor(
    'volume_ratio_20',
    lambda df: factor_volume_ratio(df, 20),
    description='成交量相对20日均值比率',
    factor_type=FactorType.LIQUIDITY,
    window=20
)

factor_engine.register_factor(
    'turnover',
    factor_turnover,
    description='换手率',
    factor_type=FactorType.LIQUIDITY
)

factor_engine.register_factor(
    'pe',
    factor_price_to_earnings,
    description='市盈率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'pb',
    factor_price_to_book,
    description='市净率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'eps_growth',
    factor_earnings_growth,
    description='EPS增长率',
    factor_type=FactorType.QUALITY
)

factor_engine.register_factor(
    'sharpe_60',
    lambda df: factor_sharpe_ratio(df, 60),
    description='60日滚动夏普比率',
    factor_type=FactorType.QUALITY,
    window=60
)


class FactorAnalyzer:
    """因子分析器。"""
    
    def __init__(self):
        pass
    
    def calculate_ic(self, factor: pd.Series, returns: pd.Series, lag: int = 1) -> float:
        """计算信息系数（IC）。"""
        factor_shifted = factor.shift(lag)
        combined = pd.concat([factor_shifted, returns], axis=1).dropna()
        
        if len(combined) < 2:
            return 0.0
        
        return combined.corr().iloc[0, 1]
    
    def calculate_ic_series(self, factor: pd.Series, returns: pd.Series, window: int = 60) -> pd.Series:
        """计算滚动IC序列。"""
        ic_values = []
        dates = []
        
        for i in range(window, len(factor)):
            factor_window = factor.iloc[i-window:i]
            returns_window = returns.iloc[i-window:i]
            ic = self.calculate_ic(factor_window, returns_window)
            ic_values.append(ic)
            dates.append(factor.index[i])
        
        return pd.Series(ic_values, index=dates)
    
    def calculate_ic_ir(self, factor: pd.Series, returns: pd.Series) -> Tuple[float, float]:
        """计算IC均值和IR（信息比率）。"""
        ic_series = self.calculate_ic_series(factor, returns)
        
        if len(ic_series) == 0:
            return 0.0, 0.0
        
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return ic_mean, ir
    
    def factor_return_analysis(self, factor: pd.Series, returns: pd.Series, n_bins: int = 5) -> pd.DataFrame:
        """因子分组收益分析。"""
        factor_quantile = pd.qcut(factor, n_bins, labels=False, duplicates='drop')
        
        grouped = pd.DataFrame({
            'factor': factor,
            'return': returns,
            'group': factor_quantile
        }).groupby('group')
        
        analysis = grouped.agg({
            'return': ['mean', 'std', 'count'],
            'factor': ['mean', 'min', 'max']
        })
        
        if len(analysis) >= 2:
            long_return = analysis['return']['mean'].iloc[-1]
            short_return = analysis['return']['mean'].iloc[0]
            analysis.loc['long_short_diff'] = [long_return - short_return, np.nan, np.nan, np.nan, np.nan, np.nan]
        
        return analysis
    
    def calculate_factor_autocorrelation(self, factor: pd.Series, lag: int = 1) -> float:
        """计算因子自相关系数。"""
        return factor.autocorr(lag=lag)
    
    def analyze_all_factors(self, factors: pd.DataFrame, returns: pd.Series) -> Dict[str, Dict[str, float]]:
        """批量分析所有因子。"""
        results = {}
        
        for factor_name in factors.columns:
            factor = factors[factor_name].dropna()
            aligned_returns = returns.loc[factor.index]
            
            if len(factor) < 20:
                continue
            
            ic_mean, ir = self.calculate_ic_ir(factor, aligned_returns)
            autocorr = self.calculate_factor_autocorrelation(factor)
            
            results[factor_name] = {
                'ic_mean': ic_mean,
                'ir': ir,
                'autocorrelation': autocorr,
                'observations': len(factor),
                'mean': float(factor.mean()),
                'std': float(factor.std())
            }
        
        return results


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    print(f"数据量: {len(data)}")
    
    # 计算所有因子
    factors = factor_engine.compute_all_factors(data)
    print(f"\n计算的因子数量: {len(factors.columns)}")
    print(factors.columns.tolist())
    print(factors.head())
    
    # 分析因子
    analyzer = FactorAnalyzer()
    returns = data['close'].pct_change().dropna()
    
    # 分析单个因子
    ic_mean, ir = analyzer.calculate_ic_ir(factors['momentum_20'], returns)
    print(f"\nmomentum_20 - IC均值: {ic_mean:.4f}, IR: {ir:.4f}")
    
    # 批量分析
    analysis_results = analyzer.analyze_all_factors(factors, returns)
    print("\n所有因子分析结果:")
    for name, stats in analysis_results.items():
        print(f"{name}: IC={stats['ic_mean']:.3f}, IR={stats['ir']:.3f}")
"""
OxQuant Factor Engine

因子挖掘模块，借鉴微软QLib框架的设计思路。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorType(Enum):
    """因子类型。"""
    ALPHA = "alpha"          # 阿尔法因子
    BETA = "beta"            # 贝塔因子
    VALUATION = "valuation"  # 估值因子
    QUALITY = "quality"      # 质量因子
    MOMENTUM = "momentum"    # 动量因子
    VOLATILITY = "volatility" # 波动率因子
    LIQUIDITY = "liquidity"  # 流动性因子


class FactorDirection(Enum):
    """因子方向。"""
    LONG = "long"            # 正向因子（因子值越高预期收益越高）
    SHORT = "short"          # 反向因子（因子值越高预期收益越低）
    NEUTRAL = "neutral"      # 中性因子


class FactorInfo:
    """因子信息类。"""
    
    def __init__(
        self,
        name: str,
        description: str,
        factor_type: FactorType,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        self.name = name
        self.description = description
        self.factor_type = factor_type
        self.direction = direction
        self.is_standardized = is_standardized
        self.window = window
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'factor_type': self.factor_type.value,
            'direction': self.direction.value,
            'is_standardized': self.is_standardized,
            'window': self.window
        }


class FactorEngine:
    """因子计算引擎。"""
    
    def __init__(self):
        self.factors: Dict[str, Callable] = {}
        self.factor_info: Dict[str, FactorInfo] = {}
    
    def register_factor(
        self,
        name: str,
        func: Callable,
        description: str = "",
        factor_type: FactorType = FactorType.ALPHA,
        direction: FactorDirection = FactorDirection.LONG,
        is_standardized: bool = True,
        window: Optional[int] = None
    ):
        """注册因子计算函数。"""
        self.factors[name] = func
        self.factor_info[name] = FactorInfo(
            name=name,
            description=description,
            factor_type=factor_type,
            direction=direction,
            is_standardized=is_standardized,
            window=window
        )
    
    def compute_factor(self, name: str, data: pd.DataFrame) -> pd.Series:
        """计算单个因子。"""
        if name not in self.factors:
            raise ValueError(f"Unknown factor: {name}")
        
        factor = self.factors[name](data)
        
        # 如果需要标准化
        if self.factor_info[name].is_standardized:
            factor = self._standardize(factor)
        
        return factor
    
    def compute_all_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有已注册因子。"""
        results = {}
        for name in self.factors:
            try:
                results[name] = self.compute_factor(name, data)
            except Exception as e:
                logger.error(f"Failed to compute factor {name}: {e}")
                results[name] = pd.Series([np.nan] * len(data), index=data.index)
        
        return pd.DataFrame(results)
    
    def _standardize(self, factor: pd.Series) -> pd.Series:
        """标准化因子（Z-score）。"""
        return (factor - factor.mean()) / factor.std()
    
    def get_factor_info(self, name: str) -> Optional[FactorInfo]:
        """获取因子信息。"""
        return self.factor_info.get(name)
    
    def list_factors(self) -> List[Dict[str, Any]]:
        """列出所有已注册因子。"""
        return [info.to_dict() for info in self.factor_info.values()]


# ==================== 常用因子实现 ====================

def factor_close_to_ma_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """收盘价相对均线比率。"""
    ma = data['close'].rolling(window=window).mean()
    return data['close'] / ma


def factor_momentum(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """动量因子：过去N日收益率。"""
    return data['close'].pct_change(window).fillna(0)


def factor_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """相对强弱指数。"""
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def factor_macd_signal(data: pd.DataFrame) -> pd.Series:
    """MACD信号因子。"""
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal


def factor_bollinger_band_width(data: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """布林带宽度。"""
    ma = data['close'].rolling(window=window).mean()
    std = data['close'].rolling(window=window).std()
    upper = ma + std * num_std
    lower = ma - std * num_std
    return (upper - lower) / ma


def factor_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """平均真实波动。"""
    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift()).abs()
    low_close = (data['low'] - data['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=window).mean()


def factor_volume_ratio(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """成交量相对均值比率。"""
    avg_volume = data['volume'].rolling(window=window).mean()
    return data['volume'] / avg_volume


def factor_turnover(data: pd.DataFrame) -> pd.Series:
    """换手率（如果数据中有）。"""
    if 'turnover' in data.columns:
        return data['turnover']
    return pd.Series([0.0] * len(data), index=data.index)


def factor_price_to_earnings(data: pd.DataFrame) -> pd.Series:
    """市盈率因子。"""
    if 'pe' in data.columns:
        return data['pe']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_price_to_book(data: pd.DataFrame) -> pd.Series:
    """市净率因子。"""
    if 'pb' in data.columns:
        return data['pb']
    return pd.Series([np.nan] * len(data), index=data.index)


def factor_earnings_growth(data: pd.DataFrame, window: int = 4) -> pd.Series:
    """盈利增长率。"""
    if 'eps' in data.columns:
        return data['eps'].pct_change(window).fillna(0)
    return pd.Series([0.0] * len(data), index=data.index)


def factor_sharpe_ratio(data: pd.DataFrame, window: int = 60) -> pd.Series:
    """滚动夏普比率。"""
    returns = data['close'].pct_change()
    return returns.rolling(window=window).mean() / returns.rolling(window=window).std() * np.sqrt(252)


# 创建全局因子引擎实例
factor_engine = FactorEngine()

# 注册常用因子
factor_engine.register_factor(
    'close_to_ma_20',
    lambda df: factor_close_to_ma_ratio(df, 20),
    description='收盘价相对20日均线比率',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_20',
    lambda df: factor_momentum(df, 20),
    description='20日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=20
)

factor_engine.register_factor(
    'momentum_60',
    lambda df: factor_momentum(df, 60),
    description='60日动量因子',
    factor_type=FactorType.MOMENTUM,
    window=60
)

factor_engine.register_factor(
    'rsi_14',
    lambda df: factor_rsi(df, 14),
    description='14日RSI指标',
    factor_type=FactorType.MOMENTUM,
    direction=FactorDirection.SHORT,
    window=14
)

factor_engine.register_factor(
    'macd_signal',
    factor_macd_signal,
    description='MACD信号线',
    factor_type=FactorType.MOMENTUM
)

factor_engine.register_factor(
    'bollinger_width',
    factor_bollinger_band_width,
    description='布林带宽度',
    factor_type=FactorType.VOLATILITY,
    window=20
)

factor_engine.register_factor(
    'atr_14',
    lambda df: factor_atr(df, 14),
    description='14日ATR',
    factor_type=FactorType.VOLATILITY,
    window=14
)

factor_engine.register_factor(
    'volume_ratio_20',
    lambda df: factor_volume_ratio(df, 20),
    description='成交量相对20日均值比率',
    factor_type=FactorType.LIQUIDITY,
    window=20
)

factor_engine.register_factor(
    'turnover',
    factor_turnover,
    description='换手率',
    factor_type=FactorType.LIQUIDITY
)

factor_engine.register_factor(
    'pe',
    factor_price_to_earnings,
    description='市盈率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'pb',
    factor_price_to_book,
    description='市净率',
    factor_type=FactorType.VALUATION,
    direction=FactorDirection.SHORT
)

factor_engine.register_factor(
    'eps_growth',
    factor_earnings_growth,
    description='EPS增长率',
    factor_type=FactorType.QUALITY
)

factor_engine.register_factor(
    'sharpe_60',
    lambda df: factor_sharpe_ratio(df, 60),
    description='60日滚动夏普比率',
    factor_type=FactorType.QUALITY,
    window=60
)


class FactorAnalyzer:
    """因子分析器。"""
    
    def __init__(self):
        pass
    
    def calculate_ic(self, factor: pd.Series, returns: pd.Series, lag: int = 1) -> float:
        """计算信息系数（IC）。"""
        factor_shifted = factor.shift(lag)
        combined = pd.concat([factor_shifted, returns], axis=1).dropna()
        
        if len(combined) < 2:
            return 0.0
        
        return combined.corr().iloc[0, 1]
    
    def calculate_ic_series(self, factor: pd.Series, returns: pd.Series, window: int = 60) -> pd.Series:
        """计算滚动IC序列。"""
        ic_values = []
        dates = []
        
        for i in range(window, len(factor)):
            factor_window = factor.iloc[i-window:i]
            returns_window = returns.iloc[i-window:i]
            ic = self.calculate_ic(factor_window, returns_window)
            ic_values.append(ic)
            dates.append(factor.index[i])
        
        return pd.Series(ic_values, index=dates)
    
    def calculate_ic_ir(self, factor: pd.Series, returns: pd.Series) -> Tuple[float, float]:
        """计算IC均值和IR（信息比率）。"""
        ic_series = self.calculate_ic_series(factor, returns)
        
        if len(ic_series) == 0:
            return 0.0, 0.0
        
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return ic_mean, ir
    
    def factor_return_analysis(self, factor: pd.Series, returns: pd.Series, n_bins: int = 5) -> pd.DataFrame:
        """因子分组收益分析。"""
        factor_quantile = pd.qcut(factor, n_bins, labels=False, duplicates='drop')
        
        grouped = pd.DataFrame({
            'factor': factor,
            'return': returns,
            'group': factor_quantile
        }).groupby('group')
        
        analysis = grouped.agg({
            'return': ['mean', 'std', 'count'],
            'factor': ['mean', 'min', 'max']
        })
        
        if len(analysis) >= 2:
            long_return = analysis['return']['mean'].iloc[-1]
            short_return = analysis['return']['mean'].iloc[0]
            analysis.loc['long_short_diff'] = [long_return - short_return, np.nan, np.nan, np.nan, np.nan, np.nan]
        
        return analysis
    
    def calculate_factor_autocorrelation(self, factor: pd.Series, lag: int = 1) -> float:
        """计算因子自相关系数。"""
        return factor.autocorr(lag=lag)
    
    def analyze_all_factors(self, factors: pd.DataFrame, returns: pd.Series) -> Dict[str, Dict[str, float]]:
        """批量分析所有因子。"""
        results = {}
        
        for factor_name in factors.columns:
            factor = factors[factor_name].dropna()
            aligned_returns = returns.loc[factor.index]
            
            if len(factor) < 20:
                continue
            
            ic_mean, ir = self.calculate_ic_ir(factor, aligned_returns)
            autocorr = self.calculate_factor_autocorrelation(factor)
            
            results[factor_name] = {
                'ic_mean': ic_mean,
                'ir': ir,
                'autocorrelation': autocorr,
                'observations': len(factor),
                'mean': float(factor.mean()),
                'std': float(factor.std())
            }
        
        return results


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    print(f"数据量: {len(data)}")
    
    # 计算所有因子
    factors = factor_engine.compute_all_factors(data)
    print(f"\n计算的因子数量: {len(factors.columns)}")
    print(factors.columns.tolist())
    print(factors.head())
    
    # 分析因子
    analyzer = FactorAnalyzer()
    returns = data['close'].pct_change().dropna()
    
    # 分析单个因子
    ic_mean, ir = analyzer.calculate_ic_ir(factors['momentum_20'], returns)
    print(f"\nmomentum_20 - IC均值: {ic_mean:.4f}, IR: {ir:.4f}")
    
    # 批量分析
    analysis_results = analyzer.analyze_all_factors(factors, returns)
    print("\n所有因子分析结果:")
    for name, stats in analysis_results.items():
        print(f"{name}: IC={stats['ic_mean']:.3f}, IR={stats['ir']:.3f}")