"""
Tests for server integration with caching and resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import patch

import pytest

from gitlab_analyzer.mcp.servers.server import create_server


class TestServerIntegration:
    """Test server integration with new features"""

    @patch("asyncio.create_task")
    def test_create_server_with_cache(self, mock_create_task):
        """Test that server is created with cache integration"""
        # Mock create_task to avoid event loop issues
        mock_create_task.return_value = None

        server = create_server()

        assert server is not None
        assert "GitLab Pipeline Analyzer v" in server.name
        assert "caching" in server.instructions.lower()

    @patch("asyncio.create_task")
    def test_server_instructions_updated(self, mock_create_task):
        """Test that server instructions mention new features"""
        # Mock create_task to avoid event loop issues
        mock_create_task.return_value = None

        server = create_server()

        instructions = server.instructions.lower()
        assert "caching" in instructions
        assert "resources" in instructions
        assert "prompts" in instructions

    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test that cache can be initialized"""
        # Test cache manager initialization directly
        from gitlab_analyzer.cache.mcp_cache import get_cache_manager

        cache_manager = get_cache_manager()

        # Should be able to initialize cache (cache auto-initializes in constructor)
        assert cache_manager is not None
        assert hasattr(cache_manager, "db_path")

        # This should not raise an exception
