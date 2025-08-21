"""
Search tools for GitLab repository content

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from typing import Annotated

from fastmcp import FastMCP

from .utils import get_gitlab_analyzer


def register_search_tools(mcp: FastMCP) -> None:
    """Register search-related MCP tools"""

    @mcp.tool
    async def search_repository_code(
        project_id: Annotated[str | int, "GitLab project ID or path"],
        search_keywords: Annotated[str, "Keywords to search for in code"],
        branch: Annotated[str | None, "Specific branch to search (optional)"] = None,
        filename_filter: Annotated[
            str | None, "Filter by filename pattern (supports wildcards)"
        ] = None,
        path_filter: Annotated[str | None, "Filter by file path pattern"] = None,
        extension_filter: Annotated[
            str | None, "Filter by file extension (e.g., 'py', 'js')"
        ] = None,
        max_results: Annotated[int, "Maximum number of results to return"] = 20,
    ) -> str:
        """
        🔍 SEARCH: Search for keywords in GitLab repository code files.

        WHEN TO USE:
        - Find code implementations containing specific keywords
        - Locate configuration files or specific patterns
        - Search for function names, class names, or variables
        - Find code examples or usage patterns

        SEARCH FEATURES:
        - Full-text search in code files
        - Branch-specific searching
        - File type filtering (by extension, filename, path)
        - Wildcard support in filters
        - Line number and context for each match

        EXAMPLES:
        - search_keywords="async def process" extension_filter="py"
        - search_keywords="import pandas" filename_filter="*.py"
        - search_keywords="class UserModel" path_filter="models/*"
        - search_keywords="TODO" branch="feature-branch"

        Args:
            project_id: The GitLab project ID or path
            search_keywords: Keywords to search for in code
            branch: Specific branch to search (optional, defaults to project's default branch)
            filename_filter: Filter by filename pattern (supports wildcards like *.py)
            path_filter: Filter by file path pattern (e.g., src/*, models/*)
            extension_filter: Filter by file extension (e.g., 'py', 'js', 'ts')
            max_results: Maximum number of results to return (default: 20)

        Returns:
            Search results with file paths, line numbers, and code snippets
        """
        try:
            gitlab_client = get_gitlab_analyzer()
            results = await gitlab_client.search_project_code(
                project_id=project_id,
                search_term=search_keywords,
                branch=branch,
                filename_filter=filename_filter,
                path_filter=path_filter,
                extension_filter=extension_filter,
            )

            if not results:
                return (
                    f"No code matches found for '{search_keywords}' in project {project_id}"
                    + (f" on branch '{branch}'" if branch else "")
                )

            # Limit results to max_results
            limited_results = results[:max_results]

            # Format search results
            output_lines = [
                f"🔍 Code Search Results for '{search_keywords}' in project {project_id}",
                f"Found {len(results)} total matches (showing first {len(limited_results)})",
            ]

            if branch:
                output_lines.append(f"Branch: {branch}")

            filters_applied = []
            if filename_filter:
                filters_applied.append(f"filename:{filename_filter}")
            if path_filter:
                filters_applied.append(f"path:{path_filter}")
            if extension_filter:
                filters_applied.append(f"extension:{extension_filter}")

            if filters_applied:
                output_lines.append(f"Filters: {', '.join(filters_applied)}")

            output_lines.append("")

            for i, result in enumerate(limited_results, 1):
                file_path = result.get("path", result.get("filename", "Unknown"))
                start_line = result.get("startline", "Unknown")
                content_snippet = result.get("data", "").strip()
                ref = result.get("ref", "Unknown")

                output_lines.extend(
                    [
                        f"📄 Result {i}: {file_path}",
                        f"   Line: {start_line} | Branch: {ref}",
                        "   Content:",
                        "   " + "─" * 50,
                    ]
                )

                # Format content snippet with line numbers if possible
                if content_snippet:
                    lines = content_snippet.split("\n")
                    for j, line in enumerate(lines[:5]):  # Show max 5 lines per result
                        line_num = (
                            start_line + j if isinstance(start_line, int) else "?"
                        )
                        output_lines.append(f"   {line_num:4} | {line}")
                    if len(lines) > 5:
                        output_lines.append(f"   ... ({len(lines) - 5} more lines)")
                else:
                    output_lines.append("   (No content preview available)")

                output_lines.append("")

            if len(results) > max_results:
                output_lines.append(
                    f"... and {len(results) - max_results} more results"
                )
                output_lines.append("Use max_results parameter to see more results")

            return "\n".join(output_lines)

        except Exception as e:  # noqa: BLE001
            return f"Error searching repository code: {str(e)}"

    @mcp.tool
    async def search_repository_commits(
        project_id: Annotated[str | int, "GitLab project ID or path"],
        search_keywords: Annotated[str, "Keywords to search for in commit messages"],
        branch: Annotated[str | None, "Specific branch to search (optional)"] = None,
        max_results: Annotated[int, "Maximum number of results to return"] = 20,
    ) -> str:
        """
        🔍 COMMITS: Search for keywords in GitLab repository commit messages.

        WHEN TO USE:
        - Find commits related to specific features or bug fixes
        - Locate commits by author, ticket number, or description
        - Track changes related to specific functionality
        - Find commits that mention specific issues or PRs

        SEARCH FEATURES:
        - Full-text search in commit messages
        - Branch-specific searching
        - Author and date information
        - Commit SHA and web links

        EXAMPLES:
        - search_keywords="fix bug" - find bug fix commits
        - search_keywords="JIRA-123" - find commits referencing ticket
        - search_keywords="refactor database" - find database refactoring
        - search_keywords="merge" branch="main" - find merge commits

        Args:
            project_id: The GitLab project ID or path
            search_keywords: Keywords to search for in commit messages
            branch: Specific branch to search (optional, defaults to project's default branch)
            max_results: Maximum number of results to return (default: 20)

        Returns:
            Search results with commit information, messages, and metadata
        """
        try:
            gitlab_client = get_gitlab_analyzer()
            results = await gitlab_client.search_project_commits(
                project_id=project_id,
                search_term=search_keywords,
                branch=branch,
            )

            if not results:
                return (
                    f"No commit matches found for '{search_keywords}' in project {project_id}"
                    + (f" on branch '{branch}'" if branch else "")
                )

            # Limit results to max_results
            limited_results = results[:max_results]

            # Format search results
            output_lines = [
                f"🔍 Commit Search Results for '{search_keywords}' in project {project_id}",
                f"Found {len(results)} total matches (showing first {len(limited_results)})",
            ]

            if branch:
                output_lines.append(f"Branch: {branch}")

            output_lines.append("")

            for i, result in enumerate(limited_results, 1):
                commit_id = result.get("id", "Unknown")
                short_id = result.get(
                    "short_id", commit_id[:8] if commit_id != "Unknown" else "Unknown"
                )
                title = result.get("title", "No title")
                message = result.get("message", "").strip()
                author_name = result.get("author_name", "Unknown")
                author_email = result.get("author_email", "")
                created_at = result.get("created_at", "Unknown")
                committed_date = result.get("committed_date", created_at)

                output_lines.extend(
                    [
                        f"📝 Commit {i}: {short_id}",
                        f"   Title: {title}",
                        f"   Author: {author_name}"
                        + (f" <{author_email}>" if author_email else ""),
                        f"   Date: {committed_date}",
                        f"   Full SHA: {commit_id}",
                    ]
                )

                # Show commit message if different from title
                if (
                    message
                    and message != title
                    and len(message.strip()) > len(title.strip())
                ):
                    output_lines.extend(
                        [
                            "   Message:",
                            "   " + "─" * 50,
                        ]
                    )
                    # Show first few lines of the commit message
                    message_lines = message.split("\n")
                    for line in message_lines[:3]:
                        if line.strip():
                            output_lines.append(f"   {line}")
                    if len(message_lines) > 3:
                        output_lines.append("   ...")

                output_lines.append("")

            if len(results) > max_results:
                output_lines.append(
                    f"... and {len(results) - max_results} more results"
                )
                output_lines.append("Use max_results parameter to see more results")

            return "\n".join(output_lines)

        except Exception as e:  # noqa: BLE001
            return f"Error searching repository commits: {str(e)}"
