# Database Storage Configuration

The GitLab Pipeline Analyzer MCP server now supports configurable database storage location through environment variables.

## Environment Variable

### `MCP_DATABASE_PATH`

Controls where the SQLite analysis cache database is stored.

**Default Value:** `analysis_cache.db` (in the current working directory)

**Examples:**

```bash
# Store database in a specific directory
export MCP_DATABASE_PATH="/var/lib/gitlab-analyzer/cache.db"

# Store database in user's data directory
export MCP_DATABASE_PATH="$HOME/.local/share/gitlab-analyzer/analysis_cache.db"

# Store database in temporary directory for testing
export MCP_DATABASE_PATH="/tmp/gitlab_analyzer_test.db"
```

## Usage

### With Environment Variable

```bash
# Set the database path
export MCP_DATABASE_PATH="/path/to/your/database.db"

# Start the server
uv run gitlab-analyzer
```

### With .env File

Add to your `.env` file:

```dotenv
MCP_DATABASE_PATH=/path/to/your/database.db
```

### Programmatic Usage

```python
from gitlab_analyzer.cache.mcp_cache import McpCache, get_cache_manager
import os

# Option 1: Use environment variable
os.environ['MCP_DATABASE_PATH'] = '/path/to/database.db'
cache = McpCache()

# Option 2: Pass path directly (overrides env var)
cache = McpCache(db_path='/path/to/database.db')

# Option 3: Using cache manager
cache_manager = get_cache_manager(db_path='/path/to/database.db')
```

## Benefits

1. **Flexible Storage**: Store the database in any directory
2. **Environment-Specific Configuration**: Different paths for development, testing, production
3. **Container Support**: Easily mount persistent storage in containers
4. **Backup/Migration**: Easier to manage database files with predictable locations

## Migration

The change is fully backward compatible. If `MCP_DATABASE_PATH` is not set, the system will continue to use `analysis_cache.db` in the current working directory, maintaining existing behavior.

## Use Cases

### Development

```bash
export MCP_DATABASE_PATH="./dev_cache.db"
```

### Production

```bash
export MCP_DATABASE_PATH="/var/lib/gitlab-analyzer/production_cache.db"
```

### Testing

```bash
export MCP_DATABASE_PATH="/tmp/test_cache_${TEST_ID}.db"
```

### Docker

```dockerfile
ENV MCP_DATABASE_PATH=/data/analysis_cache.db
VOLUME ["/data"]
```
