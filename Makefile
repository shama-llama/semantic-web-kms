# Makefile for local development checks
# Run with: make <target>

.PHONY: help all backend frontend security lint test build clean

# Default target
help:
	@echo "Available targets:"
	@echo "  all        - Run all checks (lint, test, build, security)"
	@echo "  backend    - Run backend checks only"
	@echo "  frontend   - Run frontend checks only"
	@echo "  security   - Run security checks only"
	@echo "  lint       - Run linting checks only"
	@echo "  test       - Run tests only"
	@echo "  build      - Run build checks only"
	@echo "  clean      - Clean build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make all          # Run everything"
	@echo "  make backend      # Quick backend check"
	@echo "  make frontend     # Quick frontend check"
	@echo "  make security     # Security audit"

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
	@echo "All linting passed!"

# Tests only
test:
	@echo "\033[1;36mRunning tests...\033[0m"
	@echo "Backend tests..."
	@if [ -d ".venv" ]; then source .venv/bin/activate; fi
	@pytest --cov=app --cov-report=term-missing
	@echo "Frontend tests..."
	@cd portal && npm run test:run
	@echo "\033[0;32mAll tests passed!\033[0m"

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