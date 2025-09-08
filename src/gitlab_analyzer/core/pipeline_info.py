"""
Core pipeline information utilities with branch resolution.

This module provides reusable functions for getting comprehensive pipeline
information including proper branch resolution for merge request pipelines.
"""

from datetime import datetime
from typing import Any

import httpx

from ..api.client import GitLabAnalyzer
from ..utils.jira_utils import extract_jira_from_mr


async def get_comprehensive_pipeline_info(
    analyzer: GitLabAnalyzer, project_id: str | int, pipeline_id: int
) -> dict[str, Any]:
    """
    Get comprehensive pipeline information with branch resolution and MR overview.

    This function extracts the branch resolution logic that was previously
    embedded in the MCP tool, making it reusable across the codebase.

    Features:
    - Fetches basic pipeline data from GitLab API
    - Detects if pipeline is for a merge request
    - Resolves actual source/target branches for MR pipelines
    - Fetches MR overview data including title, description, author
    - Extracts Jira tickets from MR data
    - Provides structured output with type detection
    - Handles errors gracefully

    Args:
        analyzer: GitLab analyzer instance
        project_id: The GitLab project ID or path
        pipeline_id: The ID of the GitLab pipeline

    Returns:
        Dictionary containing:
        - project_id: String representation of project ID
        - pipeline_id: Pipeline ID
        - pipeline_info: Raw pipeline data from GitLab
        - original_branch: Original ref from pipeline
        - target_branch: Resolved branch (source branch for MR, ref for regular)
        - pipeline_type: "branch" or "merge_request"
        - merge_request_info: MR details if applicable, None otherwise
        - mr_overview: Structured MR overview if applicable, None otherwise
        - jira_tickets: List of Jira tickets extracted from MR
        - can_auto_fix: Whether branch info was successfully resolved
        - analysis_timestamp: ISO timestamp of analysis

    Raises:
        httpx.HTTPError: If GitLab API request fails
        httpx.RequestError: If network request fails
        ValueError: If data parsing fails
        KeyError: If expected fields are missing
    """
    # Get basic pipeline information
    pipeline_info = await analyzer.get_pipeline(project_id, pipeline_id)

    # Extract original ref from pipeline
    original_ref = pipeline_info.get("ref", "main")

    # Initialize default values
    pipeline_type = "branch"
    target_branch = original_ref
    merge_request_info = None
    mr_overview = None
    mr_review_summary = None
    jira_tickets = []
    can_auto_fix = True

    # Check if this is a merge request pipeline
    if original_ref.startswith("refs/merge-requests/"):
        pipeline_type = "merge_request"

        try:
            # Extract MR IID from ref: refs/merge-requests/123/head -> 123
            mr_iid = int(original_ref.split("/")[2])

            # Get merge request information
            merge_request_info = await analyzer.get_merge_request(project_id, mr_iid)

            # Use source branch as target for commits
            target_branch = merge_request_info["source_branch"]

            # Get comprehensive MR overview
            mr_review_summary = None
            try:
                mr_overview = await analyzer.get_merge_request_overview(
                    project_id, mr_iid
                )

                # Extract Jira tickets from MR data
                jira_tickets = extract_jira_from_mr(mr_overview)

                # Get code review summary for additional context
                try:
                    mr_review_summary = await analyzer.get_merge_request_review_summary(
                        project_id, mr_iid
                    )
                except (httpx.HTTPError, httpx.RequestError, KeyError) as review_error:
                    # If review summary fails, continue without it
                    mr_review_summary = {
                        "error": f"Failed to get review summary: {str(review_error)}"
                    }

            except (httpx.HTTPError, httpx.RequestError, KeyError) as overview_error:
                # If overview fails, still continue with basic MR info
                mr_overview = {
                    "error": f"Failed to get MR overview: {str(overview_error)}"
                }

        except (
            ValueError,
            IndexError,
            KeyError,
            httpx.HTTPError,
            httpx.RequestError,
        ) as mr_error:
            # If we can't parse MR info, mark as non-auto-fixable
            can_auto_fix = False
            target_branch = original_ref
            merge_request_info = {"error": f"Failed to parse MR info: {str(mr_error)}"}

    return {
        "project_id": str(project_id),
        "pipeline_id": pipeline_id,
        "pipeline_info": pipeline_info,
        "original_branch": original_ref,  # Keep original for reference
        "target_branch": target_branch,  # Use this for commits
        "pipeline_type": pipeline_type,  # "branch" or "merge_request"
        "merge_request_info": merge_request_info,  # MR details if applicable
        "mr_overview": mr_overview,  # Structured MR overview if applicable
        "mr_review_summary": mr_review_summary,  # Code review summary if applicable
        "jira_tickets": jira_tickets,  # List of Jira tickets from MR
        "can_auto_fix": can_auto_fix,  # Whether auto-fix should proceed
        "analysis_timestamp": datetime.now().isoformat(),
    }


async def resolve_pipeline_branches(
    analyzer: GitLabAnalyzer, pipeline_data: dict[str, Any]
) -> tuple[str, str | None, str | None]:
    """
    Resolve actual source and target branches from pipeline data.

    This is a simplified version focused only on branch resolution.

    Args:
        analyzer: GitLab analyzer instance
        pipeline_data: Raw pipeline data from GitLab API

    Returns:
        Tuple of (pipeline_type, source_branch, target_branch)
        - pipeline_type: "branch" or "merge_request"
        - source_branch: Actual source branch name (for MR) or None
        - target_branch: Actual target branch name (for MR) or None
    """
    ref = pipeline_data.get("ref", "")

    if not ref.startswith("refs/merge-requests/"):
        # Regular branch pipeline
        return "branch", None, None

    try:
        # Extract MR IID from ref
        mr_iid = int(ref.split("/")[2])
        project_id = pipeline_data.get("project_id")

        # Ensure project_id is valid
        if project_id is None:
            return "merge_request", None, None

        # Get merge request information
        mr_info = await analyzer.get_merge_request(project_id, mr_iid)

        return (
            "merge_request",
            mr_info.get("source_branch"),
            mr_info.get("target_branch"),
        )

    except (ValueError, IndexError, KeyError, httpx.HTTPError, httpx.RequestError):
        # If we can't resolve, return unknowns
        return "merge_request", None, None
