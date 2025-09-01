# Database Debug Features

## Overview

This document describes the comprehensive debug features added to the GitLab Pipeline Analyzer MCP server to help diagnose database access issues during startup.

## Enhanced Debug Features

### 1. Database Initialization Debug (`McpCache._init_database`)

The database initialization now provides detailed debug information including:

#### Pre-Connection Diagnostics

- Database path resolution and type checking
- Parent directory existence and permissions
- File permissions (for existing databases)
- Environment variable values
- Current working directory
- Database file size information

#### Connection Diagnostics

- SQLite connection attempt logging
- Schema creation progress tracking
- Migration status reporting

#### Comprehensive Error Handling

- **SQLite OperationalError**: Usually indicates permission or disk space issues
- **SQLite DatabaseError**: Indicates corruption or version incompatibility
- **PermissionError**: Detailed file/directory permission analysis
- **OSError**: Filesystem issues or path problems
- **General Exceptions**: Full traceback with error type classification

#### Example Debug Output

```
🔧 [DEBUG] Initializing database at: /tmp/test.db
🔧 [DEBUG] Database path type: <class 'pathlib.PosixPath'>
🔧 [DEBUG] Database path absolute: /private/tmp/test.db
🔧 [DEBUG] Database path exists: False
🔧 [DEBUG] Parent directory: /tmp
🔧 [DEBUG] Parent directory exists: True
🔧 [DEBUG] Parent directory writable: True
🔧 [DEBUG] MCP_DATABASE_PATH env var: /tmp/test.db
🔧 [DEBUG] Current working directory: /Users/user/project
🔧 [DEBUG] Attempting to connect to SQLite database...
✅ [DEBUG] Successfully connected to SQLite database
🔧 [DEBUG] Creating database schema...
✅ [DEBUG] Database schema created/verified successfully
✅ [DEBUG] Database initialization completed at: /tmp/test.db
```

### 2. Server Startup Debug

Enhanced startup functions in all server types provide:

#### Environment Debug

- All relevant environment variables (with token masking)
- Database path configuration
- Server configuration parameters

#### Cache Manager Initialization

- Global cache instance creation tracking
- Initialization success/failure reporting
- Error propagation with full context

### 3. Enhanced Health Check (`McpCache.check_health`)

The health check now provides comprehensive diagnostics:

#### File System Analysis

- Database file existence and permissions
- Parent directory status and writability
- Detailed file permission modes and ownership
- Disk space analysis with usage percentages

#### Database Schema Validation

- Table existence and record counts
- Column count and structure verification
- Orphaned record detection across tables

#### Environment Information

- Python version and environment details
- Working directory and path information
- Configuration variable status

#### Health Recommendations

- Automated recommendations based on health status
- Specific actions for common issues
- Priority-based issue classification

#### Example Health Output

```json
{
  "status": "healthy",
  "database_connectivity": "ok",
  "database_path": "/private/tmp/test.db",
  "file_system": {
    "parent_directory_exists": true,
    "parent_directory_writable": true,
    "file_permissions": {
      "readable": true,
      "writable": true,
      "size_bytes": 69632,
      "size_mb": 0.07,
      "mode": "-rw-r--r--",
      "owner_uid": 501,
      "current_uid": 501
    },
    "disk_space": {
      "total_mb": 476802.04,
      "free_mb": 270202.18,
      "used_mb": 206599.86,
      "free_percent": 56.7
    }
  },
  "orphaned_records": {
    "orphaned_errors": 0,
    "orphaned_files": 0,
    "orphaned_traces": 0,
    "total_orphaned": 0
  },
  "recommendations": ["Cache system is healthy - no action required"]
}
```

## Common Issues and Debug Information

### Permission Errors

When database access fails due to permissions:

```
❌ [ERROR] Permission Error during database initialization:
❌ [ERROR] Error message: [Errno 13] Permission denied: '/path/to/db'
❌ [ERROR] Database path: /path/to/db
❌ [ERROR] Check file/directory permissions for the database path
🔧 [DEBUG] Current file permissions: -rw-r--r--
🔧 [DEBUG] File owner UID: 0
🔧 [DEBUG] Current process UID: 501
```

### Disk Space Issues

When disk space is insufficient:

```
❌ [ERROR] SQLite Operational Error during database initialization:
❌ [ERROR] Error message: database or disk is full
❌ [ERROR] This usually indicates permission issues or disk space problems
🔧 [DEBUG] Available disk space: 0.05 MB
```

### Path Issues

When database path is invalid:

```
❌ [ERROR] OS Error during database initialization:
❌ [ERROR] Error message: [Errno 2] No such file or directory
🔧 [DEBUG] Parent directory: /nonexistent
🔧 [DEBUG] Parent directory exists: False
```

## Testing Debug Features

### Basic Database Test

```python
import os
from src.gitlab_analyzer.cache.mcp_cache import get_cache_manager

os.environ['MCP_DATABASE_PATH'] = '/tmp/test_debug.db'
cache = get_cache_manager()
```

### Health Check Test

```python
import asyncio
health = await cache.check_health()
print(health)
```

### Permission Error Test

```python
os.environ['MCP_DATABASE_PATH'] = '/root/protected.db'
# Will show detailed permission error debug info
```

## Using Debug Information

1. **Startup Issues**: Check the server logs for database initialization debug output
2. **Permission Problems**: Look for file permission details and UID mismatches
3. **Disk Space**: Monitor disk space percentages in health checks
4. **Schema Issues**: Review table status and orphaned record counts
5. **Environment**: Verify environment variables and path configurations

## Tools Integration

The debug features are integrated with MCP tools:

- `cache_health()` - Comprehensive health diagnostics
- `cache_stats()` - Basic cache statistics
- `clear_cache()` - Cache cleanup with debug output

All tools provide detailed error information when database access fails.
