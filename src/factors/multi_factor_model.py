"""
OxQuant Multi-Factor Model

多因子模型实现，支持因子合成、权重优化和组合构建。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
from scipy.optimize import minimize
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorCombinationMethod(Enum):
    """因子合成方法。"""
    EQUAL_WEIGHTED = "equal_weighted"      # 等权重
    IC_WEIGHTED = "ic_weighted"            # IC加权
    IR_WEIGHTED = "ir_weighted"            # IR加权
    REGRESSION = "regression"              # 回归方法
    ML_MODEL = "ml_model"                  # 机器学习模型


class MultiFactorModel:
    """多因子模型。"""
    
    def __init__(
        self,
        factors: pd.DataFrame,
        returns: pd.Series,
        method: FactorCombinationMethod = FactorCombinationMethod.IC_WEIGHTED
    ):
        self.factors = factors
        self.returns = returns
        self.method = method
        self.weights: Optional[pd.Series] = None
        self.model = None
        self.scaler = StandardScaler()
    
    def fit(self):
        """训练多因子模型。"""
        if self.method == FactorCombinationMethod.EQUAL_WEIGHTED:
            self._fit_equal_weighted()
        elif self.method == FactorCombinationMethod.IC_WEIGHTED:
            self._fit_ic_weighted()
        elif self.method == FactorCombinationMethod.IR_WEIGHTED:
            self._fit_ir_weighted()
        elif self.method == FactorCombinationMethod.REGRESSION:
            self._fit_regression()
        
        return self
    
    def _fit_equal_weighted(self):
        """等权重合成。"""
        n_factors = len(self.factors.columns)
        self.weights = pd.Series(
            [1.0 / n_factors] * n_factors,
            index=self.factors.columns
        )
    
    def _fit_ic_weighted(self):
        """基于IC的权重合成。"""
        from .factor_engine import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        ic_values = []
        
        for factor_name in self.factors.columns:
            factor = self.factors[factor_name].dropna()
            aligned_returns = self.returns.loc[factor.index]
            ic = analyzer.calculate_ic(factor, aligned_returns)
            ic_values.append(abs(ic))
        
        total_ic = sum(ic_values)
        if total_ic > 0:
            self.weights = pd.Series(
                [ic / total_ic for ic in ic_values],
                index=self.factors.columns
            )
        else:
            self._fit_equal_weighted()
    
    def _fit_ir_weighted(self):
        """基于IR的权重合成。"""
        from .factor_engine import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        ir_values = []
        
        for factor_name in self.factors.columns:
            factor = self.factors[factor_name].dropna()
            aligned_returns = self.returns.loc[factor.index]
            _, ir = analyzer.calculate_ic_ir(factor, aligned_returns)
            ir_values.append(abs(ir))
        
        total_ir = sum(ir_values)
        if total_ir > 0:
            self.weights = pd.Series(
                [ir / total_ir for ir in ir_values],
                index=self.factors.columns
            )
        else:
            self._fit_equal_weighted()
    
    def _fit_regression(self):
        """使用回归方法训练因子权重。"""
        # 准备数据
        X = self.factors.dropna()
        y = self.returns.loc[X.index]
        
        # 标准化因子
        X_scaled = self.scaler.fit_transform(X)
        
        # 使用Ridge回归
        self.model = Ridge(alpha=1.0)
        self.model.fit(X_scaled, y)
        
        # 获取权重
        self.weights = pd.Series(
            self.model.coef_,
            index=self.factors.columns
        )
        
        # 归一化权重
        total_weight = self.weights.abs().sum()
        if total_weight > 0:
            self.weights = self.weights / total_weight
    
    def predict(self, factors: pd.DataFrame) -> pd.Series:
        """预测股票收益。"""
        if self.weights is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # 只使用已训练的因子
        common_factors = [f for f in factors.columns if f in self.weights.index]
        
        if not common_factors:
            return pd.Series([0.0] * len(factors), index=factors.index)
        
        # 计算综合因子得分
        weighted_factors = factors[common_factors] @ self.weights[common_factors]
        
        return weighted_factors
    
    def get_factor_weights(self) -> pd.Series:
        """获取因子权重。"""
        return self.weights
    
    def evaluate(self, test_factors: pd.DataFrame, test_returns: pd.Series) -> Dict[str, float]:
        """评估模型性能。"""
        predictions = self.predict(test_factors)
        
        # 对齐数据
        aligned = pd.concat([predictions, test_returns], axis=1).dropna()
        predictions_aligned = aligned.iloc[:, 0]
        returns_aligned = aligned.iloc[:, 1]
        
        if len(aligned) < 2:
            return {}
        
        # 计算IC
        ic = predictions_aligned.corr(returns_aligned)
        
        # 计算IR
        ic_series = []
        window = 60
        for i in range(window, len(aligned), window):
            ic_window = predictions_aligned.iloc[i-window:i].corr(returns_aligned.iloc[i-window:i])
            ic_series.append(ic_window)
        
        ir = np.mean(ic_series) / np.std(ic_series) if len(ic_series) > 1 else 0
        
        # 计算MSE和R2
        mse = mean_squared_error(returns_aligned, predictions_aligned)
        r2 = r2_score(returns_aligned, predictions_aligned)
        
        return {
            'ic': ic,
            'ir': ir,
            'mse': mse,
            'r2': r2,
            'observations': len(aligned)
        }


class PortfolioOptimizer:
    """组合优化器。"""
    
    def __init__(
        self,
        expected_returns: pd.Series,
        covariance_matrix: Optional[pd.DataFrame] = None,
        constraints: Optional[List[Dict]] = None
    ):
        self.expected_returns = expected_returns
        self.covariance_matrix = covariance_matrix
        self.constraints = constraints or []
        self.weights: Optional[pd.Series] = None
    
    def optimize_max_sharpe(self, risk_free_rate: float = 0.02) -> pd.Series:
        """最大化夏普比率。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            # 最大化夏普比率 = 最小化负夏普比率
            portfolio_return = weights @ self.expected_returns
            portfolio_std = np.sqrt(weights @ self.covariance_matrix @ weights.T)
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe_ratio
        
        # 约束条件
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # 权重和为1
            {'type': 'ineq', 'fun': lambda w: w}  # 权重非负
        ]
        
        # 添加自定义约束
        for constraint in self.constraints:
            if constraint['type'] == 'max_weight':
                idx = self.expected_returns.index.get_loc(constraint['symbol'])
                constraints.append({
                    'type': 'ineq',
                    'fun': lambda w, i=idx, max_w=constraint['value']: max_w - w[i]
                })
        
        # 初始权重（等权重）
        initial_weights = np.ones(n) / n
        
        # 边界条件
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            logger.warning(f"Optimization failed: {result.message}")
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def optimize_min_variance(self) -> pd.Series:
        """最小化方差。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            return weights @ self.covariance_matrix @ weights.T
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'ineq', 'fun': lambda w: w}
        ]
        
        initial_weights = np.ones(n) / n
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def optimize_risk_parity(self) -> pd.Series:
        """风险平价优化。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            # 计算风险贡献
            portfolio_std = np.sqrt(weights @ self.covariance_matrix @ weights.T)
            risk_contributions = (weights * (self.covariance_matrix @ weights)) / portfolio_std
            
            # 风险贡献的方差（目标是让所有风险贡献相等）
            return np.var(risk_contributions)
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'ineq', 'fun': lambda w: w}
        ]
        
        initial_weights = np.ones(n) / n
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def get_weights(self) -> pd.Series:
        """获取优化后的权重。"""
        return self.weights


