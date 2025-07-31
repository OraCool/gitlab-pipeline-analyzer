#!/bin/bash

# GitLab Pipeline Analyzer MCP Server - Setup Script

set -e

echo "🚀 Setting up GitLab Pipeline Analyzer MCP Server"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "gitlab_analyzer.py" ]; then
    echo "❌ Error: Please run this script from the MCP project directory"
    exit 1
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv not found. Installing with pip instead..."
    INSTALL_CMD="pip install"
else
    echo "✅ Found uv package manager"
    INSTALL_CMD="uv pip install"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
$INSTALL_CMD -r requirements.txt

# Set up environment file
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your GitLab credentials:"
    echo "   - GITLAB_URL (e.g., https://gitlab.com)"
    echo "   - GITLAB_TOKEN (your personal access token)"
    echo "   - GITLAB_PROJECT_ID (your project ID)"
else
    echo "✅ .env file already exists"
fi

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo ""
echo "🐍 Python version: $python_version"

# Test import
echo ""
echo "🧪 Testing imports..."
python3 -c "
try:
    import httpx
    import pydantic
    print('✅ Core dependencies imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your GitLab credentials"
echo "2. Test the setup: make test"
echo "3. Run the server: make run"
echo ""
echo "For help: make help"
