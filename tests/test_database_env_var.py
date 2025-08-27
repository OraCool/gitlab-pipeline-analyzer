"""Test that the MCP_DATABASE_PATH environment variable works correctly."""

import os
import tempfile
from pathlib import Path

from gitlab_analyzer.cache.mcp_cache import McpCache, get_cache_manager


class TestDatabaseEnvironmentVariable:
    """Test database path environment variable functionality."""

    def test_default_database_path(self):
        """Test that default database path is used when no env var is set."""
        # Clear any existing environment variable
        original_value = os.environ.pop("MCP_DATABASE_PATH", None)

        try:
            cache = McpCache()
            assert cache.db_path.name == "analysis_cache.db"
        finally:
            # Restore original value if it existed
            if original_value is not None:
                os.environ["MCP_DATABASE_PATH"] = original_value

    def test_custom_database_path_via_env_var(self):
        """Test that custom database path is used when env var is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_db_path = str(Path(temp_dir) / "custom_cache.db")

            # Set environment variable
            original_value = os.environ.get("MCP_DATABASE_PATH")
            os.environ["MCP_DATABASE_PATH"] = custom_db_path

            try:
                cache = McpCache()
                assert str(cache.db_path) == custom_db_path
            finally:
                # Restore original value
                if original_value is not None:
                    os.environ["MCP_DATABASE_PATH"] = original_value
                else:
                    os.environ.pop("MCP_DATABASE_PATH", None)

    def test_explicit_database_path_overrides_env_var(self):
        """Test that explicit db_path parameter overrides environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_db_path = str(Path(temp_dir) / "env_cache.db")
            explicit_db_path = str(Path(temp_dir) / "explicit_cache.db")

            # Set environment variable
            original_value = os.environ.get("MCP_DATABASE_PATH")
            os.environ["MCP_DATABASE_PATH"] = env_db_path

            try:
                cache = McpCache(db_path=explicit_db_path)
                assert str(cache.db_path) == explicit_db_path
            finally:
                # Restore original value
                if original_value is not None:
                    os.environ["MCP_DATABASE_PATH"] = original_value
                else:
                    os.environ.pop("MCP_DATABASE_PATH", None)

    def test_get_cache_manager_respects_env_var(self):
        """Test that get_cache_manager function respects environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_db_path = str(Path(temp_dir) / "manager_cache.db")

            # Set environment variable
            original_value = os.environ.get("MCP_DATABASE_PATH")
            os.environ["MCP_DATABASE_PATH"] = custom_db_path

            try:
                # Clear any global cache instance
                import gitlab_analyzer.cache.mcp_cache as cache_module

                cache_module._global_cache = None

                cache_manager = get_cache_manager()
                assert str(cache_manager.db_path) == custom_db_path
            finally:
                # Restore original value and clear global cache
                if original_value is not None:
                    os.environ["MCP_DATABASE_PATH"] = original_value
                else:
                    os.environ.pop("MCP_DATABASE_PATH", None)
                cache_module._global_cache = None

    def test_get_cache_manager_with_explicit_path(self):
        """Test that get_cache_manager with explicit path works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_db_path = str(Path(temp_dir) / "env_cache.db")
            explicit_db_path = str(Path(temp_dir) / "explicit_cache.db")

            # Set environment variable
            original_value = os.environ.get("MCP_DATABASE_PATH")
            os.environ["MCP_DATABASE_PATH"] = env_db_path

            try:
                # Clear any global cache instance
                import gitlab_analyzer.cache.mcp_cache as cache_module

                cache_module._global_cache = None

                cache_manager = get_cache_manager(db_path=explicit_db_path)
                assert str(cache_manager.db_path) == explicit_db_path
            finally:
                # Restore original value and clear global cache
                if original_value is not None:
                    os.environ["MCP_DATABASE_PATH"] = original_value
                else:
                    os.environ.pop("MCP_DATABASE_PATH", None)
                cache_module._global_cache = None
