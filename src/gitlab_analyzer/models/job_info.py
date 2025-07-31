"""
JobInfo model for GitLab CI/CD job information
"""

from pydantic import BaseModel


class JobInfo(BaseModel):
    """Information about a GitLab CI/CD job"""

    id: int
    name: str
    status: str
    stage: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    failure_reason: str | None = None
    web_url: str
