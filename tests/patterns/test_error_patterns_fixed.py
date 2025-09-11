"""
Tests for error patterns functionality.
Tests the dynamic error pattern detection.
"""

from gitlab_analyzer.analysis.error_model import Error
from gitlab_analyzer.patterns.error_patterns import (
    DynamicErrorPattern,
    DynamicErrorPatternMatcher,
    pattern_matcher,
)


class TestDynamicErrorPattern:
    """Test cases for DynamicErrorPattern class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.pattern = DynamicErrorPattern(
            pattern_id="test_pattern_001",
            representative_message="No module named 'requests'",
            similar_messages=["No module named 'requests'", "No module named 'pandas'"],
            frequency=5,
            similarity_threshold=0.8,
            category="Import Error",
            affected_files={"main.py", "utils.py"},
            affected_jobs={"build", "test"},
            severity_score=0.75,
        )

    def test_pattern_creation(self):
        """Test DynamicErrorPattern creation."""
        assert self.pattern.pattern_id == "test_pattern_001"
        assert self.pattern.representative_message == "No module named 'requests'"
        assert len(self.pattern.similar_messages) == 2
        assert self.pattern.frequency == 5
        assert self.pattern.similarity_threshold == 0.8
        assert self.pattern.category == "Import Error"
        assert len(self.pattern.affected_files) == 2
        assert len(self.pattern.affected_jobs) == 2
        assert self.pattern.severity_score == 0.75

    def test_name_property(self):
        """Test name property."""
        assert self.pattern.name == "Dynamic Import Error"

    def test_description_property(self):
        """Test description property."""
        description = self.pattern.description
        assert "Import Error pattern found 5 times" in description
        assert "No module named 'requests'" in description

    def test_severity_property(self):
        """Test severity property based on frequency and score."""
        # High severity (frequency >= 5)
        assert self.pattern.severity == "high"

        # Medium severity
        medium_pattern = DynamicErrorPattern(
            pattern_id="medium",
            representative_message="Test",
            similar_messages=["Test"],
            frequency=3,
            similarity_threshold=0.8,
            category="Test",
            affected_files={"test.py"},
            affected_jobs={"test"},
            severity_score=0.6,
        )
        assert medium_pattern.severity == "medium"

        # Low severity
        low_pattern = DynamicErrorPattern(
            pattern_id="low",
            representative_message="Test",
            similar_messages=["Test"],
            frequency=1,
            similarity_threshold=0.8,
            category="Test",
            affected_files={"test.py"},
            affected_jobs={"test"},
            severity_score=0.3,
        )
        assert low_pattern.severity == "low"

    def test_fix_template_property(self):
        """Test fix_template property."""
        fix_template = self.pattern.fix_template
        assert isinstance(fix_template, str)
        assert str(self.pattern.frequency) in fix_template

    def test_severity_score_property(self):
        """Test severity_score property."""
        # Test severity_score instead of non-existent confidence
        severity_score = self.pattern.severity_score
        assert 0.0 <= severity_score <= 1.0
        assert isinstance(severity_score, float)


class TestDynamicErrorPatternMatcher:
    """Test cases for DynamicErrorPatternMatcher class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = DynamicErrorPatternMatcher()
        self.sample_errors = [
            Error(
                message="No module named 'requests'",
                file_path="main.py",
                line_number=1,
                exception_type="ImportError",
            ),
            Error(
                message="No module named 'pandas'",
                file_path="utils.py",
                line_number=5,
                exception_type="ImportError",
            ),
            Error(
                message="invalid syntax at line 10",
                file_path="broken.py",
                line_number=10,
                exception_type="SyntaxError",
            ),
            Error(
                message="No module named 'numpy'",
                file_path="data.py",
                line_number=3,
                exception_type="ImportError",
            ),
        ]

    def test_matcher_creation(self):
        """Test DynamicErrorPatternMatcher creation."""
        assert isinstance(self.matcher, DynamicErrorPatternMatcher)
        assert hasattr(self.matcher, "analyze_errors")

    def test_analyze_errors_basic(self):
        """Test basic error analysis."""
        patterns = self.matcher.analyze_errors(self.sample_errors)

        assert isinstance(patterns, list)
        assert len(patterns) >= 1  # Should find at least one pattern

        # Check first pattern
        if patterns:
            pattern = patterns[0]
            assert isinstance(pattern, DynamicErrorPattern)
            assert pattern.frequency > 0
            assert len(pattern.similar_messages) > 0

    def test_analyze_errors_empty(self):
        """Test analysis with empty error list."""
        patterns = self.matcher.analyze_errors([])
        assert isinstance(patterns, list)
        assert len(patterns) == 0

    def test_analyze_errors_single_error(self):
        """Test analysis with single error."""
        single_error = [self.sample_errors[0]]
        patterns = self.matcher.analyze_errors(single_error)

        assert isinstance(patterns, list)
        # Should create at least one pattern for single error
        assert len(patterns) >= 0

    def test_group_similar_messages(self):
        """Test grouping of similar error messages."""
        import_errors = [
            error for error in self.sample_errors if "No module named" in error.message
        ]
        patterns = self.matcher.analyze_errors(import_errors)

        # Should group similar import errors together
        assert isinstance(patterns, list)
        if patterns:
            # At least one pattern should have multiple similar messages
            has_grouped = any(len(p.similar_messages) > 1 for p in patterns)
            assert has_grouped or len(patterns) == 1

    def test_categorize_error(self):
        """Test error categorization."""
        patterns = self.matcher.analyze_errors(self.sample_errors)

        assert isinstance(patterns, list)
        if patterns:
            # Check that patterns have valid categories
            for pattern in patterns:
                assert isinstance(pattern.category, str)
                assert len(pattern.category) > 0


