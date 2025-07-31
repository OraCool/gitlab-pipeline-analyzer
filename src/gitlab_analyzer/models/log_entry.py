"""
LogEntry model for parsed log entries
"""

from pydantic import BaseModel


class LogEntry(BaseModel):
    """A parsed log entry with error/warning information"""

    level: str  # "error", "warning", "info"
    message: str
    line_number: int | None = None
    timestamp: str | None = None
    context: str | None = None
