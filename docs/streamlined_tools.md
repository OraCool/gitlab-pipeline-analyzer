# Streamlined MCP Tools Reference

## Overview

# Comprehensive MCP Tools & Resources Reference

## Overview

The GitLab Pipeline Analyzer MCP Server provides **10 essential tools** and **comprehensive MCP resources** following DRY and KISS principles. Each tool serves a specific purpose in the pipeline analysis workflow, while resources provide efficient access to cached data.

For complete documentation with detailed parameters, examples, and usage patterns, see the [Tools and Resources Reference](tools_and_resources.rst).

## Quick Tool Reference

### 🎯 Pipeline Analysis (1 tool)

#### failed_pipeline_analysis

**Purpose**: Efficient analysis focusing only on failed jobs with intelligent parsing
**When to use**: Pipeline shows "failed" status and you need comprehensive analysis

**Features**:

- Auto-detects pytest vs generic jobs
- Intelligent parser selection
- Real branch resolution for MR pipelines
- Complete error extraction with context
- Automatic caching for performance

**Example**:

```python
result = await client.call_tool("failed_pipeline_analysis", {
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

### 🗑️ Specialized Cache Cleanup (2 tools)

#### clear_pipeline_cache

**Purpose**: Clear all cached data for a specific pipeline
**When to use**: Remove stale pipeline data or force fresh analysis

**Features**:

- Removes all pipeline-related cache entries
- Cleans associated job and error data
- Maintains data integrity during cleanup

**Example**:

```python
result = await client.call_tool("clear_pipeline_cache", {
    "project_id": "12345",
    "pipeline_id": 67890
})
```

#### clear_job_cache

**Purpose**: Clear all cached data for a specific job
**When to use**: Remove stale job data or force fresh trace analysis

**Features**:

- Removes all job-related cache entries
- Cleans associated error and trace data
- Fast targeted cleanup

**Example**:

```python
result = await client.call_tool("clear_job_cache", {
    "project_id": "12345",
    "job_id": 54321
})
```

### 🔗 Resource Access (1 tool)

#### get_mcp_resource

**Purpose**: Access data from MCP resource URIs without re-running analysis
**When to use**: Navigate to specific data or access previously analyzed results

**Features**:

- Access cached analysis results
- Navigate between related resources
- Efficient data retrieval without API calls
- Support for all resource URI patterns

**Example**:

```python
result = await client.call_tool("get_mcp_resource", {
    "resource_uri": "gl://jobs/12345/pipeline/67890/failed"
})
```

## 📦 MCP Resources Overview

The server provides **comprehensive MCP resources** for efficient data access following the `gl://` URI scheme:

### Resource Categories

#### Pipeline Resources

- `gl://pipeline/{project_id}/{pipeline_id}` - Pipeline overview with jobs list
- `gl://jobs/{project_id}/pipeline/{pipeline_id}[/failed|/success|/all]` - Pipeline jobs (filtered)

#### Job Resources

- `gl://job/{project_id}/{pipeline_id}/{job_id}` - Individual job details and traces

#### File Resources

- `gl://files/{project_id}/pipeline/{pipeline_id}` - Files with errors (paginated)
- `gl://file/{project_id}/{job_id}/{file_path}` - Specific file analysis
- `gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}` - File with trace

#### Error Resources

- `gl://error/{project_id}/{job_id}[?mode={mode}]` - Job error analysis
- `gl://errors/{project_id}/{job_id}[/{file_path}]` - Job/file-specific errors
- `gl://errors/{project_id}/pipeline/{pipeline_id}` - Pipeline-wide errors

#### Analysis Resources

- `gl://analysis/{project_id}[/pipeline/{pipeline_id}|/job/{job_id}][?mode={mode}]` - Analysis summaries

### Resource Access Pattern

All resources are accessed via the `get_mcp_resource` tool:

```python
# Get failed jobs from pipeline
result = await client.call_tool("get_mcp_resource", {
    "resource_uri": "gl://jobs/83/pipeline/1594344/failed"
})

# Get file-specific errors
result = await client.call_tool("get_mcp_resource", {
    "resource_uri": "gl://errors/83/76474172/src/main.py"
})

# Get detailed job analysis
result = await client.call_tool("get_mcp_resource", {
    "resource_uri": "gl://analysis/83/job/76474172?mode=detailed"
})
```

## Workflow Patterns

### Basic Pipeline Analysis

1. **failed_pipeline_analysis** → get complete failure analysis
2. **get_mcp_resource** → access detailed data via resource URIs
3. **search_repository_code** → find related code if needed

### Cache Maintenance

1. **cache_health** → check system status
2. **cache_stats** → review usage patterns
3. **clear_cache** → clean up old data as needed
4. **clear_pipeline_cache** → clean specific pipeline data
5. **clear_job_cache** → clean specific job data

## Migration from Legacy Tools

The streamlined architecture replaces 15+ legacy tools with **10 focused tools + comprehensive resources**:

- **All analysis tools** → `failed_pipeline_analysis` + resource access
- **All search functionality** → `search_repository_code` and `search_repository_commits`
- **All cache operations** → `clear_cache`, `cache_stats`, `cache_health`, `clear_pipeline_cache`, `clear_job_cache`
- **All resource access** → `get_mcp_resource` with comprehensive URI patterns
- **Trace access** → `get_clean_job_trace` for direct trace access

## Resource-Based Data Access

Instead of multiple specialized tools, detailed data is accessed via **resource URIs**:

- `gl://pipeline/{project_id}/{pipeline_id}` - Pipeline information with comprehensive metadata
- `gl://job/{project_id}/{pipeline_id}/{job_id}` - Job details and logs
- `gl://errors/{project_id}/{job_id}` - Structured error analysis with categorization
- `gl://file/{project_id}/{job_id}/{file_path}` - File-specific errors with context
- `gl://analysis/{project_id}/pipeline/{pipeline_id}?mode=detailed` - Deep analysis summaries

This approach follows the **KISS principle** by providing simple tools with comprehensive, efficient resource access through a unified URI scheme.
