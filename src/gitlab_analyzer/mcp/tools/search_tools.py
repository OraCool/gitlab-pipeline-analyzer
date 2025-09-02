"""
Search tools for repository content

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import time
from typing import Any

import httpx
from fastmcp import FastMCP

from gitlab_analyzer.utils.debug import debug_print, error_print, verbose_debug_print
from gitlab_analyzer.utils.utils import get_gitlab_analyzer, get_mcp_info


def register_search_tools(mcp: FastMCP) -> None:
    """Register search-related MCP tools"""

    @mcp.tool
    async def search_repository_code(
        project_id: str | int,
        search_keywords: str,
        branch: str | None = None,
        filename_filter: str | None = None,
        path_filter: str | None = None,
        extension_filter: str | None = None,
        max_results: int = 20,
        output_format: str = "text",
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
        - JSON and text output formats

        EXAMPLES:
        - search_keywords="async def process" extension_filter="py"
        - search_keywords="import pandas" filename_filter="*.py"
        - search_keywords="class UserModel" path_filter="models/*"
        - search_keywords="TODO" branch="feature-branch" output_format="json"

        Args:
            project_id: The GitLab project ID or path
            search_keywords: Keywords to search for in code
            branch: Specific branch to search (optional, defaults to project's default branch)
            filename_filter: Filter by filename pattern (supports wildcards like *.py)
            path_filter: Filter by file path pattern (e.g., src/*, models/*)
            extension_filter: Filter by file extension (e.g., 'py', 'js', 'ts')
            max_results: Maximum number of results to return (default: 20)
            output_format: Output format - 'text' for readable format, 'json' for structured data

        Returns:
            Search results with file paths, line numbers, and code snippets
            Format: Text (readable) or JSON (structured with file, branch, start_line, search_content)
        """
        start_time = time.time()
        debug_print(
            f"🔍 Starting repository code search for '{search_keywords}' in project {project_id}"
        )
        verbose_debug_print(
            f"📋 Search filters: branch={branch}, filename={filename_filter}, path={path_filter}, extension={extension_filter}"
        )
        verbose_debug_print(
            f"⚙️ Search options: max_results={max_results}, output_format={output_format}"
        )

        try:
            gitlab_client = get_gitlab_analyzer()
            verbose_debug_print("🔗 GitLab client instance obtained")

            debug_print(f"🔎 Executing search in GitLab project {project_id}...")
            results = await gitlab_client.search_project_code(
                project_id=project_id,
                search_term=search_keywords,
                branch=branch,
                filename_filter=filename_filter,
                path_filter=path_filter,
                extension_filter=extension_filter,
            )

            if not results:
                debug_print(f"📭 No search results found for '{search_keywords}'")
                no_results_msg = (
                    f"No code matches found for '{search_keywords}' in project {project_id}"
                    + (f" on branch '{branch}'" if branch else "")
                )

                if output_format == "json":
                    verbose_debug_print("📝 Formatting empty results as JSON")
                    return json.dumps(
                        {
                            "search_keywords": search_keywords,
                            "project_id": str(project_id),
                            "branch": branch,
                            "total_results": 0,
                            "showing_results": 0,
                            "filters": {
                                "filename_filter": filename_filter,
                                "path_filter": path_filter,
                                "extension_filter": extension_filter,
                            },
                            "results": [],
                            "message": no_results_msg,
                            "mcp_info": get_mcp_info("search_repository_code"),
                            "debug_timing": {
                                "duration_seconds": round(time.time() - start_time, 3)
                            },
                        },
                        indent=2,
                    )
                return no_results_msg

            total_found = len(results)
            debug_print(f"📊 Found {total_found} search results")

            # Limit results to max_results
            limited_results = results[:max_results]
            showing_count = len(limited_results)
            if showing_count < total_found:
                verbose_debug_print(
                    f"📋 Limiting display to {showing_count} out of {total_found} results"
                )

            if output_format == "json":
                verbose_debug_print("📝 Formatting results as JSON...")
                # Structure results in JSON format
                json_results = []
                for result in limited_results:
                    file_path = result.get("path", result.get("filename", "Unknown"))
                    start_line = result.get("startline", "Unknown")
                    content_snippet = result.get(
                        "data", ""
                    )  # Keep raw content without .strip()
                    ref = result.get("ref", "Unknown")

                    json_results.append(
                        {
                            "file": file_path,
                            "branch": ref,
                            "start_line": start_line,
                            "search_content": content_snippet,
                        }
                    )

                return json.dumps(
                    {
                        "search_keywords": search_keywords,
                        "project_id": str(project_id),
                        "branch": branch,
                        "total_results": len(results),
                        "showing_results": len(limited_results),
                        "filters": {
                            "filename_filter": filename_filter,
                            "path_filter": path_filter,
                            "extension_filter": extension_filter,
                        },
                        "results": json_results,
                        "mcp_info": get_mcp_info("search_repository_code"),
                        "debug_timing": {
                            "duration_seconds": round(time.time() - start_time, 3)
                        },
                    },
                    indent=2,
                )

            verbose_debug_print("📝 Formatting results as text...")
            # Format search results in text format (existing implementation)
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
                content_snippet = result.get(
                    "data", ""
                )  # Keep raw content without .strip()
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

            end_time = time.time()
            duration = end_time - start_time
            debug_print(f"✅ Code search completed successfully in {duration:.3f}s")
            return "\n".join(output_lines)

        except (httpx.HTTPError, ValueError, KeyError) as e:
            end_time = time.time()
            duration = end_time - start_time
            error_print(
                f"❌ Error searching repository code after {duration:.3f}s: {e}"
            )
            return f"Error searching repository code: {str(e)}"
        except Exception as e:  # noqa: BLE001
            end_time = time.time()
            duration = end_time - start_time
            error_print(
                f"❌ Unexpected error searching repository code after {duration:.3f}s: {e}"
            )
            return f"Error searching repository code: {str(e)}"

    @mcp.tool
    async def search_repository_commits(
        project_id: str | int,
        search_keywords: str,
        branch: str | None = None,
        max_results: int = 20,
        output_format: str = "text",
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
        - JSON and text output formats

        EXAMPLES:
        - search_keywords="fix bug" - find bug fix commits
        - search_keywords="JIRA-123" - find commits referencing ticket
        - search_keywords="refactor database" - find database refactoring
        - search_keywords="merge" branch="main" output_format="json" - find merge commits

        Args:
            project_id: The GitLab project ID or path
            search_keywords: Keywords to search for in commit messages
            branch: Specific branch to search (optional, defaults to project's default branch)
            max_results: Maximum number of results to return (default: 20)
            output_format: Output format - 'text' for readable format, 'json' for structured data

        Returns:
            Search results with commit information, messages, and metadata
            Format: Text (readable) or JSON (structured with commit details)
        """
        try:
            gitlab_client = get_gitlab_analyzer()
            results = await gitlab_client.search_project_commits(
                project_id=project_id,
                search_term=search_keywords,
                branch=branch,
            )

            if not results:
                no_results_msg = (
                    f"No commit matches found for '{search_keywords}' in project {project_id}"
                    + (f" on branch '{branch}'" if branch else "")
                )

                if output_format == "json":
                    return json.dumps(
                        {
                            "search_keywords": search_keywords,
                            "project_id": str(project_id),
                            "branch": branch,
                            "total_results": 0,
                            "showing_results": 0,
                            "commits": [],
                            "message": no_results_msg,
                            "mcp_info": get_mcp_info("search_repository_commits"),
                        },
                        indent=2,
                    )
                return no_results_msg

            # Limit results to max_results
            limited_results = results[:max_results]

            if output_format == "json":
                # Return structured JSON format
                json_result: dict[str, Any] = {
                    "search_query": search_keywords,
                    "project_id": str(project_id),
                    "branch": branch,
                    "total_matches": len(results),
                    "showing_results": len(limited_results),
                    "commits": [],
                    "mcp_info": get_mcp_info("search_repository_commits"),
                }

                for result in limited_results:
                    commit_data = {
                        "sha": result.get("id", "Unknown"),
                        "short_sha": result.get(
                            "short_id",
                            (
                                result.get("id", "Unknown")[:8]
                                if result.get("id") != "Unknown"
                                else "Unknown"
                            ),
                        ),
                        "title": result.get("title", "No title"),
                        "message": result.get("message", "").strip(),
                        "author": {
                            "name": result.get("author_name", "Unknown"),
                            "email": result.get("author_email", ""),
                        },
                        "date": result.get(
                            "committed_date", result.get("created_at", "Unknown")
                        ),
                        "created_at": result.get("created_at", "Unknown"),
                    }
                    json_result["commits"].append(commit_data)

                return json.dumps(json_result, indent=2)

            # Format search results for text output
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

        except (httpx.HTTPError, ValueError, KeyError) as e:
            return f"Error searching repository commits: {str(e)}"
        except Exception as e:  # noqa: BLE001
            return f"Error searching repository commits: {str(e)}"
