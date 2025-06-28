.PHONY: help install install-dev test lint format clean run scraper api web check infrastructure-up infrastructure-down

# Default target
help:
	@echo "Available commands:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  test             Run test suite"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black and ruff"
	@echo "  clean            Clean up build artifacts and cache"
	@echo "  run              Start the complete system"
	@echo "  scraper          Run scraper only"
	@echo "  api              Run API server only"
	@echo "  web              Run web interface only"
	@echo "  check            Run system health check"
	@echo "  infrastructure-up    Start Docker infrastructure"
	@echo "  infrastructure-down  Stop Docker infrastructure"

# Installation
install:
	@echo "Installing production dependencies..."
	pip install -e .

install-dev:
	@echo "Installing development dependencies..."
	pip install -e ".[dev]"
	pip install -r requirements.txt

# Testing
test:
	@echo "Running test suite..."
	pytest tests/ -v --cov=src/n8n_scraper --cov-report=html --cov-report=term

# Code quality
lint:
	@echo "Running linting checks..."
	ruff check src/ tests/
	mypy src/

format:
	@echo "Formatting code..."
	ruff format src/ tests/
	black src/ tests/
	ruff check --fix src/ tests/

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/

# Application commands
run:
	@echo "Starting complete system..."
	python src/scripts/start_system.py

scraper:
	@echo "Running scraper..."
	python src/scripts/run_scraper.py

api:
	@echo "Starting API server..."
	python src/scripts/start_system.py --api-only

web:
	@echo "Starting web interface..."
	python src/scripts/start_system.py --web-only

check:
	@echo "Running system check..."
	python src/tools/system_check.py

# Infrastructure
infrastructure-up:
	@echo "Starting Docker infrastructure..."
	docker-compose up -d

infrastructure-down:
	@echo "Stopping Docker infrastructure..."
	docker-compose down

# Development workflow
dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make help' to see available commands."

dev-check: lint test
	@echo "Development checks passed!"