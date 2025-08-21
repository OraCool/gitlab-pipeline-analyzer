"""
Tests for error filtering functionality in MCP tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.mcp.tools.pagination_tools import (
    _clean_error_response,
    _filter_traceback_by_paths,
)


class TestErrorFiltering:
    """Test error filtering functionality for traceback management"""

    def test_filter_traceback_by_paths_no_exclusions(self):
        """Test traceback filtering with no exclusion patterns"""
        traceback_entries = [
            {"file_path": "/app/src/main.py", "line_number": 10},
            {
                "file_path": "/app/.venv/lib/site-packages/django/core.py",
                "line_number": 20,
            },
            {
                "file_path": "/root/.local/share/uv/python/lib/contextlib.py",
                "line_number": 30,
            },
        ]

        result = _filter_traceback_by_paths(traceback_entries, [])

        # Should return all entries when no exclusions
        assert len(result) == 3
        assert result == traceback_entries

    def test_filter_traceback_by_paths_with_exclusions(self):
        """Test traceback filtering with exclusion patterns"""
        traceback_entries = [
            {"file_path": "/app/src/main.py", "line_number": 10},
            {
                "file_path": "/app/.venv/lib/site-packages/django/core.py",
                "line_number": 20,
            },
            {
                "file_path": "/root/.local/share/uv/python/lib/contextlib.py",
                "line_number": 30,
            },
            {"file_path": "/app/domains/document/models.py", "line_number": 40},
        ]
        exclude_patterns = [".venv", "/root/.local"]

        result = _filter_traceback_by_paths(traceback_entries, exclude_patterns)

        # Should exclude entries containing .venv and /root/.local
        assert len(result) == 2
        assert result[0]["file_path"] == "/app/src/main.py"
        assert result[1]["file_path"] == "/app/domains/document/models.py"

    def test_clean_error_response_include_traceback_false(self):
        """Test cleaning error response when traceback should be excluded"""
        error = {
            "level": "error",
            "message": "Test error",
            "context": "Test: test_example\nFile: test.py\n--- Complete Test Failure Details ---\nTraceback info here\nTraceback Details:\n  File test.py line 10\n    code here",
            "traceback": [
                {"file_path": "/app/test.py", "line_number": 10},
                {"file_path": "/app/.venv/lib/django.py", "line_number": 20},
            ],
            "full_error_text": "Full traceback with .venv paths",
            "has_traceback": True,
        }

        result = _clean_error_response(error, include_traceback=False)

        # Should remove traceback-related fields
        assert "traceback" not in result
        assert "full_error_text" not in result
        assert result["has_traceback"] is False

        # Should preserve all context when include_traceback=False
        context_lines = result["context"].split("\n")
        # Context is preserved, not filtered
        assert "--- Complete Test Failure Details ---" in result["context"]
        assert "Traceback Details:" in result["context"]
        assert any("Test: test_example" in line for line in context_lines)

    def test_clean_error_response_exclude_paths(self):
        """Test cleaning error response with path exclusions"""
        error = {
            "level": "error",
            "message": "Test error",
            "context": "Error context\n/app/.venv/lib/site-packages/django.py:10\n/app/src/main.py:20",
            "traceback": [
                {"file_path": "/app/src/main.py", "line_number": 20},
                {
                    "file_path": "/app/.venv/lib/site-packages/django.py",
                    "line_number": 10,
                },
            ],
            "full_error_text": "Error in /app/.venv/lib/site-packages/django.py\nError in /app/src/main.py",
        }
        exclude_paths = [".venv", "site-packages"]

        result = _clean_error_response(
            error, include_traceback=True, exclude_paths=exclude_paths
        )

        # Should filter traceback but preserve context
        assert len(result["traceback"]) == 1
        assert result["traceback"][0]["file_path"] == "/app/src/main.py"
        # Context is not filtered anymore - we preserve everything
        assert ".venv" in result["context"]

        # Should filter full_error_text
        assert ".venv" not in result["full_error_text"]
        assert "site-packages" not in result["full_error_text"]
        assert "/app/src/main.py" in result["full_error_text"]

        # Context is preserved (not filtered anymore)
        assert ".venv" in result["context"]
        assert "site-packages" in result["context"]

    def test_clean_error_response_no_filtering(self):
        """Test cleaning error response with no filtering applied"""
        original_error = {
            "level": "error",
            "message": "Test error",
            "context": "Error context",
            "traceback": [{"file_path": "/app/test.py", "line_number": 10}],
            "full_error_text": "Full error text",
        }

        result = _clean_error_response(
            original_error, include_traceback=True, exclude_paths=[]
        )

        # Should return identical copy
        assert result == original_error
        # But ensure it's a copy, not the same object
        assert result is not original_error

    def test_clean_error_response_handles_missing_fields(self):
        """Test cleaning error response when optional fields are missing"""
        error = {
            "level": "error",
            "message": "Test error",
            # Missing context, traceback, full_error_text
        }

        result = _clean_error_response(
            error, include_traceback=False, exclude_paths=[".venv"]
        )

        # Should handle missing fields gracefully
        assert result["level"] == "error"
        assert result["message"] == "Test error"
        assert result["has_traceback"] is False

    def test_filter_traceback_by_paths_empty_traceback(self):
        """Test traceback filtering with empty traceback list"""
        result = _filter_traceback_by_paths([], [".venv"])
        assert result == []

    def test_filter_traceback_by_paths_multiple_patterns(self):
        """Test traceback filtering with multiple exclusion patterns"""
        traceback_entries = [
            {"file_path": "/app/src/main.py", "line_number": 10},
            {"file_path": "/builds/project/.venv/lib/django.py", "line_number": 20},
            {
                "file_path": "/root/.local/share/uv/python/contextlib.py",
                "line_number": 30,
            },
            {
                "file_path": "/usr/lib/python3.9/site-packages/pytest.py",
                "line_number": 40,
            },
        ]
        exclude_patterns = [".venv", "/root/.local", "site-packages"]

        result = _filter_traceback_by_paths(traceback_entries, exclude_patterns)

        # Should only keep the application code
        assert len(result) == 1
        assert result[0]["file_path"] == "/app/src/main.py"

    def test_clean_error_response_preserves_other_fields(self):
        """Test that cleaning preserves fields not related to traceback"""
        error = {
            "level": "error",
            "message": "Test error",
            "line_number": 100,
            "timestamp": "2025-01-01T10:00:00",
            "test_name": "test_example",
            "exception_type": "ValueError",
            "custom_field": "custom_value",
            "traceback": [{"file_path": "/app/.venv/lib/django.py", "line_number": 20}],
        }

        result = _clean_error_response(error, include_traceback=False)

        # Should preserve all non-traceback fields
        assert result["level"] == "error"
        assert result["message"] == "Test error"
        assert result["line_number"] == 100
        assert result["timestamp"] == "2025-01-01T10:00:00"
        assert result["test_name"] == "test_example"
        assert result["exception_type"] == "ValueError"
        assert result["custom_field"] == "custom_value"

        # Should remove/modify only traceback-related fields
        assert "traceback" not in result
        assert result["has_traceback"] is False
