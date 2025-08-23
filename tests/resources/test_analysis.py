"""
Tests for analysis resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
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
        analyzer.get_pipeline_info = AsyncMock(
            return_value={
                "id": 456,
                "status": "failed",
                "created_at": "2025-01-01T00:00:00Z",
                "duration": 300,
            }
        )
        analyzer.get_pipeline_jobs = AsyncMock(
            return_value=[
                {
                    "id": 123,
                    "name": "test_job",
                    "status": "failed",
                    "stage": "test",
                    "duration": 120,
                },
                {
                    "id": 124,
                    "name": "build_job",
                    "status": "success",
                    "stage": "build",
                    "duration": 60,
                },
                {
                    "id": 125,
                    "name": "lint_job",
                    "status": "failed",
                    "stage": "test",
                    "duration": 30,
                },
            ]
        )
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
    @patch("gitlab_analyzer.mcp.resources.analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.resources.analysis.get_mcp_info")
    @patch("gitlab_analyzer.parsers.log_parser.LogParser")
    async def test_get_comprehensive_analysis_pipeline(
        self,
        mock_parser_class,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache,
        mock_cache_manager,
        mock_analyzer,
        mock_log_entries,
    ):
        """Test comprehensive analysis for pipeline scope"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_mcp_info.return_value = {"tool": "test", "timestamp": "2025-01-01"}

        mock_parser = Mock()
        mock_parser.extract_log_entries.return_value = mock_log_entries
        mock_parser_class.return_value = mock_parser

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
        assert analysis["job_id"] is None

        # Check pipeline summary
        pipeline_summary = analysis["pipeline_summary"]
        assert pipeline_summary["total_jobs"] == 3
        assert pipeline_summary["failed_jobs"] == 2
        assert pipeline_summary["success_rate"] == 33.33  # 1 success out of 3

        # Check error patterns
        error_patterns = analysis["error_patterns"]
        assert "import_errors" in error_patterns
        assert "test_failures" in error_patterns
        assert error_patterns["import_errors"]["count"] == 5
        assert error_patterns["test_failures"]["count"] == 3

        # Check metadata
        metadata = data["metadata"]
        assert metadata["response_mode"] == response_mode
        assert metadata["analysis_scope"] == "pipeline"
        assert metadata["analysis_type"] == "comprehensive"

        # Check resource URI
        expected_uri = f"gl://analysis/{project_id}/{pipeline_id}?mode={response_mode}"
        assert data["resource_uri"] == expected_uri

        # Verify calls
        mock_analyzer.get_pipeline_info.assert_called_once_with(
            project_id, int(pipeline_id)
        )
        mock_analyzer.get_pipeline_jobs.assert_called_once_with(
            project_id, int(pipeline_id)
        )

    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.resources.analysis.get_mcp_info")
    @patch("gitlab_analyzer.parsers.log_parser.LogParser")
    async def test_get_comprehensive_analysis_job(
        self,
        mock_parser_class,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache,
        mock_cache_manager,
        mock_analyzer,
        mock_log_entries,
    ):
        """Test comprehensive analysis for job scope"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_mcp_info.return_value = {"tool": "test"}

        mock_parser = Mock()
        mock_parser.extract_log_entries.return_value = mock_log_entries
        mock_parser_class.return_value = mock_parser

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
        expected_uri = (
            f"gl://analysis/{project_id}/{pipeline_id}/{job_id}?mode={response_mode}"
        )
        assert data["resource_uri"] == expected_uri

        # For job scope, should not call pipeline methods
        mock_analyzer.get_pipeline_info.assert_not_called()
        mock_analyzer.get_pipeline_jobs.assert_not_called()
        mock_analyzer.get_job_trace.assert_called_once_with(project_id, int(job_id))

    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.analysis.get_gitlab_analyzer")
    async def test_get_comprehensive_analysis_cached(
        self,
        mock_get_analyzer,
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

        # Verify cache was checked but analyzer was not called
        mock_cache_manager.get.assert_called_once()
        mock_get_analyzer.assert_not_called()

    @pytest.mark.parametrize("response_mode", ["minimal", "balanced", "fixing", "full"])
    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.resources.analysis.get_mcp_info")
    @patch("gitlab_analyzer.mcp.resources.analysis.optimize_tool_response")
    @patch("gitlab_analyzer.parsers.log_parser.LogParser")
    async def test_get_comprehensive_analysis_modes(
        self,
        mock_parser_class,
        mock_optimize,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache,
        mock_cache_manager,
        mock_analyzer,
        mock_log_entries,
        response_mode,
    ):
        """Test comprehensive analysis with different response modes"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_mcp_info.return_value = {"tool": "test"}

        mock_parser = Mock()
        mock_parser.extract_log_entries.return_value = mock_log_entries
        mock_parser_class.return_value = mock_parser

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
        assert call_args[1] == response_mode

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
    @patch("gitlab_analyzer.mcp.resources.analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.resources.analysis.get_mcp_info")
    @patch("gitlab_analyzer.parsers.log_parser.LogParser")
    async def test_success_rate_calculation(
        self,
        mock_parser_class,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache,
        mock_cache_manager,
        mock_analyzer,
    ):
        """Test success rate calculation"""
        # Setup jobs with different statuses
        jobs = [
            {"id": 1, "status": "success", "stage": "test"},
            {"id": 2, "status": "success", "stage": "build"},
            {"id": 3, "status": "failed", "stage": "test"},
            {"id": 4, "status": "canceled", "stage": "deploy"},
            {"id": 5, "status": "success", "stage": "build"},
        ]

        mock_analyzer.get_pipeline_jobs.return_value = jobs

        # Setup other mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_mcp_info.return_value = {"tool": "test"}

        mock_parser = Mock()
        mock_parser.extract_log_entries.return_value = []
        mock_parser_class.return_value = mock_parser

        # Execute
        result = await _get_comprehensive_analysis("123", "456", None, "balanced")

        # Verify success rate calculation
        data = json.loads(result)
        pipeline_summary = data["comprehensive_analysis"]["pipeline_summary"]

        assert pipeline_summary["total_jobs"] == 5
        assert pipeline_summary["successful_jobs"] == 3
        assert pipeline_summary["failed_jobs"] == 1
        assert pipeline_summary["canceled_jobs"] == 1
        assert pipeline_summary["success_rate"] == 60.0  # 3/5 * 100

    @patch("gitlab_analyzer.mcp.resources.analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.analysis.get_gitlab_analyzer")
    async def test_get_comprehensive_analysis_error_handling(
        self, mock_get_analyzer, mock_get_cache, mock_cache_manager, mock_analyzer
    ):
        """Test error handling in comprehensive analysis"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer

        # Make analyzer raise an exception
        mock_analyzer.get_pipeline_info.side_effect = Exception("GitLab API error")

        # Execute
        result = await _get_comprehensive_analysis("123", "456", None, "balanced")

        # Verify error response
        data = json.loads(result)
        assert "error" in data
        assert "Failed to get analysis resource" in data["error"]
        assert data["project_id"] == "123"
        assert data["pipeline_id"] == "456"
