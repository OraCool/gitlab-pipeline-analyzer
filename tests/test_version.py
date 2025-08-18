"""
Test version detection utility

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from pathlib import Path
from unittest.mock import Mock, patch

from gitlab_analyzer.version import get_version


class TestVersionDetection:
    """Test version detection functionality"""

    def test_get_version_from_pyproject_toml_relative_path(self):
        """Test version detection from pyproject.toml using relative path"""
        # This should work in the actual project structure
        version = get_version()
        assert isinstance(version, str)
        assert version.count(".") >= 2  # Should be in format x.y.z
        assert not version.endswith("-fallback")  # Should find real version

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("gitlab_analyzer.version.Path.read_text")
    def test_get_version_from_pyproject_toml_mock(self, mock_read_text, mock_exists):
        """Test version detection from pyproject.toml with mocked file"""
        mock_exists.return_value = True
        mock_read_text.return_value = """
[project]
name = "gitlab-pipeline-analyzer"
version = "1.2.3"
description = "Test project"
"""

        version = get_version()
        assert version == "1.2.3"

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("gitlab_analyzer.version.Path.read_text")
    @patch("importlib.metadata.version")
    def test_get_version_pyproject_toml_malformed(
        self, mock_version, mock_read_text, mock_exists
    ):
        """Test version detection with malformed pyproject.toml"""
        mock_exists.return_value = True
        mock_read_text.return_value = """
