# Streamlined MCP Tools Reference

## Overview

The GitLab Pipeline Analyzer MCP Server provides **6 focused tools** following DRY and KISS principles. Each tool serves a specific purpose in the pipeline analysis workflow.

## Tool Categories

### 🔍 Pipeline Analysis (1 tool)

#### comprehensive_pipeline_analysis

**Purpose**: Complete pipeline failure analysis with intelligent parsing
**When to use**: Pipeline shows "failed" status and you need comprehensive analysis

**Features**:

- Auto-detects pytest vs generic jobs
- Intelligent parser selection
- Real branch resolution for MR pipelines
- Complete error extraction with context
- Automatic caching for performance

**Example**:

```python
result = await client.call_tool("comprehensive_pipeline_analysis", {
    "project_id": "12345",
    "pipeline_id": 67890
})
```

### 🔍 Repository Search (2 tools)

#### search_repository_code

**Purpose**: Search for keywords in repository code files
**When to use**: Find code implementations, configuration files, or specific patterns

**Features**:

- Full-text search in code files
- Branch-specific searching
- File type filtering (by extension, filename, path)
- Wildcard support in filters

**Example**:

```python
result = await client.call_tool("search_repository_code", {
    "project_id": "12345",
    "search_keywords": "async def process",
    "extension_filter": "py"
})
```

#### search_repository_commits

**Purpose**: Search for keywords in commit messages
**When to use**: Find commits related to specific features, bug fixes, or changes

**Features**:

- Full-text search in commit messages
- Branch-specific searching
- Author and date information
- Commit SHA and web links

**Example**:

```python
result = await client.call_tool("search_repository_commits", {
    "project_id": "12345",
    "search_keywords": "fix bug",
    "branch": "main"
})
```

### 🗄️ Cache Management (3 tools)

#### clear_cache

**Purpose**: Clear cached data with flexible filtering options
**When to use**: Clean up old cache entries or specific data types

**Features**:

- Clear all cache data
- Filter by data type (pipeline, job, error, etc.)
- Filter by age (clear entries older than X days)
- Selective clearing by project or pipeline

**Example**:

```python
result = await client.call_tool("clear_cache", {
    "older_than_days": 7,
    "data_type": "job"
})
```

#### cache_stats

**Purpose**: Get comprehensive cache statistics and usage information
**When to use**: Monitor cache performance and storage usage

**Features**:

- Total entry counts by type
- Storage usage statistics
- Cache hit/miss ratios
- Performance metrics

**Example**:

```python
result = await client.call_tool("cache_stats", {})
```

#### cache_health

**Purpose**: Monitor cache system health and performance
**When to use**: Diagnose cache issues or verify system status

**Features**:

- Database connectivity checks
- Performance benchmarks
- Error rate monitoring
- System health indicators

**Example**:

```python
result = await client.call_tool("cache_health", {})
```

## Workflow Patterns

### Basic Pipeline Analysis

1. **comprehensive_pipeline_analysis** → get complete failure analysis
2. Use resource URIs for detailed data access
3. **search_repository_code** → find related code if needed

### Cache Maintenance

1. **cache_health** → check system status
2. **cache_stats** → review usage patterns
3. **clear_cache** → clean up old data as needed

## Migration from Legacy Tools

The streamlined architecture replaces 15+ legacy tools with 6 focused tools:

- **All analysis tools** → `comprehensive_pipeline_analysis`
- **All search functionality** → `search_repository_code` and `search_repository_commits`
- **All cache operations** → `clear_cache`, `cache_stats`, `cache_health`

## Resource-Based Data Access

Instead of multiple specialized tools, detailed data is accessed via resource URIs:

- `gl://pipeline/{pipeline_id}` - Pipeline information
- `gl://job/{job_id}` - Job details and logs
- `gl://errors/{job_id}` - Structured error analysis
- `gl://file-errors/{job_id}/{file_path}` - File-specific errors

This approach follows the **KISS principle** by providing simple tools with comprehensive resource access.
