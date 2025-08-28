"""
Database models for webhook-triggered analysis cache.

This implements the cache-first architecture where:
1. Webhook phase: Ingest pipeline/job data once, parse and persist
2. Serving phase: Fast resource access from cache
3. Invalidation: Based on job_id + trace_hash + parser_version

Data models and utilities - cache manager is in mcp_cache.py
"""

import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class CacheData:
    """Handles cache data serialization and compression"""

    @staticmethod
    def serialize(data: dict[str, Any]) -> str:
        """Serialize and compress data for storage"""
        json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        compressed = gzip.compress(json_str.encode("utf-8"))
        return compressed.hex()

    @staticmethod
    def deserialize(compressed_hex: str) -> dict[str, Any]:
        """Decompress and deserialize data from storage"""
        compressed = bytes.fromhex(compressed_hex)
        json_str = gzip.decompress(compressed).decode("utf-8")
        return json.loads(json_str)

    @staticmethod
    def calculate_size(data: dict[str, Any]) -> int:
        """Calculate the size of data in bytes"""
        json_str = json.dumps(data, ensure_ascii=False)
        return len(json_str.encode("utf-8"))


def generate_cache_key(
    data_type: str,
    project_id: str,
    pipeline_id: int | None = None,
    job_id: int | None = None,
    file_path: str | None = None,
    **kwargs,
) -> str:
    """Generate consistent cache key"""
    key_parts = [f"gl:{data_type}:{project_id}"]

    if pipeline_id is not None:
        key_parts.append(str(pipeline_id))

    if job_id is not None:
        key_parts.append(str(job_id))

    if file_path is not None:
        # Use hash for long file paths to avoid key length issues
        file_hash = hashlib.sha256(file_path.encode()).hexdigest()[:12]
        key_parts.append(file_hash)

    # Add any additional parameters
    for k, v in sorted(kwargs.items()):
        if v is not None:
            key_parts.append(f"{k}:{v}")

    return ":".join(key_parts)


def generate_error_id(
    error_type: str, message: str, file_path: str, line_number: int | None = None
) -> str:
    """Generate consistent error ID for error resources"""
    signature = f"{error_type}:{message}:{file_path}"
    if line_number:
        signature += f":{line_number}"

    return hashlib.sha256(signature.encode()).hexdigest()[:12]


def generate_standard_error_id(job_id: int, error_index: int) -> str:
    """Generate standardized error ID for job errors

    This is the SINGLE function that should be used everywhere for error ID generation
    to ensure consistency between errors and trace_segments tables.

    Format: {job_id}_{error_index}
    Example: 76986678_0, 76986678_1, etc.
    """
    return f"{job_id}_{error_index}"


class JobStatus(Enum):
    """GitLab job status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
    SKIPPED = "skipped"


@dataclass
class PipelineRecord:
    """Pipeline metadata record"""

    pipeline_id: int
    project_id: int
    ref: str
    sha: str
    status: str
    web_url: str
    created_at: datetime
    updated_at: datetime | None = None
    source_branch: str | None = None  # Resolved source branch for MR pipelines
    target_branch: str | None = None  # Target branch for MR pipelines

    @classmethod
    def from_gitlab_pipeline(cls, pipeline_data: dict[str, Any]) -> "PipelineRecord":
        """Create PipelineRecord from GitLab pipeline data"""
        created_at = datetime.fromisoformat(
            pipeline_data["created_at"].replace("Z", "+00:00")
        )
        updated_at = None
        if pipeline_data.get("updated_at"):
            updated_at = datetime.fromisoformat(
                pipeline_data["updated_at"].replace("Z", "+00:00")
            )

        return cls(
            pipeline_id=pipeline_data["id"],
            project_id=pipeline_data.get("project_id")
            or pipeline_data.get("project", {}).get("id"),
            ref=pipeline_data.get("ref", ""),
            sha=pipeline_data.get("sha", ""),
            status=pipeline_data.get("status", ""),
            web_url=pipeline_data.get("web_url", ""),
            created_at=created_at,
            updated_at=updated_at,
            source_branch=pipeline_data.get("source_branch"),  # Will be resolved later
            target_branch=pipeline_data.get("target_branch"),
        )


@dataclass
class JobRecord:
    """Job metadata record"""

    job_id: int
    project_id: int
    pipeline_id: int
    ref: str
    sha: str
    status: str
    trace_hash: str
    parser_version: int
    created_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def from_gitlab_job(
        cls, job_data: dict[str, Any], trace_text: str, parser_version: int
    ) -> "JobRecord":
        """Create JobRecord from GitLab job data and trace"""
        trace_hash = hashlib.sha256(trace_text.encode("utf-8")).hexdigest()

        # Parse timestamps
        created_at = datetime.fromisoformat(
            job_data["created_at"].replace("Z", "+00:00")
        )
        completed_at = None
        if job_data.get("finished_at"):
            completed_at = datetime.fromisoformat(
                job_data["finished_at"].replace("Z", "+00:00")
            )

        return cls(
            job_id=job_data["id"],
            project_id=job_data.get("project_id")
            or job_data.get("pipeline", {}).get("project_id"),
            pipeline_id=job_data["pipeline"]["id"],
            ref=job_data["ref"],
            sha=job_data["pipeline"]["sha"],
            status=job_data["status"],
            trace_hash=trace_hash,
            parser_version=parser_version,
            created_at=created_at,
            completed_at=completed_at,
        )


@dataclass
@dataclass
class ErrorRecord:
    """Individual error record"""

    job_id: int
    error_id: str
    fingerprint: str
    exception: str
    message: str
    file: str
    line: int
    detail_json: dict[str, Any]
    error_type: str = "unknown"

    @classmethod
    def from_parsed_error(
        cls, job_id: int, error_data: dict[str, Any], error_index: int
    ) -> "ErrorRecord":
        """Create ErrorRecord from parsed error data"""
        # Generate stable error ID using unified function
        error_id = generate_standard_error_id(job_id, error_index)

        # Create fingerprint for deduplication
        fingerprint_data = {
            "exception": error_data.get("exception", ""),
            "message": error_data.get("message", ""),
            "file": error_data.get("file", ""),
            "line": error_data.get("line", 0),
        }
        fingerprint = hashlib.md5(  # nosec B324
            json.dumps(fingerprint_data, sort_keys=True).encode(), usedforsecurity=False
        ).hexdigest()

        return cls(
            job_id=job_id,
            error_id=error_id,
            fingerprint=fingerprint,
            exception=error_data.get("exception", ""),
            message=error_data.get("message", ""),
            file=error_data.get("file", ""),
            line=error_data.get("line", 0),
            detail_json=error_data,
            error_type=error_data.get("error_type", "unknown"),
        )
