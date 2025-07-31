"""
JobInfo model for GitLab CI/CD job information

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
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
