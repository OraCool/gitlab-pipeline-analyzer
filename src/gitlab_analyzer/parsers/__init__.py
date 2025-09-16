"""
Parser modules for log analysis - following SOLID principles

All parsers now implement consistent BaseFrameworkParser interface.
"""

from .base_parser import BaseParser
from .log_parser import GenericLogDetector, GenericLogParser, LogParser
from .pytest_parser import PytestDetector, PytestLogParser, PytestParser

__all__ = [
    "BaseParser",
    "LogParser",  # Legacy utility class
    "GenericLogDetector",
    "GenericLogParser",
    "PytestDetector",
    "PytestParser",
    "PytestLogParser",  # Utility class
]
