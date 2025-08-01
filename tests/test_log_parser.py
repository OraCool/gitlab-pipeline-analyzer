"""
Tests for log parser functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.models import LogEntry
from gitlab_analyzer.parsers.log_parser import LogParser


class TestLogParser:
    """Test log parser functionality"""

    def test_extract_log_entries_empty_log(self):
        """Test extracting entries from empty log"""
        result = LogParser.extract_log_entries("")
        assert result == []

    def test_extract_log_entries_no_errors(self):
        """Test extracting entries from log with no errors"""
        log_content = """
        Running job...
        Installing dependencies...
        Build successful
        All tests passed
        """
        result = LogParser.extract_log_entries(log_content)
        assert result == []

    def test_extract_log_entries_with_npm_errors(self):
        """Test extracting entries with npm errors"""
        log_content = """
        $ npm ci
        npm ERR! code ENOENT
        npm ERR! syscall open
        npm ERR! path /builds/project/package.json
        npm ERR! errno -2
        npm ERR! enoent ENOENT: no such file or directory, open '/builds/project/package.json'
        npm ERR! enoent This is related to npm not being able to find a file.
        """

        result = LogParser.extract_log_entries(log_content)

        assert len(result) > 0
        # Check that we found error entries
        error_entries = [entry for entry in result if entry.level == "error"]
        assert len(error_entries) > 0

        # Check that error entries contain relevant information
        error_messages = [entry.message for entry in error_entries]
        assert any("ENOENT" in msg for msg in error_messages)

    def test_extract_log_entries_with_build_errors(self):
        """Test extracting entries with build errors"""
        log_content = """
        $ make build
        gcc -o app main.c
        main.c:10:5: error: 'undefined_function' was not declared in this scope
        main.c:15:1: error: expected ';' before '}' token
        make: *** [app] Error 1
        ERROR: Job failed: exit code 1
        """

        result = LogParser.extract_log_entries(log_content)

        assert len(result) > 0
        error_entries = [entry for entry in result if entry.level == "error"]
        assert len(error_entries) > 0

        # Check for compilation errors
        error_messages = [entry.message for entry in error_entries]
        assert any("not declared" in msg for msg in error_messages)
        assert any("expected" in msg for msg in error_messages)

    def test_extract_log_entries_with_warnings(self):
        """Test extracting entries with warnings"""
        log_content = """
        $ npm install
        npm WARN deprecated package@1.0.0: This package is deprecated
        npm WARN optional SKIPPING OPTIONAL DEPENDENCY: fsevents@1.2.13
        $ python -m pytest
        /path/to/file.py:25: DeprecationWarning: function is deprecated
        """

        result = LogParser.extract_log_entries(log_content)

        assert len(result) > 0
        warning_entries = [entry for entry in result if entry.level == "warning"]
        assert len(warning_entries) > 0

        # Check warning messages
        warning_messages = [entry.message for entry in warning_entries]
        assert any("deprecated" in msg.lower() for msg in warning_messages)

    def test_extract_log_entries_mixed_levels(self):
        """Test extracting entries with mixed error and warning levels"""
        log_content = """
        $ build_script.sh
        WARNING: This is a warning message
        INFO: Starting build process
        ERROR: Build failed due to missing dependency
        npm WARN deprecated package@1.0.0
        npm ERR! Missing script: "build"
        FATAL: Critical error occurred
        """

        result = LogParser.extract_log_entries(log_content)

        # Should have both errors and warnings
        error_entries = [entry for entry in result if entry.level == "error"]
        warning_entries = [entry for entry in result if entry.level == "warning"]

        assert len(error_entries) > 0
        assert len(warning_entries) > 0

    def test_extract_log_entries_with_context(self):
        """Test that extracted entries contain context information"""
        log_content = """
        $ npm test
        > myproject@1.0.0 test /builds/project
        > jest

        FAIL src/utils.test.js
        ● Test suite failed to run

            TypeError: Cannot read property 'length' of undefined

                at Object.<anonymous> (src/utils.test.js:5:20)
        """

        result = LogParser.extract_log_entries(log_content)

        assert len(result) > 0

        # Check that entries have proper attributes
        for entry in result:
            assert isinstance(entry, LogEntry)
            assert hasattr(entry, "level")
            assert hasattr(entry, "message")
            assert hasattr(entry, "line_number")
            assert hasattr(entry, "timestamp")
            assert entry.level in ["error", "warning"]

    def test_extract_log_entries_filters_noise(self):
        """Test that parser filters out noise and keeps relevant entries"""
        log_content = """
        Getting source from Git repository
        Fetching changes...
        Running on runner-12345
        $ echo "Starting build"
        Starting build
        $ npm ci
        added 1000 packages in 30s
        npm ERR! code ENOENT
        npm ERR! Missing file: package.json
        $ echo "Build complete"
        Build complete
        Uploading artifacts...
        """

        result = LogParser.extract_log_entries(log_content)

        # Should only extract the npm error, not the echo statements or info messages
        assert len(result) > 0
        error_entries = [entry for entry in result if entry.level == "error"]
        assert len(error_entries) > 0

        # Check that we don't extract noise
        all_messages = [entry.message for entry in result]
        assert not any("echo" in msg for msg in all_messages)
        assert not any("Starting build" in msg for msg in all_messages)

    def test_log_entry_serialization(self):
        """Test that LogEntry can be serialized to dict"""
        log_content = """
        npm ERR! code ENOENT
        npm ERR! Missing file
        """

        result = LogParser.extract_log_entries(log_content)

        assert len(result) > 0
        entry = result[0]

        # Test dict conversion
        entry_dict = entry.dict()
        assert isinstance(entry_dict, dict)
        assert "level" in entry_dict
        assert "message" in entry_dict
        assert "line_number" in entry_dict
        assert "timestamp" in entry_dict
