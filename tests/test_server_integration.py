"""
Tests for server integration with caching and resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import pytest

from gitlab_analyzer.mcp.servers.server import create_server


class TestServerIntegration:
    """Test server integration with new features"""

    def test_create_server_with_cache(self):
        """Test that server is created with cache integration"""
        server = create_server()

        assert server is not None
        assert "GitLab Pipeline Analyzer v" in server.name
        assert "caching" in server.instructions

        # Check that cache initialization hook is stored
        assert hasattr(server, "_cache_init")
        assert callable(server._cache_init)

    def test_server_instructions_updated(self):
        """Test that server instructions mention new features"""
        server = create_server()

        instructions = server.instructions.lower()
        assert "caching" in instructions
        assert "resources" in instructions
        assert "prompts" in instructions

    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test that cache can be initialized"""
        server = create_server()

        # Should be able to call the cache initialization
        await server._cache_init()

        # This should not raise an exception
