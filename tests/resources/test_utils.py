"""
Unit tests for MCP resources utilities.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json

from mcp.types import TextResourceContents
from pydantic.networks import AnyUrl

from gitlab_analyzer.mcp.resources.utils import create_text_resource


class TestCreateTextResource:
    """Test create_text_resource function."""

    def test_create_text_resource_with_dict(self):
        """Test creating text resource with dictionary data."""
        uri = "gl://test/resource"
        data = {"key": "value", "number": 42, "nested": {"inner": "data"}}

        result = create_text_resource(uri, data)

        assert isinstance(result, TextResourceContents)
        assert str(result.uri) == uri

        # The text should be JSON serialized
        parsed_text = json.loads(result.text)
        assert parsed_text == data

    def test_create_text_resource_with_string(self):
        """Test creating text resource with string data."""
        uri = "gl://test/string"
        data = "This is a plain text resource"

        result = create_text_resource(uri, data)

        assert isinstance(result, TextResourceContents)
        assert str(result.uri) == uri
        assert result.text == data

    def test_create_text_resource_with_empty_dict(self):
        """Test creating text resource with empty dictionary."""
        uri = "gl://test/empty"
        data = {}

        result = create_text_resource(uri, data)

        assert isinstance(result, TextResourceContents)
        assert str(result.uri) == uri
        assert result.text == "{}"

    def test_create_text_resource_with_empty_string(self):
        """Test creating text resource with empty string."""
        uri = "gl://test/empty-string"
        data = ""

        result = create_text_resource(uri, data)

        assert isinstance(result, TextResourceContents)
        assert str(result.uri) == uri
        assert result.text == ""

    def test_create_text_resource_with_complex_data(self):
        """Test creating text resource with complex nested data."""
        uri = "gl://test/complex"
        data = {
            "pipeline": {
                "id": 123,
                "status": "failed",
                "errors": [
                    {"file": "test.py", "line": 10, "message": "Error occurred"},
                    {"file": "main.py", "line": 25, "message": "Another error"},
                ],
            },
            "metadata": {"timestamp": "2025-08-26T10:00:00Z", "version": "1.0.0"},
        }

        result = create_text_resource(uri, data)

        assert isinstance(result, TextResourceContents)
        assert str(result.uri) == uri

        # Verify the JSON is properly formatted with indentation
        assert "\n" in result.text  # Should have newlines due to indent=2

        # Verify the data can be parsed back correctly
        parsed_text = json.loads(result.text)
        assert parsed_text == data

    def test_create_text_resource_uri_validation(self):
        """Test that URI is properly validated as AnyUrl."""
        uri = "gl://project/123/pipeline/456"
        data = {"test": "data"}

        result = create_text_resource(uri, data)

        assert isinstance(result.uri, AnyUrl)
        assert str(result.uri) == uri

    def test_create_text_resource_with_multiline_string(self):
        """Test creating text resource with multiline string."""
        uri = "gl://test/multiline"
        data = """This is a multiline
string with multiple
lines of content."""

        result = create_text_resource(uri, data)

        assert isinstance(result, TextResourceContents)
        assert str(result.uri) == uri
        assert result.text == data
        assert "\n" in result.text
