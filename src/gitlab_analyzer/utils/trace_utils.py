"""
Trace processing utilities for extracting segments and context.

This module provides utilities for processing trace logs, extracting segments
around errors, and handling trace context for storage and analysis.
"""

from gitlab_analyzer.cache.models import ErrorRecord


def extract_error_trace_segment(
    trace_lines: list[str], error: ErrorRecord, context_lines: int = 15
) -> tuple[list[str], int, int]:
    """
    Extract trace segment for a specific error with context lines.

    Args:
        trace_lines: List of trace lines
        error: ErrorRecord containing error details including line number
        context_lines: Number of lines to include before and after error

    Returns:
        Tuple of (segment_lines, start_line_index, end_line_index)
    """
    error_line = error.line if hasattr(error, "line") and error.line else 0

    # Calculate segment boundaries
    start_line = max(0, error_line - context_lines)
    end_line = min(len(trace_lines), error_line + context_lines + 1)

    # Extract segment
    segment_lines = trace_lines[start_line:end_line]

    return segment_lines, start_line, end_line


def extract_error_trace_segments_batch(
    trace_text: str, errors: list[ErrorRecord], context_lines: int = 15
) -> list[tuple[ErrorRecord, str, int, int]]:
    """
    Extract trace segments for multiple errors in batch.

    Args:
        trace_text: Full trace text
        errors: List of ErrorRecord objects
        context_lines: Number of lines to include before and after each error

    Returns:
        List of tuples: (error_record, segment_text, start_line, end_line)
    """
    trace_lines = trace_text.split("\n")
    segments = []

    for error in errors:
        segment_lines, start_line, end_line = extract_error_trace_segment(
            trace_lines, error, context_lines
        )
        segment_text = "\n".join(segment_lines)
        segments.append((error, segment_text, start_line, end_line))

    return segments


def extract_trace_excerpt(
    trace_text: str, error_line: int, mode: str = "balanced"
) -> str:
    """
    Extract trace excerpt around a specific line with different modes.

    Args:
        trace_text: Full trace text
        error_line: Line number where error occurs
        mode: Context mode - "minimal", "balanced", or "full"

    Returns:
        Formatted trace excerpt with line numbers
    """
    lines = trace_text.split("\n")

    if mode == "minimal":
        context = 2
    elif mode == "balanced":
        context = 5
    elif mode == "full":
        context = 20
    else:
        context = 5

    start = max(0, error_line - context)
    end = min(len(lines), error_line + context)

    excerpt_lines = []
    for i in range(start, end):
        marker = ">>> " if i == error_line else "    "
        excerpt_lines.append(f"{marker}{i + 1:4d}: {lines[i]}")

    return "\n".join(excerpt_lines)
