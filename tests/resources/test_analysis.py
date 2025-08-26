"""
Tests for analysis resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.resources.analysis import (
    _get_comprehensive_analysis,
    register_analysis_resources,
)


class TestAnalysisResources:
    """Test analysis resource functionality"""

    @pytest.fixture
    def mock_analyzer(self):
        """Mock GitLab analyzer"""
        analyzer = Mock()
        analyzer.get_pipeline = AsyncMock(
            return_value={
                "id": 456,
                "status": "failed",
                "created_at": "2025-01-01T00:00:00Z",
                "duration": 300,
            }
        )

        # Create job objects with attributes using SimpleNamespace
        job1 = SimpleNamespace(
            id=123,
            name="test_job",
            status="failed",
            stage="test",
            duration=120,
            failure_reason="test_failure",
        )

        job2 = SimpleNamespace(
            id=124,
            name="build_job",
            status="success",
            stage="build",
            duration=60,
            failure_reason=None,
        )

        job3 = SimpleNamespace(
            id=125,
            name="lint_job",
            status="failed",
            stage="test",
            duration=30,
            failure_reason="lint_failure",
        )

        analyzer.get_pipeline_jobs = AsyncMock(return_value=[job1, job2, job3])
        analyzer.get_job_trace = AsyncMock(return_value="mock trace content")
        return analyzer

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        cache_manager = Mock()
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        return cache_manager

    @pytest.fixture
    def mock_log_entries(self):
        """Mock log entries with patterns"""
        entries = []

        # Create entries with common patterns
        for i in range(5):
            entry = Mock()
            entry.message = f"ImportError: No module named 'missing_module_{i}'"
            entry.level = "error"
            entry.exception_type = "ImportError"
            entry.file_path = f"src/module_{i}.py"
            entries.append(entry)

        # Add some test failures
        for i in range(3):
            entry = Mock()
            entry.message = f"AssertionError in test_{i}"
            entry.level = "error"
            entry.exception_type = "AssertionError"
            entry.file_path = f"tests/test_{i}.py"
            entries.append(entry)

        return entries

    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_get_comprehensive_analysis_pipeline(
        self,
        mock_get_mcp_info,
        mock_get_cache,
        mock_cache_manager,
        mock_log_entries,
    ):
        """Test comprehensive analysis for pipeline scope"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {"tool": "test", "timestamp": "2025-01-01"}

        # Mock cache manager to return None (no cached data)
        mock_cache_manager.get.return_value = None

        # Mock async database methods for pipeline analysis
        from unittest.mock import AsyncMock

        mock_cache_manager.get_pipeline_jobs = AsyncMock(
            return_value=[
                {"id": 1, "status": "failed", "stage": "test", "name": "test-job-1"},
                {"id": 2, "status": "failed", "stage": "build", "name": "build-job"},
                {"id": 3, "status": "success", "stage": "deploy", "name": "deploy-job"},
            ]
        )
        mock_cache_manager.set = AsyncMock()
        mock_cache_manager.get_pipeline_info.return_value = {"status": "failed"}
        mock_cache_manager.get_pipeline_failed_jobs.return_value = [
            {"id": 1, "status": "failed", "stage": "test", "name": "test-job-1"},
            {"id": 2, "status": "failed", "stage": "build", "name": "build-job"},
        ]
        mock_cache_manager.get_job_errors.return_value = [
            {
                "job_id": 1,
                "error_type": "test_failure",
                "message": "Test failed",
                "file_path": "test_file.py",
                "line_number": 10,
            }
        ]

        # Test parameters
        project_id = "123"
        pipeline_id = "456"
        response_mode = "balanced"

        # Execute
        result = await _get_comprehensive_analysis(
            project_id, pipeline_id, None, response_mode
        )

        # Verify
        assert result is not None
        data = json.loads(result)

        # Check structure
        assert "comprehensive_analysis" in data
        assert "resource_uri" in data
        assert "cached_at" in data
        assert "metadata" in data
        assert "mcp_info" in data

        # Check analysis content
        analysis = data["comprehensive_analysis"]
        assert analysis["project_id"] == project_id
        assert analysis["pipeline_id"] == int(pipeline_id)
        # job_id should not be present for pipeline scope
        assert "job_id" not in analysis

        # Check pipeline summary
        summary = analysis["summary"]
        assert summary["total_jobs"] == 3
        assert summary["failed_jobs"] == 2
        assert summary["success_rate"] == 1 / 3  # 1 success out of 3

        # Check job analysis
        job_analysis = analysis["job_analysis"]
        assert "jobs" in job_analysis
        assert "failed_jobs" in job_analysis
        assert len(job_analysis["failed_jobs"]) == 2

        # Check metadata
        metadata = data["metadata"]
        assert metadata["response_mode"] == response_mode
        assert metadata["analysis_scope"] == "pipeline"

        # Check resource URI
        expected_uri = (
            f"gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={response_mode}"
        )
        assert data["resource_uri"] == expected_uri

        # Verify cache calls
        mock_cache_manager.get.assert_called_once()
        mock_cache_manager.set.assert_called_once()

    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_get_comprehensive_analysis_job(
        self,
        mock_get_mcp_info,
        mock_get_cache,
        mock_cache_manager,
        mock_log_entries,
    ):
        """Test comprehensive analysis for job scope"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Mock cache manager to return None (no cached data)
        mock_cache_manager.get.return_value = None

        # Mock async database methods for job analysis
        from unittest.mock import AsyncMock

        mock_cache_manager.get_job_info_async = AsyncMock(
            return_value={
                "id": 789,
                "status": "failed",
                "stage": "test",
                "name": "test-job",
            }
        )
        mock_cache_manager.set = AsyncMock()
        mock_cache_manager.get_job_errors.return_value = [
            {
                "job_id": 789,
                "error_type": "test_failure",
                "message": "Test failed",
                "file_path": "test_file.py",
                "line_number": 10,
            }
        ]

        # Test parameters
        project_id = "123"
        pipeline_id = "456"
        job_id = "789"
        response_mode = "full"

        # Execute
        result = await _get_comprehensive_analysis(
            project_id, pipeline_id, job_id, response_mode
        )

        # Verify
        data = json.loads(result)

        # Check job-specific content
        analysis = data["comprehensive_analysis"]
        assert analysis["job_id"] == int(job_id)
        assert data["metadata"]["analysis_scope"] == "job"

        # Check resource URI includes job_id
        expected_uri = f"gl://analysis/{project_id}/job/{job_id}?mode={response_mode}"
        assert data["resource_uri"] == expected_uri

        # Verify cache calls
        mock_cache_manager.get.assert_called_once()
        mock_cache_manager.set.assert_called_once()

    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    async def test_get_comprehensive_analysis_cached(
        self,
        mock_get_cache,
        mock_cache_manager,
    ):
        """Test comprehensive analysis with cached data"""
        # Setup cached data
        cached_data = {
            "comprehensive_analysis": {
                "project_id": "123",
                "pipeline_id": 456,
                "error_patterns": {"import_errors": {"count": 10}},
                "recommendations": ["Fix import issues"],
            },
            "cached": True,
        }
        mock_cache_manager.get.return_value = cached_data
        mock_get_cache.return_value = mock_cache_manager

        # Execute
        result = await _get_comprehensive_analysis("123", "456", None, "balanced")

        # Verify
        data = json.loads(result)
        assert data == cached_data

        # Verify cache was checked
        mock_cache_manager.get.assert_called_once()
        # Note: get_gitlab_analyzer is called at the beginning regardless of cache hit

    @pytest.mark.parametrize("response_mode", ["minimal", "balanced", "fixing", "full"])
    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    @patch("gitlab_analyzer.utils.utils.optimize_tool_response")
    async def test_get_comprehensive_analysis_modes(
        self,
        mock_optimize,
        mock_get_mcp_info,
        mock_get_cache,
        mock_cache_manager,
        mock_log_entries,
        response_mode,
    ):
        """Test comprehensive analysis with different response modes"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_cache_manager.get.return_value = None  # No cached data
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Mock async database methods for pipeline analysis
        from unittest.mock import AsyncMock

        mock_cache_manager.get_pipeline_jobs = AsyncMock(
            return_value=[
                {"id": 1, "status": "failed", "stage": "test", "name": "test-job"},
                {"id": 2, "status": "success", "stage": "build", "name": "build-job"},
            ]
        )
        mock_cache_manager.set = AsyncMock()
        mock_cache_manager.get_pipeline_info.return_value = {"status": "failed"}
        mock_cache_manager.get_pipeline_failed_jobs.return_value = [
            {"id": 1, "status": "failed", "stage": "test", "name": "test-job"},
        ]

        # Mock optimization to return the same data
        mock_optimize.side_effect = lambda x, mode: x

        # Execute
        result = await _get_comprehensive_analysis("123", "456", None, response_mode)

        # Verify
        data = json.loads(result)

        # Check mode is set correctly
        assert data["metadata"]["response_mode"] == response_mode
        assert f"mode={response_mode}" in data["resource_uri"]

        # Verify optimization was called with correct mode
        mock_optimize.assert_called_once()
        call_args = mock_optimize.call_args
        assert call_args[0][1] == response_mode  # Second positional argument

    def test_pattern_identification(self):
        """Test error pattern identification logic"""
        from gitlab_analyzer.mcp.resources.analysis import _identify_patterns

        # Create mock entries with different patterns
        entries = []

        # Import errors
        for i in range(3):
            entry = Mock()
            entry.message = f"ImportError: No module named 'module_{i}'"
            entry.exception_type = "ImportError"
            entries.append(entry)

        # Syntax errors
        for _ in range(2):
            entry = Mock()
            entry.message = "SyntaxError: invalid syntax"
            entry.exception_type = "SyntaxError"
            entries.append(entry)

        # Test failures
        entry = Mock()
        entry.message = "AssertionError: test failed"
        entry.exception_type = "AssertionError"
        entries.append(entry)

        # Execute pattern identification
        patterns = _identify_patterns(entries)

        # Verify patterns (returns list, not dict)
        assert "import_errors" in patterns
        assert "syntax_errors" in patterns

    def test_register_analysis_resources(self):
        """Test resource registration"""
        # Mock MCP server
        mock_mcp = Mock()

        # Execute registration
        register_analysis_resources(mock_mcp)

        # Verify resource decorators were called
        assert (
            mock_mcp.resource.call_count == 6
        )  # 6 resources: project, project+mode, pipeline, pipeline+mode, job, job+mode

        # Check the resource URI patterns
        call_args = [call[0][0] for call in mock_mcp.resource.call_args_list]
        expected_patterns = [
            "gl://analysis/{project_id}",
            "gl://analysis/{project_id}?mode={mode}",
            "gl://analysis/{project_id}/pipeline/{pipeline_id}",
            "gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={mode}",
            "gl://analysis/{project_id}/job/{job_id}",
            "gl://analysis/{project_id}/job/{job_id}?mode={mode}",
        ]

        for pattern in expected_patterns:
            assert pattern in call_args

    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_success_rate_calculation(
        self,
        mock_get_mcp_info,
        mock_get_cache,
        mock_cache_manager,
    ):
        """Test success rate calculation"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_cache_manager.get.return_value = None  # No cached data
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Mock async database methods with specific job data for success rate calculation
        from unittest.mock import AsyncMock

        jobs = [
            {"id": 1, "status": "success", "stage": "test", "name": "test1"},
            {"id": 2, "status": "success", "stage": "build", "name": "build1"},
            {"id": 3, "status": "failed", "stage": "test", "name": "test2"},
            {"id": 4, "status": "success", "stage": "deploy", "name": "deploy1"},
            {"id": 5, "status": "success", "stage": "build", "name": "build2"},
        ]

        mock_cache_manager.get_pipeline_jobs = AsyncMock(return_value=jobs)
        mock_cache_manager.set = AsyncMock()
        mock_cache_manager.get_pipeline_info.return_value = {
            "id": 456,
            "status": "failed",
        }
        mock_cache_manager.get_pipeline_failed_jobs.return_value = [
            {"id": 3, "status": "failed", "stage": "test", "name": "test2"},
        ]

        # Execute
        result = await _get_comprehensive_analysis("123", "456", None, "balanced")

        # Verify success rate calculation
        data = json.loads(result)
        summary = data["comprehensive_analysis"]["summary"]

        assert summary["total_jobs"] == 5
        assert summary["failed_jobs"] == 1  # Only job3 is failed
        # success_rate = (total - failed) / total = (5 - 1) / 5 = 0.8
        assert summary["success_rate"] == 0.8

    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    async def test_get_comprehensive_analysis_error_handling(
        self, mock_get_cache, mock_cache_manager
    ):
        """Test error handling in comprehensive analysis"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager

        # Make cache manager raise an exception to simulate database error
        from unittest.mock import AsyncMock

        mock_cache_manager.get_pipeline_jobs = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Execute
        result = await _get_comprehensive_analysis("123", "456", None, "balanced")

        # Verify error response
        data = json.loads(result)
        assert "error" in data
        assert "Failed to get analysis resource" in data["error"]
        assert data["project_id"] == "123"
        # Note: pipeline_id is not included in error responses
