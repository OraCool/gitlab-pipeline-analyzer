"""
GitLab API client for analyzing pipelines

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

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
