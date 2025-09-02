"""
Debug utilities for GitLab Pipeline Analyzer MCP Server.

Provides centralized debug output control via environment variables.

Debug levels:
- 0: No debug output (default)
- 1: Basic debug messages
- 2: Verbose debug messages (includes basic debug)
- 3: Very verbose debug messages (includes all above)
"""

import os
import sys
from typing import Any


def get_debug_level() -> int:
    """Get the current debug level from environment variable.

    Returns:
        Debug level (0-3), defaults to 0 if not set or invalid
    """
    try:
        return int(os.environ.get("MCP_DEBUG_LEVEL", "0"))
    except ValueError:
        return 0


def is_debug_enabled(level: int = 1) -> bool:
    """Check if debug output is enabled for the given level.

    Args:
        level: Minimum debug level required (1=basic, 2=verbose, 3=very verbose)

    Returns:
        True if current debug level is >= required level
    """
    return get_debug_level() >= level


def debug_print(*args: Any, level: int = 1, **kwargs: Any) -> None:
    """Print debug message if debug level is sufficient.

    Args:
        *args: Arguments to pass to print()
        level: Required debug level (1=basic, 2=verbose, 3=very verbose)
        **kwargs: Keyword arguments to pass to print()
    """
    if is_debug_enabled(level):
        # Always use stderr to avoid interfering with STDIO protocol
        kwargs.setdefault("file", sys.stderr)
        print(*args, **kwargs)


def verbose_debug_print(*args: Any, **kwargs: Any) -> None:
    """Print verbose debug message (level 2).

    Args:
        *args: Arguments to pass to print()
        **kwargs: Keyword arguments to pass to print()
    """
    debug_print(*args, level=2, **kwargs)


def very_verbose_debug_print(*args: Any, **kwargs: Any) -> None:
    """Print very verbose debug message (level 3).

    Args:
        *args: Arguments to pass to print()
        **kwargs: Keyword arguments to pass to print()
    """
    debug_print(*args, level=3, **kwargs)


def startup_print(*args: Any, **kwargs: Any) -> None:
    """Print startup message. Always shown regardless of debug settings.

    Args:
        *args: Arguments to pass to print()
        **kwargs: Keyword arguments to pass to print()
    """
    # Always use stderr to avoid interfering with STDIO protocol
    kwargs.setdefault("file", sys.stderr)
    print(*args, **kwargs)


def error_print(*args: Any, **kwargs: Any) -> None:
    """Print error message. Always shown regardless of debug settings.

    Args:
        *args: Arguments to pass to print()
        **kwargs: Keyword arguments to pass to print()
    """
    # Always use stderr to avoid interfering with STDIO protocol
    kwargs.setdefault("file", sys.stderr)
    print(*args, **kwargs)
