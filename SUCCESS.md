# GitLab Pipeline Analyzer MCP Server - Setup Complete! 🎉

## ✅ What We've Created

A complete FastMCP server for analyzing GitLab CI/CD pipeline failures with the following features:

### 🔧 Core Components

1. **`gitlab_analyzer.py`** - Main MCP server with 5 tools:
   - `analyze_failed_pipeline(pipeline_id)` - Complete pipeline failure analysis
   - `get_pipeline_jobs(pipeline_id)` - Get all jobs for a pipeline
   - `get_job_trace(job_id)` - Get trace log for a specific job
   - `extract_log_errors(log_text)` - Extract errors/warnings from raw logs
   - `get_pipeline_status(pipeline_id)` - Get basic pipeline status

2. **Log Parser** - Intelligent error/warning extraction supporting:
   - Python errors (Error, Exception, Traceback)
   - Test failures (FAILED, AssertionError, pytest)
   - Build errors (compilation, process exits)
   - Linting errors (pylint, flake8, mypy)
   - General warnings and deprecation notices

3. **Configuration System** - Environment-based setup:
   - `GITLAB_URL` - GitLab instance URL
   - `GITLAB_TOKEN` - Personal access token
   - `GITLAB_PROJECT_ID` - Target project ID

### 📦 Virtual Environment Setup

✅ **Created with Python 3.12** (required for FastMCP 2.0)
✅ **All dependencies installed** (FastMCP 2.10.6, httpx, pydantic, python-gitlab)
✅ **Successfully tested** - Log extraction working perfectly

### 🧪 Test Results

The server successfully extracted **12 entries** from a sample CI/CD log:
- **10 Errors**: Package failures, test failures, linting errors, process exits
- **2 Warnings**: Deprecated API usage, code coverage issues

### 📁 Project Structure

```
mcp/
├── .venv/                  # Virtual environment (Python 3.12)
├── gitlab_analyzer.py      # Main MCP server ⭐
├── config.py              # Configuration management
├── test_simple.py          # Working test (no credentials needed) ✅
├── example.py              # Full usage examples
├── test_client.py          # Development test client
├── pyproject.toml          # Python project configuration
├── requirements.txt        # Dependencies
├── Makefile               # Build commands
├── setup.sh               # Automated setup script
├── .env.example           # Environment template
├── .env                   # Your environment (to be configured)
├── README.md              # Documentation
└── ARCHITECTURE.md        # Technical details
```

## 🚀 Next Steps

### 1. Configure GitLab Credentials
Edit `.env` with your GitLab details:
```bash
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your-personal-access-token
GITLAB_PROJECT_ID=your-project-id
```

### 2. Run the Server
```bash
# Activate environment and run
source .venv/bin/activate
python gitlab_analyzer.py

# Or use Makefile
make run
```

### 3. Use with AI Tools
The server provides structured JSON responses perfect for AI analysis:
```json
{
  "pipeline_id": 12345,
  "failed_jobs": [...],
  "analysis": {
    "lint": [{"level": "error", "message": "...", "line_number": 42}],
    "test": [{"level": "error", "message": "...", "context": "..."}]
  },
  "summary": {
    "total_errors": 8,
    "total_warnings": 3,
    "failed_stages": ["lint", "test"]
  }
}
```

## 🎯 Key Features for CI/CD Analysis

- **Stage-aware**: Understands lint, test, and build stages
- **Context-rich**: Provides surrounding log lines for better understanding
- **Extensible**: Easy to add new error patterns
- **AI-ready**: Structured JSON output perfect for LLM consumption
- **Fast**: Efficient pattern matching and async operations

## 💡 Usage Examples

**Basic log analysis** (works without GitLab API):
```bash
source .venv/bin/activate
python test_simple.py
```

**Full pipeline analysis** (requires GitLab credentials):
```bash
# Set EXAMPLE_PIPELINE_ID=123456 in .env
source .venv/bin/activate
python example.py
```

The MCP server is now ready to analyze GitLab CI/CD pipeline failures and provide structured error information for AI-powered analysis! 🚀
