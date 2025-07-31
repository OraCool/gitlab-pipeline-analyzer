#!/usr/bin/env python3
"""
GitLab Pipeline Analyzer MCP Server

A FastMCP server that analyzes GitLab CI/CD pipeline failures, extracts errors
and warnings from job traces, and returns structured JSON responses for AI
analysis.
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel


class JobInfo(BaseModel):
    """Information about a GitLab CI/CD job"""
    id: int
    name: str
    status: str
    stage: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    failure_reason: Optional[str] = None
    web_url: str


class LogEntry(BaseModel):
    """A parsed log entry with error/warning information"""
    level: str  # "error", "warning", "info"
    message: str
    line_number: Optional[int] = None
    timestamp: Optional[str] = None
    context: Optional[str] = None


class PipelineAnalysis(BaseModel):
    """Complete analysis of a failed pipeline"""
    pipeline_id: int
    pipeline_status: str
    failed_jobs: List[JobInfo]
    analysis: Dict[str, List[LogEntry]]
    summary: Dict[str, Any]


class GitLabAnalyzer:
    """GitLab API client for analyzing pipelines"""
    
    def __init__(self, gitlab_url: str, token: str):
        self.gitlab_url = gitlab_url.rstrip('/')
        self.token = token
        self.api_url = f"{self.gitlab_url}/api/v4"
        
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def get_pipeline(
        self, project_id: Union[str, int], pipeline_id: int
    ) -> Dict[str, Any]:
        """Get pipeline information"""
        url = (
            f"{self.api_url}/projects/{project_id}/"
            f"pipelines/{pipeline_id}"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def get_pipeline_jobs(
        self, project_id: Union[str, int], pipeline_id: int
    ) -> List[JobInfo]:
        """Get all jobs for a pipeline"""
        url = (
            f"{self.api_url}/projects/{project_id}/"
            f"pipelines/{pipeline_id}/jobs"
        )
        
        async with httpx.AsyncClient() as client:
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
                    web_url=job_data["web_url"]
                )
                jobs.append(job)
            
            return jobs
    
    async def get_failed_pipeline_jobs(
        self, project_id: Union[str, int], pipeline_id: int
    ) -> List[JobInfo]:
        """Get only failed jobs for a specific pipeline (more efficient)"""
        url = (
            f"{self.api_url}/projects/{project_id}/"
            f"pipelines/{pipeline_id}/jobs"
        )
        params = {"scope[]": "failed"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=self.headers, params=params
            )
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
                    web_url=job_data["web_url"]
                )
                jobs.append(job)
            
            return jobs
    
    async def get_job_trace(
        self, project_id: Union[str, int], job_id: int
    ) -> str:
        """Get the trace log for a specific job"""
        url = f"{self.api_url}/projects/{project_id}/jobs/{job_id}/trace"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 404:
                return ""
            response.raise_for_status()
            return response.text


class LogParser:
    """Parser for extracting errors and warnings from CI/CD logs"""
    
    # Common error patterns for Python projects
    ERROR_PATTERNS = [
        # Python errors
        (r'(.*)Error: (.+)', 'error'),
        (r'(.*)Exception: (.+)', 'error'),
        (r'(.*)Traceback \(most recent call last\):', 'error'),
        (r'(.*)FAILED (.+)', 'error'),
        (r'(.*)FAIL: (.+)', 'error'),
        (r'(.*)E\s+(.+)', 'error'),  # pytest errors
        
        # Build/compilation errors
        (r'(.*)fatal error: (.+)', 'error'),
        (r'(.*)error: (.+)', 'error'),
        (r'(.*)ERROR: (.+)', 'error'),
        
        # Linting errors
        (r'(.*)pylint: (.+)', 'error'),
        (r'(.*)flake8: (.+)', 'error'),
        (r'(.*)mypy: (.+)', 'error'),
        
        # Test framework errors
        (r'(.*)AssertionError: (.+)', 'error'),
        (r'(.*)Test failed: (.+)', 'error'),
        
        # General failure patterns
        (r'(.*)Command failed with exit code (\d+)', 'error'),
        (r'(.*)Process exited with code (\d+)', 'error'),
    ]
    
    WARNING_PATTERNS = [
        (r'(.*)Warning: (.+)', 'warning'),
        (r'(.*)WARNING: (.+)', 'warning'),
        (r'(.*)WARN: (.+)', 'warning'),
        (r'(.*)DeprecationWarning: (.+)', 'warning'),
        (r'(.*)UserWarning: (.+)', 'warning'),
        (r'(.*)FutureWarning: (.+)', 'warning'),
    ]
    
    @classmethod
    def extract_log_entries(cls, log_text: str) -> List[LogEntry]:
        """Extract error and warning entries from log text"""
        entries = []
        lines = log_text.split('\n')
        
        for line_num, log_line in enumerate(lines, 1):
            log_line = log_line.strip()
            if not log_line:
                continue
            
            # Check for errors
            for pattern, level in cls.ERROR_PATTERNS:
                match = re.search(pattern, log_line, re.IGNORECASE)
                if match:
                    entry = LogEntry(
                        level=level,
                        message=log_line,
                        line_number=line_num,
                        context=cls._get_context(lines, line_num)
                    )
                    entries.append(entry)
                    break
            
            # Check for warnings
            for pattern, level in cls.WARNING_PATTERNS:
                match = re.search(pattern, log_line, re.IGNORECASE)
                if match:
                    entry = LogEntry(
                        level=level,
                        message=log_line,
                        line_number=line_num,
                        context=cls._get_context(lines, line_num)
                    )
                    entries.append(entry)
                    break
        
        return entries
    
    @classmethod
    def _get_context(cls, lines: List[str], current_line: int, context_size: int = 2) -> str:
        """Get surrounding context for a log entry"""
        start = max(0, current_line - context_size - 1)
        end = min(len(lines), current_line + context_size)
        context_lines = lines[start:end]
        return '\n'.join(context_lines)


# Initialize FastMCP server
mcp = FastMCP("GitLab Pipeline Analyzer")

# Initialize GitLab analyzer (will be configured from environment variables)
gitlab_analyzer: Optional[GitLabAnalyzer] = None


def get_gitlab_analyzer() -> GitLabAnalyzer:
    """Get or create GitLab analyzer instance"""
    global gitlab_analyzer
    
    if gitlab_analyzer is None:
        gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        gitlab_token = os.getenv("GITLAB_TOKEN")
        
        if not gitlab_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")
        
        gitlab_analyzer = GitLabAnalyzer(gitlab_url, gitlab_token)
    
    return gitlab_analyzer


@mcp.tool
async def analyze_failed_pipeline(
    project_id: Union[str, int], pipeline_id: int
) -> Dict[str, Any]:
    """
    Analyze a failed GitLab CI/CD pipeline and extract errors/warnings from all 
    failed jobs. Uses optimized API calls to fetch only failed jobs.
    
    Args:
        project_id: The GitLab project ID or path
        pipeline_id: The ID of the GitLab pipeline to analyze
        
    Returns:
        Complete analysis including pipeline info, failed jobs, and extracted 
        errors/warnings
    """
    return await analyze_failed_pipeline_optimized(project_id, pipeline_id)


async def analyze_failed_pipeline_optimized(
    project_id: Union[str, int], pipeline_id: int
) -> Dict[str, Any]:
    """
    Optimized version that only fetches failed jobs (faster for large pipelines)
    
    Args:
        project_id: The GitLab project ID or path
        pipeline_id: The ID of the GitLab pipeline to analyze
        
    Returns:
        Analysis focusing only on failed jobs without total job statistics
    """
    analyzer = get_gitlab_analyzer()
    
    try:
        # Get pipeline information
        pipeline = await analyzer.get_pipeline(project_id, pipeline_id)
        
        # Get only failed jobs (optimized - single API call)
        failed_jobs = await analyzer.get_failed_pipeline_jobs(
            project_id, pipeline_id
        )
        
        # Analyze each failed job
        analysis = {}
        for job in failed_jobs:
            trace = await analyzer.get_job_trace(project_id, job.id)
            log_entries = LogParser.extract_log_entries(trace)
            analysis[job.name] = [entry.dict() for entry in log_entries]
        
        # Create summary (without total job count for efficiency)
        total_errors = sum(
            len([entry for entry in entries if entry["level"] == "error"])
            for entries in analysis.values()
        )
        total_warnings = sum(
            len([entry for entry in entries if entry["level"] == "warning"])
            for entries in analysis.values()
        )
        
        summary = {
            "pipeline_id": pipeline_id,
            "pipeline_status": pipeline["status"],
            "failed_jobs_count": len(failed_jobs),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "failed_stages": list(set(job.stage for job in failed_jobs)),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        result = {
            "pipeline_id": pipeline_id,
            "pipeline_status": pipeline["status"],
            "pipeline_url": pipeline["web_url"],
            "failed_jobs": [job.dict() for job in failed_jobs],
            "analysis": analysis,
            "summary": summary
        }
        
        return result
        
    except Exception as e:
        return {
            "error": f"Failed to analyze pipeline {pipeline_id}: {str(e)}",
            "pipeline_id": pipeline_id
        }


@mcp.tool
async def get_pipeline_jobs(
    project_id: Union[str, int], pipeline_id: int
) -> Dict[str, Any]:
    """
    Get all jobs for a specific GitLab pipeline.
    
    Args:
        project_id: The GitLab project ID or path
        pipeline_id: The ID of the GitLab pipeline
        
    Returns:
        List of all jobs in the pipeline with their status and details
    """
    analyzer = get_gitlab_analyzer()
    
    try:
        jobs = await analyzer.get_pipeline_jobs(project_id, pipeline_id)
        return {
            "project_id": str(project_id),
            "pipeline_id": pipeline_id,
            "jobs": [job.dict() for job in jobs],
            "total_jobs": len(jobs),
            "failed_jobs": len([job for job in jobs if job.status == "failed"]),
            "passed_jobs": len([job for job in jobs if job.status == "success"]),
        }
    except Exception as e:
        return {
            "error": f"Failed to get jobs for pipeline {pipeline_id}: {str(e)}",
            "project_id": str(project_id),
            "pipeline_id": pipeline_id
        }


@mcp.tool
async def get_job_trace(
    project_id: Union[str, int], job_id: int
) -> Dict[str, Any]:
    """
    Get the trace log for a specific GitLab CI/CD job.
    
    Args:
        project_id: The GitLab project ID or path
        job_id: The ID of the GitLab job
        
    Returns:
        The complete trace log for the job
    """
    analyzer = get_gitlab_analyzer()
    
    try:
        trace = await analyzer.get_job_trace(project_id, job_id)
        return {
            "project_id": str(project_id),
            "job_id": job_id,
            "trace": trace,
            "trace_length": len(trace),
            "has_content": bool(trace.strip())
        }
    except Exception as e:
        return {
            "error": f"Failed to get trace for job {job_id}: {str(e)}",
            "project_id": str(project_id),
            "job_id": job_id
        }


@mcp.tool
async def extract_log_errors(log_text: str) -> Dict[str, Any]:
    """
    Extract errors and warnings from log text.
    
    Args:
        log_text: The log text to analyze
        
    Returns:
        Extracted errors and warnings with context
    """
    try:
        log_entries = LogParser.extract_log_entries(log_text)
        
        errors = [entry.dict() for entry in log_entries if entry.level == "error"]
        warnings = [entry.dict() for entry in log_entries if entry.level == "warning"]
        
        return {
            "total_entries": len(log_entries),
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "analysis_timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": f"Failed to extract log errors: {str(e)}"
        }


@mcp.tool
async def get_pipeline_status(
    project_id: Union[str, int], pipeline_id: int
) -> Dict[str, Any]:
    """
    Get the current status and basic information of a GitLab pipeline.
    
    Args:
        project_id: The GitLab project ID or path
        pipeline_id: The ID of the GitLab pipeline
        
    Returns:
        Pipeline status and basic information
    """
    analyzer = get_gitlab_analyzer()
    
    try:
        pipeline = await analyzer.get_pipeline(project_id, pipeline_id)
        return {
            "project_id": str(project_id),
            "pipeline_id": pipeline_id,
            "status": pipeline["status"],
            "created_at": pipeline["created_at"],
            "updated_at": pipeline["updated_at"],
            "web_url": pipeline["web_url"],
            "ref": pipeline["ref"],
            "sha": pipeline["sha"],
            "source": pipeline.get("source", "unknown")
        }
    except Exception as e:
        return {
            "error": f"Failed to get pipeline status for {pipeline_id}: {str(e)}",
            "project_id": str(project_id),
            "pipeline_id": pipeline_id
        }


if __name__ == "__main__":
    # Load environment variables from .env file if it exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Run the FastMCP server
    mcp.run()