class SignalGenerator:
    """信号生成器。"""
    
    def __init__(self, multi_factor_model: MultiFactorModel):
        self.model = multi_factor_model
    
    def generate_signals(
        self,
        factors: pd.DataFrame,
        top_n: Optional[int] = None,
        long_only: bool = True
    ) -> pd.Series:
        """生成交易信号。"""
        # 预测收益
        predictions = self.model.predict(factors)
        
        # 排序
        sorted_predictions = predictions.sort_values(ascending=False)
        
        if top_n is not None:
            # 只选择前N个
            selected = sorted_predictions.head(top_n)
            signals = pd.Series(0, index=factors.index)
            signals.loc[selected.index] = selected.values
        else:
            signals = predictions
        
        # 如果只做多
        if long_only:
            signals[signals < 0] = 0
        
        return signals
    
    def generate_position_weights(
        self,
        factors: pd.DataFrame,
        top_n: int = 50,
        long_only: bool = True
    ) -> pd.Series:
        """生成持仓权重。"""
        predictions = self.model.predict(factors)
        
        if long_only:
            # 只选择正预测的股票
            positive_predictions = predictions[predictions > 0]
            sorted_predictions = positive_predictions.sort_values(ascending=False).head(top_n)
        else:
            sorted_predictions = predictions.sort_values(ascending=False).head(top_n)
        
        # 归一化权重
        total = sorted_predictions.abs().sum()
        if total > 0:
            weights = sorted_predictions.abs() / total
        else:
            weights = pd.Series(0, index=sorted_predictions.index)
        
        return weights


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    from src.factors.factor_engine import factor_engine
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    
    # 计算因子
    factors = factor_engine.compute_all_factors(data)
    
    # 计算未来收益（作为标签）
    returns = data['close'].pct_change().shift(-1).dropna()
    
    # 对齐数据
    aligned_data = pd.concat([factors, returns], axis=1).dropna()
    factors_aligned = aligned_data.iloc[:, :-1]
    returns_aligned = aligned_data.iloc[:, -1]
    
    # 创建多因子模型
    model = MultiFactorModel(factors_aligned, returns_aligned, method=FactorCombinationMethod.IC_WEIGHTED)
    model.fit()
    
    print("因子权重:")
    print(model.get_factor_weights().sort_values(ascending=False))
    
    # 评估模型
    train_size = int(len(factors_aligned) * 0.8)
    train_factors = factors_aligned.iloc[:train_size]
    train_returns = returns_aligned.iloc[:train_size]
    test_factors = factors_aligned.iloc[train_size:]
    test_returns = returns_aligned.iloc[train_size:]
    
    model2 = MultiFactorModel(train_factors, train_returns)
    model2.fit()
    
    metrics = model2.evaluate(test_factors, test_returns)
    print(f"\n模型评估结果:")
    print(f"IC: {metrics.get('ic', 0):.4f}")
    print(f"IR: {metrics.get('ir', 0):.4f}")
    print(f"R2: {metrics.get('r2', 0):.4f}")
    
    # 生成信号
    signal_generator = SignalGenerator(model2)
    signals = signal_generator.generate_signals(test_factors, top_n=10)
    print(f"\n生成的信号数量: {len(signals[signals != 0])}")
