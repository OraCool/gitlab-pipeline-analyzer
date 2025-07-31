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
