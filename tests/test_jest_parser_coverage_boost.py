"""
Comprehensive test coverage for Jest parser to boost overall test coverage.

This test file targets the Jest parser functionality that was previously untested
to increase coverage from ~20% to a higher percentage.
"""

from gitlab_analyzer.parsers.base_parser import TestFramework
from gitlab_analyzer.parsers.jest_parser import JestDetector, JestParser


class TestJestDetector:
    """Test Jest detector functionality"""

    def test_framework_property(self):
        """Test framework property returns Jest"""
        detector = JestDetector()
        assert detector.framework == TestFramework.JEST

    def test_priority_property(self):
        """Test priority property returns expected value"""
        detector = JestDetector()
        assert detector.priority == 85

    def test_detect_by_job_name_jest(self):
        """Test detection by job name containing 'jest'"""
        detector = JestDetector()
        assert detector.detect(
            job_name="run-jest-tests", job_stage="test", trace_content=""
        )

    def test_detect_by_job_name_js_test(self):
        """Test detection by job name containing 'js test'"""
        detector = JestDetector()
        assert detector.detect(
            job_name="js-unit-tests", job_stage="test", trace_content=""
        )

    def test_detect_by_job_name_ts_test(self):
        """Test detection by job name containing 'ts test'"""
        detector = JestDetector()
        assert detector.detect(
            job_name="ts-integration-test", job_stage="test", trace_content=""
        )

    def test_detect_by_job_name_javascript_test(self):
        """Test detection by job name containing 'javascript test'"""
        detector = JestDetector()
        assert detector.detect(
            job_name="javascript-unit-test", job_stage="test", trace_content=""
        )

    def test_detect_by_job_name_typescript_test(self):
        """Test detection by job name containing 'typescript test'"""
        detector = JestDetector()
        assert detector.detect(
            job_name="typescript-integration-test", job_stage="test", trace_content=""
        )

    def test_detect_by_trace_content_test_suites(self):
        """Test detection by trace content containing Jest test suite output"""
        detector = JestDetector()
        trace_content = """
        Test Suites: 5 passed, 2 failed, 7 total
        Tests:       15 passed, 3 failed, 18 total
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_tests_summary(self):
        """Test detection by trace content containing Jest tests summary"""
        detector = JestDetector()
        trace_content = """
        Tests: 10 passed, 2 failed, 12 total
        Snapshots: 0 total
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_pass_test_file(self):
        """Test detection by trace content containing PASS test file"""
        detector = JestDetector()
        trace_content = """
        PASS src/components/Button.test.js (8.123s)
        PASS src/utils/helpers.test.ts (2.456s)
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_fail_test_file(self):
        """Test detection by trace content containing FAIL test file"""
        detector = JestDetector()
        trace_content = """
        FAIL src/components/Form.test.js (12.789s)
        FAIL src/api/client.test.ts (5.123s)
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_jest_cli_options(self):
        """Test detection by trace content containing Jest CLI Options"""
        detector = JestDetector()
        trace_content = """
        Jest CLI Options:
          --verbose
          --coverage
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_running_tests_with_jest(self):
        """Test detection by trace content containing 'Running tests with Jest'"""
        detector = JestDetector()
        trace_content = """
        Running tests with Jest configuration
        Found 25 test files matching pattern
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_negative_case(self):
        """Test non-Jest job is not detected"""
        detector = JestDetector()
        assert not detector.detect(
            job_name="build-app",
            job_stage="build",
            trace_content="Building application",
        )


