"""
GitLab API client for analyzing pipelines

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import datetime
from typing import Any

import httpx

from ..models import JobInfo


class GitLabAnalyzer:
    """GitLab API client for analyzing pipelines"""

    def __init__(self, gitlab_url: str, token: str):
        self.gitlab_url = gitlab_url.rstrip("/")
        self.token = token
        self.api_url = f"{self.gitlab_url}/api/v4"

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get_pipeline(
        self, project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """Get pipeline information"""
        url = f"{self.api_url}/projects/{project_id}/pipelines/{pipeline_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_pipeline_jobs(
        self, project_id: str | int, pipeline_id: int
    ) -> list[JobInfo]:
        """Get all jobs for a pipeline"""
        url = f"{self.api_url}/projects/{project_id}/pipelines/{pipeline_id}/jobs"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            jobs_data = response.json()

            jobs = []
            for job_data in jobs_data:
                job = JobInfo(
                    id=job_data["id"],
                    name=job_data["name"],
                    status=job_data["status"],
                    stage=job_data["stage"],
                    created_at=job_data["created_at"],
                    started_at=job_data.get("started_at"),
                    finished_at=job_data.get("finished_at"),
                    failure_reason=job_data.get("failure_reason"),
                    web_url=job_data["web_url"],
                )
                jobs.append(job)

            return jobs

    async def get_failed_pipeline_jobs(
        self, project_id: str | int, pipeline_id: int
    ) -> list[JobInfo]:
        """Get only failed jobs for a specific pipeline (more efficient)"""
        url = f"{self.api_url}/projects/{project_id}/pipelines/{pipeline_id}/jobs"
        params = {"scope[]": "failed"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            jobs_data = response.json()

            jobs = []
            for job_data in jobs_data:
                job = JobInfo(
                    id=job_data["id"],
                    name=job_data["name"],
                    status=job_data["status"],
                    stage=job_data["stage"],
                    created_at=job_data["created_at"],
                    started_at=job_data.get("started_at"),
                    finished_at=job_data.get("finished_at"),
                    failure_reason=job_data.get("failure_reason"),
                    web_url=job_data["web_url"],
                )
                jobs.append(job)

            return jobs

    async def get_job_info(
        self, project_id: str | int, job_id: int
    ) -> dict[str, Any] | None:
        """Get information for a specific job"""
        url = f"{self.api_url}/projects/{project_id}/jobs/{job_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def get_job_trace(self, project_id: str | int, job_id: int) -> str:
        """Get the trace log for a specific job"""
        url = f"{self.api_url}/projects/{project_id}/jobs/{job_id}/trace"

        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for logs
            response = await client.get(url, headers=self.headers)
            if response.status_code == 404:
                return ""
            response.raise_for_status()
            return response.text

    async def get_merge_request(
        self, project_id: str | int, merge_request_iid: int
    ) -> dict[str, Any]:
        """Get merge request information by IID"""
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{merge_request_iid}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_merge_request_overview(
        self, project_id: str | int, merge_request_iid: int
    ) -> dict[str, Any]:
        """
        Get comprehensive merge request overview with key information.

        This method extracts and structures the most important MR information
        for pipeline analysis context.

        Args:
            project_id: The GitLab project ID or path
            merge_request_iid: The merge request IID (internal ID)

        Returns:
            Dictionary containing:
            - iid: Merge request IID
            - title: MR title
            - description: MR description (may be None)
            - author: Author information (name, username)
            - state: MR state (opened, closed, merged)
            - web_url: Direct link to the MR
            - source_branch: Source branch name
            - target_branch: Target branch name
            - labels: List of labels
            - milestone: Milestone information (may be None)
            - created_at: Creation timestamp
            - updated_at: Last update timestamp

        Raises:
            httpx.HTTPError: If GitLab API request fails
            httpx.RequestError: If network request fails
        """
        # Use the existing get_merge_request method to get full data
        mr_data = await self.get_merge_request(project_id, merge_request_iid)

        # Extract and structure key information
        author_data = mr_data.get("author") or {}
        overview = {
            "iid": mr_data.get("iid"),
            "title": mr_data.get("title") or "",
            "description": mr_data.get("description") or "",
            "author": {
                "name": author_data.get("name", ""),
                "username": author_data.get("username", ""),
                "web_url": author_data.get("web_url", ""),
            },
            "state": mr_data.get("state") or "",
            "web_url": mr_data.get("web_url") or "",
            "source_branch": mr_data.get("source_branch") or "",
            "target_branch": mr_data.get("target_branch") or "",
            "labels": mr_data.get("labels") or [],
            "milestone": mr_data.get("milestone"),
            "created_at": mr_data.get("created_at") or "",
            "updated_at": mr_data.get("updated_at") or "",
        }

        return overview

    async def get_merge_request_discussions(
        self, project_id: str | int, merge_request_iid: int
    ) -> list[dict[str, Any]]:
        """
        Get all discussions (review comments, notes) for a merge request.

        This method fetches all discussions from a merge request, which includes:
        - General notes and comments
        - Code review comments on specific lines
        - System notes (e.g., status changes, approvals)
        - Resolvable discussions and their resolution status

        Args:
            project_id: The GitLab project ID or path
            merge_request_iid: The merge request IID (internal ID)

        Returns:
            List of discussions, each containing:
            - id: Discussion ID
            - individual_note: Whether this is a single note
            - notes: List of notes in the discussion
            - created_at: Discussion creation timestamp
            - updated_at: Discussion last update timestamp

        Raises:
            httpx.HTTPError: If GitLab API request fails
            httpx.RequestError: If network request fails
        """
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{merge_request_iid}/discussions"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_merge_request_notes(
        self, project_id: str | int, merge_request_iid: int
    ) -> list[dict[str, Any]]:
        """
        Get all notes for a merge request (simpler than discussions).

        This method fetches all notes from a merge request, which is a flatter
        structure than discussions and includes all comments and review feedback.

        Args:
            project_id: The GitLab project ID or path
            merge_request_iid: The merge request IID (internal ID)

        Returns:
            List of notes, each containing:
            - id: Note ID
            - type: Note type (e.g., "DiffNote", "DiscussionNote")
            - body: Note content/text
            - author: Author information
            - created_at: Note creation timestamp
            - updated_at: Note last update timestamp
            - system: Whether this is a system-generated note
            - resolvable: Whether this note can be resolved
            - resolved: Whether this note has been resolved

        Raises:
            httpx.HTTPError: If GitLab API request fails
            httpx.RequestError: If network request fails
        """
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{merge_request_iid}/notes"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_merge_request_review_summary(
        self, project_id: str | int, merge_request_iid: int
    ) -> dict[str, Any]:
        """
        Get a comprehensive review summary for a merge request.

        This method combines discussions and notes to provide a structured
        summary of all review feedback, categorized by type and importance.

        Args:
            project_id: The GitLab project ID or path
            merge_request_iid: The merge request IID (internal ID)

        Returns:
            Dictionary containing:
            - review_comments: List of code review comments
            - general_comments: List of general discussion comments
            - system_notes: List of system-generated notes
            - unresolved_discussions: List of unresolved review threads
            - approval_status: Information about approvals/rejections
            - review_statistics: Summary counts and metrics

        Raises:
            httpx.HTTPError: If GitLab API request fails
            httpx.RequestError: If network request fails
        """
        try:
            # Get both discussions and notes
            discussions = await self.get_merge_request_discussions(
                project_id, merge_request_iid
            )
            notes = await self.get_merge_request_notes(project_id, merge_request_iid)

            # Categorize review feedback
            review_comments = []
            general_comments = []
            system_notes = []
            unresolved_discussions = []

            # Process discussions for threaded conversations
            for discussion in discussions:
                discussion_notes = discussion.get("notes", [])
                if not discussion_notes:
                    continue

                first_note = discussion_notes[0]
                is_resolvable = first_note.get("resolvable", False)
                is_resolved = first_note.get("resolved", False)

                # Check if this is an unresolved discussion
                if is_resolvable and not is_resolved:
                    unresolved_discussions.append(
                        {
                            "discussion_id": discussion.get("id"),
                            "created_at": first_note.get("created_at"),
                            "author": first_note.get("author", {}).get(
                                "name", "Unknown"
                            ),
                            "body": first_note.get("body", ""),
                            "notes_count": len(discussion_notes),
                            "position": first_note.get(
                                "position"
                            ),  # Code position info
                        }
                    )

            # Process notes for different types of feedback
            for note in notes:
                note_data = {
                    "id": note.get("id"),
                    "body": note.get("body", ""),
                    "author": note.get("author", {}).get("name", "Unknown"),
                    "created_at": note.get("created_at"),
                    "updated_at": note.get("updated_at"),
                    "type": note.get("type"),
                    "system": note.get("system", False),
                    "resolvable": note.get("resolvable", False),
                    "resolved": note.get("resolved", False),
                }

                if note.get("system", False):
                    # System notes (merges, approvals, status changes)
                    system_notes.append(note_data)
                elif note.get("type") == "DiffNote":
                    # Code review comments on specific lines
                    review_comments.append(
                        {
                            **note_data,
                            "position": note.get("position"),  # File/line position
                            "diff_refs": note.get("diff_refs"),  # Diff context
                        }
                    )
                else:
                    # General discussion comments
                    general_comments.append(note_data)

            # Calculate approval status from system notes
            approval_status: dict[str, Any] = {
                "approved_count": 0,
                "unapproved_count": 0,
                "approvals": [],
                "rejections": [],
            }

            for sys_note in system_notes:
                body = sys_note.get("body", "").lower()
                author = sys_note.get("author", "Unknown")

                if "approved this merge request" in body:
                    approval_status["approved_count"] += 1
                    approval_status["approvals"].append(
                        {"author": author, "created_at": sys_note.get("created_at")}
                    )
                elif "unapproved this merge request" in body:
                    approval_status["unapproved_count"] += 1
                    approval_status["rejections"].append(
                        {"author": author, "created_at": sys_note.get("created_at")}
                    )

            # Generate review statistics
            review_statistics = {
                "total_comments": len(review_comments) + len(general_comments),
                "review_comments_count": len(review_comments),
                "general_comments_count": len(general_comments),
                "system_notes_count": len(system_notes),
                "unresolved_discussions_count": len(unresolved_discussions),
                "total_discussions": len(discussions),
                "total_notes": len(notes),
                "has_unresolved_feedback": len(unresolved_discussions) > 0,
                "approval_summary": approval_status,
            }

            return {
                "review_comments": review_comments,
                "general_comments": general_comments,
                "system_notes": system_notes,
                "unresolved_discussions": unresolved_discussions,
                "approval_status": approval_status,
                "review_statistics": review_statistics,
                "metadata": {
                    "project_id": str(project_id),
                    "merge_request_iid": merge_request_iid,
                    "retrieved_at": datetime.now().isoformat(),
                },
            }

        except (httpx.HTTPError, httpx.RequestError) as e:
            # Return error structure if API calls fail
            return {
                "error": f"Failed to get review summary: {str(e)}",
                "review_comments": [],
                "general_comments": [],
                "system_notes": [],
                "unresolved_discussions": [],
                "approval_status": {
                    "approved_count": 0,
                    "unapproved_count": 0,
                    "approvals": [],
                    "rejections": [],
                },
                "review_statistics": {
                    "total_comments": 0,
                    "has_unresolved_feedback": False,
                },
                "metadata": {
                    "project_id": str(project_id),
                    "merge_request_iid": merge_request_iid,
                    "error_at": datetime.now().isoformat(),
                },
            }

    async def search_project_code(
        self,
        project_id: str | int,
        search_term: str,
        branch: str | None = None,
        filename_filter: str | None = None,
        path_filter: str | None = None,
        extension_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for code within a project repository

        Args:
            project_id: The GitLab project ID or path
            search_term: The keyword(s) to search for
            branch: Specific branch to search (optional, defaults to project's default branch)
            filename_filter: Filter by filename pattern (supports wildcards)
            path_filter: Filter by file path pattern
            extension_filter: Filter by file extension (e.g., 'py', 'js')

        Returns:
            List of code search results with file paths, line numbers, and content snippets
        """
        url = f"{self.api_url}/projects/{project_id}/search"

        # Build search query with filters
        search_query = search_term
        if filename_filter:
            search_query += f" filename:{filename_filter}"
        if path_filter:
            search_query += f" path:{path_filter}"
        if extension_filter:
            search_query += f" extension:{extension_filter}"

        params = {"scope": "blobs", "search": search_query}  # Search in code files

        # Add branch-specific search if specified
        if branch:
            params["ref"] = branch

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def search_project_commits(
        self,
        project_id: str | int,
        search_term: str,
        branch: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for commits within a project repository

        Args:
            project_id: The GitLab project ID or path
            search_term: The keyword(s) to search for in commit messages
            branch: Specific branch to search (optional, defaults to project's default branch)

        Returns:
            List of commit search results
        """
        url = f"{self.api_url}/projects/{project_id}/search"

        params = {
            "scope": "commits",  # Search in commit messages
            "search": search_term,
        }

        # Add branch-specific search if specified
        if branch:
            params["ref"] = branch

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
