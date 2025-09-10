"""Error models for root cause analysis."""

from dataclasses import dataclass


@dataclass
class Error:
    """Standardized error representation for root cause analysis."""

    message: str
    file_path: str | None = None
    line_number: int | None = None
    level: str = "error"
    exception_type: str | None = None
    context: str | None = None

    @classmethod
    def from_dict(cls, error_data: dict) -> "Error":
        """Create Error from dictionary (from parsed logs)."""
        return cls(
            message=error_data.get("message", ""),
            file_path=error_data.get("file", error_data.get("test_file")),
            line_number=error_data.get("line_number"),
            level=error_data.get("level", "error"),
            exception_type=error_data.get("exception_type", error_data.get("type")),
            context=error_data.get("context"),
        )

    @classmethod
    def from_log_entry(cls, log_entry) -> "Error":
        """Create Error from LogEntry model."""
        return cls(
            message=log_entry.message,
            file_path=None,  # LogEntry doesn't have file_path
            line_number=log_entry.line_number,
            level=log_entry.level,
            exception_type=log_entry.error_type,
            context=log_entry.context,
        )
