# OxQuant - Next-Generation AI Quantitative Trading Platform

## 🚀 Overview
OxQuant is a cutting-edge AI-powered quantitative trading platform that combines traditional quantitative finance with modern machine learning techniques. The platform enables systematic trading strategy development, backtesting, risk management, and live trading across multiple asset classes.

## ✨ Features
- **AI-Driven Strategy Development**: Leverage LLMs for strategy ideation and code generation
- **Multi-Asset Support**: Equities, Futures, Options, Crypto, Forex
- **High-Performance Backtesting**: GPU-accelerated simulation engine
- **Risk Management Suite**: Advanced portfolio optimization and risk metrics
- **Live Trading Integration**: Connect to major brokers and exchanges
- **Research Environment**: Jupyter notebooks with pre-built templates
- **Collaboration Tools**: Team workflow management and version control

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
│   ├── core/              # Core trading engine
│   ├── data/              # Data pipelines
│   ├── ml/                # Machine learning models
│   ├── strategies/        # Trading strategies
│   └── ui/                # React frontend
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

## 📈 Example Strategy

```python
from src.strategies.examples import MovingAverageCrossover
import pandas as pd
import numpy as np

# Generate sample data
dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
data = pd.DataFrame({'close': prices}, index=dates)

# Create and run strategy
strategy = MovingAverageCrossover(short_window=10, long_window=30)
result = strategy.generate_signals(data)

print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
```

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
- [ ] Phase 2: AI integration and strategy generation
- [ ] Phase 3: Multi-broker execution and risk management
- [ ] Phase 4: Enterprise features and scaling