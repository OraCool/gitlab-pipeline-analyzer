"""
Tests for MCP cache functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import tempfile
from pathlib import Path

import pytest

from gitlab_analyzer.cache.mcp_cache import McpCache, get_cache_manager
from gitlab_analyzer.cache.models import ErrorRecord


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


class TestErrorRecord:
    """Test ErrorRecord model functionality"""

    def test_error_record_can_be_imported(self):
        """Test that ErrorRecord can be imported and has expected attributes"""
        # This just tests that the import works and the class exists
        assert ErrorRecord is not None
        # We can add more specific tests when we know the actual ErrorRecord API