"""
OxQuant Multi-Factor Model

多因子模型实现，支持因子合成、权重优化和组合构建。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
from scipy.optimize import minimize
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorCombinationMethod(Enum):
    """因子合成方法。"""
    EQUAL_WEIGHTED = "equal_weighted"      # 等权重
    IC_WEIGHTED = "ic_weighted"            # IC加权
    IR_WEIGHTED = "ir_weighted"            # IR加权
    REGRESSION = "regression"              # 回归方法
    ML_MODEL = "ml_model"                  # 机器学习模型


class MultiFactorModel:
    """多因子模型。"""
    
    def __init__(
        self,
        factors: pd.DataFrame,
        returns: pd.Series,
        method: FactorCombinationMethod = FactorCombinationMethod.IC_WEIGHTED
    ):
        self.factors = factors
        self.returns = returns
        self.method = method
        self.weights: Optional[pd.Series] = None
        self.model = None
        self.scaler = StandardScaler()
    
    def fit(self):
        """训练多因子模型。"""
        if self.method == FactorCombinationMethod.EQUAL_WEIGHTED:
            self._fit_equal_weighted()
        elif self.method == FactorCombinationMethod.IC_WEIGHTED:
            self._fit_ic_weighted()
        elif self.method == FactorCombinationMethod.IR_WEIGHTED:
            self._fit_ir_weighted()
        elif self.method == FactorCombinationMethod.REGRESSION:
            self._fit_regression()
        
        return self
    
    def _fit_equal_weighted(self):
        """等权重合成。"""
        n_factors = len(self.factors.columns)
        self.weights = pd.Series(
            [1.0 / n_factors] * n_factors,
            index=self.factors.columns
        )
    
    def _fit_ic_weighted(self):
        """基于IC的权重合成。"""
        from .factor_engine import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        ic_values = []
        
        for factor_name in self.factors.columns:
            factor = self.factors[factor_name].dropna()
            aligned_returns = self.returns.loc[factor.index]
            ic = analyzer.calculate_ic(factor, aligned_returns)
            ic_values.append(abs(ic))
        
        total_ic = sum(ic_values)
        if total_ic > 0:
            self.weights = pd.Series(
                [ic / total_ic for ic in ic_values],
                index=self.factors.columns
            )
        else:
            self._fit_equal_weighted()
    
    def _fit_ir_weighted(self):
        """基于IR的权重合成。"""
        from .factor_engine import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        ir_values = []
        
        for factor_name in self.factors.columns:
            factor = self.factors[factor_name].dropna()
            aligned_returns = self.returns.loc[factor.index]
            _, ir = analyzer.calculate_ic_ir(factor, aligned_returns)
            ir_values.append(abs(ir))
        
        total_ir = sum(ir_values)
        if total_ir > 0:
            self.weights = pd.Series(
                [ir / total_ir for ir in ir_values],
                index=self.factors.columns
            )
        else:
            self._fit_equal_weighted()
    
    def _fit_regression(self):
        """使用回归方法训练因子权重。"""
        # 准备数据
        X = self.factors.dropna()
        y = self.returns.loc[X.index]
        
        # 标准化因子
        X_scaled = self.scaler.fit_transform(X)
        
        # 使用Ridge回归
        self.model = Ridge(alpha=1.0)
        self.model.fit(X_scaled, y)
        
        # 获取权重
        self.weights = pd.Series(
            self.model.coef_,
            index=self.factors.columns
        )
        
        # 归一化权重
        total_weight = self.weights.abs().sum()
        if total_weight > 0:
            self.weights = self.weights / total_weight
    
    def predict(self, factors: pd.DataFrame) -> pd.Series:
        """预测股票收益。"""
        if self.weights is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # 只使用已训练的因子
        common_factors = [f for f in factors.columns if f in self.weights.index]
        
        if not common_factors:
            return pd.Series([0.0] * len(factors), index=factors.index)
        
        # 计算综合因子得分
        weighted_factors = factors[common_factors] @ self.weights[common_factors]
        
        return weighted_factors
    
    def get_factor_weights(self) -> pd.Series:
        """获取因子权重。"""
        return self.weights
    
    def evaluate(self, test_factors: pd.DataFrame, test_returns: pd.Series) -> Dict[str, float]:
        """评估模型性能。"""
        predictions = self.predict(test_factors)
        
        # 对齐数据
        aligned = pd.concat([predictions, test_returns], axis=1).dropna()
        predictions_aligned = aligned.iloc[:, 0]
        returns_aligned = aligned.iloc[:, 1]
        
        if len(aligned) < 2:
            return {}
        
        # 计算IC
        ic = predictions_aligned.corr(returns_aligned)
        
        # 计算IR
        ic_series = []
        window = 60
        for i in range(window, len(aligned), window):
            ic_window = predictions_aligned.iloc[i-window:i].corr(returns_aligned.iloc[i-window:i])
            ic_series.append(ic_window)
        
        ir = np.mean(ic_series) / np.std(ic_series) if len(ic_series) > 1 else 0
        
        # 计算MSE和R2
        mse = mean_squared_error(returns_aligned, predictions_aligned)
        r2 = r2_score(returns_aligned, predictions_aligned)
        
        return {
            'ic': ic,
            'ir': ir,
            'mse': mse,
            'r2': r2,
            'observations': len(aligned)
        }


class PortfolioOptimizer:
    """组合优化器。"""
    
    def __init__(
        self,
        expected_returns: pd.Series,
        covariance_matrix: Optional[pd.DataFrame] = None,
        constraints: Optional[List[Dict]] = None
    ):
        self.expected_returns = expected_returns
        self.covariance_matrix = covariance_matrix
        self.constraints = constraints or []
        self.weights: Optional[pd.Series] = None
    
    def optimize_max_sharpe(self, risk_free_rate: float = 0.02) -> pd.Series:
        """最大化夏普比率。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            # 最大化夏普比率 = 最小化负夏普比率
            portfolio_return = weights @ self.expected_returns
            portfolio_std = np.sqrt(weights @ self.covariance_matrix @ weights.T)
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe_ratio
        
        # 约束条件
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # 权重和为1
            {'type': 'ineq', 'fun': lambda w: w}  # 权重非负
        ]
        
        # 添加自定义约束
        for constraint in self.constraints:
            if constraint['type'] == 'max_weight':
                idx = self.expected_returns.index.get_loc(constraint['symbol'])
                constraints.append({
                    'type': 'ineq',
                    'fun': lambda w, i=idx, max_w=constraint['value']: max_w - w[i]
                })
        
        # 初始权重（等权重）
        initial_weights = np.ones(n) / n
        
        # 边界条件
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            logger.warning(f"Optimization failed: {result.message}")
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def optimize_min_variance(self) -> pd.Series:
        """最小化方差。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            return weights @ self.covariance_matrix @ weights.T
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'ineq', 'fun': lambda w: w}
        ]
        
        initial_weights = np.ones(n) / n
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def optimize_risk_parity(self) -> pd.Series:
        """风险平价优化。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            # 计算风险贡献
            portfolio_std = np.sqrt(weights @ self.covariance_matrix @ weights.T)
            risk_contributions = (weights * (self.covariance_matrix @ weights)) / portfolio_std
            
            # 风险贡献的方差（目标是让所有风险贡献相等）
            return np.var(risk_contributions)
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'ineq', 'fun': lambda w: w}
        ]
        
        initial_weights = np.ones(n) / n
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def get_weights(self) -> pd.Series:
        """获取优化后的权重。"""
        return self.weights


