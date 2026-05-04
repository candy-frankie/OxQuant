# OxQuant - Next-Generation AI Quantitative Trading Platform

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange)](LICENSE)

## 🚀 Overview
OxQuant is a cutting-edge AI-powered quantitative trading platform that combines traditional quantitative finance with modern machine learning techniques. The platform enables systematic trading strategy development, backtesting, risk management, and live trading across multiple asset classes.

## ✨ Features
- **AI-Driven Strategy Development**: Leverage LLMs for strategy ideation and code generation
- **Multi-Asset Support**: Equities, Futures, Options, Crypto, Forex
- **High-Performance Backtesting**: Comprehensive backtesting engine with Walk Forward Analysis
- **Risk Management Suite**: Advanced portfolio optimization, position limits, and drawdown control
- **RESTful API**: Complete CRUD APIs for strategies, portfolios, and backtesting
- **Live Trading Integration**: Connect to major brokers and exchanges
- **Research Environment**: Jupyter notebooks with pre-built templates
- **Collaboration Tools**: Team workflow management and version control

## 📊 Core Engine Enhancements

### Order Management
- Order status tracking (PENDING, FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED)
- Automatic unique order ID generation
- Real-time remaining quantity calculation

### Position Management
- Asset class categorization
- Direction tracking (LONG/SHORT/FLAT)
- Unrealized P&L calculation with percentage metrics

### Portfolio Management
- Initial capital tracking
- Total return calculation
- Risk exposure metrics
- Multi-position management

### Risk Management
- Position size limits
- Portfolio concentration limits
- Maximum drawdown protection
- Daily loss limits

### Strategy Framework
- Signal type management (LONG/SHORT/FLAT/EXIT)
- Strategy context management
- Signal filtering mechanism
- Performance metrics calculation

## 🏗️ Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     OxQuant Platform                        │
├─────────────────────────────────────────────────────────────┤
│  Frontend Layer          │  API Gateway                    │
│  • Web Dashboard         │  • REST/WebSocket APIs          │
│  • Strategy Studio       │  • Authentication               │
│  • Research Notebooks    │  • Rate Limiting                │
├─────────────────────────────────────────────────────────────┤
│  Core Engine Layer       │  Data Layer                     │
│  • Strategy Engine       │  • Market Data Pipeline         │
│  • Backtesting Engine    │  • Feature Store                │
│  • Risk Engine           │  • Model Registry               │
│  • Execution Engine      │  • Results Database             │
├─────────────────────────────────────────────────────────────┤
│  AI/ML Layer             │  Infrastructure Layer           │
│  • LLM Integration       │  • Container Orchestration      │
│  • Feature Engineering   │  • Monitoring & Alerting        │
│  • Model Training        │  • CI/CD Pipeline               │
│  • Model Serving         │  • Security & Compliance        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- (可选) Docker & Docker Compose
- Git

### 一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/candy-frankie/OxQuant.git
cd OxQuant

# 安装依赖
./start.sh --install

# 本地启动API服务
./start.sh --local
```

**Windows用户：**
```cmd
start.bat --install
start.bat --local
```

### 部署方式对比

| 方式 | 命令 | 说明 |
|------|------|------|
| 本地启动 | `./start.sh --local` | 最简单，直接运行（推荐） |
| Docker简化版 | `./start.sh --docker` | 轻量容器，SQLite数据库 |
| Docker完整版 | `./start.sh --docker-full` | 完整服务，PostgreSQL+Redis |
| Jupyter | `./start.sh --jupyter` | 启动研究环境 |
| 运行测试 | `./start.sh --test` | 执行测试用例 |

### 手动安装

```bash
# 安装依赖
pip install -r requirements.slim.txt

# 设置环境变量
export ENVIRONMENT=development
export DATABASE_URL=sqlite:///./data/oxquant.db

# 启动API服务
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Access Services
- **API Documentation**: http://localhost:8000/docs
- **Jupyter Notebooks**: http://localhost:8888 (password: oxquant)
- **PostgreSQL (完整版)**: localhost:5432
- **Redis (完整版)**: localhost:6379

## 📁 Project Structure
```
oxquant/
├── docs/                    # Documentation
├── src/                    # Source code
│   ├── api/               # FastAPI backend
│   │   ├── routers/       # API endpoints
│   │   │   ├── auth.py    # Authentication routes
│   │   │   ├── backtesting.py  # Backtesting routes
│   │   │   ├── portfolio.py    # Portfolio management
│   │   │   ├── data.py         # Market data routes
│   │   │   └── strategies.py   # Strategy management
│   │   ├── schemas/       # Pydantic models
│   │   ├── utils/         # Utility functions
│   │   └── main.py        # Application entry
│   ├── core/              # Core trading engine
│   │   ├── engine.py      # Order/Position/Portfolio/Strategy classes
│   │   ├── backtesting.py # Backtest engine and Walk Forward analyzer
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # Database connections
│   │   └── models.py      # SQLAlchemy models
│   ├── strategies/        # Trading strategies
│   │   └── examples.py    # Strategy implementations
│   └── data/              # Data pipelines
├── notebooks/             # Research notebooks
├── tests/                 # Test suite
├── deployment/            # Docker, Kubernetes configs
└── tools/                 # Development utilities
```

