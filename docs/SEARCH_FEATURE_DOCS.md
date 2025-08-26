# GitLab Repository Search Feature

This document describes the new search functionality added to the GitLab Pipeline Analyzer MCP server.

## Overview

The search feature allows you to search for keywords in GitLab repository code files and commit messages using GitLab's powerful Search API. This is particularly useful for:

- Finding code implementations containing specific keywords
- Locating configuration files or specific patterns
- Searching for function names, class names, or variables
- Finding commits related to specific features or bug fixes
- Tracking changes related to specific functionality

## New API Methods

### `search_project_code()`

Search for keywords in repository code files.

```python
async def search_project_code(
    project_id: str | int,
    search_term: str,
    branch: str = None,
    filename_filter: str = None,
    path_filter: str = None,
    extension_filter: str = None,
) -> list[dict[str, Any]]:
```

**Parameters:**

- `project_id`: GitLab project ID or path
- `search_term`: Keywords to search for
- `branch`: Specific branch to search (optional, defaults to project's default branch)
- `filename_filter`: Filter by filename pattern (supports wildcards like `*.py`)
- `path_filter`: Filter by file path pattern (e.g., `src/*`, `models/*`)
- `extension_filter`: Filter by file extension (e.g., `py`, `js`, `ts`)

**Returns:** List of search results with file paths, line numbers, and code snippets.

### `search_project_commits()`

Search for keywords in commit messages.

```python
async def search_project_commits(
    project_id: str | int,
    search_term: str,
    branch: str = None,
) -> list[dict[str, Any]]:
```

**Parameters:**

- `project_id`: GitLab project ID or path
- `search_term`: Keywords to search for in commit messages
- `branch`: Specific branch to search (optional, defaults to project's default branch)

**Returns:** List of commit search results with commit information and metadata.

## MCP Tools

### `search_repository_code`

🔍 **SEARCH**: Search for keywords in GitLab repository code files.

**Usage Examples:**

```
search_repository_code(
    project_id=123,
    search_keywords="async def process",
    extension_filter="py"
)

search_repository_code(
    project_id="group/project",
    search_keywords="import pandas",
    filename_filter="*.py"
)

search_repository_code(
    project_id=456,
    search_keywords="class UserModel",
    path_filter="models/*"
)

search_repository_code(
    project_id=789,
    search_keywords="TODO",
    branch="feature-branch"
)
```

### `search_repository_commits`

🔍 **COMMITS**: Search for keywords in GitLab repository commit messages.

**Usage Examples:**

```
search_repository_commits(
    project_id=123,
    search_keywords="fix bug"
)

search_repository_commits(
    project_id="group/project",
    search_keywords="JIRA-123"
)

search_repository_commits(
    project_id=456,
    search_keywords="refactor database"
)

search_repository_commits(
    project_id=789,
    search_keywords="merge",
    branch="main"
)
```

## Search Features

### Advanced Filtering

The code search supports powerful filtering options:

1. **Filename Filtering**: `filename:*.py` - only Python files
2. **Path Filtering**: `path:src/models/*` - only files in models directory under src
3. **Extension Filtering**: `extension:js` - only JavaScript files
4. **Combined Filters**: `async def filename:*.py path:src/*` - async functions in Python files under src/

### Branch-Specific Search

Both search functions support branch-specific searching:

- **Default**: Searches the project's default branch (usually `main` or `master`)
- **Specific Branch**: Using the `branch` parameter searches only that branch
- **Use Cases**:
  - Search feature branches for new code
  - Compare code patterns between branches
  - Find branch-specific implementations

### Search Results

#### Code Search Results

Each code search result includes:

- `path`: Full file path in the repository
- `data`: Code snippet containing the match
- `startline`: Line number where the match begins
- `ref`: The branch/ref where the match was found
- `project_id`: The project containing the match

#### Commit Search Results

Each commit search result includes:

- `id`: Full commit SHA
- `short_id`: Abbreviated commit SHA
- `title`: Commit title/subject
- `message`: Full commit message
- `author_name`: Commit author name
- `author_email`: Commit author email
- `created_at`: Commit creation date
- `committed_date`: Commit date

## GitLab Requirements

### API Access

- Requires valid GitLab access token with read permissions to the target project
- Works with GitLab.com, GitLab self-managed, and GitLab Dedicated

### Tier Requirements

- **Free Tier**: Basic search functionality available
- **Premium/Ultimate**: Advanced search features with better performance and additional scopes

### Permissions

- User must have read access to the repository
- For private projects, appropriate project membership is required

## Implementation Details

### Error Handling

- HTTP errors are properly handled and returned as descriptive error messages
- Timeout protection prevents hanging requests
- Invalid project IDs return appropriate 404 errors

### Performance

- Results are paginated to handle large repositories
- Search queries are optimized for GitLab's API
- Supports max_results parameter to limit response size

### Integration

- Seamlessly integrated with existing GitLab Pipeline Analyzer tools
- Uses the same authentication and configuration as other tools
- Follows the same error handling and response patterns

## Testing

The implementation includes comprehensive tests:

1. **Unit Tests**: Test individual API methods with mocked responses
2. **Integration Tests**: Test with real GitLab instances
3. **MCP Tool Tests**: Verify tools work correctly within the MCP framework

To run tests:

```bash
cd /path/to/mcp
uv run python quick_search_test.py      # Quick integration test
uv run python verify_search.py         # Implementation verification
```

## Future Enhancements

Potential future improvements:

- Support for more GitLab search scopes (wiki, issues, merge requests)
- Search result caching for better performance
- Advanced query syntax support
- Search across multiple projects
- Integration with other GitLab features

---

The search functionality is now fully integrated and ready to use! 🎉
