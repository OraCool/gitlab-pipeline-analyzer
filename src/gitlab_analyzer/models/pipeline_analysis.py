"""
PipelineAnalysis model for complete pipeline analysis results

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from typing import Any

from pydantic import BaseModel

from .job_info import JobInfo
from .log_entry import LogEntry


class PipelineAnalysis(BaseModel):
    """Complete analysis of a failed pipeline"""

    pipeline_id: int
    pipeline_status: str
    failed_jobs: list[JobInfo]
    analysis: dict[str, list[LogEntry]]
    summary: dict[str, Any]
