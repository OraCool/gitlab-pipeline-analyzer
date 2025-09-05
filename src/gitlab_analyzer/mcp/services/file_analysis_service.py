"""
File Analysis Service - Advanced file analysis and enhancement operations

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging
from datetime import datetime, timezone
from typing import Any

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.utils.debug import verbose_debug_print

from .file_service import get_file_service

logger = logging.getLogger(__name__)


class FileAnalysisService:
    """Service for advanced file analysis and enhancement operations"""

    def __init__(self):
        self.cache_manager = None
        self.file_service = get_file_service()

    async def _get_cache_manager(self):
        """Get cache manager instance"""
        if not self.cache_manager:
            self.cache_manager = get_cache_manager()
        return self.cache_manager

    async def get_file_with_trace(
        self,
        project_id: str,
        job_id: str,
        file_path: str,
        mode: str = "balanced",
        include_trace: str = "false",
    ) -> dict[str, Any]:
        """Get file analysis with optional trace inclusion"""
        verbose_debug_print(
            f"Getting file with trace: project_id={project_id}, job_id={job_id}, file_path={file_path}, mode={mode}, include_trace={include_trace}"
        )

        cache_manager = await self._get_cache_manager()

        # Handle include_trace parameter safely
        include_trace_str = str(include_trace or "false").lower()

        # Create cache key
        cache_key = (
            f"file_trace_{project_id}_{job_id}_{file_path}_{mode}_{include_trace_str}"
        )

        async def compute_file_with_trace() -> dict[str, Any]:
            """Compute file data with optional trace"""
            try:
                # Get basic file data
                file_data = await self.file_service.get_file_data(
                    project_id, job_id, file_path, mode
                )

                # If trace is requested, add trace data
                if include_trace_str == "true":
                    # Get job trace segments that mention this file
                    trace_segments = await cache_manager.get_trace_segments_for_file(
                        project_id, job_id, file_path
                    )

                    file_data["trace_data"] = {
                        "include_trace": True,
                        "trace_segments": trace_segments,
                        "trace_count": len(trace_segments),
                    }
                else:
                    file_data["trace_data"] = {
                        "include_trace": False,
                        "message": "Use include_trace=true to get trace data",
                    }

                # Add resource links
                file_data["resource_links"] = self._generate_file_resource_links(
                    project_id, job_id, file_path, mode, include_trace_str
                )

                # Add analysis metadata
                file_data["analysis_metadata"] = {
                    "mode": mode,
                    "include_trace": include_trace_str,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                    "data_source": "database_with_enhancement",
                }

                return file_data

            except Exception as e:
                logger.error(f"Error computing file with trace: {e}")
                return {
                    "project_id": project_id,
                    "job_id": job_id,
                    "file_path": file_path,
                    "error": str(e),
                    "trace_data": {"include_trace": False, "error": str(e)},
                }

        return await cache_manager.get_or_compute(cache_key, compute_file_with_trace)

    async def get_enhanced_pipeline_files(
        self,
        project_id: str,
        pipeline_id: str,
        mode: str = "balanced",
        include_trace: str = "false",
        max_errors: int = 10,
    ) -> dict[str, Any]:
        """Get enhanced pipeline files with additional analysis"""
        verbose_debug_print(
            f"Getting enhanced pipeline files: project_id={project_id}, pipeline_id={pipeline_id}, mode={mode}, include_trace={include_trace}, max_errors={max_errors}"
        )

        cache_manager = await self._get_cache_manager()

        # Handle parameters safely
        include_trace_str = str(include_trace or "false").lower()
        max_errors_int = max(1, min(max_errors, 100))  # Limit between 1-100

        # Create cache key
        cache_key = f"enhanced_pipeline_files_{project_id}_{pipeline_id}_{mode}_{include_trace_str}_{max_errors_int}"

        async def compute_enhanced_pipeline_files() -> dict[str, Any]:
            """Compute enhanced pipeline files data"""
            try:
                # Get basic pipeline files data
                pipeline_files = await self.file_service.get_pipeline_files(
                    project_id, pipeline_id, page=1, limit=50
                )

                # Enhance each file with additional analysis
                enhanced_files = []
                for file_data in pipeline_files.get("files", []):
                    file_path = file_data["file_path"]

                    # Limit errors per file for performance
                    limited_errors = file_data["errors"][:max_errors_int]

                    enhanced_file = {
                        "file_path": file_path,
                        "error_count": file_data["error_count"],
                        "jobs_affected_count": file_data.get("jobs_affected_count", 0),
                        "jobs_affected": file_data.get("jobs_affected", []),
                        "errors": limited_errors,
                        "errors_truncated": len(file_data["errors"]) > max_errors_int,
                        "total_errors_available": len(file_data["errors"]),
                    }

                    # Add trace data if requested
                    if include_trace_str == "true":
                        # Get trace segments for this file across all jobs
                        trace_segments = []
                        for job_id in file_data.get("jobs_affected", []):
                            job_trace_segments = (
                                await cache_manager.get_trace_segments_for_file(
                                    project_id, job_id, file_path
                                )
                            )
                            trace_segments.extend(job_trace_segments)

                        enhanced_file["trace_data"] = {
                            "include_trace": True,
                            "trace_segments": trace_segments[
                                :10
                            ],  # Limit to 10 segments
                            "trace_count": len(trace_segments),
                            "trace_truncated": len(trace_segments) > 10,
                        }
                    else:
                        enhanced_file["trace_data"] = {
                            "include_trace": False,
                            "message": "Use include_trace=true to get trace data",
                        }

                    # Add resource links for this file
                    enhanced_file["resource_links"] = (
                        self._generate_file_resource_links(
                            project_id,
                            None,
                            file_path,
                            mode,
                            include_trace_str,
                            pipeline_id,
                        )
                    )

                    enhanced_files.append(enhanced_file)

                # Sort by error count descending
                enhanced_files.sort(key=lambda x: x["error_count"], reverse=True)

                result = {
                    "project_id": project_id,
                    "pipeline_id": pipeline_id,
                    "files": enhanced_files,
                    "enhancement_config": {
                        "mode": mode,
                        "include_trace": include_trace_str,
                        "max_errors_per_file": max_errors_int,
                    },
                    "summary": pipeline_files.get("summary", {}),
                    "analysis_metadata": {
                        "enhancement_level": "advanced",
                        "data_source": "database_with_enhancement",
                        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }

                return result

            except Exception as e:
                logger.error(f"Error computing enhanced pipeline files: {e}")
                return {
                    "project_id": project_id,
                    "pipeline_id": pipeline_id,
                    "error": str(e),
                    "files": [],
                    "enhancement_config": {
                        "mode": mode,
                        "include_trace": include_trace_str,
                        "max_errors_per_file": max_errors_int,
                    },
                }

        return await cache_manager.get_or_compute(
            cache_key, compute_enhanced_pipeline_files
        )

    def _generate_file_resource_links(
        self,
        project_id: str,
        job_id: str | None = None,
        file_path: str = "",
        mode: str = "balanced",
        include_trace: str = "false",
        pipeline_id: str | None = None,
    ) -> list[dict[str, str]]:
        """Generate resource links for file-related resources"""
        links = []

        if job_id:
            # Job-specific file links
            links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}",
                    "text": f"View basic file analysis for {file_path} in job {job_id}",
                }
            )

            if include_trace == "true":
                links.append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace=true",
                        "text": f"View {file_path} with trace data from job {job_id}",
                    }
                )

            links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://files/{project_id}/{job_id}",
                    "text": f"View all files with errors in job {job_id}",
                }
            )

        if pipeline_id:
            # Pipeline-specific file links
            links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://files/{project_id}/pipeline/{pipeline_id}",
                    "text": f"View all files with errors across pipeline {pipeline_id}",
                }
            )

            links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://files/{project_id}/pipeline/{pipeline_id}/enhanced?mode={mode}&include_trace={include_trace}",
                    "text": f"View enhanced pipeline files analysis for pipeline {pipeline_id}",
                }
            )

        return links


# Singleton instance
_file_analysis_service = None


def get_file_analysis_service() -> FileAnalysisService:
    """Get the singleton FileAnalysisService instance"""
    global _file_analysis_service
    if _file_analysis_service is None:
        _file_analysis_service = FileAnalysisService()
    return _file_analysis_service
