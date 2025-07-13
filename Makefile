# Makefile for Semantic Web Knowledge Management System
# Group One, CoSc 6232 (Spring 2025)
# Run with: make <target>

.PHONY: help all backend frontend security lint test build clean install dev format type-check coverage audit

# Default target
help:
	@echo "Semantic Web Knowledge Management System - Development Commands"
	@echo "=============================================================="
	@echo ""
	@echo "Available targets:"
	@echo "  all        - Run all checks (lint, test, build, security)"
	@echo "  backend    - Run backend checks only"
	@echo "  frontend   - Run frontend checks only"
	@echo "  security   - Run security checks only"
	@echo "  lint       - Run linting checks only"
	@echo "  test       - Run tests only"
	@echo "  build      - Run build checks only"
	@echo "  clean      - Clean build artifacts"
	@echo "  install    - Install all dependencies"
	@echo "  dev        - Quick development check (backend only, fast)"
	@echo "  format     - Format code with black and isort"
	@echo "  type-check - Run type checking with mypy and pyright"
	@echo "  coverage   - Run tests with coverage report"
	@echo "  audit      - Run security audit"
	@echo ""
	@echo "Examples:"
	@echo "  make all          # Run everything"
	@echo "  make backend      # Quick backend check"
	@echo "  make frontend     # Quick frontend check"
	@echo "  make security     # Security audit"
	@echo "  make format       # Format code"
	@echo "  make type-check   # Type checking"

# Run all checks
all:
	@echo "\033[1;36mRunning all checks...\033[0m"
	./scripts/local-checks.sh

# Backend checks
backend:
	@echo "\033[1;36mRunning backend checks...\033[0m"
	./scripts/backend-checks.sh

# Frontend checks
frontend:
	@echo "\033[1;36mRunning frontend checks...\033[0m"
	./scripts/frontend-checks.sh

# Security checks
security:
	@echo "\033[1;36mRunning security checks...\033[0m"
	./scripts/security-checks.sh

# Install all dependencies
install:
	@echo "\033[1;36mInstalling dependencies...\033[0m"
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	@pip install -e .
	@pip install -e ".[dev]"
	@echo "Installing frontend dependencies..."
	@cd portal && npm ci
	@echo "\033[0;32mAll dependencies installed!\033[0m"

# Linting only
lint:
	@echo "\033[1;36mRunning linting checks...\033[0m"
	@echo "Backend linting..."
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	@pip install flake8 mypy black isort pydocstyle vulture pyright > /dev/null 2>&1 || true
	@flake8 app/
	@mypy app/
	@black --check app/
	@isort --check-only app/
	@echo "Frontend linting..."
	@cd portal && npm run lint
	@echo "\033[0;32mAll linting passed!\033[0m"

# Format code
format:
	@echo "\033[1;36mFormatting code...\033[0m"
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	@black app/
	@isort app/
	@echo "\033[0;32mCode formatted!\033[0m"

# Type checking
type-check:
	@echo "\033[1;36mRunning type checks...\033[0m"
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	@mypy app/
	@pyright app/
	@echo "Frontend type checking..."
	@cd portal && npx tsc --noEmit
	@echo "\033[0;32mAll type checks passed!\033[0m"

# Tests only
test:
	@echo "\033[1;36mRunning tests...\033[0m"
	@echo "Backend tests..."
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	PYTHONPATH=. pytest --maxfail=3 --disable-warnings -q
	@echo "Frontend tests..."
	@cd portal && npm run test:run
	@echo "\033[0;32mAll tests passed!\033[0m"

# Coverage report
coverage:
	@echo "\033[1;36mRunning tests with coverage...\033[0m"
	@echo "Backend coverage..."
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	PYTHONPATH=. pytest --cov=app --cov-report=term-missing --cov-report=html
	@echo "Frontend coverage..."
	@cd portal && npm run test:coverage
	@echo "\033[0;32mCoverage reports generated!\033[0m"

# Security audit
audit:
	@echo "\033[1;36mRunning security audit...\033[0m"
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	@pip install pip-audit bandit > /dev/null 2>&1 || true
	@pip-audit
	@bandit -r app/
	@echo "Frontend security audit..."
	@cd portal && npm audit
	@echo "\033[0;32mSecurity audit complete!\033[0m"

# Build only
build:
	@echo "\033[1;36mRunning build checks...\033[0m"
	@echo "Backend build..."
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	@pip install build > /dev/null 2>&1 || true
	@python -m build
	@echo "Frontend build..."
	@cd portal && npm run build
	@echo "\033[0;32mAll builds successful!\033[0m"

# Clean build artifacts
clean:
	@echo "\033[1;36mCleaning build artifacts...\033[0m"
	@rm -rf dist/
	@rm -rf build/
	@rm -rf *.egg-info/
	@rm -rf portal/dist/
	@rm -rf portal/coverage/
	@rm -rf .coverage
	@rm -rf .pytest_cache/
	@rm -rf .mypy_cache/
	@rm -rf htmlcov/
	@rm -rf .pyright_cache/
	@echo "\033[0;32mCleaned!\033[0m"

# Quick development check (backend only, fast)
dev:
	@echo "\033[1;36mQuick development check...\033[0m"
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	@black --check app/
	@isort --check-only app/
	@flake8 app/
	@pytest --tb=short
	@echo "\033[0;32mQuick check passed!\033[0m" 