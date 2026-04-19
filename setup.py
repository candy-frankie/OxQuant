#!/usr/bin/env python3
"""
OxQuant Setup Script

Installation script for the OxQuant quantitative trading platform.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check Python version."""
    if sys.version_info < (3, 11):
        print("Error: OxQuant requires Python 3.11 or higher")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def check_poetry():
    """Check if Poetry is installed."""
    try:
        subprocess.run(["poetry", "--version"], capture_output=True, check=True)
        print("✓ Poetry is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ Poetry is not installed. Installing...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "poetry", "--quiet"
            ], check=True)
            print("✓ Poetry installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("✗ Failed to install Poetry")
            return False


def install_dependencies():
    """Install project dependencies using Poetry."""
    print("\nInstalling dependencies with Poetry...")
    
    # Install main dependencies
    try:
        subprocess.run(["poetry", "install", "--no-root"], check=True)
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("✗ Failed to install dependencies")
        return False
    
    # Install development dependencies
    try:
        subprocess.run(["poetry", "install", "--no-root", "--with", "dev"], check=True)
        print("✓ Development dependencies installed")
    except subprocess.CalledProcessError:
        print("⚠ Failed to install development dependencies")
    
    return True


def setup_environment():
    """Setup environment variables."""
    print("\nSetting up environment...")
    
    env_file = Path(".env")
    if not env_file.exists():
        env_content = """# OxQuant Environment Configuration
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oxquant

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# API Keys (optional)
# OPENAI_API_KEY=your-openai-api-key
# ANTHROPIC_API_KEY=your-anthropic-api-key

# Trading
DEFAULT_INITIAL_CAPITAL=100000
DEFAULT_COMMISSION_RATE=0.001
"""
        env_file.write_text(env_content)
        print("✓ Created .env file with default configuration")
    else:
        print("✓ .env file already exists")
    
    # Create data directories
    directories = ["data", "cache", "logs", "backtest_results"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created {directory}/ directory")


def setup_database():
    """Initialize database."""
    print("\nSetting up database...")
    
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        print("✓ Docker is available")
        
        # Start database services
        print("Starting database services with Docker Compose...")
        subprocess.run(["docker-compose", "up", "-d", "postgres", "redis"], check=True)
        print("✓ Database services started")
        
        # Wait for services to be ready
        import time
        print("Waiting for services to be ready...")
        time.sleep(10)
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ Docker not available. Please ensure PostgreSQL and Redis are running manually.")
        print("  PostgreSQL: postgresql://postgres:postgres@localhost:5432/oxquant")
        print("  Redis: redis://localhost:6379/0")


def run_migrations():
    """Run database migrations."""
    print("\nRunning database migrations...")
    
    try:
        # Import after dependencies are installed
        sys.path.insert(0, str(Path.cwd()))
        
        from src.core.database import init_db
        import asyncio
        
        asyncio.run(init_db())
        print("✓ Database migrations completed")
    except Exception as e:
        print(f"⚠ Failed to run migrations: {e}")
        print("  You can run migrations manually later with: python -c 'from src.core.database import init_db; import asyncio; asyncio.run(init_db())'")


def main():
    """Main setup function."""
    print("=" * 60)
    print("OxQuant Setup")
    print("=" * 60)
    
    # Check Python version
    check_python_version()
    
    # Check and install Poetry
    if not check_poetry():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Setup database
    setup_database()
    
    # Run migrations
    run_migrations()
    
    print("\n" + "=" * 60)
    print("Setup completed successfully! 🎉")
    print("\nNext steps:")
    print("1. Review and update the .env file with your API keys")
    print("2. Start the API server: docker-compose up api")
    print("3. Access the API documentation: http://localhost:8000/docs")
    print("4. Start Jupyter notebooks: docker-compose up jupyter")
    print("=" * 60)


if __name__ == "__main__":
    main()