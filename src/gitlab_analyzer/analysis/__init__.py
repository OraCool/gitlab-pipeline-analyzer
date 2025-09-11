"""Root cause analysis module for GitLab Pipeline Analyzer.

This module provides tools for analyzing CI/CD pipeline errors and
identifying root causes with minimal context for AI assistants.
"""

from .error_model import Error
from .root_cause_analyzer import ErrorGroup, RootCauseAnalysis, RootCauseAnalyzer

# Export main classes for easy import
__all__ = ["Error", "ErrorGroup", "RootCauseAnalysis", "RootCauseAnalyzer"]
