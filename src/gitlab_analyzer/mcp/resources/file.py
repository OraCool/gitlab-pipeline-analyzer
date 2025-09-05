"""
File resources for MCP server - SOLID refactored version

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging

from mcp.types import TextResourceContents

from ..services.file_analysis_service import get_file_analysis_service
from ..services.file_service import get_file_service
from .utils import create_text_resource

logger = logging.getLogger(__name__)


def register_file_resources(mcp) -> None:
    """Register file resources with MCP server"""

    file_service = get_file_service()
    file_analysis_service = get_file_analysis_service()

    @mcp.resource("gl://files/{project_id}/pipeline/{pipeline_id}")
    async def get_pipeline_files_resource_handler(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """
        Get all files with errors across all jobs in a pipeline from database only.

        Returns a comprehensive list of files that have errors in any job within the pipeline,
        aggregated with error counts and job information.
        Uses only pre-analyzed data from the database cache.
        """
        result = await file_service.get_pipeline_files(project_id, pipeline_id)
        return create_text_resource(
            f"gl://files/{project_id}/pipeline/{pipeline_id}", result
        )

    @mcp.resource(
        "gl://files/{project_id}/pipeline/{pipeline_id}/page/{page}/limit/{limit}"
    )
    async def get_pipeline_files_resource_paginated(
        project_id: str, pipeline_id: str, page: str, limit: str
    ) -> TextResourceContents:
        """
        Get paginated list of files with errors across all jobs in a pipeline from database only.
        """
        try:
            page_num = int(page)
            limit_num = int(limit)
        except ValueError:
            page_num = 1
            limit_num = 50

        result = await file_service.get_pipeline_files(
            project_id, pipeline_id, page=page_num, limit=limit_num
        )
        return create_text_resource(
            f"gl://files/{project_id}/pipeline/{pipeline_id}/page/{page}/limit/{limit}",
            result,
        )

    @mcp.resource("gl://files/{project_id}/pipeline/{pipeline_id}/enhanced")
    async def get_pipeline_files_resource_enhanced_handler(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """
        Get enhanced analysis of files with errors across all jobs in a pipeline.

        Similar to the basic pipeline files resource, but includes additional analysis
        such as error categorization, trace data (if requested), and enhanced metadata.
        Query parameters:
        - mode: analysis mode (detailed, balanced, quick)
        - include_trace: include trace data (true/false)
        - max_errors: maximum errors per file to include (default: 10)
        """
        # Default values
        mode = "balanced"
        include_trace = "false"
        max_errors = 10

        result = await file_analysis_service.get_enhanced_pipeline_files(
            project_id,
            pipeline_id,
            mode=mode,
            include_trace=include_trace,
            max_errors=max_errors,
        )
        return create_text_resource(
            f"gl://files/{project_id}/pipeline/{pipeline_id}/enhanced", result
        )

    @mcp.resource(
        "gl://files/{project_id}/pipeline/{pipeline_id}/enhanced/page/{page}/limit/{limit}"
    )
    async def get_pipeline_files_resource_enhanced_paginated(
        project_id: str, pipeline_id: str, page: str, limit: str
    ) -> TextResourceContents:
        """
        Get paginated enhanced analysis of files with errors across all jobs in a pipeline.
        """
        try:
            page_num = int(page)
            limit_num = int(limit)
        except ValueError:
            page_num = 1
            limit_num = 50

        # Default values for enhancement
        mode = "balanced"
        include_trace = "false"
        max_errors = 10

        # Get enhanced data first, then apply pagination
        enhanced_result = await file_analysis_service.get_enhanced_pipeline_files(
            project_id,
            pipeline_id,
            mode=mode,
            include_trace=include_trace,
            max_errors=max_errors,
        )

        # Apply pagination to the files
        all_files = enhanced_result.get("files", [])
        start_idx = (page_num - 1) * limit_num
        end_idx = start_idx + limit_num
        paginated_files = all_files[start_idx:end_idx]

        # Update the result with paginated data
        enhanced_result["files"] = paginated_files
        enhanced_result["pagination"] = {
            "page": page_num,
            "limit": limit_num,
            "total_files": len(all_files),
            "total_pages": (len(all_files) + limit_num - 1) // limit_num,
            "has_next": end_idx < len(all_files),
            "has_prev": page_num > 1,
        }

        return create_text_resource(
            f"gl://files/{project_id}/pipeline/{pipeline_id}/enhanced/page/{page}/limit/{limit}",
            enhanced_result,
        )

    @mcp.resource("gl://file/{project_id}/{job_id}/{file_path}")
    async def get_file_resource_handler(
        project_id: str, job_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get analysis for a specific file in a specific job from database only.
        """
        result = await file_service.get_file_data(project_id, job_id, file_path)
        return create_text_resource(
            f"gl://file/{project_id}/{job_id}/{file_path}", result
        )

    @mcp.resource("gl://files/{project_id}/{job_id}")
    async def get_files_resource_handler(
        project_id: str, job_id: str
    ) -> TextResourceContents:
        """
        Get all files with errors in a specific job from database only.
        """
        result = await file_service.get_files_for_job(project_id, job_id)
        return create_text_resource(f"gl://files/{project_id}/{job_id}", result)

    @mcp.resource("gl://files/{project_id}/{job_id}/page/{page}/limit/{limit}")
    async def get_files_resource_paginated(
        project_id: str, job_id: str, page: str, limit: str
    ) -> TextResourceContents:
        """
        Get paginated list of files with errors in a specific job from database only.
        """
        try:
            page_num = int(page)
            limit_num = int(limit)
        except ValueError:
            page_num = 1
            limit_num = 50

        result = await file_service.get_files_for_job(
            project_id, job_id, page=page_num, limit=limit_num
        )
        return create_text_resource(
            f"gl://files/{project_id}/{job_id}/page/{page}/limit/{limit}", result
        )

    @mcp.resource("gl://file/{project_id}/{job_id}/{file_path}/trace")
    async def get_file_resource_with_trace_handler(
        project_id: str, job_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get file analysis with optional trace data from database only.

        Query parameters supported:
        - mode: analysis mode (detailed, balanced, quick)
        - include_trace: whether to include trace data (true/false)
        """
        # Default values
        mode = "balanced"
        include_trace = "false"

        result = await file_analysis_service.get_file_with_trace(
            project_id, job_id, file_path, mode=mode, include_trace=include_trace
        )
        return create_text_resource(
            f"gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={include_trace}",
            result,
        )

    @mcp.resource("gl://errors/{project_id}/pipeline/{pipeline_id}/{file_path}")
    async def get_pipeline_file_errors_resource_handler(
        project_id: str, pipeline_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get all errors for a specific file across all jobs in a pipeline from database only.

        This resource shows how a specific file fails across different jobs in the same pipeline,
        useful for understanding file-specific issues that affect multiple build stages.
        """
        result = await file_service.get_file_errors_in_pipeline(
            project_id, pipeline_id, file_path
        )
        return create_text_resource(
            f"gl://errors/{project_id}/pipeline/{pipeline_id}/{file_path}", result
        )

    @mcp.resource("gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/trace")
    async def get_pipeline_file_trace_resource_handler_with_params(
        project_id: str, pipeline_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get trace data for a specific file across all jobs in a pipeline.

        Query parameters supported:
        - mode: analysis mode (detailed, balanced, quick)
        - include_trace: whether to include trace data (true/false)
        """
        # Default values
        mode = "balanced"
        include_trace = "true"  # Default to true for trace endpoint

        # Get errors for this file across the pipeline
        file_errors_data = await file_service.get_file_errors_in_pipeline(
            project_id, pipeline_id, file_path
        )

        # Enhance with trace data if requested
        if include_trace == "true":
            enhanced_data = await file_analysis_service.get_file_with_trace(
                project_id,
                list(file_errors_data.get("jobs_with_errors", {}).keys())[0]
                if file_errors_data.get("jobs_with_errors")
                else "unknown",
                file_path,
                mode=mode,
                include_trace=include_trace,
            )
            file_errors_data.update(enhanced_data.get("trace_data", {}))

        return create_text_resource(
            f"gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/trace?mode={mode}&include_trace={include_trace}",
            file_errors_data,
        )

    @mcp.resource("gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}")
    async def get_pipeline_file_trace_resource_handler(
        project_id: str, pipeline_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get basic file analysis for a specific file across all jobs in a pipeline.
        """
        result = await file_service.get_file_errors_in_pipeline(
            project_id, pipeline_id, file_path
        )
        return create_text_resource(
            f"gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}", result
        )

    @mcp.resource("gl://jobs/{project_id}/pipeline/{pipeline_id}/{file_path}")
    async def get_pipeline_file_jobs_resource_handler(
        project_id: str, pipeline_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get all jobs that have errors related to a specific file in a pipeline.

        This resource is useful for understanding which build stages or jobs
        are affected by issues in a particular file.
        """
        result = await file_service.get_file_jobs_in_pipeline(
            project_id, pipeline_id, file_path
        )
        return create_text_resource(
            f"gl://jobs/{project_id}/pipeline/{pipeline_id}/{file_path}", result
        )
