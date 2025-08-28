"""
Tests for Auto-Cleanup functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from gitlab_analyzer.cache.auto_cleanup import (
    AutoCleanupManager,
    get_auto_cleanup_manager,
)
from gitlab_analyzer.cache.mcp_cache import McpCache


class TestAutoCleanupManager:
    """Test the AutoCleanupManager functionality"""

    def setup_method(self):
        """Setup for each test method"""
        # Clear any existing global instance
        import gitlab_analyzer.cache.auto_cleanup as auto_cleanup_module

        auto_cleanup_module._auto_cleanup_manager = None

    def test_initialization_with_defaults(self):
        """Test initialization with default values"""
        with patch.dict(os.environ, {}, clear=True):
            manager = AutoCleanupManager()

            assert manager.enabled is True
            assert manager.cleanup_interval_minutes == 60
            assert manager.max_age_hours == 24
            assert manager._last_cleanup_time is None
            assert manager._cleanup_in_progress is False

    def test_initialization_with_env_vars(self):
        """Test initialization with environment variables"""
        env_vars = {
            "MCP_AUTO_CLEANUP_ENABLED": "false",
            "MCP_AUTO_CLEANUP_INTERVAL_MINUTES": "30",
            "MCP_AUTO_CLEANUP_MAX_AGE_HOURS": "12",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            manager = AutoCleanupManager()

            assert manager.enabled is False
            assert manager.cleanup_interval_minutes == 30
            assert manager.max_age_hours == 12

    def test_should_run_cleanup_disabled(self):
        """Test should_run_cleanup when disabled"""
        with patch.dict(os.environ, {"MCP_AUTO_CLEANUP_ENABLED": "false"}, clear=True):
            manager = AutoCleanupManager()
            assert manager.should_run_cleanup() is False

    def test_should_run_cleanup_first_time(self):
        """Test should_run_cleanup on first run"""
        manager = AutoCleanupManager()
        assert manager.should_run_cleanup() is True

    def test_should_run_cleanup_too_soon(self):
        """Test should_run_cleanup when called too soon"""
        manager = AutoCleanupManager()
        manager._last_cleanup_time = time.time()  # Just ran
        assert manager.should_run_cleanup() is False

    def test_should_run_cleanup_after_interval(self):
        """Test should_run_cleanup after interval has passed"""
        with patch.dict(
            os.environ, {"MCP_AUTO_CLEANUP_INTERVAL_MINUTES": "1"}, clear=True
        ):
            manager = AutoCleanupManager()
            manager._last_cleanup_time = time.time() - 120  # 2 minutes ago
            assert manager.should_run_cleanup() is True

    def test_should_run_cleanup_in_progress(self):
        """Test should_run_cleanup when cleanup is in progress"""
        manager = AutoCleanupManager()
        manager._cleanup_in_progress = True
        assert manager.should_run_cleanup() is False

    @pytest.mark.asyncio
    async def test_trigger_cleanup_not_needed(self):
        """Test trigger_cleanup_if_needed when cleanup is not needed"""
        with patch.dict(os.environ, {"MCP_AUTO_CLEANUP_ENABLED": "false"}, clear=True):
            manager = AutoCleanupManager()

            result = await manager.trigger_cleanup_if_needed()

            assert result["cleanup_triggered"] is False
            assert result["reason"] == "disabled"

    @pytest.mark.asyncio
    async def test_trigger_cleanup_needed(self):
        """Test trigger_cleanup_if_needed when cleanup is needed"""
        manager = AutoCleanupManager()

        with patch.object(manager, "_run_cleanup_background"):
            result = await manager.trigger_cleanup_if_needed()

            assert result["cleanup_triggered"] is True
            assert result["max_age_hours"] == 24
            assert result["interval_minutes"] == 60

    @pytest.mark.asyncio
    async def test_run_cleanup_background_success(self):
        """Test successful background cleanup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_cleanup.db"

            # Create a cache manager with test data
            cache = McpCache(db_path=db_path)

            with patch(
                "gitlab_analyzer.cache.auto_cleanup.get_cache_manager",
                return_value=cache,
            ):
                manager = AutoCleanupManager()

                # Mock the clear_old_entries method
                with patch.object(
                    cache, "clear_old_entries", return_value=5
                ) as mock_clear:
                    await manager._run_cleanup_background()

                    mock_clear.assert_called_once_with(24)  # default max_age_hours
                    assert manager._last_cleanup_time is not None
                    assert manager._cleanup_in_progress is False

    @pytest.mark.asyncio
    async def test_run_cleanup_background_error_handling(self):
        """Test error handling in background cleanup"""
        manager = AutoCleanupManager()

        with patch(
            "gitlab_analyzer.cache.auto_cleanup.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.clear_old_entries.side_effect = Exception("Database error")
            mock_get_cache.return_value = mock_cache

            # Should not raise exception
            await manager._run_cleanup_background()

            assert manager._cleanup_in_progress is False

    def test_get_next_cleanup_minutes_disabled(self):
        """Test get_next_cleanup_minutes when disabled"""
        with patch.dict(os.environ, {"MCP_AUTO_CLEANUP_ENABLED": "false"}, clear=True):
            manager = AutoCleanupManager()
            assert manager._get_next_cleanup_minutes() is None

    def test_get_next_cleanup_minutes_no_previous(self):
        """Test get_next_cleanup_minutes with no previous cleanup"""
        manager = AutoCleanupManager()
        assert manager._get_next_cleanup_minutes() is None

    def test_get_next_cleanup_minutes_with_previous(self):
        """Test get_next_cleanup_minutes with previous cleanup"""
        with patch.dict(
            os.environ, {"MCP_AUTO_CLEANUP_INTERVAL_MINUTES": "60"}, clear=True
        ):
            manager = AutoCleanupManager()
            manager._last_cleanup_time = time.time() - 1800  # 30 minutes ago

            next_cleanup = manager._get_next_cleanup_minutes()
            assert next_cleanup is not None
            assert 29 <= next_cleanup <= 31  # Should be around 30 minutes

    def test_get_status(self):
        """Test get_status method"""
        manager = AutoCleanupManager()
        manager._last_cleanup_time = time.time()
        manager._cleanup_in_progress = True

        status = manager.get_status()

        assert status["enabled"] is True
        assert status["cleanup_interval_minutes"] == 60
        assert status["max_age_hours"] == 24
        assert status["last_cleanup_time"] is not None
        assert status["cleanup_in_progress"] is True
        assert status["next_cleanup_in_minutes"] is not None

    def test_get_auto_cleanup_manager_singleton(self):
        """Test that get_auto_cleanup_manager returns singleton"""
        manager1 = get_auto_cleanup_manager()
        manager2 = get_auto_cleanup_manager()

        assert manager1 is manager2


class TestAutoCleanupIntegration:
    """Integration tests with the resource access system"""

    def setup_method(self):
        """Setup for each test method"""
        # Clear any existing global instance
        import gitlab_analyzer.cache.auto_cleanup as auto_cleanup_module

        auto_cleanup_module._auto_cleanup_manager = None

    @pytest.mark.asyncio
    async def test_resource_access_triggers_cleanup(self):
        """Test that resource access triggers auto-cleanup"""
        from gitlab_analyzer.mcp.tools.resource_access_tools import get_mcp_resource

        with patch(
            "gitlab_analyzer.cache.auto_cleanup.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.clear_old_entries.return_value = 3
            mock_get_cache.return_value = mock_cache

            # Mock the actual resource function to avoid database dependency
            with patch(
                "gitlab_analyzer.mcp.resources.pipeline.get_pipeline_resource"
            ) as mock_resource:
                mock_resource.return_value = {"test": "data"}

                result = await get_mcp_resource("gl://pipeline/83/1594344")

                # Check that auto_cleanup status is added to response
                assert "auto_cleanup" in result
                assert "cleanup_triggered" in result["auto_cleanup"]

    @pytest.mark.asyncio
    async def test_multiple_resource_access_rate_limiting(self):
        """Test that multiple resource accesses respect rate limiting"""
        from gitlab_analyzer.mcp.tools.resource_access_tools import get_mcp_resource

        with patch(
            "gitlab_analyzer.cache.auto_cleanup.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.clear_old_entries.return_value = 2
            mock_get_cache.return_value = mock_cache

            # Mock the actual resource function
            with patch(
                "gitlab_analyzer.mcp.resources.pipeline.get_pipeline_resource"
            ) as mock_resource:
                mock_resource.return_value = {"test": "data"}

                # First call should trigger cleanup
                result1 = await get_mcp_resource("gl://pipeline/83/1594344")
                assert result1["auto_cleanup"]["cleanup_triggered"] is True

                # Second call immediately after should not trigger cleanup
                result2 = await get_mcp_resource("gl://pipeline/83/1594344")
                assert result2["auto_cleanup"]["cleanup_triggered"] is False
                assert result2["auto_cleanup"]["reason"] == "not_needed"

    def test_environment_variable_configuration(self):
        """Test that environment variables properly configure the system"""
        env_vars = {
            "MCP_AUTO_CLEANUP_ENABLED": "true",
            "MCP_AUTO_CLEANUP_INTERVAL_MINUTES": "120",
            "MCP_AUTO_CLEANUP_MAX_AGE_HOURS": "48",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            manager = get_auto_cleanup_manager()

            assert manager.enabled is True
            assert manager.cleanup_interval_minutes == 120
            assert manager.max_age_hours == 48


class TestAutoCleanupCacheManagerIntegration:
    """Test integration with cache manager"""

    @pytest.mark.asyncio
    async def test_cache_manager_clear_old_entries(self):
        """Test that cache manager's clear_old_entries method works"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_cleanup_integration.db"

            cache = McpCache(db_path=db_path)

            # Should not raise any errors
            cleared_count = await cache.clear_old_entries(24)
            assert isinstance(cleared_count, int)
            assert cleared_count >= 0
