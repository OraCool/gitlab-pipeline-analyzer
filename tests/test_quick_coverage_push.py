"""
Quick coverage boost test - targeting specific high-impact lines to reach 65% coverage threshold.
This test file focuses on easy-to-test functions that provide maximum coverage impact.
"""

from gitlab_analyzer.parsers.base_parser import (
    BaseFrameworkDetector,
    BaseFrameworkParser,
)
from gitlab_analyzer.utils.utils import (
    categorize_files_by_type,
    combine_exclude_file_patterns,
    extract_file_path_from_message,
    should_exclude_file_path,
)


class TestQuickCoveragePush:
    """Tests targeting high-impact coverage gaps for final push to 65%"""

    def test_extract_file_path_from_message_python_traceback(self):
        """Test extracting file path from Python traceback format"""
        message = 'File "/home/user/project/src/main.py", line 15, in function_name'
        result = extract_file_path_from_message(message)
        assert result == "/home/user/project/src/main.py"

    def test_extract_file_path_from_message_simple_path(self):
        """Test extracting file path from simple path format"""
        message = "Error in src/utils/helper.py at line 20"
        result = extract_file_path_from_message(message)
        assert result == "src/utils/helper.py"

    def test_extract_file_path_from_message_no_match(self):
        """Test extracting file path when no file path found"""
        message = "Generic error message without file path"
        result = extract_file_path_from_message(message)
        assert result is None

    def test_should_exclude_file_path_system_paths(self):
        """Test should_exclude_file_path with system paths"""
        assert (
            should_exclude_file_path("/usr/lib/python3.9/site-packages/test.py") is True
        )
        assert (
            should_exclude_file_path(
                "/home/user/.local/lib/python3.9/site-packages/test.py"
            )
            is True
        )
        assert (
            should_exclude_file_path(
                "/opt/miniconda/lib/python3.9/site-packages/test.py"
            )
            is True
        )

    def test_should_exclude_file_path_venv_paths(self):
        """Test should_exclude_file_path with virtual environment paths"""
        assert (
            should_exclude_file_path("venv/lib/python3.9/site-packages/test.py") is True
        )
        assert (
            should_exclude_file_path(".venv/lib/python3.9/site-packages/test.py")
            is True
        )
        assert (
            should_exclude_file_path("env/lib/python3.9/site-packages/test.py") is True
        )

    def test_should_exclude_file_path_user_code(self):
        """Test should_exclude_file_path with user code paths"""
        assert should_exclude_file_path("src/main.py") is False
        assert should_exclude_file_path("tests/test_main.py") is False
        assert should_exclude_file_path("my_project/utils.py") is False

    def test_should_exclude_file_path_custom_patterns(self):
        """Test should_exclude_file_path with custom exclude patterns"""
        custom_patterns = ["node_modules/", "build/", "dist/"]
        assert (
            should_exclude_file_path("node_modules/express/index.js", custom_patterns)
            is True
        )
        assert should_exclude_file_path("build/output.js", custom_patterns) is True
        assert should_exclude_file_path("src/index.js", custom_patterns) is False

    def test_categorize_files_by_type_python(self):
        """Test categorizing files by type - Python files"""
        files = [
            {"file_path": "src/main.py", "error_count": 5},
            {"file_path": "tests/test_main.py", "error_count": 2},
            {"file_path": "config.py", "error_count": 1},
        ]
        result = categorize_files_by_type(files)
        assert "python" in result
        assert len(result["python"]) == 3

    def test_categorize_files_by_type_javascript(self):
        """Test categorizing files by type - JavaScript files"""
        files = [
            {"file_path": "src/app.js", "error_count": 3},
            {"file_path": "tests/app.test.js", "error_count": 1},
        ]
        result = categorize_files_by_type(files)
        assert "javascript" in result
        assert len(result["javascript"]) == 2

    def test_categorize_files_by_type_mixed(self):
        """Test categorizing files by type - Mixed file types"""
        files = [
            {"file_path": "src/main.py", "error_count": 5},
            {"file_path": "src/app.js", "error_count": 3},
            {"file_path": "README.md", "error_count": 1},
            {"file_path": "Dockerfile", "error_count": 2},
        ]
        result = categorize_files_by_type(files)
        assert "python" in result
        assert "javascript" in result
        assert "other" in result

    def test_combine_exclude_file_patterns_no_custom(self):
        """Test combining exclude file patterns with no custom patterns"""
        result = combine_exclude_file_patterns(None)
        # Should return default patterns
        assert isinstance(result, list)
        assert len(result) > 0
        assert any("site-packages" in pattern for pattern in result)

    def test_combine_exclude_file_patterns_with_custom(self):
        """Test combining exclude file patterns with custom patterns"""
        custom_patterns = ["node_modules/", "build/"]
        result = combine_exclude_file_patterns(custom_patterns)
        # Should include both default and custom patterns
        assert "node_modules/" in result
        assert "build/" in result
        assert any("site-packages" in pattern for pattern in result)

    def test_base_framework_detector_interface(self):
        """Test BaseFrameworkDetector abstract interface"""
        # This tests that the interface exists and can be imported
        assert hasattr(BaseFrameworkDetector, "framework")
        assert hasattr(BaseFrameworkDetector, "priority")
        assert hasattr(BaseFrameworkDetector, "detect")

    def test_base_framework_parser_interface(self):
        """Test BaseFrameworkParser abstract interface"""
        # This tests that the interface exists and can be imported
        assert hasattr(BaseFrameworkParser, "framework")
        assert hasattr(BaseFrameworkParser, "parse")
        assert hasattr(BaseFrameworkParser, "validate_output")

    def test_extract_file_path_from_message_windows_path(self):
        """Test extracting file path from Windows-style paths"""
        message = 'File "C:\\Users\\user\\project\\src\\main.py", line 15'
        result = extract_file_path_from_message(message)
        assert result == "C:\\Users\\user\\project\\src\\main.py"

    def test_extract_file_path_from_message_relative_path(self):
        """Test extracting file path from relative path"""
        message = "Error in ./src/utils/helper.py:20"
        result = extract_file_path_from_message(message)
        assert result == "./src/utils/helper.py"
