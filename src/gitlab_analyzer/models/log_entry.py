"""
LogEntry model for parsed log entries
"""

from typing import Optional
from pydantic import BaseModel


class LogEntry(BaseModel):
    """A parsed log entry with error/warning information"""

    level: str  # "error", "warning", "info"
    message: str
    line_number: Optional[int] = None
    timestamp: Optional[str] = None
    context: Optional[str] = None
