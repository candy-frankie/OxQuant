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
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/candy-frankie/OxQuant.git
   cd OxQuant
   ```

2. **Setup with Docker (Recommended)**
   ```bash
   # Copy environment file
   cp .env.example .env
   
   # Start database services
   docker-compose up -d postgres redis
   
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Start API server
   docker-compose up api
   ```

3. **Or setup locally**
   ```bash
   # Run setup script
   python setup.py
   
   # Start services
   docker-compose up -d
   ```

### Access Services
- **API Documentation**: http://localhost:8000/docs
- **Jupyter Notebooks**: http://localhost:8888 (password: oxquant)
- **PostgreSQL**: localhost:5432 (user: postgres, password: postgres)
- **Redis**: localhost:6379

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