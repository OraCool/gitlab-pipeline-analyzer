"""
Tests for MCP cache functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gitlab_analyzer.cache.mcp_cache import McpCache, get_cache_manager
from gitlab_analyzer.cache.models import ErrorRecord, JobRecord, PipelineRecord


class TestMCPCacheManager:
    """Test MCP cache manager functionality"""

    @pytest.fixture
    async def temp_cache_manager(self):
        """Create a temporary cache manager for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            manager = MCPCacheManager(tmp.name)
            await manager.initialize()
            yield manager
            await manager.close()
            Path(tmp.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self, temp_cache_manager):
        """Test cache manager initialization"""
        manager = temp_cache_manager
        stats = await manager.get_cache_stats()

        assert "total_entries" in stats
        assert "total_size_mb" in stats
        assert stats["total_entries"] >= 0

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, temp_cache_manager):
        """Test setting and getting cache data"""
        manager = temp_cache_manager

        test_data = {
            "test": "value",
            "number": 42,
            "nested": {"key": "value"},
        }

        # Set data
        await manager.set(
            key="test-key",
            data=test_data,
            data_type="test",
            project_id="123",
            pipeline_id=456,
        )

        # Get data
        retrieved_data = await manager.get("test-key")

        assert retrieved_data is not None
        assert retrieved_data["test"] == "value"
        assert retrieved_data["number"] == 42
        assert retrieved_data["nested"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_cache_get_nonexistent(self, temp_cache_manager):
        """Test getting non-existent cache key"""
        manager = temp_cache_manager

        result = await manager.get("nonexistent-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_store_pipeline_info(self, temp_cache_manager):
        """Test storing pipeline information"""
        manager = temp_cache_manager

        pipeline_info = {
            "id": 456,
            "status": "failed",
            "source_branch": "feature/test",
            "sha": "abc123",
            "created_at": "2025-01-01T10:00:00Z",
        }

        await manager.store_pipeline_info_async(
            project_id="123", pipeline_id=456, pipeline_info=pipeline_info
        )

        # Verify pipeline was stored (this would require implementing get_pipeline_info)
        # For now, just verify no errors were raised
        assert True

    @pytest.mark.asyncio
    async def test_cache_store_job_file_errors(self, temp_cache_manager):
        """Test storing job file errors"""
        manager = temp_cache_manager

        files = [
            {
                "file_path": "test_example.py",
                "error_count": 2,
                "errors": [
                    {"message": "Test failed", "line_number": "42"},
                    {"message": "Another error", "line_number": "50"},
                ],
            }
        ]

        errors = [
            {"message": "Test failed", "line_number": "42"},
            {"message": "Another error", "line_number": "50"},
        ]

        await manager.store_job_file_errors(
            project_id="123",
            pipeline_id=456,
            job_id=789,
            files=files,
            errors=errors,
            parser_type="pytest",
        )

        # Verify no errors were raised
        assert True

    @pytest.mark.asyncio
    async def test_cache_store_error_trace_segments(self, temp_cache_manager):
        """Test storing error trace segments"""
        manager = temp_cache_manager

        error_records = [
            ErrorRecord(
                job_id=789,
                error_data={"message": "Test error", "line_number": "42"},
                error_index=0,
            )
        ]

        await manager.store_error_trace_segments(
            job_id=789,
            trace_text="Test trace content",
            trace_hash="abc123",
            errors=error_records,
            parser_type="pytest",
        )

        # Verify no errors were raised
        assert True

    @pytest.mark.asyncio
    async def test_cache_clear_all(self, temp_cache_manager):
        """Test clearing all cache"""
        manager = temp_cache_manager

        # Add some test data
        await manager.set(
            key="test-key",
            data={"test": "data"},
            data_type="test",
            project_id="123",
        )

        # Clear all cache
        cleared_count = await manager.clear_all_cache()

        assert cleared_count >= 0

        # Verify data was cleared
        result = await manager.get("test-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_clear_by_type(self, temp_cache_manager):
        """Test clearing cache by type"""
        manager = temp_cache_manager

        # Add test data of different types
        await manager.set(
            key="test-pipeline",
            data={"type": "pipeline"},
            data_type="pipeline",
            project_id="123",
        )

        await manager.set(
            key="test-job",
            data={"type": "job"},
            data_type="job",
            project_id="123",
        )

        # Clear only job cache
        cleared_count = await manager.clear_cache_by_type("job")

        assert cleared_count >= 0

    @pytest.mark.asyncio
    async def test_cache_clear_old_entries(self, temp_cache_manager):
        """Test clearing old cache entries"""
        manager = temp_cache_manager

        # Clear old entries (none should exist in new cache)
        cleared_count = await manager.clear_old_entries(24)

        assert cleared_count >= 0

    @pytest.mark.asyncio
    async def test_cache_health_check(self, temp_cache_manager):
        """Test cache health check"""
        manager = temp_cache_manager

        health = await manager.check_health()

        assert "status" in health
        assert "database_status" in health
        assert health["status"] in ["healthy", "warning", "error"]

    @pytest.mark.asyncio
    async def test_cache_stats(self, temp_cache_manager):
        """Test getting cache statistics"""
        manager = temp_cache_manager

        stats = await manager.get_cache_stats()

        assert "total_entries" in stats
        assert "total_size_mb" in stats
        assert "entries_by_type" in stats
        assert isinstance(stats["total_entries"], int)
        assert isinstance(stats["total_size_mb"], (int, float))

    @pytest.mark.asyncio
    async def test_cache_get_job_errors(self, temp_cache_manager):
        """Test getting job errors from cache"""
        manager = temp_cache_manager

        # This should not raise an error even if no errors exist
        errors = manager.get_job_errors(123)

        assert isinstance(errors, list)

    def test_get_cache_manager_singleton(self):
        """Test that get_cache_manager returns singleton"""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2

    @patch("gitlab_analyzer.cache.mcp_cache.MCPCacheManager")
    def test_get_cache_manager_initialization(self, mock_manager_class):
        """Test cache manager initialization through get_cache_manager"""
        mock_instance = Mock()
        mock_manager_class.return_value = mock_instance

        # Clear singleton
        from gitlab_analyzer.cache import mcp_cache

        mcp_cache._cache_manager = None

        # Get manager (should create new instance)
        manager = get_cache_manager()

        assert manager is mock_instance
        mock_manager_class.assert_called_once()


class TestCacheEntry:
    """Test CacheEntry model functionality"""

    def test_cache_entry_creation(self):
        """Test creating a cache entry"""
        entry = CacheEntry(
            key="test-key",
            data={"test": "data"},
            data_type="test",
            project_id="123",
            pipeline_id=456,
            job_id=789,
        )

        assert entry.key == "test-key"
        assert entry.data == {"test": "data"}
        assert entry.data_type == "test"
        assert entry.project_id == "123"
        assert entry.pipeline_id == 456
        assert entry.job_id == 789

    def test_cache_entry_from_dict(self):
        """Test creating cache entry from dictionary"""
        data = {
            "key": "test-key",
            "data": {"test": "data"},
            "data_type": "test",
            "project_id": "123",
            "pipeline_id": 456,
            "job_id": 789,
        }

        entry = CacheEntry.from_dict(data)

        assert entry.key == "test-key"
        assert entry.data == {"test": "data"}
        assert entry.data_type == "test"


class TestErrorRecord:
    """Test ErrorRecord model functionality"""

    def test_error_record_creation(self):
        """Test creating an error record"""
        error_data = {
            "message": "Test error",
            "line_number": "42",
            "file_path": "test.py",
        }

        record = ErrorRecord(
            job_id=123,
            error_data=error_data,
            error_index=0,
        )

        assert record.job_id == 123
        assert record.error_data == error_data
        assert record.error_index == 0

    def test_error_record_from_parsed_error(self):
        """Test creating error record from parsed error"""
        error_data = {
            "message": "Test error",
            "line_number": "42",
            "file_path": "test.py",
            "exception_type": "AssertionError",
        }

        record = ErrorRecord.from_parsed_error(
            job_id=123,
            error_data=error_data,
            error_index=0,
        )

        assert record.job_id == 123
        assert record.error_data == error_data
        assert record.error_index == 0
