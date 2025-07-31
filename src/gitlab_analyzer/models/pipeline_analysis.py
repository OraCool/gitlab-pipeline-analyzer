"""
PipelineAnalysis model for complete pipeline analysis results
"""

from typing import Any, Dict, List
from pydantic import BaseModel
from .job_info import JobInfo
from .log_entry import LogEntry


class PipelineAnalysis(BaseModel):
    """Complete analysis of a failed pipeline"""

    pipeline_id: int
    pipeline_status: str
    failed_jobs: List[JobInfo]
    analysis: Dict[str, List[LogEntry]]
    summary: Dict[str, Any]
