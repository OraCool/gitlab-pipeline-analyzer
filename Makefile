.PHONY: install install-dev test clean run help

# Default target
help:
	@echo "GitLab Pipeline Analyzer MCP Server"
	@echo "===================================="
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test         - Run test client"
	@echo "  run          - Run the MCP server"
	@echo "  clean        - Clean up temporary files"
	@echo "  setup        - Initial setup (copy .env.example to .env)"
	@echo ""
	@echo "Before running:"
	@echo "1. Run 'make setup' to create .env file"
	@echo "2. Edit .env with your GitLab credentials"
	@echo "3. Run 'make install' to install dependencies"
	@echo "4. Run 'make run' to start the server"

# Create virtual environment and install dependencies
install:
	@echo "Creating virtual environment with Python 3.12..."
	uv venv --python 3.12
	@echo "Installing dependencies..."
	source .venv/bin/activate && uv pip install -r requirements.txt

# Install development dependencies
install-dev: install
	@echo "Installing development dependencies..."
	source .venv/bin/activate && uv pip install -e ".[dev]"

# Set up environment
setup:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp .env.example .env; \
		echo "Please edit .env with your GitLab credentials"; \
	else \
		echo ".env file already exists"; \
	fi

# Run the MCP server
run:
	@echo "Starting GitLab Pipeline Analyzer MCP Server..."
	source .venv/bin/activate && python gitlab_analyzer.py

# Run the FastMCP CLI version
run-cli:
	@echo "Starting server with FastMCP CLI..."
	source .venv/bin/activate && fastmcp run gitlab_analyzer.py:mcp

# Run test client
test:
	@echo "Running test client..."
	source .venv/bin/activate && python test_client.py

# Clean up
clean:
	@echo "Cleaning up..."
	fd -tf "\.pyc$$" -x rm {}
	fd -td "__pycache__" -x rm -rf {}
	fd -td "\.egg-info$$" -x rm -rf {}
	rm -rf build/
	rm -rf dist/

# Check environment variables
check-env:
	@echo "Checking environment configuration..."
	@if [ -z "$$GITLAB_TOKEN" ]; then \
		echo "❌ GITLAB_TOKEN not set"; \
	else \
		echo "✅ GITLAB_TOKEN is set"; \
	fi
	@if [ -z "$$GITLAB_PROJECT_ID" ]; then \
		echo "❌ GITLAB_PROJECT_ID not set"; \
	else \
		echo "✅ GITLAB_PROJECT_ID is set"; \
	fi
	@if [ -z "$$GITLAB_URL" ]; then \
		echo "ℹ️  GITLAB_URL not set (will use default: https://gitlab.com)"; \
	else \
		echo "✅ GITLAB_URL is set to: $$GITLAB_URL"; \
	fi
