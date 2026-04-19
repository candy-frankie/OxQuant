#!/usr/bin/env python3
"""
OxQuant Project Verification

Verify that the project structure and dependencies are correctly set up.
"""

import os
import sys
import importlib
from pathlib import Path


def check_directory_structure():
    """Check if all required directories exist."""
    print("Checking directory structure...")
    
    required_dirs = [
        "src",
        "src/api",
        "src/api/routers",
        "src/api/schemas",
        "src/api/utils",
        "src/core",
        "src/strategies",
        "src/data",
        "src/ml",
        "notebooks",
        "tests",
        "deployment",
        "deployment/postgres",
        "docs",
        "tools"
    ]
    
    all_good = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ (missing)")
            all_good = False
    
    return all_good


def check_required_files():
    """Check if all required files exist."""
    print("\nChecking required files...")
    
    required_files = [
        "README.md",
        "pyproject.toml",
        "docker-compose.yml",
        "Dockerfile.api",
        "Dockerfile.web",
        ".env.example",
        "setup.py",
        "requirements.txt",
        ".gitignore",
        "src/api/main.py",
        "src/core/config.py",
        "src/core/database.py",
        "src/core/models.py",
        "src/strategies/examples.py"
    ]
    
    all_good = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} (missing)")
            all_good = False
    
    return all_good


def check_python_imports():
    """Check if Python imports work."""
    print("\nChecking Python imports...")
    
    imports_to_test = [
        ("fastapi", "FastAPI"),
        ("pydantic", "BaseModel"),
        ("sqlalchemy", "create_engine"),
        ("pandas", "DataFrame"),
        ("numpy", "array"),
    ]
    
    all_good = True
    for module_name, import_name in imports_to_test:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, import_name):
                print(f"  ✓ {module_name}.{import_name}")
            else:
                print(f"  ✗ {module_name}.{import_name} (not found)")
                all_good = False
        except ImportError:
            print(f"  ✗ {module_name} (cannot import)")
            all_good = False
    
    return all_good


def check_project_imports():
    """Check if project modules can be imported."""
    print("\nChecking project imports...")
    
    project_imports = [
        "src.core.config",
        "src.core.database",
        "src.core.models",
        "src.strategies.examples",
    ]
    
    all_good = True
    for import_path in project_imports:
        try:
            importlib.import_module(import_path)
            print(f"  ✓ {import_path}")
        except ImportError as e:
            print(f"  ✗ {import_path}: {e}")
            all_good = False
    
    return all_good


def check_docker_compose():
    """Check if docker-compose.yml is valid."""
    print("\nChecking docker-compose configuration...")
    
    if not Path("docker-compose.yml").exists():
        print("  ✗ docker-compose.yml not found")
        return False
    
    try:
        import yaml
        with open("docker-compose.yml", 'r') as f:
            config = yaml.safe_load(f)
        
        required_services = ["postgres", "redis", "api"]
        services = config.get('services', {})
        
        for service in required_services:
            if service in services:
                print(f"  ✓ Service '{service}' configured")
            else:
                print(f"  ✗ Service '{service}' missing")
                return False
        
        return True
    except ImportError:
        print("  ⚠ PyYAML not installed, skipping detailed check")
        return True
    except Exception as e:
        print(f"  ✗ Error parsing docker-compose.yml: {e}")
        return False


def check_environment():
    """Check environment setup."""
    print("\nChecking environment setup...")
    
    # Check .env.example
    if Path(".env.example").exists():
        print("  ✓ .env.example exists")
        
        # Check if .env exists (optional)
        if Path(".env").exists():
            print("  ✓ .env exists (will override .env.example)")
        else:
            print("  ⚠ .env not found (create from .env.example for local development)")
    else:
        print("  ✗ .env.example missing")
        return False
    
    return True


def main():
    """Main verification function."""
    print("=" * 60)
    print("OxQuant Project Verification")
    print("=" * 60)
    
    checks = [
        ("Directory Structure", check_directory_structure),
        ("Required Files", check_required_files),
        ("Python Imports", check_python_imports),
        ("Project Imports", check_project_imports),
        ("Docker Compose", check_docker_compose),
        ("Environment", check_environment),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"  ✗ Error during check: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 60)
    print("Verification Summary:")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{check_name:30} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All checks passed! Project is ready for development.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and update with your settings")
        print("2. Run: docker-compose up -d postgres redis")
        print("3. Run: python setup.py (or poetry install)")
        print("4. Start the API: docker-compose up api")
        print("5. Access docs at: http://localhost:8000/docs")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)
    
    print("=" * 60)


if __name__ == "__main__":
    main()