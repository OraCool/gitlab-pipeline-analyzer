"""
Tests for cache manager

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from gitlab_analyzer.mcp.cache.manager import CacheManager


@pytest.fixture
async def temp_cache_manager():
    """Create a temporary cache manager for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        manager = CacheManager(tmp.name)
        await manager.initialize()
        yield manager
        await manager.close()
        Path(tmp.name).unlink(missing_ok=True)


class TestCacheManager:
    """Test CacheManager functionality"""

    @pytest.mark.asyncio
    async def test_initialization(self, temp_cache_manager):
        """Test cache manager initialization"""
        manager = temp_cache_manager
        stats = await manager.get_stats()

        assert stats.total_entries == 0
        assert stats.total_size_bytes == 0
        assert stats.entries_by_type == {}

    @pytest.mark.asyncio
    async def test_set_and_get(self, temp_cache_manager):
        """Test setting and getting cache data"""
        manager = temp_cache_manager

        test_data = {
            "test": "value",
            "number": 42,
            "mcp_info": {"tool": "test", "version": "1.0"},
        }

        # Set data
        await manager.set(
            key="test-key", data=test_data, data_type="test", project_id="123"
        )

        # Get data
        retrieved_data = await manager.get("test-key")

        assert retrieved_data is not None
        assert retrieved_data["test"] == "value"
        assert retrieved_data["number"] == 42
        assert "mcp_info" in retrieved_data

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, temp_cache_manager):
        """Test getting non-existent key returns None"""
        manager = temp_cache_manager

        result = await manager.get("nonexistent-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_miss(self, temp_cache_manager):
        """Test get_or_compute with cache miss"""
        manager = temp_cache_manager

        def compute_func():
            return {
                "computed": True,
                "value": 123,
                "mcp_info": {"computed_at": "2025-01-01"},
            }

        result = await manager.get_or_compute(
            key="compute-test",
            compute_func=compute_func,
            data_type="test",
            project_id="456",
        )

        assert result["computed"] is True
        assert result["value"] == 123
        assert "mcp_info" in result

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_hit(self, temp_cache_manager):
        """Test get_or_compute with cache hit"""
        manager = temp_cache_manager

        # First, set some data
        original_data = {"cached": True, "mcp_info": {"cached_at": "2025-01-01"}}

        await manager.set(
            key="cache-hit-test", data=original_data, data_type="test", project_id="789"
        )

        call_count = 0

        def compute_func():
            nonlocal call_count
            call_count += 1
            return {"should_not_be_called": True}

        result = await manager.get_or_compute(
            key="cache-hit-test",
            compute_func=compute_func,
            data_type="test",
            project_id="789",
        )

        # Should return cached data, not call compute_func
        assert result["cached"] is True
        assert call_count == 0
        assert "should_not_be_called" not in result

    @pytest.mark.asyncio
    async def test_async_compute_function(self, temp_cache_manager):
        """Test get_or_compute with async compute function"""
        manager = temp_cache_manager

        async def async_compute():
            await asyncio.sleep(0.01)  # Small delay to simulate async work
            return {"async_result": True, "mcp_info": {"async_computed": True}}

        result = await manager.get_or_compute(
            key="async-test",
            compute_func=async_compute,
            data_type="test",
            project_id="async",
        )

        assert result["async_result"] is True

    @pytest.mark.asyncio
    async def test_invalidate_project(self, temp_cache_manager):
        """Test invalidating all cache entries for a project"""
        manager = temp_cache_manager

        # Add multiple entries for the same project
        for i in range(3):
            await manager.set(
                key=f"project-123-{i}",
                data={"value": i, "mcp_info": {}},
                data_type="test",
                project_id="123",
            )

        # Add entry for different project
        await manager.set(
            key="project-456-1",
            data={"value": 999, "mcp_info": {}},
            data_type="test",
            project_id="456",
        )

        # Invalidate project 123
        deleted_count = await manager.invalidate_project("123")
        assert deleted_count == 3

        # Check that project 123 entries are gone
        for i in range(3):
            result = await manager.get(f"project-123-{i}")
            assert result is None

        # Check that project 456 entry still exists
        result = await manager.get("project-456-1")
        assert result is not None
        assert result["value"] == 999

    @pytest.mark.asyncio
    async def test_stats_update(self, temp_cache_manager):
        """Test that stats are updated correctly"""
        manager = temp_cache_manager

        # Add some data
        await manager.set(
            key="stats-test",
            data={"test": "data", "mcp_info": {}},
            data_type="pipeline",
            project_id="stats",
        )

        stats = await manager.get_stats()
        assert stats.total_entries == 1
        assert stats.total_size_bytes > 0
        assert stats.entries_by_type["pipeline"] == 1