class SignalGenerator:
    """信号生成器。"""
    
    def __init__(self, multi_factor_model: MultiFactorModel):
        self.model = multi_factor_model
    
    def generate_signals(
        self,
        factors: pd.DataFrame,
        top_n: Optional[int] = None,
        long_only: bool = True
    ) -> pd.Series:
        """生成交易信号。"""
        # 预测收益
        predictions = self.model.predict(factors)
        
        # 排序
        sorted_predictions = predictions.sort_values(ascending=False)
        
        if top_n is not None:
            # 只选择前N个
            selected = sorted_predictions.head(top_n)
            signals = pd.Series(0, index=factors.index)
            signals.loc[selected.index] = selected.values
        else:
            signals = predictions
        
        # 如果只做多
        if long_only:
            signals[signals < 0] = 0
        
        return signals
    
    def generate_position_weights(
        self,
        factors: pd.DataFrame,
        top_n: int = 50,
        long_only: bool = True
    ) -> pd.Series:
        """生成持仓权重。"""
        predictions = self.model.predict(factors)
        
        if long_only:
            # 只选择正预测的股票
            positive_predictions = predictions[predictions > 0]
            sorted_predictions = positive_predictions.sort_values(ascending=False).head(top_n)
        else:
            sorted_predictions = predictions.sort_values(ascending=False).head(top_n)
        
        # 归一化权重
        total = sorted_predictions.abs().sum()
        if total > 0:
            weights = sorted_predictions.abs() / total
        else:
            weights = pd.Series(0, index=sorted_predictions.index)
        
        return weights


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    from src.factors.factor_engine import factor_engine
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    
    # 计算因子
    factors = factor_engine.compute_all_factors(data)
    
    # 计算未来收益（作为标签）
    returns = data['close'].pct_change().shift(-1).dropna()
    
    # 对齐数据
    aligned_data = pd.concat([factors, returns], axis=1).dropna()
    factors_aligned = aligned_data.iloc[:, :-1]
    returns_aligned = aligned_data.iloc[:, -1]
    
    # 创建多因子模型
    model = MultiFactorModel(factors_aligned, returns_aligned, method=FactorCombinationMethod.IC_WEIGHTED)
    model.fit()
    
    print("因子权重:")
    print(model.get_factor_weights().sort_values(ascending=False))
    
    # 评估模型
    train_size = int(len(factors_aligned) * 0.8)
    train_factors = factors_aligned.iloc[:train_size]
    train_returns = returns_aligned.iloc[:train_size]
    test_factors = factors_aligned.iloc[train_size:]
    test_returns = returns_aligned.iloc[train_size:]
    
    model2 = MultiFactorModel(train_factors, train_returns)
    model2.fit()
    
    metrics = model2.evaluate(test_factors, test_returns)
    print(f"\n模型评估结果:")
    print(f"IC: {metrics.get('ic', 0):.4f}")
    print(f"IR: {metrics.get('ir', 0):.4f}")
    print(f"R2: {metrics.get('r2', 0):.4f}")
    
    # 生成信号
    signal_generator = SignalGenerator(model2)
    signals = signal_generator.generate_signals(test_factors, top_n=10)
    print(f"\n生成的信号数量: {len(signals[signals != 0])}")
