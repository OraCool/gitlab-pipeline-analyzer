"""
Cache data models

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata"""

    key: str
    data_type: str
    project_id: str
    pipeline_id: int | None = None
    job_id: int | None = None
    file_path: str | None = None
    parser_type: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    data_size: int = 0
    json_data: str | None = None
    mcp_info: str | None = None

    def __post_init__(self):
        """Set default values after initialization"""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)


@dataclass
class CacheStats:
    """Cache statistics for monitoring"""

    total_entries: int
    total_size_bytes: int
    entries_by_type: dict[str, int]
    oldest_entry: datetime | None
    newest_entry: datetime | None
    hit_rate: float = 0.0
    miss_rate: float = 0.0


class CacheData:
    """Handles cache data serialization and compression"""

    @staticmethod
    def serialize(data: dict[str, Any]) -> str:
        """Serialize and compress data for storage"""
        json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        compressed = zlib.compress(json_str.encode("utf-8"))
        return compressed.hex()

    @staticmethod
    def deserialize(compressed_hex: str) -> dict[str, Any]:
        """Decompress and deserialize data from storage"""
        compressed = bytes.fromhex(compressed_hex)
        json_str = zlib.decompress(compressed).decode("utf-8")
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
        import hashlib

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
    import hashlib

    signature = f"{error_type}:{message}:{file_path}"
    if line_number:
        signature += f":{line_number}"

    return hashlib.sha256(signature.encode()).hexdigest()[:12]
