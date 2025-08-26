"""
Utility functions for MCP resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json

from mcp.types import TextResourceContents
from pydantic.networks import AnyUrl


def create_text_resource(uri: str, data: dict | str) -> TextResourceContents:
    """
    Create a TextResourceContents object with proper URI type.

    Args:
        uri: The resource URI as a string
        data: The data to include (dict will be JSON serialized, str used as-is)

    Returns:
        TextResourceContents with proper URI type
    """
    text = json.dumps(data, indent=2) if isinstance(data, dict) else data
    return TextResourceContents(uri=AnyUrl(uri), text=text)
