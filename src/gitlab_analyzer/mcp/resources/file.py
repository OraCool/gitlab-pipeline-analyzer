"""
File resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import UTC, datetime

from ..cache import get_cache_manager
from ..tools.utils import get_gitlab_analyzer, get_mcp_info

logger = logging.getLogger(__name__)


def register_file_resources(mcp) -> None:
    """Register file resources with MCP server"""

    @mcp.resource("gl://file/{project_id}/{job_id}/{file_path}")
    async def get_file_resource(project_id: str, job_id: str, file_path: str) -> str:
        """
        Get file error analysis as a resource with caching.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            file_path: File path to analyze

        Returns:
            File error analysis with metadata and MCP info
        """
        try:
            cache_manager = get_cache_manager()
            analyzer = get_gitlab_analyzer()

            # Create cache key for file analysis
            cache_key = (
                f"file_errors_{project_id}_{job_id}_{file_path.replace('/', '_')}"
            )

            # Try to get from cache first
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                return json.dumps(cached_data, indent=2)

            # Get job trace and extract file-specific errors
            trace = await analyzer.get_job_trace(project_id, int(job_id))

            # Extract errors from the trace using the log parser
            from gitlab_analyzer.parsers.log_parser import LogParser

            parser = LogParser()
            log_entries = parser.extract_log_entries(trace)

            # Filter errors for this specific file
            file_errors = []
            for entry in log_entries:
                # Check if this error relates to the specified file
                if (
                    (hasattr(entry, "test_file") and file_path in str(entry.test_file))
                    or (
                        hasattr(entry, "file_path")
                        and file_path in str(entry.file_path)
                    )
                    or file_path in entry.message
                ):
                    file_errors.append(
                        {
                            "message": entry.message,
                            "level": entry.level,
                            "line_number": getattr(entry, "line_number", None),
                            "test_file": getattr(entry, "test_file", None),
                            "file_path": getattr(entry, "file_path", None),
                            "exception_type": getattr(entry, "exception_type", None),
                            "exception_message": getattr(
                                entry, "exception_message", None
                            ),
                            "context": getattr(entry, "context", []),
                        }
                    )

            # Process the analysis data
            result = {
                "file_analysis": {
                    "project_id": project_id,
                    "job_id": int(job_id),
                    "file_path": file_path,
                    "errors": file_errors,
                    "error_count": len(file_errors),
                    "file_statistics": {
                        "total_errors": len(file_errors),
                        "error_types": list(
                            {
                                error.get(
                                    "exception_type", error.get("category", "unknown")
                                )
                                for error in file_errors
                            }
                        ),
                        "line_numbers": [
                            error.get("line_number")
                            for error in file_errors
                            if error.get("line_number")
                        ],
                    },
                },
                "resource_uri": f"gl://file/{project_id}/{job_id}/{file_path}",
                "cached_at": datetime.now(UTC).isoformat(),
                "metadata": {
                    "file_type": _classify_file_type(file_path),
                    "analysis_scope": "file-specific",
                    "source": "job_trace",
                },
            }

            mcp_info = get_mcp_info(
                tool_used="get_job_trace", error=False, parser_type="resource"
            )

            # Cache the result
            result["mcp_info"] = mcp_info
            await cache_manager.set(
                cache_key,
                result,
                data_type="file_errors",
                project_id=project_id,
                job_id=int(job_id),
                file_path=file_path,
            )

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(
                "Error getting file resource %s/%s/%s: %s",
                project_id,
                job_id,
                file_path,
                e,
            )
            error_result = {
                "error": f"Failed to get file resource: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "file_path": file_path,
                "resource_uri": f"gl://file/{project_id}/{job_id}/{file_path}",
            }
            return json.dumps(error_result, indent=2)

    logger.info("File resources registered")


def _classify_file_type(file_path: str) -> str:
    """Classify file type based on path and extension"""
    if "test" in file_path.lower() or file_path.endswith(("_test.py", "test_*.py")):
        return "test"
    elif file_path.endswith((".py", ".js", ".ts", ".java", ".cpp", ".c", ".rs")):
        return "source"
    elif file_path.endswith((".yml", ".yaml", ".json", ".toml", ".cfg", ".ini")):
        return "config"
    elif file_path.endswith((".md", ".rst", ".txt")):
        return "documentation"
    else:
        return "unknown"