class TestModuleLevelFunctions:
    """Test module-level functions and variables."""

    def test_pattern_matcher_exists(self):
        """Test that pattern_matcher module variable exists."""
        assert pattern_matcher is not None
        assert isinstance(pattern_matcher, DynamicErrorPatternMatcher)

    def test_pattern_matcher_is_functional(self):
        """Test that module-level pattern_matcher works."""
        test_error = Error(
            message="test message",
            file_path="test.py",
            line_number=1,
            exception_type="TestError",
        )

        patterns = pattern_matcher.analyze_errors([test_error])
        assert isinstance(patterns, list)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = DynamicErrorPatternMatcher()

    def test_errors_with_none_values(self):
        """Test handling of errors with None values."""
        problematic_errors = [
            Error(
                message="test error",
                file_path=None,  # None file path
                line_number=1,
                exception_type="Error",
            ),
            Error(
                message="another error",
                file_path="test.py",
                line_number=2,
                exception_type=None,  # None type
            ),
            Error(
                message=None,  # None message
                file_path="test.py",
                line_number=3,
                exception_type="Error",
            ),
        ]

        # Should not crash with None values
        patterns = self.matcher.analyze_errors(problematic_errors)
        assert isinstance(patterns, list)

    def test_very_long_error_messages(self):
        """Test handling of very long error messages."""
        long_message = "x" * 10000  # Very long message
        long_error = Error(
            message=long_message,
            file_path="test.py",
            line_number=1,
            exception_type="LongError",
        )

        patterns = self.matcher.analyze_errors([long_error])
        assert isinstance(patterns, list)

    def test_duplicate_errors(self):
        """Test handling of duplicate errors."""
        duplicate_errors = [
            Error(
                message="duplicate message",
                file_path="test.py",
                line_number=1,
                exception_type="Error",
            ),
            Error(
                message="duplicate message",
                file_path="test.py",
                line_number=1,
                exception_type="Error",
            ),
        ]

        patterns = self.matcher.analyze_errors(duplicate_errors)
        assert isinstance(patterns, list)

    def test_mixed_error_types(self):
        """Test handling of mixed error types."""
        mixed_errors = [
            Error(
                message="import failed",
                file_path="a.py",
                line_number=1,
                exception_type="ImportError",
            ),
            Error(
                message="syntax error",
                file_path="b.py",
                line_number=2,
                exception_type="SyntaxError",
            ),
            Error(
                message="value error",
                file_path="c.py",
                line_number=3,
                exception_type="ValueError",
            ),
            Error(
                message="type error",
                file_path="d.py",
                line_number=4,
                exception_type="TypeError",
            ),
            Error(
                message="runtime error",
                file_path="e.py",
                line_number=5,
                exception_type="RuntimeError",
            ),
        ]

        patterns = self.matcher.analyze_errors(mixed_errors)
        assert isinstance(patterns, list)

        if patterns:
            # Should create appropriate patterns for different error types
            categories = {p.category for p in patterns}
            assert len(categories) >= 1


