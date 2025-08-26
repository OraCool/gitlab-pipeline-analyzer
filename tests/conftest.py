"""
Test configuration and fixtures for MCP server tests

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock

import pytest

from gitlab_analyzer.api.client import GitLabAnalyzer
from gitlab_analyzer.mcp.servers.server import create_server
from gitlab_analyzer.models import JobInfo


@pytest.fixture
def mock_gitlab_url():
    """Mock GitLab URL for testing"""
    return "https://gitlab.example.com"


@pytest.fixture
def mock_gitlab_token():
    """Mock GitLab token for testing"""
    return "test-token-123"


@pytest.fixture
def mock_env_vars(mock_gitlab_url, mock_gitlab_token, monkeypatch):
    """Set up mock environment variables"""
    monkeypatch.setenv("GITLAB_URL", mock_gitlab_url)
    monkeypatch.setenv("GITLAB_TOKEN", mock_gitlab_token)


@pytest.fixture
def mock_gitlab_analyzer(mock_gitlab_url, mock_gitlab_token):
    """Create a mock GitLab analyzer"""
    analyzer = Mock(spec=GitLabAnalyzer)
    analyzer.gitlab_url = mock_gitlab_url
    analyzer.token = mock_gitlab_token
    analyzer.api_url = f"{mock_gitlab_url}/api/v4"

    # Mock async methods
    analyzer.get_pipeline = AsyncMock()
    analyzer.get_pipeline_jobs = AsyncMock()
    analyzer.get_failed_jobs = AsyncMock()
    analyzer.get_job_trace = AsyncMock()

    return analyzer


@pytest.fixture
def sample_pipeline_data():
    """Sample pipeline data for testing"""
    return {
        "id": 12345,
        "iid": 123,
        "project_id": 1,
        "sha": "abc123def456",
        "ref": "main",
        "status": "failed",
        "created_at": "2025-01-01T10:00:00.000Z",
        "updated_at": "2025-01-01T10:30:00.000Z",
        "web_url": "https://gitlab.example.com/project/-/pipelines/12345",
        "user": {"id": 1, "username": "testuser", "name": "Test User"},
    }


@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return [
        JobInfo(
            id=1001,
            name="test-job",
            status="failed",
            stage="test",
            created_at="2025-01-01T10:05:00.000Z",
            started_at="2025-01-01T10:06:00.000Z",
            finished_at="2025-01-01T10:15:00.000Z",
            failure_reason="script_failure",
            web_url="https://gitlab.example.com/project/-/jobs/1001",
        ),
        JobInfo(
            id=1002,
            name="build-job",
            status="success",
            stage="build",
            created_at="2025-01-01T10:00:00.000Z",
            started_at="2025-01-01T10:01:00.000Z",
            finished_at="2025-01-01T10:05:00.000Z",
            failure_reason=None,
            web_url="https://gitlab.example.com/project/-/jobs/1002",
        ),
    ]


@pytest.fixture
def sample_failed_jobs():
    """Sample failed jobs data for testing"""
    return [
        JobInfo(
            id=1001,
            name="test-job",
            status="failed",
            stage="test",
            created_at="2025-01-01T10:05:00.000Z",
            started_at="2025-01-01T10:06:00.000Z",
            finished_at="2025-01-01T10:15:00.000Z",
            failure_reason="script_failure",
            web_url="https://gitlab.example.com/project/-/jobs/1001",
        )
    ]


@pytest.fixture
def sample_job_trace():
    """Sample job trace with errors and warnings for testing"""
    return """
Running with gitlab-runner 15.7.0
Preparing the "docker" executor
Using Docker executor with image node:18-alpine
Pulling docker image node:18-alpine ...
Using docker image node:18-alpine:latest
Preparing environment
Running on runner-abcdef12-project-1-concurrent-0 via runner-host...
Getting source from Git repository
Fetching changes with git depth set to 20...
Initialized empty Git repository in /builds/project/.git/
+ git fetch origin
+ git checkout -f main
HEAD is now at abc123d Fix CI configuration
Executing "step_script" stage of the job script
$ npm ci
npm WARN deprecated package@1.0.0: This package is deprecated
npm ERR! code ENOENT
npm ERR! syscall open
npm ERR! path /builds/project/package.json
npm ERR! errno -2
npm ERR! enoent ENOENT: no such file or directory, open '/builds/project/package.json'
npm ERR! enoent This is related to npm not being able to find a file.
npm ERR! enoent
$ npm test
npm ERR! Missing script: "test"
npm ERR!
npm ERR! Did you mean one of these?
npm ERR!     npm star # Mark your favorite packages
npm ERR!     npm stars # View packages marked as favorites
npm ERR!
npm ERR! To see a list of scripts, run:
npm ERR!   npm run
ERROR: Job failed: exit code 1
Cleaning up project directory and file based variables
"""


@pytest.fixture
def mcp_server():
    """Create a FastMCP server for testing"""
    return create_server()


@pytest.fixture
def clean_global_analyzer(monkeypatch):
    """Clean the global analyzer instance before tests"""
    import gitlab_analyzer.utils.utils

    monkeypatch.setattr(gitlab_analyzer.utils.utils, "_GITLAB_ANALYZER", None)