"""
OxQuant Multi-Factor Model

多因子模型实现，支持因子合成、权重优化和组合构建。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
from scipy.optimize import minimize
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorCombinationMethod(Enum):
    """因子合成方法。"""
    EQUAL_WEIGHTED = "equal_weighted"      # 等权重
    IC_WEIGHTED = "ic_weighted"            # IC加权
    IR_WEIGHTED = "ir_weighted"            # IR加权
    REGRESSION = "regression"              # 回归方法
    ML_MODEL = "ml_model"                  # 机器学习模型


class MultiFactorModel:
    """多因子模型。"""
    
    def __init__(
        self,
        factors: pd.DataFrame,
        returns: pd.Series,
        method: FactorCombinationMethod = FactorCombinationMethod.IC_WEIGHTED
    ):
        self.factors = factors
        self.returns = returns
        self.method = method
        self.weights: Optional[pd.Series] = None
        self.model = None
        self.scaler = StandardScaler()
    
    def fit(self):
        """训练多因子模型。"""
        if self.method == FactorCombinationMethod.EQUAL_WEIGHTED:
            self._fit_equal_weighted()
        elif self.method == FactorCombinationMethod.IC_WEIGHTED:
            self._fit_ic_weighted()
        elif self.method == FactorCombinationMethod.IR_WEIGHTED:
            self._fit_ir_weighted()
        elif self.method == FactorCombinationMethod.REGRESSION:
            self._fit_regression()
        
        return self
    
    def _fit_equal_weighted(self):
        """等权重合成。"""
        n_factors = len(self.factors.columns)
        self.weights = pd.Series(
            [1.0 / n_factors] * n_factors,
            index=self.factors.columns
        )
    
    def _fit_ic_weighted(self):
        """基于IC的权重合成。"""
        from .factor_engine import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        ic_values = []
        
        for factor_name in self.factors.columns:
            factor = self.factors[factor_name].dropna()
            aligned_returns = self.returns.loc[factor.index]
            ic = analyzer.calculate_ic(factor, aligned_returns)
            ic_values.append(abs(ic))
        
        total_ic = sum(ic_values)
        if total_ic > 0:
            self.weights = pd.Series(
                [ic / total_ic for ic in ic_values],
                index=self.factors.columns
            )
        else:
            self._fit_equal_weighted()
    
    def _fit_ir_weighted(self):
        """基于IR的权重合成。"""
        from .factor_engine import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        ir_values = []
        
        for factor_name in self.factors.columns:
            factor = self.factors[factor_name].dropna()
            aligned_returns = self.returns.loc[factor.index]
            _, ir = analyzer.calculate_ic_ir(factor, aligned_returns)
            ir_values.append(abs(ir))
        
        total_ir = sum(ir_values)
        if total_ir > 0:
            self.weights = pd.Series(
                [ir / total_ir for ir in ir_values],
                index=self.factors.columns
            )
        else:
            self._fit_equal_weighted()
    
    def _fit_regression(self):
        """使用回归方法训练因子权重。"""
        # 准备数据
        X = self.factors.dropna()
        y = self.returns.loc[X.index]
        
        # 标准化因子
        X_scaled = self.scaler.fit_transform(X)
        
        # 使用Ridge回归
        self.model = Ridge(alpha=1.0)
        self.model.fit(X_scaled, y)
        
        # 获取权重
        self.weights = pd.Series(
            self.model.coef_,
            index=self.factors.columns
        )
        
        # 归一化权重
        total_weight = self.weights.abs().sum()
        if total_weight > 0:
            self.weights = self.weights / total_weight
    
    def predict(self, factors: pd.DataFrame) -> pd.Series:
        """预测股票收益。"""
        if self.weights is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # 只使用已训练的因子
        common_factors = [f for f in factors.columns if f in self.weights.index]
        
        if not common_factors:
            return pd.Series([0.0] * len(factors), index=factors.index)
        
        # 计算综合因子得分
        weighted_factors = factors[common_factors] @ self.weights[common_factors]
        
        return weighted_factors
    
    def get_factor_weights(self) -> pd.Series:
        """获取因子权重。"""
        return self.weights
    
    def evaluate(self, test_factors: pd.DataFrame, test_returns: pd.Series) -> Dict[str, float]:
        """评估模型性能。"""
        predictions = self.predict(test_factors)
        
        # 对齐数据
        aligned = pd.concat([predictions, test_returns], axis=1).dropna()
        predictions_aligned = aligned.iloc[:, 0]
        returns_aligned = aligned.iloc[:, 1]
        
        if len(aligned) < 2:
            return {}
        
        # 计算IC
        ic = predictions_aligned.corr(returns_aligned)
        
        # 计算IR
        ic_series = []
        window = 60
        for i in range(window, len(aligned), window):
            ic_window = predictions_aligned.iloc[i-window:i].corr(returns_aligned.iloc[i-window:i])
            ic_series.append(ic_window)
        
        ir = np.mean(ic_series) / np.std(ic_series) if len(ic_series) > 1 else 0
        
        # 计算MSE和R2
        mse = mean_squared_error(returns_aligned, predictions_aligned)
        r2 = r2_score(returns_aligned, predictions_aligned)
        
        return {
            'ic': ic,
            'ir': ir,
            'mse': mse,
            'r2': r2,
            'observations': len(aligned)
        }


class PortfolioOptimizer:
    """组合优化器。"""
    
    def __init__(
        self,
        expected_returns: pd.Series,
        covariance_matrix: Optional[pd.DataFrame] = None,
        constraints: Optional[List[Dict]] = None
    ):
        self.expected_returns = expected_returns
        self.covariance_matrix = covariance_matrix
        self.constraints = constraints or []
        self.weights: Optional[pd.Series] = None
    
    def optimize_max_sharpe(self, risk_free_rate: float = 0.02) -> pd.Series:
        """最大化夏普比率。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            # 最大化夏普比率 = 最小化负夏普比率
            portfolio_return = weights @ self.expected_returns
            portfolio_std = np.sqrt(weights @ self.covariance_matrix @ weights.T)
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe_ratio
        
        # 约束条件
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # 权重和为1
            {'type': 'ineq', 'fun': lambda w: w}  # 权重非负
        ]
        
        # 添加自定义约束
        for constraint in self.constraints:
            if constraint['type'] == 'max_weight':
                idx = self.expected_returns.index.get_loc(constraint['symbol'])
                constraints.append({
                    'type': 'ineq',
                    'fun': lambda w, i=idx, max_w=constraint['value']: max_w - w[i]
                })
        
        # 初始权重（等权重）
        initial_weights = np.ones(n) / n
        
        # 边界条件
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            logger.warning(f"Optimization failed: {result.message}")
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def optimize_min_variance(self) -> pd.Series:
        """最小化方差。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            return weights @ self.covariance_matrix @ weights.T
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'ineq', 'fun': lambda w: w}
        ]
        
        initial_weights = np.ones(n) / n
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def optimize_risk_parity(self) -> pd.Series:
        """风险平价优化。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            # 计算风险贡献
            portfolio_std = np.sqrt(weights @ self.covariance_matrix @ weights.T)
            risk_contributions = (weights * (self.covariance_matrix @ weights)) / portfolio_std
            
            # 风险贡献的方差（目标是让所有风险贡献相等）
            return np.var(risk_contributions)
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'ineq', 'fun': lambda w: w}
        ]
        
        initial_weights = np.ones(n) / n
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def get_weights(self) -> pd.Series:
        """获取优化后的权重。"""
        return self.weights