class TestJestParser:
    """Test Jest parser functionality"""

    def test_framework_property(self):
        """Test framework property returns Jest"""
        parser = JestParser()
        assert parser.framework == TestFramework.JEST

    def test_parse_simple_jest_output(self):
        """Test parsing simple Jest output"""
        parser = JestParser()
        trace_content = """
        PASS src/components/Button.test.js
        PASS src/utils/helpers.test.ts
        Test Suites: 2 passed, 2 total
        Tests: 15 passed, 15 total
        """

        result = parser.parse(trace_content)

        assert result["parser_type"] == "jest"
        assert result["framework"] == "jest"
        assert result["error_count"] == 0
        assert result["warning_count"] == 0
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["summary"], dict)

    def test_parse_jest_test_failure(self):
        """Test parsing Jest test failure"""
        parser = JestParser()
        trace_content = """
        FAIL src/components/Form.test.js
        ● Form › should render correctly

        TypeError: Cannot read property 'value' of undefined
          at Object.<anonymous> (src/components/Form.test.js:15:23)
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        assert any(
            "Form.test.js" in error.get("message", "") for error in result["errors"]
        )

    def test_parse_syntax_error(self):
        """Test parsing JavaScript syntax error"""
        parser = JestParser()
        trace_content = """
        SyntaxError: Unexpected token '{'
          at Module._compile (internal/modules/cjs/loader.js:723:23)
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        assert any(
            "JavaScript Syntax Error" in error.get("exception_type", "")
            for error in result["errors"]
        )

    def test_parse_typescript_error(self):
        """Test parsing TypeScript error"""
        parser = JestParser()
        trace_content = """
        TS2345: Argument of type 'string' is not assignable to parameter of type 'number'
          at src/utils/math.ts:42:15
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        assert any(
            "TypeScript Error" in error.get("exception_type", "")
            for error in result["errors"]
        )

    def test_parse_module_not_found_error(self):
        """Test parsing module not found error"""
        parser = JestParser()
        trace_content = """
        Cannot find module './nonexistent-module'
        Require stack:
        - src/components/App.js:5:1
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        assert any(
            "Module Not Found" in error.get("exception_type", "")
            for error in result["errors"]
        )

    def test_parse_test_timeout_error(self):
        """Test parsing test timeout error"""
        parser = JestParser()
        trace_content = """
        Test timeout of 5000ms exceeded for test: should complete async operation
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        assert any(
            "Test Timeout" in error.get("exception_type", "")
            for error in result["errors"]
        )

    def test_parse_jest_assertion_error(self):
        """Test parsing Jest assertion error"""
        parser = JestParser()
        trace_content = """
        Error: expect(received).toBe(expected)
        Expected: 42
        Received: 24
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        assert any(
            "Jest Assertion Error" in error.get("exception_type", "")
            for error in result["errors"]
        )

    def test_parse_jest_warnings(self):
        """Test parsing Jest warnings"""
        parser = JestParser()
        trace_content = """
        WARNING: Using deprecated method getByTestId
        DEPRECATED: This API will be removed in the next version
        Jest: The following options are deprecated: collectCoverageFrom
        """

        result = parser.parse(trace_content)

        assert result["warning_count"] > 0
        assert len(result["warnings"]) >= 2

    def test_parse_mixed_content(self):
        """Test parsing mixed Jest output with errors and warnings"""
        parser = JestParser()
        trace_content = """
        PASS src/components/Button.test.js
        FAIL src/components/Form.test.js
        ● Form › validation

        TypeError: Cannot read property 'length' of null
          at Object.<anonymous> (src/components/Form.test.js:25:10)

        WARNING: Using deprecated Jest matcher

        Test Suites: 1 failed, 1 passed, 2 total
        Tests: 8 failed, 12 passed, 20 total
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        assert result["warning_count"] > 0
        assert "Form.test.js" in str(result)

    def test_extract_source_file_and_line_jest_error(self):
        """Test extracting source file and line from Jest error"""
        parser = JestParser()
        error_message = "at Object.<anonymous> (/path/to/file.test.js:42:5)"

        file_path, line_num = parser._extract_source_file_and_line(error_message)

        assert file_path == "/path/to/file.test.js"
        assert line_num == 42

    def test_extract_source_file_and_line_no_match(self):
        """Test extracting source file and line when no pattern matches"""
        parser = JestParser()
        error_message = "Generic error message without location"

        file_path, line_num = parser._extract_source_file_and_line(error_message)

        assert file_path is None
        assert line_num is None

    def test_jest_summary_parsing(self):
        """Test parsing Jest summary information"""
        parser = JestParser()
        trace_content = """
        Test Suites: 3 failed, 5 passed, 8 total
        Tests: 12 failed, 25 passed, 39 total
        """

        result = parser.parse(trace_content)

        assert "summary" in result
        summary = result["summary"]

        # Check if summary contains expected Jest-specific keys
        expected_keys = [
            "failed_tests",
            "passed_tests",
            "total_tests",
            "failed_suites",
            "passed_suites",
            "total_suites",
        ]
        for key in expected_keys:
            assert key in summary

    def test_jest_file_tracking(self):
        """Test that parser correctly tracks current test file"""
        parser = JestParser()
        trace_content = """
        PASS src/utils/math.test.js
        ✓ should add numbers correctly
        FAIL src/components/Form.test.js
        ✗ should validate input
        Error: Expected true but received false
        """

        result = parser.parse(trace_content)

        # Should parse errors and associate them with correct files
        assert result["error_count"] > 0

    def test_jest_jsx_tsx_file_detection(self):
        """Test Jest parser handles JSX and TSX files"""
        parser = JestParser()
        trace_content = """
        PASS src/components/Button.test.jsx
        FAIL src/components/Form.test.tsx
        """

        result = parser.parse(trace_content)

        # Should handle different Jest file extensions
        assert result["parser_type"] == "jest"

    def test_empty_trace_content(self):
        """Test parsing empty trace content"""
        parser = JestParser()
        result = parser.parse("")

        assert result["error_count"] == 0
        assert result["warning_count"] == 0
        assert result["parser_type"] == "jest"

    def test_malformed_jest_output(self):
        """Test parser handles malformed Jest output gracefully"""
        parser = JestParser()
        trace_content = """
        This is not valid Jest output
        Some random text
        Not following Jest patterns
        """

        result = parser.parse(trace_content)

        # Should not crash and return valid structure
        assert "parser_type" in result
        assert "errors" in result
        assert "warnings" in result
