"""
LogEntry model for CI/CD log entries

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from pydantic import BaseModel


class LogEntry(BaseModel):
    """A parsed log entry with error/warning information"""

    level: str  # "error", "warning", "info"
    message: str
    line_number: int | None = None
    timestamp: str | None = None
    context: str | None = None
    error_type: str | None = (
        None  # Classified error type (e.g., "test_failure", "linting_error")
    )