[project]
name = "gitlab-pipeline-analyzer"
# Missing version line
description = "Test project"
"""
        # Mock the fallback to importlib.metadata
        mock_version.return_value = "2.0.0-from-metadata"

        # Should fall back to package metadata
        version = get_version()
        assert isinstance(version, str)
        assert version == "2.0.0-from-metadata"

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("gitlab_analyzer.version.Path.read_text")
    def test_get_version_pyproject_toml_read_error(self, mock_read_text, mock_exists):
        """Test version detection when pyproject.toml read fails"""
        mock_exists.return_value = True
        mock_read_text.side_effect = OSError("Permission denied")

        # Should fall back to package metadata or fallback version
        version = get_version()
        assert isinstance(version, str)

    @patch("gitlab_analyzer.version.Path.exists")
    def test_get_version_no_pyproject_toml(self, mock_exists):
        """Test version detection when pyproject.toml doesn't exist"""
        mock_exists.return_value = False

        # Should fall back to package metadata or fallback version
        version = get_version()
        assert isinstance(version, str)

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("importlib.metadata.version")
    def test_get_version_from_importlib_metadata(self, mock_version, mock_exists):
        """Test version detection from importlib.metadata"""
        mock_exists.return_value = False  # No pyproject.toml
        mock_version.return_value = "2.1.0"

        version = get_version()
        assert version == "2.1.0"

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("importlib.metadata.version")
    def test_get_version_importlib_metadata_error(self, mock_version, mock_exists):
        """Test version detection when importlib.metadata fails"""
        mock_exists.return_value = False  # No pyproject.toml
        mock_version.side_effect = Exception("Package not found")

        # Should fall back to fallback version
        version = get_version()
        assert version.endswith("-fallback")

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("importlib.metadata.version", side_effect=ImportError())
    @patch("pkg_resources.get_distribution")
    def test_get_version_from_pkg_resources(
        self, mock_get_distribution, mock_version, mock_exists
    ):
        """Test version detection from pkg_resources (Python < 3.8 compatibility)"""
        mock_exists.return_value = False  # No pyproject.toml

        mock_dist = Mock()
        mock_dist.version = "1.5.2"
        mock_get_distribution.return_value = mock_dist

        version = get_version()
        assert version == "1.5.2"

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("importlib.metadata.version", side_effect=ImportError())
    @patch("pkg_resources.get_distribution")
    def test_get_version_pkg_resources_error(
        self, mock_get_distribution, mock_version, mock_exists
    ):
        """Test version detection when pkg_resources fails"""
        mock_exists.return_value = False  # No pyproject.toml
        mock_get_distribution.side_effect = Exception("Distribution not found")

        # Should fall back to fallback version
        version = get_version()
        assert version.endswith("-fallback")

    def test_get_version_multiple_paths_first_exists(self):
        """Test version detection when first path exists"""
        # Use a more direct approach by mocking the file reading
        original_read_text = Path.read_text
        original_exists = Path.exists

        def mock_exists(self):
            return "pyproject.toml" in str(self)

        def mock_read_text(self, encoding="utf-8"):
            return """
[project]
version = "3.0.0"
"""

        try:
            Path.exists = mock_exists
            Path.read_text = mock_read_text
            version = get_version()
            assert version == "3.0.0"
        finally:
            Path.exists = original_exists
            Path.read_text = original_read_text

    def test_get_version_multiple_paths_second_exists(self):
        """Test version detection when second path exists"""
        original_read_text = Path.read_text
        original_exists = Path.exists
        call_count = 0

        def mock_exists(self):
            nonlocal call_count
            call_count += 1
            # First path doesn't exist, second path exists
            return call_count > 1 and "pyproject.toml" in str(self)

        def mock_read_text(self, encoding="utf-8"):
            return """
[project]
version = "4.0.0"
"""

        try:
            Path.exists = mock_exists
            Path.read_text = mock_read_text
            version = get_version()
            assert version == "4.0.0"
        finally:
            Path.exists = original_exists
            Path.read_text = original_read_text

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("gitlab_analyzer.version.Path.read_text")
    def test_get_version_pyproject_toml_different_format(
        self, mock_read_text, mock_exists
    ):
        """Test version detection with different pyproject.toml format"""
        mock_exists.return_value = True
        mock_read_text.return_value = """
[build-system]
requires = ["setuptools"]

[project]
name = "test"
version = "5.1.0-beta"
authors = []
"""

        version = get_version()
        assert version == "5.1.0-beta"

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("gitlab_analyzer.version.Path.read_text")
    @patch("importlib.metadata.version")
    def test_get_version_pyproject_toml_single_quotes(
        self, mock_version, mock_read_text, mock_exists
    ):
        """Test version detection with single quotes in pyproject.toml"""
        mock_exists.return_value = True
        mock_read_text.return_value = """
[project]
name = 'gitlab-pipeline-analyzer'
version = '6.0.0'
description = 'Test project'
"""
        # Mock the fallback since current implementation only handles double quotes
        mock_version.return_value = "6.0.0-from-metadata"

        # Current implementation expects double quotes, so this should fallback
        version = get_version()
        # Should fallback since it looks for double quotes specifically
        assert isinstance(version, str)
        assert version == "6.0.0-from-metadata"

    def test_get_version_integration(self):
        """Test version detection integration with real environment"""
        # This test runs without mocks to verify real behavior
        version = get_version()

        # Should return a valid version string
        assert isinstance(version, str)
        assert len(version) > 0

        # Should be in semver format or fallback format
        if not version.endswith("-fallback"):
            parts = version.split(".")
            assert len(parts) >= 2  # At least major.minor
            assert all(
                part.replace("-", "")
                .replace("a", "")
                .replace("b", "")
                .replace("rc", "")
                .isdigit()
                for part in parts
                if part
            )  # All parts should be numeric (allowing pre-release suffixes)

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("gitlab_analyzer.version.Path.read_text")
    @patch("importlib.metadata.version")
    def test_get_version_empty_file(self, mock_version, mock_read_text, mock_exists):
        """Test version detection with empty pyproject.toml"""
        mock_exists.return_value = True
        mock_read_text.return_value = ""
        # Mock the fallback
        mock_version.return_value = "1.0.0-from-metadata"

        # Should fall back gracefully
        version = get_version()
        assert isinstance(version, str)
        assert version == "1.0.0-from-metadata"

    @patch("gitlab_analyzer.version.Path.exists")
    @patch("gitlab_analyzer.version.Path.read_text")
    def test_get_version_unicode_content(self, mock_read_text, mock_exists):
        """Test version detection with unicode content in pyproject.toml"""
        mock_exists.return_value = True
        mock_read_text.return_value = """
[project]
name = "gitlab-pipeline-analyzer"
version = "1.0.0"
description = "Test with unicode: 🚀 Pipeline analyzer"
"""

        version = get_version()
        assert version == "1.0.0"
