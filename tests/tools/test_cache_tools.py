"""
Tests for cache tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.tools.cache_tools import register_cache_tools


class TestCacheTools:
    """Test cache management tools"""

    @pytest.fixture
    def mock_mcp(self):
        """Mock FastMCP server"""
        mcp = Mock()
        mcp.tool = Mock()
        return mcp

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        manager = Mock()
        manager.clear_old_entries = AsyncMock(return_value=42)
        manager.clear_all_cache = AsyncMock(return_value=100)
        manager.clear_cache_by_type = AsyncMock(return_value=25)
        manager.get_cache_stats = AsyncMock(
            return_value={
                "total_entries": 150,
                "total_size_mb": 25.5,
                "entries_by_type": {"pipeline": 50, "job": 75, "error": 25},
            }
        )
        manager.check_health = AsyncMock(
            return_value={
                "status": "healthy",
                "database_status": "connected",
                "schema_version": "1.0",
            }
        )
        return manager

    def test_register_cache_tools(self, mock_mcp):
        """Test cache tools registration"""
        register_cache_tools(mock_mcp)

        # Verify 3 tools were registered
        assert mock_mcp.tool.call_count == 3

        # Check that tools were decorated (registered)
        assert mock_mcp.tool.called

    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info")
    async def test_clear_cache_all(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_cache_manager, mock_mcp
    ):
        """Test clearing all cache"""
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {
            "tool": "clear_cache",
            "timestamp": "2025-01-01",
        }

        # Register tools to get access to the functions
        register_cache_tools(mock_mcp)

        # Find the clear_cache function from the decorator calls
        clear_cache_func = None
        for call in mock_mcp.tool.call_args_list:
            if hasattr(call[0][0], "__name__") and call[0][0].__name__ == "clear_cache":
                clear_cache_func = call[0][0]
                break

        assert clear_cache_func is not None, "clear_cache function not found"

        # Test clearing all cache
        result = await clear_cache_func()

        assert result["operation"] == "clear_all_cache"
        assert result["cleared_entries"] == 100
        assert result["status"] == "success"
        assert "mcp_info" in result

        mock_cache_manager.clear_all_cache.assert_called_once_with(None)

    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info")
    async def test_clear_cache_old(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_cache_manager, mock_mcp
    ):
        """Test clearing old cache entries"""
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {
            "tool": "clear_cache",
            "timestamp": "2025-01-01",
        }

        # Register tools
        register_cache_tools(mock_mcp)

        # Find the clear_cache function
        clear_cache_func = None
        for call in mock_mcp.tool.call_args_list:
            if hasattr(call[0][0], "__name__") and call[0][0].__name__ == "clear_cache":
                clear_cache_func = call[0][0]
                break

        # Test clearing old cache
        result = await clear_cache_func(cache_type="old", max_age_hours=24)

        assert result["operation"] == "clear_old_cache"
        assert result["max_age_hours"] == 24
        assert result["cleared_entries"] == 42
        assert result["status"] == "success"

        mock_cache_manager.clear_old_entries.assert_called_once_with(24)

    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info")
    async def test_clear_cache_by_type(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_cache_manager, mock_mcp
    ):
        """Test clearing cache by type"""
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {
            "tool": "clear_cache",
            "timestamp": "2025-01-01",
        }

        # Register tools
        register_cache_tools(mock_mcp)

        # Find the clear_cache function
        clear_cache_func = None
        for call in mock_mcp.tool.call_args_list:
            if hasattr(call[0][0], "__name__") and call[0][0].__name__ == "clear_cache":
                clear_cache_func = call[0][0]
                break

        # Test clearing cache by type
        result = await clear_cache_func(cache_type="job", project_id="123")

        assert result["operation"] == "clear_job_cache"
        assert result["cache_type"] == "job"
        assert result["cleared_entries"] == 25
        assert result["project_id"] == "123"
        assert result["status"] == "success"

        mock_cache_manager.clear_cache_by_type.assert_called_once_with("job", "123")

    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info")
    async def test_cache_stats(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_cache_manager, mock_mcp
    ):
        """Test getting cache statistics"""
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {
            "tool": "cache_stats",
            "timestamp": "2025-01-01",
        }

        # Register tools
        register_cache_tools(mock_mcp)

        # Find the cache_stats function
        cache_stats_func = None
        for call in mock_mcp.tool.call_args_list:
            if hasattr(call[0][0], "__name__") and call[0][0].__name__ == "cache_stats":
                cache_stats_func = call[0][0]
                break

        assert cache_stats_func is not None, "cache_stats function not found"

        # Test getting stats
        result = await cache_stats_func()

        assert result["operation"] == "cache_stats"
        assert result["status"] == "success"
        assert "stats" in result
        assert result["stats"]["total_entries"] == 150
        assert result["stats"]["total_size_mb"] == 25.5

        mock_cache_manager.get_cache_stats.assert_called_once()

    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info")
    async def test_cache_health(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_cache_manager, mock_mcp
    ):
        """Test checking cache health"""
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {
            "tool": "cache_health",
            "timestamp": "2025-01-01",
        }

        # Register tools
        register_cache_tools(mock_mcp)

        # Find the cache_health function
        cache_health_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "cache_health"
            ):
                cache_health_func = call[0][0]
                break

        assert cache_health_func is not None, "cache_health function not found"

        # Test health check
        result = await cache_health_func()

        assert result["operation"] == "cache_health"
        assert result["status"] == "success"
        assert "health" in result
        assert result["health"]["status"] == "healthy"

        mock_cache_manager.check_health.assert_called_once()

    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info")
    async def test_clear_cache_error_handling(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_mcp
    ):
        """Test error handling in clear_cache"""
        # Setup error
        mock_cache_manager = Mock()
        mock_cache_manager.clear_all_cache = AsyncMock(
            side_effect=Exception("Database error")
        )
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {"tool": "clear_cache", "error": True}

        # Register tools
        register_cache_tools(mock_mcp)

        # Find the clear_cache function
        clear_cache_func = None
        for call in mock_mcp.tool.call_args_list:
            if hasattr(call[0][0], "__name__") and call[0][0].__name__ == "clear_cache":
                clear_cache_func = call[0][0]
                break

        # Test error handling
        result = await clear_cache_func()

        assert result["operation"] == "clear_cache"
        assert result["status"] == "error"
        assert "Failed to clear cache" in result["error"]
        assert "mcp_info" in result

    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info")
    async def test_cache_stats_error_handling(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_mcp
    ):
        """Test error handling in cache_stats"""
        # Setup error
        mock_cache_manager = Mock()
        mock_cache_manager.get_cache_stats = AsyncMock(
            side_effect=Exception("Stats error")
        )
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {"tool": "cache_stats", "error": True}

        # Register tools
        register_cache_tools(mock_mcp)

        # Find the cache_stats function
        cache_stats_func = None
        for call in mock_mcp.tool.call_args_list:
            if hasattr(call[0][0], "__name__") and call[0][0].__name__ == "cache_stats":
                cache_stats_func = call[0][0]
                break

        # Test error handling
        result = await cache_stats_func()

        assert result["operation"] == "cache_stats"
        assert result["status"] == "error"
        assert "Failed to get cache stats" in result["error"]

    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info")
    async def test_cache_health_error_handling(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_mcp
    ):
        """Test error handling in cache_health"""
        # Setup error
        mock_cache_manager = Mock()
        mock_cache_manager.check_health = AsyncMock(
            side_effect=Exception("Health check error")
        )
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {"tool": "cache_health", "error": True}

        # Register tools
        register_cache_tools(mock_mcp)

        # Find the cache_health function
        cache_health_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "cache_health"
            ):
                cache_health_func = call[0][0]
                break

        # Test error handling
        result = await cache_health_func()

        assert result["operation"] == "cache_health"
        assert result["status"] == "error"
        assert "Failed to check cache health" in result["error"]
