# OxQuant Development Environment

## Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)

## Quick Start

### Option 1: Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/candy-frankie/OxQuant.git
cd OxQuant

# Start all services
docker-compose up -d

# Access the services:
# - Web UI: http://localhost:8501
# - API Docs: http://localhost:8000/docs
# - JupyterLab: http://localhost:8888
```

### Option 2: Local Development
```bash
# Clone the repository
git clone https://github.com/candy-frankie/OxQuant.git
cd OxQuant

# Install Poetry if not installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Setup environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Run services
# API Server
uvicorn src.api.main:app --reload --port 8000

# Web Dashboard
streamlit run src/ui/app.py

# Celery Worker
celery -A src.core.tasks worker --loglevel=info

# Jupyter Lab
jupyter lab
```

## Project Structure
```
oxquant/
├── src/                    # Source code
│   ├── api/               # FastAPI application
│   │   ├── routers/       # API endpoints
│   │   ├── middleware/    # Custom middleware
│   │   └── dependencies/  # FastAPI dependencies
│   ├── core/              # Core trading engine
│   │   ├── engine/        # Strategy execution engine
│   │   ├── backtesting/   # Backtesting framework
│   │   ├── risk/          # Risk management
│   │   └── execution/     # Order execution
│   ├── data/              # Data pipelines
│   │   ├── pipelines/     # ETL pipelines
│   │   ├── providers/     # Data providers
│   │   └── storage/       # Data storage
│   ├── ml/                # Machine learning
│   │   ├── models/        # ML models
│   │   ├── features/      # Feature engineering
│   │   └── training/      # Model training
│   ├── strategies/        # Trading strategies
│   │   ├── base/          # Base strategy classes
│   │   ├── examples/      # Example strategies
│   │   └── registry/      # Strategy registry
│   └── ui/                # Frontend application
│       ├── components/    # React components
│       ├── pages/         # Page components
│       └── utils/         # Frontend utilities
├── notebooks/             # Research notebooks
├── tests/                 # Test suite
├── deployment/            # Deployment configurations
└── tools/                 # Development tools
```

## Development Workflow

### 1. Setting Up Development Environment
```bash
# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Check code quality
black src tests
isort src tests
flake8 src tests
mypy src
```

### 2. Creating a New Strategy
```python
# src/strategies/examples/moving_average_crossover.py
from src.strategies.base import BaseStrategy

class MovingAverageCrossover(BaseStrategy):
    """Simple moving average crossover strategy."""
    
    def __init__(self, fast_period=20, slow_period=50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        
    def calculate_features(self, data):
        data['fast_ma'] = data['close'].rolling(self.fast_period).mean()
        data['slow_ma'] = data['close'].rolling(self.slow_period).mean()
        return data
        
    def generate_signals(self, data):
        data['signal'] = 0
        data.loc[data['fast_ma'] > data['slow_ma'], 'signal'] = 1
        data.loc[data['fast_ma'] < data['slow_ma'], 'signal'] = -1
        return data
```

### 3. Backtesting a Strategy
```python
# notebooks/backtest_example.ipynb
from src.core.backtesting import BacktestEngine
from src.strategies.examples.moving_average_crossover import MovingAverageCrossover

# Initialize backtest engine
engine = BacktestEngine(
    strategy=MovingAverageCrossover(fast_period=20, slow_period=50),
    data_provider='yahoo',
    symbol='AAPL',
    start_date='2020-01-01',
    end_date='2023-12-31',
    initial_capital=100000
)

# Run backtest
results = engine.run()

# Analyze results
print(results.metrics)
results.plot()
```

### 4. API Development
```python
# src/api/routers/strategies.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.strategies.registry import StrategyRegistry

router = APIRouter(prefix="/strategies", tags=["strategies"])

class StrategyCreate(BaseModel):
    name: str
    code: str
    parameters: dict

@router.post("/")
async def create_strategy(strategy: StrategyCreate):
    """Create a new trading strategy."""
    try:
        strategy_id = StrategyRegistry.register(
            name=strategy.name,
            code=strategy.code,
            parameters=strategy.parameters
        )
        return {"strategy_id": strategy_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Testing
```bash
# Run all tests
pytest

# Run specific test module
pytest tests/core/test_backtesting.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run integration tests
pytest tests/integration/ -v
```

## Deployment

### Docker Deployment
```bash
# Build and push Docker image
docker build -t oxquant:latest .
docker tag oxquant:latest your-registry/oxquant:latest
docker push your-registry/oxquant:latest

# Deploy with Kubernetes
kubectl apply -f deployment/kubernetes/
```

### Cloud Deployment
```bash
# Deploy to AWS ECS
aws ecs create-service --cluster oxquant-cluster --service-name oxquant-api

# Deploy to Google Cloud Run
gcloud run deploy oxquant-api --source .
```

## Monitoring & Observability
- **Metrics**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger or OpenTelemetry
- **Alerting**: AlertManager

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run test suite
6. Submit a pull request

## License
Apache 2.0 - See LICENSE file for details.