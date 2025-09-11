"""Tests for error analysis service module."""

from unittest.mock import patch

from gitlab_analyzer.mcp.services.error_analysis_service import ErrorAnalysisService


class TestErrorAnalysisService:
    """Test cases for ErrorAnalysisService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ErrorAnalysisService()
        self.sample_error = {
            "error_type": "ImportError",
            "message": "No module named 'requests'",
            "file_path": "main.py",
            "line_number": 5,
            "exception_type": "ImportError",
            "exception_message": "No module named 'requests'",
        }

    def test_service_creation(self):
        """Test ErrorAnalysisService creation."""
        assert self.service is not None
        assert hasattr(self.service, "enhance_error_with_fix_guidance")

    @patch("gitlab_analyzer.utils.utils._generate_fix_guidance")
    def test_enhance_error_with_fix_guidance_fixing_mode(self, mock_fix_guidance):
        """Test enhance_error_with_fix_guidance in fixing mode."""
        mock_fix_guidance.return_value = (
            "Install the missing package: pip install requests"
        )

        result = self.service.enhance_error_with_fix_guidance(
            self.sample_error, mode="fixing"
        )

        assert isinstance(result, dict)
        assert mock_fix_guidance.called

    @patch("gitlab_analyzer.utils.utils._generate_fix_guidance")
    def test_enhance_error_with_fix_guidance_detailed_mode(self, mock_fix_guidance):
        """Test enhance_error_with_fix_guidance in detailed mode."""
        mock_fix_guidance.return_value = (
            "Install the missing package: pip install requests"
        )

        result = self.service.enhance_error_with_fix_guidance(
            self.sample_error, mode="detailed"
        )

        assert isinstance(result, dict)
        assert mock_fix_guidance.called

    def test_enhance_error_with_fix_guidance_minimal_mode(self):
        """Test enhance_error_with_fix_guidance in minimal mode (no enhancement)."""
        result = self.service.enhance_error_with_fix_guidance(
            self.sample_error, mode="minimal"
        )

        # Should return original error unchanged
        assert result == self.sample_error

    def test_enhance_error_with_fix_guidance_balanced_mode(self):
        """Test enhance_error_with_fix_guidance in balanced mode (no enhancement)."""
        result = self.service.enhance_error_with_fix_guidance(
            self.sample_error, mode="balanced"
        )

        # Should return original error unchanged
        assert result == self.sample_error

    @patch("gitlab_analyzer.utils.utils._generate_fix_guidance")
    def test_enhance_error_with_missing_fields(self, mock_fix_guidance):
        """Test enhance_error_with_fix_guidance with missing fields."""
        mock_fix_guidance.return_value = "Generic fix guidance"

        minimal_error = {"message": "Some error"}

        result = self.service.enhance_error_with_fix_guidance(
            minimal_error, mode="fixing"
        )

        assert isinstance(result, dict)
        assert mock_fix_guidance.called

    @patch("gitlab_analyzer.utils.utils._generate_fix_guidance")
    def test_enhance_error_with_alternative_field_names(self, mock_fix_guidance):
        """Test enhance_error_with_fix_guidance with alternative field names."""
        mock_fix_guidance.return_value = "Fix guidance"

        alt_error = {
            "exception_type": "ValueError",
            "file": "alt.py",
            "line": 10,
            "message": "Invalid value",
        }

        result = self.service.enhance_error_with_fix_guidance(alt_error, mode="fixing")

        assert isinstance(result, dict)
        assert mock_fix_guidance.called

    @patch("gitlab_analyzer.utils.utils._generate_fix_guidance")
    def test_enhance_error_exception_handling(self, mock_fix_guidance):
        """Test enhance_error_with_fix_guidance exception handling."""
        mock_fix_guidance.side_effect = Exception("Fix guidance failed")

        result = self.service.enhance_error_with_fix_guidance(
            self.sample_error, mode="fixing"
        )

        # Should handle exception gracefully
        assert isinstance(result, dict)

    def test_enhance_error_with_none_error(self):
        """Test enhance_error_with_fix_guidance with None error."""
        result = self.service.enhance_error_with_fix_guidance(None, mode="fixing")

        # Should handle None gracefully
        assert result == {}

    def test_enhance_error_with_empty_error(self):
        """Test enhance_error_with_fix_guidance with empty error."""
        empty_error = {}

        result = self.service.enhance_error_with_fix_guidance(
            empty_error, mode="fixing"
        )

        assert isinstance(result, dict)

    @patch("gitlab_analyzer.utils.utils._generate_fix_guidance")
    def test_enhance_error_with_test_specific_info(self, mock_fix_guidance):
        """Test enhance_error_with_fix_guidance with test-specific information."""
        mock_fix_guidance.return_value = "Test-specific fix"

        test_error = {
            "error_type": "AssertionError",
            "message": "assert False",
            "file_path": "test_main.py",
            "line_number": 20,
            "test_name": "test_function",
            "test_class": "TestClass",
        }

        result = self.service.enhance_error_with_fix_guidance(test_error, mode="fixing")

        assert isinstance(result, dict)
        assert mock_fix_guidance.called


class TestErrorAnalysisServiceEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ErrorAnalysisService()

    def test_enhance_with_invalid_mode(self):
        """Test enhance_error_with_fix_guidance with invalid mode."""
        error = {"message": "test error"}

        result = self.service.enhance_error_with_fix_guidance(
            error, mode="invalid_mode"
        )

        # Should handle invalid mode gracefully (treat as non-enhancing)
        assert result == error

    def test_enhance_with_numeric_fields(self):
        """Test enhance_error_with_fix_guidance with numeric fields."""
        error_with_numbers = {
            "error_type": "TypeError",
            "message": "type error",
            "file_path": "main.py",
            "line_number": 42,  # Numeric line number
            "line": 42.5,  # Float line number
        }

        result = self.service.enhance_error_with_fix_guidance(
            error_with_numbers, mode="fixing"
        )

        assert isinstance(result, dict)

    def test_enhance_with_unicode_content(self):
        """Test enhance_error_with_fix_guidance with unicode content."""
        unicode_error = {
            "error_type": "UnicodeError",
            "message": "Unicode error: café ñoño 中文",
            "file_path": "unicode_test.py",
            "line_number": 1,
        }

        result = self.service.enhance_error_with_fix_guidance(
            unicode_error, mode="fixing"
        )

        assert isinstance(result, dict)

    @patch("gitlab_analyzer.utils.utils._generate_fix_guidance")
    def test_enhance_with_very_long_message(self, mock_fix_guidance):
        """Test enhance_error_with_fix_guidance with very long error message."""
        mock_fix_guidance.return_value = "Fix for long message"

        long_message = "x" * 10000  # Very long message
        long_error = {
            "error_type": "LongError",
            "message": long_message,
            "file_path": "long.py",
            "line_number": 1,
        }

        result = self.service.enhance_error_with_fix_guidance(long_error, mode="fixing")

        assert isinstance(result, dict)
        assert mock_fix_guidance.called


class TestErrorAnalysisServiceIntegration:
    """Integration tests for ErrorAnalysisService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ErrorAnalysisService()

    def test_realistic_import_error_enhancement(self):
        """Test enhancement of realistic import error."""
        import_error = {
            "error_type": "ModuleNotFoundError",
            "message": "No module named 'requests'",
            "file_path": "src/api_client.py",
            "line_number": 3,
            "exception_type": "ModuleNotFoundError",
            "exception_message": "No module named 'requests'",
        }

        result = self.service.enhance_error_with_fix_guidance(
            import_error, mode="fixing"
        )

        assert isinstance(result, dict)
        assert "error_type" in result
        assert "message" in result

    def test_realistic_syntax_error_enhancement(self):
        """Test enhancement of realistic syntax error."""
        syntax_error = {
            "error_type": "SyntaxError",
            "message": "invalid syntax (main.py, line 15)",
            "file_path": "main.py",
            "line_number": 15,
            "exception_type": "SyntaxError",
            "exception_message": "invalid syntax",
        }

        result = self.service.enhance_error_with_fix_guidance(
            syntax_error, mode="detailed"
        )

        assert isinstance(result, dict)
        assert "error_type" in result
        assert "message" in result

    def test_realistic_test_failure_enhancement(self):
        """Test enhancement of realistic test failure."""
        test_failure = {
            "error_type": "AssertionError",
            "message": "assert response.status_code == 200\nActual: 404",
            "file_path": "tests/test_api.py",
            "line_number": 25,
            "test_name": "test_get_user",
            "test_class": "TestUserAPI",
            "exception_type": "AssertionError",
            "exception_message": "assert response.status_code == 200",
        }

        result = self.service.enhance_error_with_fix_guidance(
            test_failure, mode="fixing"
        )

        assert isinstance(result, dict)
        assert "error_type" in result
        assert "message" in result

    def test_batch_error_enhancement(self):
        """Test enhancement of multiple errors."""
        errors = [
            {
                "error_type": "ImportError",
                "message": "No module named 'pandas'",
                "file_path": "data.py",
                "line_number": 1,
            },
            {
                "error_type": "SyntaxError",
                "message": "invalid syntax",
                "file_path": "broken.py",
                "line_number": 10,
            },
            {
                "error_type": "TypeError",
                "message": "unsupported operand type(s)",
                "file_path": "calc.py",
                "line_number": 5,
            },
        ]

        enhanced_errors = []
        for error in errors:
            enhanced = self.service.enhance_error_with_fix_guidance(
                error, mode="fixing"
            )
            enhanced_errors.append(enhanced)

        assert len(enhanced_errors) == len(errors)
        for enhanced in enhanced_errors:
            assert isinstance(enhanced, dict)
            assert "error_type" in enhanced
            assert "message" in enhanced
