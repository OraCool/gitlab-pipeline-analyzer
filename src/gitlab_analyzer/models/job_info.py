"""
JobInfo model for GitLab CI/CD job information
"""

from typing import Optional
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
