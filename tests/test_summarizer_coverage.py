"""Coverage improvement tests for summarizer module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gitlab_analyzer.analysis.summarizer import (
    ErrorSummarizer,
    MinimalErrorSummary,
    RootCauseSummary,
)


class TestSummarizerCoverage:
    """Test summarizer module to improve coverage."""

    def test_import(self):
        """Test module can be imported."""
        assert MinimalErrorSummary is not None
        assert RootCauseSummary is not None
        assert ErrorSummarizer is not None

    def test_minimal_error_summary_creation(self):
        """Test MinimalErrorSummary can be created."""
        summary = MinimalErrorSummary(
            issue="Test error",
            location="test.py:42",
            fix_suggestion="Fix the issue",
            confidence=0.8,
            error_count=5,
            affected_files=2,
        )
        assert summary is not None
        assert summary.issue == "Test error"
        assert summary.error_count == 5

    def test_root_cause_summary_creation(self):
        """Test RootCauseSummary can be created."""
        summary = RootCauseSummary(
            primary_issue="Import error",
            category="import",
            severity="high",
            quick_fix="Install missing package",
            broader_fix="Review dependencies",
            impact_assessment="Blocks pipeline",
            related_errors=3,
            key_insights=["Missing dependency"],
            context_reduction_percentage=75.0,
        )
        assert summary is not None
        assert summary.primary_issue == "Import error"

    def test_error_summarizer_creation(self):
        """Test ErrorSummarizer can be created."""
        summarizer = ErrorSummarizer()
        assert summarizer is not None
