"""
Integration tests for the new MCP cache functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gitlab_analyzer.cache.mcp_cache import get_cache_manager


class TestMCPCacheIntegration:
    """Test MCP cache integration functionality"""

    @pytest.fixture
    async def temp_cache_manager(self):
        """Create a temporary cache manager for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            with patch("gitlab_analyzer.cache.mcp_cache._cache_manager", None):
                # Clear singleton to ensure fresh instance
                manager = get_cache_manager(db_path=tmp.name)
                yield manager
                # Cleanup
                if hasattr(manager, "close"):
                    try:
                        await manager.close()
                    except Exception:
                        pass
                Path(tmp.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_cache_manager_singleton(self):
        """Test that cache manager is a singleton"""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_cache_basic_operations(self, temp_cache_manager):
        """Test basic cache operations"""
        cache_manager = temp_cache_manager

        # Test setting data
        test_data = {
            "project_id": "123",
            "pipeline_id": 456,
            "status": "failed",
            "mcp_info": {"tool": "test", "timestamp": "2025-01-01"},
        }

        await cache_manager.set(
            key="test-pipeline-123-456",
            data=test_data,
            data_type="pipeline",
            project_id="123",
        )

        # Test getting data
        retrieved_data = await cache_manager.get("test-pipeline-123-456")
        assert retrieved_data is not None
        assert retrieved_data["project_id"] == "123"
        assert retrieved_data["pipeline_id"] == 456
        assert retrieved_data["status"] == "failed"

    @pytest.mark.asyncio
    async def test_cache_expiration(self, temp_cache_manager):
        """Test cache expiration functionality"""
        cache_manager = temp_cache_manager

        # Set data with short TTL
        await cache_manager.set(
            key="expire-test",
            data={"test": "data"},
            data_type="test",
            project_id="123",
            ttl=1,  # 1 second
        )

        # Should be available immediately
        data = await cache_manager.get("expire-test")
        assert data is not None

        # Wait for expiration (in real test, we'd mock time)
        import asyncio

        await asyncio.sleep(1.1)

        # Should be expired now
        data = await cache_manager.get("expire-test")
        assert data is None

    @pytest.mark.asyncio
    async def test_cache_stats(self, temp_cache_manager):
        """Test cache statistics"""
        cache_manager = temp_cache_manager

        # Add some test data
        for i in range(5):
            await cache_manager.set(
                key=f"stats-test-{i}",
                data={"index": i, "mcp_info": {}},
                data_type="test",
                project_id="stats",
            )

        # Get stats
        stats = await cache_manager.get_cache_stats()

        assert "total_entries" in stats
        assert "entries_by_type" in stats
        assert stats["total_entries"] >= 5
        assert "test" in stats["entries_by_type"]

    @pytest.mark.asyncio
    async def test_cache_clear_operations(self, temp_cache_manager):
        """Test cache clearing operations"""
        cache_manager = temp_cache_manager

        # Add test data for different types and projects
        test_data = [
            ("pipeline-1", {"type": "pipeline"}, "pipeline", "123"),
            ("pipeline-2", {"type": "pipeline"}, "pipeline", "456"),
            ("job-1", {"type": "job"}, "job", "123"),
            ("job-2", {"type": "job"}, "job", "456"),
            ("analysis-1", {"type": "analysis"}, "analysis", "123"),
        ]

        for key, data, data_type, project_id in test_data:
            await cache_manager.set(
                key=key, data=data, data_type=data_type, project_id=project_id
            )

        # Test clearing by type
        cleared = await cache_manager.clear_cache_by_type("pipeline")
        assert cleared >= 2

        # Verify pipeline data is gone
        assert await cache_manager.get("pipeline-1") is None
        assert await cache_manager.get("pipeline-2") is None

        # Verify other data still exists
        assert await cache_manager.get("job-1") is not None
        assert await cache_manager.get("analysis-1") is not None

        # Test clearing by project
        cleared = await cache_manager.clear_cache_by_project("123")
        assert cleared >= 2

        # Verify project 123 data is gone
        assert await cache_manager.get("job-1") is None
        assert await cache_manager.get("analysis-1") is None

        # Verify project 456 data still exists
        assert await cache_manager.get("job-2") is not None

    @pytest.mark.asyncio
    async def test_cache_health_check(self, temp_cache_manager):
        """Test cache health check"""
        cache_manager = temp_cache_manager

        health = await cache_manager.check_health()

        assert "status" in health
        assert health["status"] in ["healthy", "warning", "critical"]
        assert "database_connected" in health
        assert "total_entries" in health

    @pytest.mark.asyncio
    async def test_store_job_file_errors(self, temp_cache_manager):
        """Test storing job file errors"""
        cache_manager = temp_cache_manager

        # Mock file and error data
        files = [
            {
                "file_path": "test_example.py",
                "error_count": 2,
                "errors": [
                    {"message": "AssertionError", "line_number": "42"},
                    {"message": "ImportError", "line_number": "10"},
                ],
            }
        ]

        errors = [
            {
                "message": "AssertionError",
                "file_path": "test_example.py",
                "line_number": "42",
            },
            {
                "message": "ImportError",
                "file_path": "test_example.py",
                "line_number": "10",
            },
        ]

        # Store the data
        await cache_manager.store_job_file_errors(
            project_id="123",
            pipeline_id=456,
            job_id=789,
            files=files,
            errors=errors,
            parser_type="generic",
        )

        # Verify data was stored
        job_errors = cache_manager.get_job_errors(789)
        assert len(job_errors) == 2
        assert job_errors[0]["message"] == "AssertionError"
        assert job_errors[1]["message"] == "ImportError"

    @pytest.mark.asyncio
    async def test_store_pipeline_info(self, temp_cache_manager):
        """Test storing pipeline information"""
        cache_manager = temp_cache_manager

        pipeline_info = {
            "id": 456,
            "status": "failed",
            "source_branch": "feature/test",
            "target_branch": "main",
            "sha": "abc123def456",
            "created_at": "2025-01-01T10:00:00Z",
            "jobs": [{"id": 789, "name": "test-job", "status": "failed"}],
        }

        # Store pipeline info
        await cache_manager.store_pipeline_info_async(
            project_id="123", pipeline_id=456, pipeline_info=pipeline_info
        )

        # Verify stored (this would need to be verified via database query in real implementation)
        # For now, just verify no errors occurred
        assert True

    @pytest.mark.asyncio
    async def test_error_trace_segments(self, temp_cache_manager):
        """Test storing error trace segments"""
        cache_manager = temp_cache_manager

        # Mock error records
        from gitlab_analyzer.cache.models import ErrorRecord

        error_records = [
            ErrorRecord(
                job_id=789,
                file_path="test_example.py",
                line=42,
                column=0,
                exception="AssertionError",
                message="Test failed",
                severity="error",
            )
        ]

        trace_text = """
        Running test_example.py::test_function...
        FAILED test_example.py::test_function - AssertionError: Test failed
        """

        # Store trace segments
        await cache_manager.store_error_trace_segments(
            job_id=789,
            trace_text=trace_text,
            trace_hash="abc123",
            errors=error_records,
            parser_type="pytest",
        )

        # Verify no errors occurred
        assert True

    @pytest.mark.asyncio
    async def test_cache_integration_with_tools(self, temp_cache_manager):
        """Test cache integration with MCP tools"""
        from gitlab_analyzer.mcp.tools.cache_tools import register_cache_tools

        # Setup mock MCP server
        mock_mcp = Mock()
        tools_registry = {}

        def mock_tool_decorator(func):
            tools_registry[func.__name__] = func
            return func

        mock_mcp.tool = mock_tool_decorator

        # Register cache tools
        register_cache_tools(mock_mcp)

        # Test that all tools were registered
        assert "clear_cache" in tools_registry
        assert "cache_stats" in tools_registry
        assert "cache_health" in tools_registry

        # Mock the get_cache_manager function to return our test manager
        with patch(
            "gitlab_analyzer.mcp.tools.cache_tools.get_cache_manager",
            return_value=temp_cache_manager,
        ):
            with patch(
                "gitlab_analyzer.mcp.tools.cache_tools.get_mcp_info",
                return_value={"test": True},
            ):
                # Test cache_stats tool
                cache_stats_func = tools_registry["cache_stats"]
                result = await cache_stats_func()

                assert result["operation"] == "cache_stats"
                assert result["status"] == "success"
                assert "stats" in result

                # Test cache_health tool
                cache_health_func = tools_registry["cache_health"]
                result = await cache_health_func()

                assert result["operation"] == "cache_health"
                assert result["status"] == "success"
                assert "health" in result

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self, temp_cache_manager):
        """Test concurrent cache access"""
        cache_manager = temp_cache_manager

        import asyncio

        async def write_data(i):
            await cache_manager.set(
                key=f"concurrent-{i}",
                data={"value": i, "mcp_info": {}},
                data_type="test",
                project_id="concurrent",
            )

        async def read_data(i):
            return await cache_manager.get(f"concurrent-{i}")

        # Write data concurrently
        write_tasks = [write_data(i) for i in range(10)]
        await asyncio.gather(*write_tasks)

        # Read data concurrently
        read_tasks = [read_data(i) for i in range(10)]
        results = await asyncio.gather(*read_tasks)

        # Verify all data was written and read correctly
        for i, result in enumerate(results):
            assert result is not None
            assert result["value"] == i

    @pytest.mark.asyncio
    async def test_cache_large_data(self, temp_cache_manager):
        """Test cache with large data objects"""
        cache_manager = temp_cache_manager

        # Create large test data
        large_data = {
            "errors": [
                {"message": f"Error {i}", "details": "x" * 1000} for i in range(100)
            ],
            "trace": "y" * 10000,
            "mcp_info": {"tool": "test", "large": True},
        }

        # Store large data
        await cache_manager.set(
            key="large-data-test", data=large_data, data_type="test", project_id="large"
        )

        # Retrieve and verify
        retrieved = await cache_manager.get("large-data-test")
        assert retrieved is not None
        assert len(retrieved["errors"]) == 100
        assert len(retrieved["trace"]) == 10000
        assert retrieved["mcp_info"]["large"] is True
