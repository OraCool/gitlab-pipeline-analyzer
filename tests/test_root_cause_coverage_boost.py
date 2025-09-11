"""
Additional tests to boost root cause analyzer coverage.
"""

from gitlab_analyzer.analysis.error_model import Error
from gitlab_analyzer.analysis.root_cause_analyzer import (
    ErrorGroup,
    RootCauseAnalysis,
    RootCauseAnalyzer,
)
from gitlab_analyzer.patterns.error_patterns import DynamicErrorPattern


class TestRootCauseAnalyzerCoverage:
    """Test cases to increase root cause analyzer coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = RootCauseAnalyzer()
        self.sample_errors = [
            Error(
                message="ImportError: No module named 'example'",
                file_path="src/main.py",
                line_number=10,
                exception_type="ImportError",
            ),
            Error(
                message="SyntaxError: invalid syntax",
                file_path="src/utils.py",
                line_number=5,
                exception_type="SyntaxError",
            ),
            Error(
                message="Test failed: assertion error",
                file_path="tests/test_example.py",
                line_number=15,
                exception_type="AssertionError",
            ),
        ]

    def test_generate_fix_suggestions_multiple_groups(self):
        """Test fix suggestion generation with multiple error groups."""
        # Create various error groups with different categories
        import_pattern = DynamicErrorPattern(
            pattern_id="import_error",
            representative_message="ImportError: No module named 'example'",
            similar_messages=["ImportError: No module named 'example'"],
            frequency=1,
            similarity_threshold=0.8,
            category="Import Error",
            affected_files={"src/main.py"},
            affected_jobs={"job1"},
            severity_score=0.8,
        )

        syntax_pattern = DynamicErrorPattern(
            pattern_id="syntax_error",
            representative_message="SyntaxError: invalid syntax",
            similar_messages=["SyntaxError: invalid syntax"],
            frequency=1,
            similarity_threshold=0.8,
            category="Syntax Error",
            affected_files={"src/utils.py"},
            affected_jobs={"job1"},
            severity_score=0.9,
        )

        test_pattern = DynamicErrorPattern(
            pattern_id="test_error",
            representative_message="Test failed: assertion error",
            similar_messages=["Test failed: assertion error"],
            frequency=1,
            similarity_threshold=0.8,
            category="Test Failure",
            affected_files={"tests/test_example.py"},
            affected_jobs={"job1"},
            severity_score=0.6,
        )

        groups = [
            ErrorGroup(
                pattern=import_pattern,
                errors=[self.sample_errors[0]],
                confidence=0.9,
                impact_score=8,
            ),
            ErrorGroup(
                pattern=syntax_pattern,
                errors=[self.sample_errors[1]],
                confidence=0.8,
                impact_score=9,
            ),
            ErrorGroup(
                pattern=test_pattern,
                errors=[self.sample_errors[2]],
                confidence=0.7,
                impact_score=6,
            ),
        ]

        suggestions = self.analyzer._generate_fix_suggestions(groups)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_generate_dynamic_fix_suggestion_import_error(self):
        """Test dynamic fix suggestion for import errors."""
        pattern = DynamicErrorPattern(
            pattern_id="import_error",
            representative_message="ImportError: No module named 'example'",
            similar_messages=["ImportError: No module named 'example'"],
            frequency=1,
            similarity_threshold=0.8,
            category="Import Error",
            affected_files={"src/main.py"},
            affected_jobs={"job1"},
            severity_score=0.8,
        )

        group = ErrorGroup(
            pattern=pattern,
            errors=[self.sample_errors[0]],
            confidence=0.9,
            impact_score=8,
        )

        suggestion = self.analyzer._generate_dynamic_fix_suggestion(group)
        assert suggestion is not None
        assert "import" in suggestion.lower() or "module" in suggestion.lower()

    def test_generate_dynamic_fix_suggestion_syntax_error(self):
        """Test dynamic fix suggestion for syntax errors."""
        pattern = DynamicErrorPattern(
            pattern_id="syntax_error",
            representative_message="SyntaxError: invalid syntax",
            similar_messages=["SyntaxError: invalid syntax"],
            frequency=1,
            similarity_threshold=0.8,
            category="Syntax Error",
            affected_files={"src/utils.py"},
            affected_jobs={"job1"},
            severity_score=0.9,
        )

        group = ErrorGroup(
            pattern=pattern,
            errors=[self.sample_errors[1]],
            confidence=0.8,
            impact_score=9,
        )

        suggestion = self.analyzer._generate_dynamic_fix_suggestion(group)
        assert suggestion is not None
        assert "syntax" in suggestion.lower()

    def test_generate_dynamic_fix_suggestion_test_error(self):
        """Test dynamic fix suggestion for test failures."""
        pattern = DynamicErrorPattern(
            pattern_id="test_error",
            representative_message="Test failed: assertion error",
            similar_messages=["Test failed: assertion error"],
            frequency=1,
            similarity_threshold=0.8,
            category="Test Failure",
            affected_files={"tests/test_example.py"},
            affected_jobs={"job1"},
            severity_score=0.6,
        )

        group = ErrorGroup(
            pattern=pattern,
            errors=[self.sample_errors[2]],
            confidence=0.7,
            impact_score=6,
        )

        suggestion = self.analyzer._generate_dynamic_fix_suggestion(group)
        assert suggestion is not None
        assert "test" in suggestion.lower()

    def test_customize_fix_suggestion(self):
        """Test fix suggestion customization."""
        pattern = DynamicErrorPattern(
            pattern_id="import_error",
            representative_message="ImportError: No module named 'pandas'",
            similar_messages=["ImportError: No module named 'pandas'"],
            frequency=1,
            similarity_threshold=0.8,
            category="Import Error",
            affected_files={"src/main.py"},
            affected_jobs={"job1"},
            severity_score=0.8,
        )

        group = ErrorGroup(
            pattern=pattern,
            errors=[
                Error(
                    message="ImportError: No module named 'pandas'",
                    file_path="src/main.py",
                    line_number=10,
                    exception_type="ImportError",
                )
            ],
            confidence=0.9,
            impact_score=8,
        )

        suggestion = self.analyzer._customize_fix_suggestion(group)
        assert suggestion is not None
        assert isinstance(suggestion, str)

    def test_calculate_impact_score_various_files(self):
        """Test impact score calculation with various file types."""
        errors_critical = [
            Error(
                message="error in service",
                file_path="src/service/user_service.py",
                line_number=10,
                exception_type="Error",
            ),
            Error(
                message="error in model",
                file_path="src/model/user_model.py",
                line_number=5,
                exception_type="Error",
            ),
        ]

        errors_test = [
            Error(
                message="test error",
                file_path="tests/test_user.py",
                line_number=15,
                exception_type="AssertionError",
            )
        ]

        score_critical = self.analyzer._calculate_impact_score(errors_critical)
        score_test = self.analyzer._calculate_impact_score(errors_test)

        assert isinstance(score_critical, int)
        assert isinstance(score_test, int)
        assert score_critical >= score_test  # Critical files should have higher impact

    def test_format_primary_error_with_none(self):
        """Test formatting primary error with None input."""
        result = self.analyzer._format_primary_error(None)
        assert isinstance(result, str)
        assert "no primary error" in result.lower() or "none" in result.lower()

    def test_format_primary_error_with_error(self):
        """Test formatting primary error with actual error."""
        error = Error(
            message="ImportError: No module named 'example'",
            file_path="src/main.py",
            line_number=10,
            exception_type="ImportError",
        )
        result = self.analyzer._format_primary_error(error)
        assert isinstance(result, str)
        assert "ImportError" in result
        assert "main.py" in result

    def test_is_test_failure_various_cases(self):
        """Test test failure detection with various cases."""
        test_error = Error(
            message="AssertionError: test failed",
            file_path="tests/test_example.py",
            line_number=15,
            exception_type="AssertionError",
        )

        pytest_error = Error(
            message="pytest.fail: test failed",
            file_path="tests/test_example.py",
            line_number=15,
            exception_type="Exception",
        )

        non_test_error = Error(
            message="ImportError: No module named 'example'",
            file_path="src/main.py",
            line_number=10,
            exception_type="ImportError",
        )

        assert self.analyzer._is_test_failure(test_error) is True
        assert self.analyzer._is_test_failure(pytest_error) is True
        assert self.analyzer._is_test_failure(non_test_error) is False

    def test_create_generic_pattern(self):
        """Test generic pattern creation."""
        pattern = self.analyzer._create_generic_pattern()
        assert isinstance(pattern, DynamicErrorPattern)
        assert pattern.pattern_id == "generic_error"
        assert pattern.category == "Unknown"

    def test_empty_analysis(self):
        """Test empty analysis creation."""
        analysis = self.analyzer._empty_analysis()
        assert isinstance(analysis, RootCauseAnalysis)
        assert analysis.confidence == 0.0
        assert analysis.summary == {"issue": "No errors to analyze"}

    def test_rank_error_groups_empty(self):
        """Test ranking with empty groups."""
        result = self.analyzer._rank_error_groups([])
        assert result == []

    def test_rank_error_groups_single(self):
        """Test ranking with single group."""
        pattern = DynamicErrorPattern(
            pattern_id="test_pattern",
            representative_message="Test error",
            similar_messages=["Test error"],
            frequency=1,
            similarity_threshold=0.8,
            category="Test",
            affected_files={"test.py"},
            affected_jobs={"job1"},
            severity_score=0.8,
        )

        group = ErrorGroup(
            pattern=pattern,
            errors=[self.sample_errors[0]],
            confidence=0.8,
            impact_score=5,
        )

        result = self.analyzer._rank_error_groups([group])
        assert len(result) == 1
        assert result[0] == group

    def test_analyze_with_complex_errors(self):
        """Test analysis with more complex error scenarios."""
        complex_errors = [
            Error(
                message="ModuleNotFoundError: No module named 'requests'",
                file_path="src/api/client.py",
                line_number=1,
                exception_type="ModuleNotFoundError",
            ),
            Error(
                message="AttributeError: 'NoneType' object has no attribute 'text'",
                file_path="src/api/client.py",
                line_number=15,
                exception_type="AttributeError",
            ),
            Error(
                message="ConnectionError: Failed to establish connection",
                file_path="src/api/client.py",
                line_number=25,
                exception_type="ConnectionError",
            ),
            Error(
                message="TypeError: unsupported operand type(s)",
                file_path="src/utils/helpers.py",
                line_number=10,
                exception_type="TypeError",
            ),
        ]

        result = self.analyzer.analyze(complex_errors)
        assert isinstance(result, RootCauseAnalysis)
        assert result.primary_cause is not None
        assert result.confidence > 0.0
        assert len(result.fix_suggestions) > 0