## 🛠️ Technology Stack
- **Backend**: Python 3.11+, FastAPI, PostgreSQL, Redis
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **Data**: Dask, Polars, TimescaleDB
- **ML**: PyTorch, Scikit-learn, XGBoost, LangChain
- **Infra**: Docker, Kubernetes, Terraform, Prometheus
- **Brokers**: Interactive Brokers, Alpaca, Binance, etc.

## 📈 Available Strategies

| Strategy | Description | Parameters |
|----------|-------------|------------|
| `ma_crossover` | Moving Average Crossover | short_window, long_window |
| `mean_reversion` | Bollinger Bands Mean Reversion | window, num_std |
| `macd` | MACD Crossover | fast_period, slow_period, signal_period |
| `rsi` | RSI Overbought/Oversold | window, oversold, overbought |
| `atr_exit` | ATR Trailing Stop | atr_window, atr_multiplier |

### Example: Run Multiple Strategies

```python
from src.strategies.examples import (
    MovingAverageCrossover,
    MeanReversion,
    MACDStrategy,
    RSIStrategy,
    ATRExitStrategy,
    create_strategy
)
import pandas as pd
import numpy as np

# Generate sample data
np.random.seed(42)
dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
data = pd.DataFrame({'close': prices}, index=dates)

# Test all strategies
strategies = [
    MovingAverageCrossover(10, 30),
    MeanReversion(20, 2.0),
    MACDStrategy(12, 26, 9),
    RSIStrategy(14, 30, 70),
    ATRExitStrategy(14, 1.5)
]

for strategy in strategies:
    result = strategy.generate_signals(data)
    print(f"\n{strategy.name}:")
    print(f"  Total Return: {result.metrics['total_return']:.2%}")
    print(f"  Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {result.metrics['max_drawdown']:.2%}")
    print(f"  Win Rate: {result.metrics['win_rate']:.1%}")
    print(f"  Total Trades: {result.metrics['total_trades']}")
```

## 🌐 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/token` - Get access token
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Strategies
- `GET /api/v1/strategies` - List strategies
- `POST /api/v1/strategies` - Create strategy
- `GET /api/v1/strategies/{id}` - Get strategy
- `PUT /api/v1/strategies/{id}` - Update strategy
- `DELETE /api/v1/strategies/{id}` - Delete strategy

### Backtesting
- `POST /api/v1/backtesting/run` - Run backtest
- `GET /api/v1/backtesting/results` - List results
- `POST /api/v1/backtesting/optimize` - Optimize parameters
- `POST /api/v1/backtesting/walkforward` - Walk Forward Analysis

### Portfolio
- `GET /api/v1/portfolio` - List portfolios
- `POST /api/v1/portfolio` - Create portfolio
- `GET /api/v1/portfolio/{id}` - Get portfolio
- `GET /api/v1/portfolio/{id}/positions` - Get positions
- `GET /api/v1/portfolio/{id}/trades` - Get trades

### Market Data
- `GET /api/v1/data/symbols` - Get available symbols
- `GET /api/v1/data/prices/{symbol}` - Get price history
- `GET /api/v1/data/prices/{symbol}/latest` - Get latest price
- `GET /api/v1/data/market/indices` - Get market indices
- `GET /api/v1/data/market/news` - Get market news

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
isort src/
flake8 src/
```

### Database Migrations
```bash
# Initialize database
python -c "from src.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

