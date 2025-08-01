# Makefile for MCP Server Development and Testing
#
# Copyright (c) 2025 Siarhei Skuratovich
# Licensed under the MIT License - see LICENSE file for details

.PHONY: help test test-verbose test-coverage install-dev lint format clean check

# Default target
help:
	@echo "Available targets:"
	@echo "  test          - Run all tests"
	@echo "  test-verbose  - Run tests with verbose output"
	@echo "  test-coverage - Run tests with coverage reporting"
	@echo "  install-dev   - Install development dependencies"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code with ruff"
	@echo "  clean         - Clean up generated files"
	@echo "  check         - Run all checks (lint + test)"

# Install development dependencies
install-dev:
	@echo "📦 Installing development dependencies..."
	uv sync --dev

# Run tests
test:
	@echo "🧪 Running tests..."
	uv run pytest tests/ -v

# Run tests with verbose output
test-verbose:
	@echo "🧪 Running tests (verbose)..."
	uv run pytest tests/ -v --tb=long

# Run tests with coverage
test-coverage:
	@echo "📊 Running tests with coverage..."
	uv run pytest tests/ --cov=gitlab_analyzer --cov-report=term-missing --cov-report=html:htmlcov

# Run linting
lint:
	@echo "🔍 Running linting checks..."
	uv run ruff check src/ tests/
	uv run mypy src/

# Format code
format:
	@echo "✨ Formatting code..."
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

# Clean up generated files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run all checks
check: lint test
	@echo "✅ All checks completed!"

# Quick test run (for development)
test-quick:
	@echo "⚡ Running quick tests..."
	uv run pytest tests/ -x --tb=short

# Test specific file
test-file:
	@echo "🎯 Testing specific file: $(FILE)"
	uv run pytest $(FILE) -v

# Run tests in parallel
test-parallel:
	@echo "🚀 Running tests in parallel..."
	uv run pytest tests/ -n auto