class SignalGenerator:
    """信号生成器。"""
    
    def __init__(self, multi_factor_model: MultiFactorModel):
        self.model = multi_factor_model
    
    def generate_signals(
        self,
        factors: pd.DataFrame,
        top_n: Optional[int] = None,
        long_only: bool = True
    ) -> pd.Series:
        """生成交易信号。"""
        # 预测收益
        predictions = self.model.predict(factors)
        
        # 排序
        sorted_predictions = predictions.sort_values(ascending=False)
        
        if top_n is not None:
            # 只选择前N个
            selected = sorted_predictions.head(top_n)
            signals = pd.Series(0, index=factors.index)
            signals.loc[selected.index] = selected.values
        else:
            signals = predictions
        
        # 如果只做多
        if long_only:
            signals[signals < 0] = 0
        
        return signals
    
    def generate_position_weights(
        self,
        factors: pd.DataFrame,
        top_n: int = 50,
        long_only: bool = True
    ) -> pd.Series:
        """生成持仓权重。"""
        predictions = self.model.predict(factors)
        
        if long_only:
            # 只选择正预测的股票
            positive_predictions = predictions[predictions > 0]
            sorted_predictions = positive_predictions.sort_values(ascending=False).head(top_n)
        else:
            sorted_predictions = predictions.sort_values(ascending=False).head(top_n)
        
        # 归一化权重
        total = sorted_predictions.abs().sum()
        if total > 0:
            weights = sorted_predictions.abs() / total
        else:
            weights = pd.Series(0, index=sorted_predictions.index)
        
        return weights


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    from src.factors.factor_engine import factor_engine
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    
    # 计算因子
    factors = factor_engine.compute_all_factors(data)
    
    # 计算未来收益（作为标签）
    returns = data['close'].pct_change().shift(-1).dropna()
    
    # 对齐数据
    aligned_data = pd.concat([factors, returns], axis=1).dropna()
    factors_aligned = aligned_data.iloc[:, :-1]
    returns_aligned = aligned_data.iloc[:, -1]
    
    # 创建多因子模型
    model = MultiFactorModel(factors_aligned, returns_aligned, method=FactorCombinationMethod.IC_WEIGHTED)
    model.fit()
    
    print("因子权重:")
    print(model.get_factor_weights().sort_values(ascending=False))
    
    # 评估模型
    train_size = int(len(factors_aligned) * 0.8)
    train_factors = factors_aligned.iloc[:train_size]
    train_returns = returns_aligned.iloc[:train_size]
    test_factors = factors_aligned.iloc[train_size:]
    test_returns = returns_aligned.iloc[train_size:]
    
    model2 = MultiFactorModel(train_factors, train_returns)
    model2.fit()
    
    metrics = model2.evaluate(test_factors, test_returns)
    print(f"\n模型评估结果:")
    print(f"IC: {metrics.get('ic', 0):.4f}")
    print(f"IR: {metrics.get('ir', 0):.4f}")
    print(f"R2: {metrics.get('r2', 0):.4f}")
    
    # 生成信号
    signal_generator = SignalGenerator(model2)
    signals = signal_generator.generate_signals(test_factors, top_n=10)
    print(f"\n生成的信号数量: {len(signals[signals != 0])}")