## 🤝 Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 📞 Support
- **Issues**: [GitHub Issues](https://github.com/candy-frankie/OxQuant/issues)
- **Email**: 644743502@qq.com

## 🚀 Roadmap
- [x] Phase 1: Core architecture and basic backtesting
- [x] Phase 1.5: API development and strategy library expansion
- [ ] Phase 2: AI integration and strategy generation
- [ ] Phase 3: Multi-broker execution and risk management
- [ ] Phase 4: Enterprise features and scaling

## 📊 Performance Metrics

The backtesting engine calculates the following metrics:

| Metric | Description |
|--------|-------------|
| `total_return` | Total portfolio return |
| `annual_return` | Annualized return |
| `cagr` | Compound annual growth rate |
| `volatility` | Annualized volatility |
| `sharpe_ratio` | Risk-adjusted return (with risk-free rate) |
| `sortino_ratio` | Downside risk-adjusted return |
| `calmar_ratio` | Return-to-max-drawdown ratio |
| `max_drawdown` | Maximum peak-to-trough decline |
| `win_rate` | Percentage of profitable trades |
| `profit_factor` | Gross profits / gross losses |
| `expectancy` | Expected value per trade |
| `risk_reward_ratio` | Average win / average loss |
| `avg_trade_duration_days` | Average trade holding period |

## 📈 A股市场交易完整链路

OxQuant提供完整的A股交易链路，从数据获取到实盘交易：

```
数据获取 → 因子挖掘 → 多因子模型 → 策略开发 → 回测分析 → 模拟交易 → 实盘交易 → 风控监控
     │           │            │            │            │            │            │            │
  AKShare    QLib思路    IC加权      策略基类    A股专用     实时模拟    同花顺/QMT   VaR/CVaR
  Tushare    12+因子     回归方法    信号生成    交易规则    历史回放    券商接口    风险告警
```

### 1. 数据获取

支持AKShare和Tushare两种数据源：

```python
from src.data.data_providers import data_manager, DataProviderType

# 获取股票价格数据
data = data_manager.get_price_data(
    symbol="000001",
    start_date="20230101",
    end_date="20231231",
    provider=DataProviderType.AKSHARE
)

# 获取指数成分股
universe = data_manager.get_universe("000300")  # 沪深300
```

### 2. 因子挖掘（基于QLib框架）

```python
from src.factors.factor_engine import factor_engine, FactorAnalyzer

# 计算所有因子
factors = factor_engine.compute_all_factors(data)

# 因子分析
analyzer = FactorAnalyzer()
ic = analyzer.calculate_ic(factors['momentum_20'], data['close'].pct_change().shift(-1))
ir = analyzer.calculate_ic_ir(factors['momentum_20'], data['close'].pct_change().shift(-1))

print(f"IC: {ic:.4f}, IR: {ir:.4f}")
```

**支持的因子类型：**
| 因子名称 | 类型 | 描述 |
|----------|------|------|
| momentum_20/60/120 | 动量 | 多周期动量因子 |
| rsi_14 | 动量 | 相对强弱指数 |
| macd | 动量 | MACD指标 |
| pe/pb/ps | 估值 | 市盈率/市净率/市销率 |
| volatility_20/60 | 波动率 | 多周期波动率 |
| volume_20/turnover_20 | 流动性 | 均量和换手率 |
| beta/alpha | 风险 | 风险因子 |

### 3. 多因子模型

```python
from src.factors.multi_factor_model import (
    MultiFactorModel, FactorCombinationMethod, SignalGenerator
)

# 创建多因子模型
model = MultiFactorModel(
    factors=factors_df,
    returns=returns_series,
    method=FactorCombinationMethod.IC_WEIGHTED
)
model.fit()

# 生成交易信号
generator = SignalGenerator(model)
signals = generator.generate_signals(factors_df, top_n=10)
```

### 4. A股专用回测

```python
from src.core.a_stock_backtester import AStockBacktestEngine

backtester = AStockBacktestEngine(
    initial_capital=1000000,
    commission=0.0003,
    slippage=0.0001,
    stamp_tax=0.001
)

result = backtester.run(
    symbols=universe[:20],
    start_date="20230101",
    end_date="20231231",
    strategy_type="multi_factor"
)

print(result.metrics)
```

### 5. 模拟交易

```python
from src.trading.simulation import SimulationEngine, SimulationMode

engine = SimulationEngine(
    initial_capital=100000,
    mode=SimulationMode.REALTIME_SIM
)
engine.set_strategy(MyStrategy())
engine.start()
```

### 6. 实盘交易

```python
from src.trading.live_trading import LiveTradingEngine, BrokerType

engine = LiveTradingEngine(broker_type=BrokerType.EASYTRADER)
engine.connect(user="your_user", password="your_password")
engine.set_strategy(MyStrategy())
engine.start()
```

### 7. 风险管理

```python
from src.risk.risk_management import RiskManager

risk_manager = RiskManager(
    max_position_size_pct=0.1,
    max_drawdown_pct=0.1,
    max_daily_loss_pct=0.05
)

result = risk_manager.check_all(
    order_value=150000,
    portfolio_value=1000000
)
```

## 🔧 A股市场配置

### 交易规则
- **最小交易单位**: 100股（1手）
- **涨跌幅限制**: ±10%（ST股±5%）
- **T+1交易**: 当日买入，次日卖出
- **印花税**: 卖出时收取0.1%
- **佣金**: 双向收取，约0.03%-0.05%
- **最低佣金**: 5元/笔

### 交易时间
- **上午**: 09:30 - 11:30
- **下午**: 13:00 - 15:00
- **集合竞价**: 09:15 - 09:25