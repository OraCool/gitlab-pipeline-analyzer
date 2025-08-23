"""
Simple integration tests for MCP resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import pytest

from gitlab_analyzer.mcp.resources.analysis import register_analysis_resources
from gitlab_analyzer.mcp.resources.error import register_error_resources
from gitlab_analyzer.mcp.resources.file import register_file_resources
from gitlab_analyzer.mcp.resources.job import register_job_resources
from gitlab_analyzer.mcp.resources.pipeline import register_pipeline_resources


class TestResourceRegistration:
    """Test that all resource modules can be registered without errors"""

    def test_file_resources_registration(self):
        """Test file resources can be registered"""
        from unittest.mock import Mock

        mock_mcp = Mock()

        # Should not raise an exception
        register_file_resources(mock_mcp)

        # Should have called the resource decorator
        assert mock_mcp.resource.called

    def test_error_resources_registration(self):
        """Test error resources can be registered"""
        from unittest.mock import Mock

        mock_mcp = Mock()

        # Should not raise an exception
        register_error_resources(mock_mcp)

        # Should have called the resource decorator
        assert mock_mcp.resource.called

    def test_analysis_resources_registration(self):
        """Test analysis resources can be registered"""
        from unittest.mock import Mock

        mock_mcp = Mock()

        # Should not raise an exception
        register_analysis_resources(mock_mcp)

        # Should have called the resource decorator
        assert mock_mcp.resource.called

    def test_pipeline_resources_registration(self):
        """Test pipeline resources can be registered"""
        from unittest.mock import Mock

        mock_mcp = Mock()

        # Should not raise an exception
        register_pipeline_resources(mock_mcp)

        # Should have called the resource decorator
        assert mock_mcp.resource.called

    def test_job_resources_registration(self):
        """Test job resources can be registered"""
        from unittest.mock import Mock

        mock_mcp = Mock()

        # Should not raise an exception
        register_job_resources(mock_mcp)

        # Should have called the resource decorator
        assert mock_mcp.resource.called


class TestResourceImports:
    """Test that all resource modules can be imported"""

    def test_can_import_file_resources(self):
        """Test file resources module imports"""
        import gitlab_analyzer.mcp.resources.file

        assert hasattr(gitlab_analyzer.mcp.resources.file, "register_file_resources")

    def test_can_import_error_resources(self):
        """Test error resources module imports"""
        import gitlab_analyzer.mcp.resources.error

        assert hasattr(gitlab_analyzer.mcp.resources.error, "register_error_resources")

    def test_can_import_analysis_resources(self):
        """Test analysis resources module imports"""
        import gitlab_analyzer.mcp.resources.analysis

        assert hasattr(
            gitlab_analyzer.mcp.resources.analysis, "register_analysis_resources"
        )

    def test_can_import_pipeline_resources(self):
        """Test pipeline resources module imports"""
        import gitlab_analyzer.mcp.resources.pipeline

        assert hasattr(
            gitlab_analyzer.mcp.resources.pipeline, "register_pipeline_resources"
        )

    def test_can_import_job_resources(self):
        """Test job resources module imports"""
        import gitlab_analyzer.mcp.resources.job

        assert hasattr(gitlab_analyzer.mcp.resources.job, "register_job_resources")


class TestCacheIntegration:
    """Test cache manager integration"""

    def test_cache_manager_import(self):
        """Test cache manager can be imported"""
        from gitlab_analyzer.mcp.cache import get_cache_manager

        assert callable(get_cache_manager)

    def test_cache_models_import(self):
        """Test cache models can be imported"""
        from gitlab_analyzer.mcp.cache.models import CacheData, generate_cache_key

        assert CacheData is not None
        assert callable(generate_cache_key)

    def test_cache_key_generation(self):
        """Test cache key generation works"""
        from gitlab_analyzer.mcp.cache.models import generate_cache_key

        key = generate_cache_key("test", "123", 456)
        assert key is not None
        assert isinstance(key, str)
        assert "test" in key
        assert "123" in key
        assert "456" in key


class TestUtilsIntegration:
    """Test utility functions integration"""

    def test_utils_import(self):
        """Test utils can be imported"""
        from gitlab_analyzer.mcp.tools.utils import get_mcp_info

        assert callable(get_mcp_info)

    def test_mcp_info_generation(self):
        """Test MCP info generation"""
        from gitlab_analyzer.mcp.tools.utils import get_mcp_info

        info = get_mcp_info(tool_used="test")
        assert isinstance(info, dict)
        assert "tool_used" in info
        assert info["tool_used"] == "test"
        # MCP info contains basic metadata
        assert "name" in info
        assert "version" in info


class TestParserIntegration:
    """Test parser integration"""

    def test_log_parser_import(self):
        """Test log parser can be imported"""
        from gitlab_analyzer.parsers.log_parser import LogParser

        assert LogParser is not None

    def test_log_parser_initialization(self):
        """Test log parser can be initialized"""
        from gitlab_analyzer.parsers.log_parser import LogParser

        parser = LogParser()
        assert parser is not None


@pytest.mark.asyncio
class TestAsyncIntegration:
    """Test async integration without external dependencies"""

    async def test_cache_manager_creation(self):
        """Test cache manager can be created"""
        from gitlab_analyzer.mcp.cache import get_cache_manager

        # Should not raise an exception
        cache_manager = get_cache_manager()
        assert cache_manager is not None
