"""
Webhook-triggered analysis proc        def __init__(
        self, gitlab_analyzer: GitLabAnalyzer, cache: McpCache | None = None
    ):
        self.gitlab_analyzer = gitlab_analyzer
        self.cache = cache or McpCache()_init__(
        self, gitlab_analyzer: GitLabAnalyzer, cache: McpCache | None = None
    ):
        self.gitlab_analyzer = gitlab_analyzer
        self.cache = cache or McpCache().

This implements the ingestion phase:
1. Receive {project_id, pipeline_id} from webhook
2. Fetch failed jobs and traces from GitLab
3. Parse and persist to cache
4. Mark records immutable when jobs complete
"""

import asyncio
import logging
from typing import Any
from datetime import datetime

from ..cache.mcp_cache import McpCache
from ..cache.models import JobRecord, PipelineRecord
from ..parsers.log_parser import LogParser
from ..api.client import GitLabAnalyzer


logger = logging.getLogger(__name__)


class WebhookAnalysisProcessor:
    """
    Processes webhook events to analyze and cache pipeline data.

    Flow:
    1. webhook_event({project_id, pipeline_id})
    2. get_failed_jobs()
    3. for each job: fetch_trace() -> parse() -> cache()
    4. mark_immutable() when job completes
    """

    def __init__(self, gitlab_analyzer: GitLabAnalyzer, cache: McpCache | None = None):
        self.analyzer = gitlab_analyzer
        self.cache = cache or McpCache()
        self.parser = LogParser()

    async def process_pipeline_webhook(
        self, project_id: str, pipeline_id: int
    ) -> dict[str, Any]:
        """
        Main webhook entry point: process pipeline and cache analysis.

        Returns summary of processing results.
        """
        start_time = datetime.now()
        logger.info(
            f"Processing webhook for pipeline {pipeline_id} in project {project_id}"
        )

        try:
            # Get pipeline info and jobs
            pipeline_info = await self._get_pipeline_info(project_id, pipeline_id)
            failed_jobs = await self._get_failed_jobs(project_id, pipeline_id)

            # Store pipeline info in cache
            if not pipeline_info.get("error"):
                pipeline_record = PipelineRecord.from_gitlab_pipeline(pipeline_info)
                self.cache.store_pipeline_info(pipeline_record)

            # Process each failed job
            processed_jobs = []
            cached_jobs = []
            errors = []

            for job in failed_jobs:
                try:
                    result = await self._process_job(job)
                    if result["cached"]:
                        cached_jobs.append(result["job_id"])
                    else:
                        processed_jobs.append(result["job_id"])
                except Exception as e:
                    logger.error(f"Failed to process job {job.get('id')}: {e}")
                    errors.append({"job_id": job.get("id"), "error": str(e)})

            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "status": "success",
                "pipeline_id": pipeline_id,
                "project_id": project_id,
                "pipeline_info": pipeline_info,
                "processing_summary": {
                    "total_failed_jobs": len(failed_jobs),
                    "processed_jobs": len(processed_jobs),
                    "cached_jobs": len(cached_jobs),
                    "errors": len(errors),
                    "processing_time": processing_time,
                },
                "processed_job_ids": processed_jobs,
                "cached_job_ids": cached_jobs,
                "processing_errors": errors,
            }

        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            return {
                "status": "error",
                "pipeline_id": pipeline_id,
                "project_id": project_id,
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds(),
            }

    async def _get_pipeline_info(
        self, project_id: str, pipeline_id: int
    ) -> dict[str, Any]:
        """Get basic pipeline information"""
        try:
            pipeline_data = await self.analyzer.get_pipeline(project_id, pipeline_id)
            return {
                "id": pipeline_data.get("id"),
                "status": pipeline_data.get("status"),
                "ref": pipeline_data.get("ref"),
                "sha": pipeline_data.get("sha"),
                "web_url": pipeline_data.get("web_url"),
                "created_at": pipeline_data.get("created_at"),
                "updated_at": pipeline_data.get("updated_at"),
            }
        except Exception as e:
            logger.warning(f"Could not get pipeline info: {e}")
            return {"error": str(e)}

    async def _get_failed_jobs(
        self, project_id: str, pipeline_id: int
    ) -> list[dict[str, Any]]:
        """Get all failed jobs for the pipeline"""
        try:
            all_jobs = await self.analyzer.get_pipeline_jobs(project_id, pipeline_id)

            # Convert JobInfo objects to dictionaries and filter failed jobs
            failed_jobs = []
            for job in all_jobs:
                # Convert JobInfo to dict if needed
                job_dict = job.to_dict() if hasattr(job, "to_dict") else job.__dict__
                if job_dict.get("status") == "failed":
                    failed_jobs.append(job_dict)

            logger.info(
                f"Found {len(failed_jobs)} failed jobs out of {len(all_jobs)} total jobs"
            )
            return failed_jobs

        except Exception as e:
            logger.error(f"Failed to get jobs for pipeline {pipeline_id}: {e}")
            return []

    async def _process_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single job: fetch trace, parse, and cache.

        Returns processing result with cache status.
        """
        job_id = job_data["id"]
        project_id = str(
            job_data.get("project_id") or job_data.get("pipeline", {}).get("project_id")
        )

        try:
            # Get job trace
            trace_text = await self._get_job_trace(project_id, job_id)
            if not trace_text:
                return {
                    "job_id": job_id,
                    "cached": False,
                    "error": "No trace available",
                }

            # Check if already cached
            trace_hash = self._compute_trace_hash(trace_text)
            if self.cache.is_job_cached(job_id, trace_hash):
                logger.info(f"Job {job_id} already cached with hash {trace_hash[:8]}")
                return {"job_id": job_id, "cached": True, "trace_hash": trace_hash}

            # Parse trace
            parsed_data = await self._parse_job_trace(job_data, trace_text)

            # Create job record
            job_record = JobRecord.from_gitlab_job(
                job_data, trace_text, self.cache.parser_version
            )

            # Store in cache
            self.cache.store_job_analysis(job_record, trace_text, parsed_data)

            logger.info(
                f"Processed and cached job {job_id} with {len(parsed_data.get('errors', []))} errors"
            )

            return {
                "job_id": job_id,
                "cached": False,
                "trace_hash": trace_hash,
                "errors_found": len(parsed_data.get("errors", [])),
                "parsed_data": parsed_data,
            }

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            return {"job_id": job_id, "cached": False, "error": str(e)}

    async def _get_job_trace(self, project_id: str, job_id: int) -> str | None:
        """Fetch job trace from GitLab"""
        try:
            trace = await self.analyzer.get_job_trace(project_id, job_id)
            return trace if trace else None
        except Exception as e:
            logger.warning(f"Could not get trace for job {job_id}: {e}")
            return None

    async def _parse_job_trace(
        self, job_data: dict[str, Any], trace_text: str
    ) -> dict[str, Any]:
        """Parse job trace and extract errors/problems"""
        try:
            # Use existing log parser
            errors = self.parser.extract_errors(trace_text)

            # Add job context to each error
            for error in errors:
                error.update(
                    {
                        "job_id": job_data["id"],
                        "job_name": job_data.get("name", ""),
                        "job_stage": job_data.get("stage", ""),
                        "pipeline_id": job_data.get("pipeline", {}).get("id"),
                        "ref": job_data.get("ref", ""),
                    }
                )

            # Build comprehensive analysis
            parsed_data = {
                "job_info": {
                    "id": job_data["id"],
                    "name": job_data.get("name"),
                    "stage": job_data.get("stage"),
                    "status": job_data.get("status"),
                    "failure_reason": job_data.get("failure_reason"),
                    "web_url": job_data.get("web_url"),
                },
                "errors": errors,
                "summary": {
                    "total_errors": len(errors),
                    "error_types": self._categorize_errors(errors),
                    "files_with_errors": len(
                        set(e.get("file", "") for e in errors if e.get("file"))
                    ),
                    "parser_version": self.cache.parser_version,
                    "parsed_at": datetime.now().isoformat(),
                },
            }

            return parsed_data

        except Exception as e:
            logger.error(f"Failed to parse trace: {e}")
            return {
                "job_info": {"id": job_data["id"]},
                "errors": [],
                "summary": {"total_errors": 0, "parse_error": str(e)},
                "raw_trace_length": len(trace_text),
            }

    def _categorize_errors(self, errors: list[dict[str, Any]]) -> dict[str, int]:
        """Categorize errors by type"""
        categories = {}
        for error in errors:
            error_type = error.get("level", "unknown")
            categories[error_type] = categories.get(error_type, 0) + 1
        return categories

    def _compute_trace_hash(self, trace_text: str) -> str:
        """Compute SHA256 hash of trace text"""
        import hashlib

        return hashlib.sha256(trace_text.encode("utf-8")).hexdigest()

    async def cleanup_completed_jobs(self, project_id: str, pipeline_id: int):
        """Mark jobs as immutable when they complete"""
        try:
            # This could be called periodically or via another webhook
            # For now, jobs are marked complete when we first process them
            pass
        except Exception as e:
            logger.error(f"Failed to cleanup jobs: {e}")


# Utility function for webhook integration
async def process_webhook_event(
    project_id: str, pipeline_id: int, gitlab_analyzer: GitLabAnalyzer = None
) -> dict[str, Any]:
    """
    Convenience function for processing webhook events.

    Usage:
    result = await process_webhook_event("83", 1594344)
    """
    if not gitlab_analyzer:
        # Import here to avoid circular dependencies
        from ..mcp.tools.utils import get_gitlab_analyzer

        gitlab_analyzer = get_gitlab_analyzer()

    processor = WebhookAnalysisProcessor(gitlab_analyzer)
    return await processor.process_pipeline_webhook(project_id, pipeline_id)
