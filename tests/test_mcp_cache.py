"""
Tests for MCP cache functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import tempfile
from pathlib import Path

import pytest

from gitlab_analyzer.cache.mcp_cache import McpCache, get_cache_manager
from gitlab_analyzer.cache.models import ErrorRecord, JobRecord, PipelineRecord


class TestMCPCacheBasic:
    """Test basic MCP cache functionality"""

    @pytest.fixture
    def temp_cache_manager(self):
        """Create a temporary cache manager for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            manager = McpCache(tmp.name)
            yield manager
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)

    def test_cache_manager_creation(self, temp_cache_manager):
        """Test cache manager can be created"""
        manager = temp_cache_manager
        assert manager is not None
        assert manager.db_path.exists()

    def test_cache_manager_initialization(self, temp_cache_manager):
        """Test cache manager properties after initialization"""
        manager = temp_cache_manager
        assert manager.parser_version == 2  # v2 adds error_type classification
        assert "pipeline" in manager.ttl_config
        assert "job" in manager.ttl_config
        assert "analysis" in manager.ttl_config
        assert manager.ttl_config["pipeline"] is None  # Never expires
        assert manager.ttl_config["job"] == 86400  # 24 hours

    def test_get_cache_manager_singleton(self):
        """Test that get_cache_manager returns singleton"""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2

    def test_job_cached_check(self, temp_cache_manager):
        """Test checking if job is cached"""
        manager = temp_cache_manager

        # Should return False for non-existent job
        is_cached = manager.is_job_cached(job_id=123, trace_hash="abc123")
        assert not is_cached

    def test_get_job_errors_empty(self, temp_cache_manager):
        """Test getting job errors when none exist"""
        manager = temp_cache_manager

        # Should return empty list for non-existent job
        errors = manager.get_job_errors(123)
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_get_pipeline_failed_jobs_empty(self, temp_cache_manager):
        """Test getting pipeline failed jobs when none exist"""
        manager = temp_cache_manager

        # Should return empty list for non-existent pipeline
        jobs = manager.get_pipeline_failed_jobs(456)
        assert isinstance(jobs, list)
        assert len(jobs) == 0

    def test_get_file_errors_empty(self, temp_cache_manager):
        """Test getting file errors when none exist"""
        manager = temp_cache_manager

        # Should return empty list for non-existent job/file
        errors = manager.get_file_errors(123, "test.py")
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_get_pipeline_info_none(self, temp_cache_manager):
        """Test getting pipeline info when none exists"""
        manager = temp_cache_manager

        # Should return None for non-existent pipeline
        info = manager.get_pipeline_info(789)
        assert info is None

    def test_get_job_trace_excerpt_empty(self, temp_cache_manager):
        """Test getting job trace excerpt when no data exists"""
        manager = temp_cache_manager

        # Should return None or empty for non-existent job
        excerpt = manager.get_job_trace_excerpt(123, "error123")
        assert excerpt is None

    def test_cleanup_old_versions(self, temp_cache_manager):
        """Test cleanup of old parser versions"""
        manager = temp_cache_manager

        # Should not raise an exception
        manager.cleanup_old_versions()

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, temp_cache_manager):
        """Test getting cache statistics"""
        manager = temp_cache_manager

        stats = await manager.get_cache_stats()
        assert isinstance(stats, dict)
        assert "total_pipelines" in stats
        assert "total_jobs" in stats
        assert "current_parser_version" in stats

    @pytest.mark.asyncio
    async def test_check_health(self, temp_cache_manager):
        """Test health check functionality"""
        manager = temp_cache_manager

        health = await manager.check_health()
        assert isinstance(health, dict)
        assert "database_connectivity" in health
        assert "database_size_bytes" in health

    @pytest.mark.asyncio
    async def test_clear_all_cache(self, temp_cache_manager):
        """Test clearing all cache"""
        manager = temp_cache_manager

        cleared = await manager.clear_all_cache()
        assert isinstance(cleared, int)
        assert cleared >= 0

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, temp_cache_manager):
        """Test cleanup of expired entries"""
        manager = temp_cache_manager

        cleaned = await manager.cleanup_expired()
        assert isinstance(cleaned, int)
        assert cleaned >= 0

    @pytest.mark.asyncio
    async def test_clear_old_entries(self, temp_cache_manager):
        """Test clearing old entries by age"""
        manager = temp_cache_manager

        cleared = await manager.clear_old_entries(max_age_hours=24)
        assert isinstance(cleared, int)
        assert cleared >= 0

    @pytest.mark.asyncio
    async def test_get_pipeline_jobs_empty(self, temp_cache_manager):
        """Test getting pipeline jobs when none exist"""
        manager = temp_cache_manager

        jobs = await manager.get_pipeline_jobs(123)
        assert isinstance(jobs, list)
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_get_pipeline_info_async_none(self, temp_cache_manager):
        """Test getting pipeline info async when none exists"""
        manager = temp_cache_manager

        info = await manager.get_pipeline_info_async(456)
        assert info is None

    @pytest.mark.asyncio
    async def test_get_job_info_async_none(self, temp_cache_manager):
        """Test getting job info async when none exists"""
        manager = temp_cache_manager

        info = await manager.get_job_info_async(789)
        assert info is None

    @pytest.mark.asyncio
    async def test_get_job_files_with_errors_empty(self, temp_cache_manager):
        """Test getting job files with errors when none exist"""
        manager = temp_cache_manager

        files = await manager.get_job_files_with_errors(123)
        assert isinstance(files, list)
        assert len(files) == 0


class TestCacheModels:
    """Test cache model functionality"""

    def test_error_record_can_be_imported(self):
        """Test that ErrorRecord can be imported"""
        assert ErrorRecord is not None

    def test_job_record_can_be_imported(self):
        """Test that JobRecord can be imported"""
        assert JobRecord is not None

    def test_pipeline_record_can_be_imported(self):
        """Test that PipelineRecord can be imported"""
        assert PipelineRecord is not None