"""
OxQuant Multi-Factor Model

多因子模型实现，支持因子合成、权重优化和组合构建。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
from scipy.optimize import minimize
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorCombinationMethod(Enum):
    """因子合成方法。"""
    EQUAL_WEIGHTED = "equal_weighted"      # 等权重
    IC_WEIGHTED = "ic_weighted"            # IC加权
    IR_WEIGHTED = "ir_weighted"            # IR加权
    REGRESSION = "regression"              # 回归方法
    ML_MODEL = "ml_model"                  # 机器学习模型


class MultiFactorModel:
    """多因子模型。"""
    
    def __init__(
        self,
        factors: pd.DataFrame,
        returns: pd.Series,
        method: FactorCombinationMethod = FactorCombinationMethod.IC_WEIGHTED
    ):
        self.factors = factors
        self.returns = returns
        self.method = method
        self.weights: Optional[pd.Series] = None
        self.model = None
        self.scaler = StandardScaler()
    
    def fit(self):
        """训练多因子模型。"""
        if self.method == FactorCombinationMethod.EQUAL_WEIGHTED:
            self._fit_equal_weighted()
        elif self.method == FactorCombinationMethod.IC_WEIGHTED:
            self._fit_ic_weighted()
        elif self.method == FactorCombinationMethod.IR_WEIGHTED:
            self._fit_ir_weighted()
        elif self.method == FactorCombinationMethod.REGRESSION:
            self._fit_regression()
        
        return self
    
    def _fit_equal_weighted(self):
        """等权重合成。"""
        n_factors = len(self.factors.columns)
        self.weights = pd.Series(
            [1.0 / n_factors] * n_factors,
            index=self.factors.columns
        )
    
    def _fit_ic_weighted(self):
        """基于IC的权重合成。"""
        from .factor_engine import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        ic_values = []
        
        for factor_name in self.factors.columns:
            factor = self.factors[factor_name].dropna()
            aligned_returns = self.returns.loc[factor.index]
            ic = analyzer.calculate_ic(factor, aligned_returns)
            ic_values.append(abs(ic))
        
        total_ic = sum(ic_values)
        if total_ic > 0:
            self.weights = pd.Series(
                [ic / total_ic for ic in ic_values],
                index=self.factors.columns
            )
        else:
            self._fit_equal_weighted()
    
    def _fit_ir_weighted(self):
        """基于IR的权重合成。"""
        from .factor_engine import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        ir_values = []
        
        for factor_name in self.factors.columns:
            factor = self.factors[factor_name].dropna()
            aligned_returns = self.returns.loc[factor.index]
            _, ir = analyzer.calculate_ic_ir(factor, aligned_returns)
            ir_values.append(abs(ir))
        
        total_ir = sum(ir_values)
        if total_ir > 0:
            self.weights = pd.Series(
                [ir / total_ir for ir in ir_values],
                index=self.factors.columns
            )
        else:
            self._fit_equal_weighted()
    
    def _fit_regression(self):
        """使用回归方法训练因子权重。"""
        # 准备数据
        X = self.factors.dropna()
        y = self.returns.loc[X.index]
        
        # 标准化因子
        X_scaled = self.scaler.fit_transform(X)
        
        # 使用Ridge回归
        self.model = Ridge(alpha=1.0)
        self.model.fit(X_scaled, y)
        
        # 获取权重
        self.weights = pd.Series(
            self.model.coef_,
            index=self.factors.columns
        )
        
        # 归一化权重
        total_weight = self.weights.abs().sum()
        if total_weight > 0:
            self.weights = self.weights / total_weight
    
    def predict(self, factors: pd.DataFrame) -> pd.Series:
        """预测股票收益。"""
        if self.weights is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # 只使用已训练的因子
        common_factors = [f for f in factors.columns if f in self.weights.index]
        
        if not common_factors:
            return pd.Series([0.0] * len(factors), index=factors.index)
        
        # 计算综合因子得分
        weighted_factors = factors[common_factors] @ self.weights[common_factors]
        
        return weighted_factors
    
    def get_factor_weights(self) -> pd.Series:
        """获取因子权重。"""
        return self.weights
    
    def evaluate(self, test_factors: pd.DataFrame, test_returns: pd.Series) -> Dict[str, float]:
        """评估模型性能。"""
        predictions = self.predict(test_factors)
        
        # 对齐数据
        aligned = pd.concat([predictions, test_returns], axis=1).dropna()
        predictions_aligned = aligned.iloc[:, 0]
        returns_aligned = aligned.iloc[:, 1]
        
        if len(aligned) < 2:
            return {}
        
        # 计算IC
        ic = predictions_aligned.corr(returns_aligned)
        
        # 计算IR
        ic_series = []
        window = 60
        for i in range(window, len(aligned), window):
            ic_window = predictions_aligned.iloc[i-window:i].corr(returns_aligned.iloc[i-window:i])
            ic_series.append(ic_window)
        
        ir = np.mean(ic_series) / np.std(ic_series) if len(ic_series) > 1 else 0
        
        # 计算MSE和R2
        mse = mean_squared_error(returns_aligned, predictions_aligned)
        r2 = r2_score(returns_aligned, predictions_aligned)
        
        return {
            'ic': ic,
            'ir': ir,
            'mse': mse,
            'r2': r2,
            'observations': len(aligned)
        }


class PortfolioOptimizer:
    """组合优化器。"""
    
    def __init__(
        self,
        expected_returns: pd.Series,
        covariance_matrix: Optional[pd.DataFrame] = None,
        constraints: Optional[List[Dict]] = None
    ):
        self.expected_returns = expected_returns
        self.covariance_matrix = covariance_matrix
        self.constraints = constraints or []
        self.weights: Optional[pd.Series] = None
    
    def optimize_max_sharpe(self, risk_free_rate: float = 0.02) -> pd.Series:
        """最大化夏普比率。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            # 最大化夏普比率 = 最小化负夏普比率
            portfolio_return = weights @ self.expected_returns
            portfolio_std = np.sqrt(weights @ self.covariance_matrix @ weights.T)
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe_ratio
        
        # 约束条件
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # 权重和为1
            {'type': 'ineq', 'fun': lambda w: w}  # 权重非负
        ]
        
        # 添加自定义约束
        for constraint in self.constraints:
            if constraint['type'] == 'max_weight':
                idx = self.expected_returns.index.get_loc(constraint['symbol'])
                constraints.append({
                    'type': 'ineq',
                    'fun': lambda w, i=idx, max_w=constraint['value']: max_w - w[i]
                })
        
        # 初始权重（等权重）
        initial_weights = np.ones(n) / n
        
        # 边界条件
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            logger.warning(f"Optimization failed: {result.message}")
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def optimize_min_variance(self) -> pd.Series:
        """最小化方差。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            return weights @ self.covariance_matrix @ weights.T
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'ineq', 'fun': lambda w: w}
        ]
        
        initial_weights = np.ones(n) / n
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def optimize_risk_parity(self) -> pd.Series:
        """风险平价优化。"""
        n = len(self.expected_returns)
        
        def objective(weights):
            # 计算风险贡献
            portfolio_std = np.sqrt(weights @ self.covariance_matrix @ weights.T)
            risk_contributions = (weights * (self.covariance_matrix @ weights)) / portfolio_std
            
            # 风险贡献的方差（目标是让所有风险贡献相等）
            return np.var(risk_contributions)
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'ineq', 'fun': lambda w: w}
        ]
        
        initial_weights = np.ones(n) / n
        bounds = tuple((0, 1) for _ in range(n))
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.weights = pd.Series(result.x, index=self.expected_returns.index)
        else:
            self.weights = pd.Series(initial_weights, index=self.expected_returns.index)
        
        return self.weights
    
    def get_weights(self) -> pd.Series:
        """获取优化后的权重。"""
        return self.weights


class SignalGenerator:
    """信号生成器。"""
    
    def __init__(self, multi_factor_model: MultiFactorModel):
        self.model = multi_factor_model
    
    def generate_signals(
        self,
        factors: pd.DataFrame,
        top_n: Optional[int] = None,
        long_only: bool = True
    ) -> pd.Series:
        """生成交易信号。"""
        # 预测收益
        predictions = self.model.predict(factors)
        
        # 排序
        sorted_predictions = predictions.sort_values(ascending=False)
        
        if top_n is not None:
            # 只选择前N个
            selected = sorted_predictions.head(top_n)
            signals = pd.Series(0, index=factors.index)
            signals.loc[selected.index] = selected.values
        else:
            signals = predictions
        
        # 如果只做多
        if long_only:
            signals[signals < 0] = 0
        
        return signals
    
    def generate_position_weights(
        self,
        factors: pd.DataFrame,
        top_n: int = 50,
        long_only: bool = True
    ) -> pd.Series:
        """生成持仓权重。"""
        predictions = self.model.predict(factors)
        
        if long_only:
            # 只选择正预测的股票
            positive_predictions = predictions[predictions > 0]
            sorted_predictions = positive_predictions.sort_values(ascending=False).head(top_n)
        else:
            sorted_predictions = predictions.sort_values(ascending=False).head(top_n)
        
        # 归一化权重
        total = sorted_predictions.abs().sum()
        if total > 0:
            weights = sorted_predictions.abs() / total
        else:
            weights = pd.Series(0, index=sorted_predictions.index)
        
        return weights


# 示例用法
if __name__ == "__main__":
    from src.data.data_providers import data_manager
    from src.factors.factor_engine import factor_engine
    
    # 获取股票数据
    data = data_manager.get_price_data("000001", "20230101", "20231231")
    
    # 计算因子
    factors = factor_engine.compute_all_factors(data)
    
    # 计算未来收益（作为标签）
    returns = data['close'].pct_change().shift(-1).dropna()
    
    # 对齐数据
    aligned_data = pd.concat([factors, returns], axis=1).dropna()
    factors_aligned = aligned_data.iloc[:, :-1]
    returns_aligned = aligned_data.iloc[:, -1]
    
    # 创建多因子模型
    model = MultiFactorModel(factors_aligned, returns_aligned, method=FactorCombinationMethod.IC_WEIGHTED)
    model.fit()
    
    print("因子权重:")
    print(model.get_factor_weights().sort_values(ascending=False))
    
    # 评估模型
    train_size = int(len(factors_aligned) * 0.8)
    train_factors = factors_aligned.iloc[:train_size]
    train_returns = returns_aligned.iloc[:train_size]
    test_factors = factors_aligned.iloc[train_size:]
    test_returns = returns_aligned.iloc[train_size:]
    
    model2 = MultiFactorModel(train_factors, train_returns)
    model2.fit()
    
    metrics = model2.evaluate(test_factors, test_returns)
    print(f"\n模型评估结果:")
    print(f"IC: {metrics.get('ic', 0):.4f}")
    print(f"IR: {metrics.get('ir', 0):.4f}")
    print(f"R2: {metrics.get('r2', 0):.4f}")
    
    # 生成信号
    signal_generator = SignalGenerator(model2)
    signals = signal_generator.generate_signals(test_factors, top_n=10)
    print(f"\n生成的信号数量: {len(signals[signals != 0])}")