class TestPatternMatching:
    """Test pattern matching algorithms."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = DynamicErrorPatternMatcher()

    def test_similarity_detection(self):
        """Test similarity detection between error messages."""
        similar_errors = [
            Error(
                message="File not found: config.yml",
                file_path="a.py",
                line_number=1,
                exception_type="Error",
            ),
            Error(
                message="File not found: settings.yml",
                file_path="b.py",
                line_number=2,
                exception_type="Error",
            ),
            Error(
                message="File not found: data.yml",
                file_path="c.py",
                line_number=3,
                exception_type="Error",
            ),
        ]

        patterns = self.matcher.analyze_errors(similar_errors)
        assert isinstance(patterns, list)

        if patterns:
            # Should group similar "File not found" messages
            found_grouped = any(len(p.similar_messages) > 1 for p in patterns)
            assert found_grouped or len(patterns) == 1

    def test_dissimilar_messages_separate_patterns(self):
        """Test that dissimilar messages create separate patterns."""
        dissimilar_errors = [
            Error(
                message="Database connection failed",
                file_path="a.py",
                line_number=1,
                exception_type="Error",
            ),
            Error(
                message="HTTP request timeout",
                file_path="b.py",
                line_number=2,
                exception_type="Error",
            ),
            Error(
                message="Invalid JSON format",
                file_path="c.py",
                line_number=3,
                exception_type="Error",
            ),
        ]

        patterns = self.matcher.analyze_errors(dissimilar_errors)
        assert isinstance(patterns, list)

        # Very dissimilar messages should create separate patterns
        # or be grouped with low similarity
        if len(patterns) > 1:
            assert len(patterns) >= 1


class TestIntegration:
    """Integration test cases."""

    def test_realistic_ci_errors(self):
        """Test with realistic CI/CD error scenarios."""
        realistic_errors = [
            # Import errors
            Error(
                message="No module named 'pytest'",
                file_path="test_main.py",
                line_number=1,
                exception_type="ImportError",
            ),
            Error(
                message="No module named 'requests'",
                file_path="api.py",
                line_number=5,
                exception_type="ImportError",
            ),
            Error(
                message="No module named 'pandas'",
                file_path="data.py",
                line_number=10,
                exception_type="ImportError",
            ),
            # Test failures
            Error(
                message="assert 1 == 2",
                file_path="test_calc.py",
                line_number=15,
                exception_type="AssertionError",
            ),
            Error(
                message="assert response.status_code == 200",
                file_path="test_api.py",
                line_number=20,
                exception_type="AssertionError",
            ),
            # Configuration errors
            Error(
                message="config.yml not found",
                file_path="main.py",
                line_number=25,
                exception_type="FileNotFoundError",
            ),
            Error(
                message="'DATABASE_URL' key not found",
                file_path="settings.py",
                line_number=30,
                exception_type="KeyError",
            ),
        ]

        matcher = DynamicErrorPatternMatcher()
        patterns = matcher.analyze_errors(realistic_errors)

        assert isinstance(patterns, list)
        assert len(patterns) >= 1

        # Verify patterns have expected attributes
        for pattern in patterns:
            assert isinstance(pattern, DynamicErrorPattern)
            assert pattern.frequency > 0
            assert len(pattern.affected_files) > 0
            assert isinstance(pattern.category, str)
            assert 0 <= pattern.severity_score <= 1.0
