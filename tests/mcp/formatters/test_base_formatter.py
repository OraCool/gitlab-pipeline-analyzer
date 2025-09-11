"""Tests for base formatter module."""

import pytest

from gitlab_analyzer.mcp.formatters.base_formatter import BaseFormatter


class ConcreteFormatter(BaseFormatter):
    """Concrete implementation for testing."""

    def format(self, data: dict, mode: str = "balanced") -> dict:
        """Test implementation of format method."""
        return self.optimize_for_mode(data, mode)


class TestBaseFormatter:
    """Test cases for BaseFormatter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ConcreteFormatter()
        self.sample_data = {
            "errors": ["error1", "error2"],
            "metadata": {"timestamp": "2023-01-01"},
            "cached_at": "2023-01-01T10:00:00Z",
            "debug_timing": {"parse_time": 1.5},
            "auto_cleanup": True,
            "essential_field": "important_data",
        }

    def test_abstract_base_class(self):
        """Test that BaseFormatter is abstract."""
        with pytest.raises(TypeError):
            BaseFormatter()

    def test_minimal_optimization(self):
        """Test minimal mode optimization removes verbose fields."""
        result = self.formatter.optimize_for_mode(self.sample_data, "minimal")

        # Verbose fields should be removed
        assert "metadata" not in result
        assert "cached_at" not in result
        assert "debug_timing" not in result
        assert "auto_cleanup" not in result

        # Essential fields should remain
        assert "errors" in result
        assert "essential_field" in result
        assert result["errors"] == ["error1", "error2"]
        assert result["essential_field"] == "important_data"

    def test_balanced_optimization(self):
        """Test balanced mode optimization keeps all data."""
        result = self.formatter.optimize_for_mode(self.sample_data, "balanced")

        # All fields should be preserved in balanced mode
        assert result == self.sample_data
        assert "metadata" in result
        assert "cached_at" in result
        assert "debug_timing" in result
        assert "auto_cleanup" in result
        assert "errors" in result
        assert "essential_field" in result

    def test_detailed_optimization(self):
        """Test detailed mode optimization keeps all data."""
        result = self.formatter.optimize_for_mode(self.sample_data, "detailed")

        # All fields should be preserved in detailed mode
        assert result == self.sample_data

    def test_fixing_optimization(self):
        """Test fixing mode optimization keeps all data like detailed."""
        result = self.formatter.optimize_for_mode(self.sample_data, "fixing")

        # All fields should be preserved in fixing mode
        assert result == self.sample_data

    def test_unknown_mode_defaults_to_balanced(self):
        """Test that unknown modes default to balanced optimization."""
        result = self.formatter.optimize_for_mode(self.sample_data, "unknown_mode")

        # Should behave like balanced mode
        assert result == self.sample_data

    def test_empty_data(self):
        """Test optimization with empty data."""
        empty_data = {}

        result_minimal = self.formatter.optimize_for_mode(empty_data, "minimal")
        result_balanced = self.formatter.optimize_for_mode(empty_data, "balanced")
        result_detailed = self.formatter.optimize_for_mode(empty_data, "detailed")

        assert result_minimal == {}
        assert result_balanced == {}
        assert result_detailed == {}

    def test_data_without_verbose_fields(self):
        """Test optimization with data that has no verbose fields."""
        simple_data = {"errors": ["error1"], "files": ["file1"]}

        result = self.formatter.optimize_for_mode(simple_data, "minimal")

        # Should remain unchanged since no verbose fields to remove
        assert result == simple_data

    def test_partial_verbose_fields(self):
        """Test optimization with only some verbose fields present."""
        partial_data = {
            "errors": ["error1"],
            "metadata": {"info": "test"},
            "essential_field": "keep_me",
        }

        result = self.formatter.optimize_for_mode(partial_data, "minimal")

        # Only metadata should be removed
        assert "metadata" not in result
        assert "errors" in result
        assert "essential_field" in result
        assert result["errors"] == ["error1"]
        assert result["essential_field"] == "keep_me"

    def test_concrete_formatter_format_method(self):
        """Test that concrete formatter's format method works."""
        result = self.formatter.format(self.sample_data, "minimal")

        # Should call optimize_for_mode internally
        assert "metadata" not in result
        assert "errors" in result

    def test_default_mode_in_format(self):
        """Test that format method uses balanced mode by default."""
        result = self.formatter.format(self.sample_data)

        # Should preserve all data (balanced mode)
        assert result == self.sample_data


class TestFormatterEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ConcreteFormatter()

    def test_none_data_handling(self):
        """Test handling of None data."""
        with pytest.raises(AttributeError):
            self.formatter.optimize_for_mode(None, "minimal")

    def test_data_modification_isolation(self):
        """Test that optimization doesn't modify original data."""
        original_data = {
            "errors": ["error1"],
            "metadata": {"timestamp": "2023-01-01"},
            "field": "value",
        }
        original_copy = original_data.copy()

        result = self.formatter.optimize_for_mode(original_data, "minimal")

        # Original data should be unchanged
        assert original_data == original_copy
        # Result should be different (metadata removed)
        assert "metadata" not in result
        assert "metadata" in original_data

    def test_nested_data_preservation(self):
        """Test that nested data structures are preserved correctly."""
        nested_data = {
            "errors": [
                {"type": "syntax", "file": "test.py"},
                {"type": "import", "file": "main.py"},
            ],
            "metadata": {"nested": {"deep": "value"}},
            "stats": {"count": 2, "files": ["test.py", "main.py"]},
        }

        result = self.formatter.optimize_for_mode(nested_data, "minimal")

        # Complex structures should be preserved
        assert result["errors"] == nested_data["errors"]
        assert result["stats"] == nested_data["stats"]
        # Metadata should be removed
        assert "metadata" not in result
