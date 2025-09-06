"""
File Service - Core file data operations (Simple version)

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging
from datetime import datetime, timezone
from typing import Any

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.mcp.utils.pipeline_validation import check_pipeline_analyzed
from gitlab_analyzer.utils.debug import verbose_debug_print

logger = logging.getLogger(__name__)


class FileService:
    """Service for core file data operations"""

    def __init__(self):
        self.cache_manager = get_cache_manager()

    async def get_file_data(
        self, project_id: str, job_id: str, file_path: str, mode: str = "balanced"
    ) -> dict[str, Any]:
        """Get basic file data from cache"""
        verbose_debug_print(
            f"Getting file data: project_id={project_id}, job_id={job_id}, file_path={file_path}, mode={mode}"
        )

        try:
            # Get errors for this specific file
            file_errors = self.cache_manager.get_file_errors(int(job_id), file_path)

            # Get basic file info
            file_info = {
                "project_id": project_id,
                "job_id": job_id,
                "file_path": file_path,
                "error_count": len(file_errors),
                "errors": file_errors,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            return file_info

        except Exception as e:
            logger.error(f"Error getting file data: {e}")
            return {
                "project_id": project_id,
                "job_id": job_id,
                "file_path": file_path,
                "error": str(e),
                "error_count": 0,
                "errors": [],
            }

    async def get_files_for_job(
        self, project_id: str, job_id: str, page: int = 1, limit: int = 50
    ) -> dict[str, Any]:
        """Get files with errors for a specific job"""
        verbose_debug_print(
            f"Getting files for job: project_id={project_id}, job_id={job_id}, page={page}, limit={limit}"
        )

        try:
            # Get all errors for this job
            all_errors = self.cache_manager.get_job_errors(int(job_id))

            # Group errors by file
            files_with_errors = {}
            for error in all_errors:
                file_path = error.get("file_path", "unknown")
                if file_path not in files_with_errors:
                    files_with_errors[file_path] = {
                        "file_path": file_path,
                        "error_count": 0,
                        "errors": [],
                    }
                files_with_errors[file_path]["errors"].append(error)
                files_with_errors[file_path]["error_count"] += 1

            # Convert to list and sort by error count
            files_list = list(files_with_errors.values())
            files_list.sort(key=lambda x: x["error_count"], reverse=True)

            # Apply pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_files = files_list[start_idx:end_idx]

            return {
                "project_id": project_id,
                "job_id": job_id,
                "files": paginated_files,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_files": len(files_list),
                    "total_pages": (len(files_list) + limit - 1) // limit,
                    "has_next": end_idx < len(files_list),
                    "has_prev": page > 1,
                },
                "summary": {
                    "total_files_with_errors": len(files_list),
                    "total_errors": sum(f["error_count"] for f in files_list),
                },
            }

        except Exception as e:
            logger.error(f"Error getting files for job: {e}")
            return {
                "project_id": project_id,
                "job_id": job_id,
                "error": str(e),
                "files": [],
                "pagination": {"page": page, "limit": limit, "total_files": 0},
                "summary": {"total_files_with_errors": 0, "total_errors": 0},
            }

    async def get_pipeline_files(
        self, project_id: str, pipeline_id: str, page: int = 1, limit: int = 50
    ) -> dict[str, Any]:
        """Get files with errors across all jobs in a pipeline"""
        verbose_debug_print(
            f"Getting pipeline files: project_id={project_id}, pipeline_id={pipeline_id}, page={page}, limit={limit}"
        )

        try:
            # Check if pipeline has been analyzed using utility function
            error_response = await check_pipeline_analyzed(
                project_id, pipeline_id, "pipeline_files"
            )
            if error_response:
                return error_response

            # Get all jobs for this pipeline
            pipeline_jobs = await self.cache_manager.get_pipeline_jobs(int(pipeline_id))

            # Collect all errors from all jobs, grouped by file
            all_files_with_errors = {}

            for job in pipeline_jobs:
                job_id = int(job.get("job_id", job.get("id")))
                job_errors = self.cache_manager.get_job_errors(job_id)

                for error in job_errors:
                    file_path = error.get("file_path", "unknown")
                    if file_path not in all_files_with_errors:
                        all_files_with_errors[file_path] = {
                            "file_path": file_path,
                            "error_count": 0,
                            "errors": [],
                            "jobs_affected": set(),
                        }

                    all_files_with_errors[file_path]["errors"].append(
                        {
                            **error,
                            "job_id": str(job_id),
                            "job_name": job.get("name", f"job-{job_id}"),
                        }
                    )
                    all_files_with_errors[file_path]["error_count"] += 1
                    all_files_with_errors[file_path]["jobs_affected"].add(str(job_id))

            # Convert sets to lists and sort
            for file_data in all_files_with_errors.values():
                file_data["jobs_affected"] = list(file_data["jobs_affected"])
                file_data["jobs_affected_count"] = len(file_data["jobs_affected"])

            # Convert to list and sort by error count
            files_list = list(all_files_with_errors.values())
            files_list.sort(key=lambda x: x["error_count"], reverse=True)

            # Apply pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_files = files_list[start_idx:end_idx]

            return {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "files": paginated_files,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_files": len(files_list),
                    "total_pages": (len(files_list) + limit - 1) // limit,
                    "has_next": end_idx < len(files_list),
                    "has_prev": page > 1,
                },
                "summary": {
                    "total_files_with_errors": len(files_list),
                    "total_errors": sum(f["error_count"] for f in files_list),
                    "total_jobs": len(pipeline_jobs),
                },
            }

        except Exception as e:
            logger.error(f"Error getting pipeline files: {e}")
            return {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "error": str(e),
                "files": [],
                "pagination": {"page": page, "limit": limit, "total_files": 0},
                "summary": {
                    "total_files_with_errors": 0,
                    "total_errors": 0,
                    "total_jobs": 0,
                },
            }

    async def get_file_errors_in_pipeline(
        self, project_id: str, pipeline_id: str, file_path: str
    ) -> dict[str, Any]:
        """Get all errors for a specific file across all jobs in a pipeline"""
        verbose_debug_print(
            f"Getting file errors in pipeline: project_id={project_id}, pipeline_id={pipeline_id}, file_path={file_path}"
        )

        try:
            # Get all jobs for this pipeline
            pipeline_jobs = await self.cache_manager.get_pipeline_jobs(int(pipeline_id))

            # Collect errors for this specific file from all jobs
            file_errors_by_job = {}

            for job in pipeline_jobs:
                job_id = int(job.get("job_id", job.get("id")))
                job_name = job.get("name", f"job-{job_id}")

                # Get errors for this file in this job
                file_errors = self.cache_manager.get_file_errors(job_id, file_path)

                if file_errors:
                    file_errors_by_job[str(job_id)] = {
                        "job_id": str(job_id),
                        "job_name": job_name,
                        "job_status": job.get("status", "unknown"),
                        "errors": file_errors,
                        "error_count": len(file_errors),
                    }

            # Calculate totals
            total_errors = sum(
                job_data["error_count"] for job_data in file_errors_by_job.values()
            )
            jobs_with_errors = list(file_errors_by_job.keys())

            return {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "file_path": file_path,
                "jobs_with_errors": file_errors_by_job,
                "summary": {
                    "total_errors": total_errors,
                    "jobs_affected": len(jobs_with_errors),
                    "jobs_affected_list": jobs_with_errors,
                },
            }

        except Exception as e:
            logger.error(f"Error getting file errors in pipeline: {e}")
            return {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "file_path": file_path,
                "error": str(e),
                "jobs_with_errors": {},
                "summary": {
                    "total_errors": 0,
                    "jobs_affected": 0,
                    "jobs_affected_list": [],
                },
            }

    async def get_file_jobs_in_pipeline(
        self, project_id: str, pipeline_id: str, file_path: str
    ) -> dict[str, Any]:
        """Get all jobs that have errors related to a specific file"""
        verbose_debug_print(
            f"Getting file jobs in pipeline: project_id={project_id}, pipeline_id={pipeline_id}, file_path={file_path}"
        )

        # This is essentially the same as get_file_errors_in_pipeline but focused on job info
        file_data = await self.get_file_errors_in_pipeline(
            project_id, pipeline_id, file_path
        )

        # Transform the data to focus on jobs rather than errors
        jobs_info = []
        for job_id, job_data in file_data.get("jobs_with_errors", {}).items():
            jobs_info.append(
                {
                    "job_id": job_id,
                    "job_name": job_data["job_name"],
                    "job_status": job_data["job_status"],
                    "error_count": job_data["error_count"],
                    "has_errors": job_data["error_count"] > 0,
                }
            )

        # Sort by error count descending
        jobs_info.sort(key=lambda x: x["error_count"], reverse=True)

        return {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "file_path": file_path,
            "jobs": jobs_info,
            "summary": {
                "total_jobs_with_errors": len(jobs_info),
                "total_errors_across_jobs": file_data.get("summary", {}).get(
                    "total_errors", 0
                ),
            },
        }


# Singleton instance
_file_service = None


def get_file_service() -> FileService:
    """Get the singleton FileService instance"""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
