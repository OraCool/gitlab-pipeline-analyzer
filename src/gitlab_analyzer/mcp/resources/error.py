"""
Error Resources - Resource Registration Only

This module only handles MCP resource registration for error-related endpoints.
All business logic has been moved to services for better separation of concerns.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging

from mcp.types import TextResourceContents

from gitlab_analyzer.mcp.services.error_analysis_service import error_analysis_service
from gitlab_analyzer.mcp.services.error_service import error_service
from gitlab_analyzer.utils.utils import optimize_tool_response

from .utils import create_text_resource

logger = logging.getLogger(__name__)


def register_error_resources(mcp) -> None:
    """Register error resources with MCP server"""

    @mcp.resource("gl://error/{project_id}/{job_id}")
    async def get_error_resource(project_id: str, job_id: str) -> TextResourceContents:
        """Get error analysis for a specific job."""
        return await get_error_resource_with_mode(project_id, job_id, "balanced")

    @mcp.resource("gl://error/{project_id}/{job_id}?mode={mode}")
    async def get_error_resource_with_mode(
        project_id: str, job_id: str, mode: str
    ) -> TextResourceContents:
        """Get error analysis for a specific job with specified mode."""
        data = await error_service.get_job_errors(project_id, job_id, mode)

        # Apply response mode optimization
        data = optimize_tool_response(data, mode)

        return create_text_resource(
            f"gl://error/{project_id}/{job_id}?mode={mode}",
            json.dumps(data, indent=2),
        )

    @mcp.resource("gl://error/{project_id}/{job_id}/{error_id}")
    async def get_individual_error_resource(
        project_id: str, job_id: str, error_id: str
    ) -> TextResourceContents:
        """Get individual error details with basic information."""
        return await get_individual_error_resource_with_mode(
            project_id, job_id, error_id, "balanced"
        )

    @mcp.resource("gl://error/{project_id}/{job_id}/{error_id}?mode={mode}")
    async def get_individual_error_resource_with_mode(
        project_id: str, job_id: str, error_id: str, mode: str
    ) -> TextResourceContents:
        """Get individual error details with specified mode."""
        data = await error_service.get_individual_error(
            project_id, job_id, error_id, mode
        )

        # Enhance with fix guidance if needed
        if mode in ["fixing", "detailed"] and "individual_error_analysis" in data:
            error_data = data["individual_error_analysis"]["error"]
            enhanced_error = error_analysis_service.enhance_error_with_fix_guidance(
                error_data, mode
            )
            data["individual_error_analysis"]["error"] = enhanced_error

        # Apply response mode optimization
        data = optimize_tool_response(data, mode)

        return create_text_resource(
            f"gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
            json.dumps(data, indent=2),
        )

    @mcp.resource("gl://errors/{project_id}/{job_id}")
    async def get_job_errors_resource(
        project_id: str, job_id: str
    ) -> TextResourceContents:
        """Get all errors for a specific job."""
        data = await error_service.get_job_errors(project_id, job_id, "balanced")
        return create_text_resource(
            f"gl://errors/{project_id}/{job_id}",
            json.dumps(data, indent=2),
        )

    @mcp.resource("gl://errors/{project_id}/{job_id}/{file_path}")
    async def get_job_file_errors_resource(
        project_id: str, job_id: str, file_path: str
    ) -> TextResourceContents:
        """Get errors for a specific file in a job."""
        data = await error_service.get_file_errors(project_id, job_id, file_path)
        return create_text_resource(
            f"gl://errors/{project_id}/{job_id}/{file_path}",
            json.dumps(data, indent=2),
        )

    @mcp.resource("gl://errors/{project_id}/pipeline/{pipeline_id}")
    async def get_pipeline_errors_resource(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """Get all errors across all jobs in a pipeline."""
        data = await error_service.get_pipeline_errors(project_id, pipeline_id)
        return create_text_resource(
            f"gl://errors/{project_id}/pipeline/{pipeline_id}",
            json.dumps(data, indent=2),
        )

    # Limited error resources
    @mcp.resource("gl://errors/{project_id}/{job_id}/limit/{limit}")
    async def get_limited_job_errors_resource(
        project_id: str, job_id: str, limit: str
    ) -> TextResourceContents:
        """Get limited number of errors for a job."""
        try:
            limit_num = int(limit)
        except ValueError:
            return create_text_resource(
                f"gl://errors/{project_id}/{job_id}/limit/{limit}",
                json.dumps({"error": "Invalid limit parameter"}, indent=2),
            )

        data = await error_service.get_limited_job_errors(project_id, job_id, limit_num)
        return create_text_resource(
            f"gl://errors/{project_id}/{job_id}/limit/{limit}",
            json.dumps(data, indent=2),
        )

    @mcp.resource(
        "gl://errors/{project_id}/{job_id}/limit/{limit}?mode={mode}&include_trace={include_trace}"
    )
    async def get_limited_job_errors_resource_with_params(
        project_id: str, job_id: str, limit: str, mode: str, include_trace: str
    ) -> TextResourceContents:
        """Get limited number of errors for a job with mode and trace parameters."""
        try:
            limit_num = int(limit)
            include_trace_bool = include_trace.lower() == "true"
        except ValueError:
            return create_text_resource(
                f"gl://errors/{project_id}/{job_id}/limit/{limit}?mode={mode}&include_trace={include_trace}",
                json.dumps(
                    {"error": "Invalid limit or include_trace parameter"}, indent=2
                ),
            )

        data = await error_service.get_limited_job_errors(
            project_id, job_id, limit_num, mode, include_trace_bool
        )

        # Enhance errors with fix guidance if needed
        if mode in ["fixing", "detailed"] and "errors" in data:
            enhanced_errors = error_analysis_service.enhance_errors_batch(
                data["errors"], mode
            )
            data["errors"] = enhanced_errors

        # Apply response mode optimization
        data = optimize_tool_response(data, mode)

        return create_text_resource(
            f"gl://errors/{project_id}/{job_id}/limit/{limit}?mode={mode}&include_trace={include_trace}",
            json.dumps(data, indent=2),
        )

    @mcp.resource("gl://errors/{project_id}/pipeline/{pipeline_id}/limit/{limit}")
    async def get_limited_pipeline_errors_resource(
        project_id: str, pipeline_id: str, limit: str
    ) -> TextResourceContents:
        """Get limited number of errors across all jobs in a pipeline."""
        try:
            limit_num = int(limit)
        except ValueError:
            return create_text_resource(
                f"gl://errors/{project_id}/pipeline/{pipeline_id}/limit/{limit}",
                json.dumps({"error": "Invalid limit parameter"}, indent=2),
            )

        data = await error_service.get_limited_pipeline_errors(
            project_id, pipeline_id, limit_num
        )
        return create_text_resource(
            f"gl://errors/{project_id}/pipeline/{pipeline_id}/limit/{limit}",
            json.dumps(data, indent=2),
        )

    @mcp.resource(
        "gl://errors/{project_id}/pipeline/{pipeline_id}/limit/{limit}?mode={mode}&include_trace={include_trace}"
    )
    async def get_limited_pipeline_errors_resource_with_params(
        project_id: str, pipeline_id: str, limit: str, mode: str, include_trace: str
    ) -> TextResourceContents:
        """Get limited number of errors across all jobs in a pipeline with mode and trace parameters."""
        try:
            limit_num = int(limit)
            include_trace_bool = include_trace.lower() == "true"
        except ValueError:
            return create_text_resource(
                f"gl://errors/{project_id}/pipeline/{pipeline_id}/limit/{limit}?mode={mode}&include_trace={include_trace}",
                json.dumps(
                    {"error": "Invalid limit or include_trace parameter"}, indent=2
                ),
            )

        data = await error_service.get_limited_pipeline_errors(
            project_id, pipeline_id, limit_num, mode, include_trace_bool
        )

        # Enhance errors with fix guidance if needed
        if mode in ["fixing", "detailed"] and "errors" in data:
            enhanced_errors = error_analysis_service.enhance_errors_batch(
                data["errors"], mode
            )
            data["errors"] = enhanced_errors

        # Apply response mode optimization
        data = optimize_tool_response(data, mode)

        return create_text_resource(
            f"gl://errors/{project_id}/pipeline/{pipeline_id}/limit/{limit}?mode={mode}&include_trace={include_trace}",
            json.dumps(data, indent=2),
        )

    logger.info("Error resources registered")
