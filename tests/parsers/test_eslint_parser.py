"""
Unit tests for ESLint parser using real trace data from pipeline 1632130.

This module tests the ESLint parser against actual GitLab CI/CD trace content
to ensure accurate parsing of linting warnings and errors.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import pytest

from gitlab_analyzer.parsers.base_parser import TestFramework
from gitlab_analyzer.parsers.eslint_parser import ESLintDetector, ESLintParser


class TestESLintDetector:
    """Test ESLint framework detection"""

    def test_detect_by_job_name(self):
        """Test detection based on job name patterns"""
        detector = ESLintDetector()

        # Should detect linting jobs with ESLint content
        eslint_content = "eslint src/**/*.ts --cache @typescript-eslint/explicit-module-boundary-types"
        assert detector.detect("lint", "test", eslint_content)
        assert detector.detect("eslint", "quality", eslint_content)
        assert detector.detect("code-quality", "lint", eslint_content)

        # Should not detect non-linting jobs without strong content indicators
        assert not detector.detect("build", "build", "npm install")
        assert not detector.detect("test", "test", "jest output")

    def test_detect_by_trace_content(self):
        """Test detection based on trace content patterns"""
        detector = ESLintDetector()

        # Strong ESLint indicators
        eslint_trace = """
        $ yarn run lint
        yarn run v1.22.22
        $ eslint "src/**/*.{ts,tsx}" --cache
        
        /builds/product/appjs-document-wizard/src/@Development/subscription/SubscriptionModel.ts
          14:3  warning  Missing return type on function  @typescript-eslint/explicit-module-boundary-types
        
        ✖ 191 problems (3 errors, 188 warnings)
        2 errors and 0 warnings potentially fixable with the `--fix` option.
        """

        assert detector.detect("unknown", "unknown", eslint_trace)

    def test_framework_property(self):
        """Test framework property returns correct enum"""
        detector = ESLintDetector()
        assert detector.framework == TestFramework.ESLINT

    def test_priority_property(self):
        """Test priority is appropriate for linting jobs"""
        detector = ESLintDetector()
        assert detector.priority == 80  # High priority for linting


class TestESLintParser:
    """Test ESLint trace parsing"""

    @pytest.fixture
    def real_eslint_trace(self):
        """Real ESLint trace from pipeline 1632130, job 78998490"""
        return """$ yarn run lint
yarn run v1.22.22
$ eslint "src/**/*.{ts,tsx}" --cache

/builds/product/appjs-document-wizard/src/@Development/subscription/SubscriptionModel.ts
  14:3  warning  Missing return type on function  @typescript-eslint/explicit-module-boundary-types

/builds/product/appjs-document-wizard/src/@DocumentWizard/application/ioc/__tests__/container.spec.ts
   95:32  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  109:34  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/builds/product/appjs-document-wizard/src/@DocumentWizard/infra/redux/modules/features/__tests__/featureFlagsSelectors.spec.ts
  517:0  error  Parsing error: Declaration or statement expected

/builds/product/appjs-document-wizard/src/@DocumentWizard/infra/redux/modules/converter/converterSelectors.ts
  4:1  error  Unexpected blank line before this statement  padding-line-between-statements

✖ 191 problems (3 errors, 188 warnings)
  2 errors and 0 warnings potentially fixable with the `--fix` option.

error Command failed with exit code 1."""

    def test_framework_property(self):
        """Test framework property returns correct enum"""
        parser = ESLintParser()
        assert parser.framework == TestFramework.ESLINT

    def test_parse_real_trace(self, real_eslint_trace):
        """Test parsing real ESLint trace data"""
        parser = ESLintParser()
        result = parser.parse(real_eslint_trace)

        # Verify basic structure
        assert result["parser_type"] == "eslint"
        assert result["framework"] == "eslint"
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["summary"], dict)

        # Should detect errors and warnings
        assert result["error_count"] > 0
        assert result["warning_count"] > 0
        assert len(result["errors"]) == result["error_count"]
        assert len(result["warnings"]) == result["warning_count"]

    def test_parse_eslint_warnings(self, real_eslint_trace):
        """Test parsing ESLint warnings"""
        parser = ESLintParser()
        result = parser.parse(real_eslint_trace)

        # Check warning structure
        warnings = result["warnings"]
        assert len(warnings) > 0

        # Test a specific warning
        warning = warnings[0]
        assert warning["severity"] == "warning"
        assert (
            warning["eslint_rule"]
            == "@typescript-eslint/explicit-module-boundary-types"
        )
        assert "Missing return type on function" in warning["message"]
        assert warning["source_line"] == 14
        assert warning["source_column"] == 3

    def test_parse_eslint_errors(self, real_eslint_trace):
        """Test parsing ESLint errors"""
        parser = ESLintParser()
        result = parser.parse(real_eslint_trace)

        # Check error structure
        errors = result["errors"]
        assert len(errors) > 0

        # Test a specific error
        error = errors[0]
        assert error["severity"] == "error"
        assert error["exception_type"] == "ESLint Error"
        assert "Parsing error" in error["message"]
        assert error["source_line"] == 517
        assert error["source_column"] == 0

    def test_parse_summary(self, real_eslint_trace):
        """Test parsing ESLint summary statistics"""
        parser = ESLintParser()
        result = parser.parse(real_eslint_trace)

        summary = result["summary"]
        assert summary["total_problems"] == 191
        assert summary["total_errors"] == 3
        assert summary["total_warnings"] == 188
        assert summary["fixable_problems"] == 2
        assert summary["files_with_issues"] > 0

    def test_file_path_extraction(self):
        """Test file path extraction and cleaning"""
        parser = ESLintParser()

        # Test build path cleaning
        build_path = "/builds/product/appjs-document-wizard/src/@DocumentWizard/test.ts"
        clean_path = parser._extract_file_path(build_path)
        assert clean_path == "src/@DocumentWizard/test.ts"

        # Test relative path
        relative_path = "src/components/Button.tsx"
        clean_relative = parser._extract_file_path(relative_path)
        assert clean_relative == "src/components/Button.tsx"

    def test_file_path_detection(self):
        """Test file path detection logic"""
        parser = ESLintParser()

        # Should detect valid file paths
        assert parser._is_file_path("/builds/product/app/src/test.ts")
        assert parser._is_file_path("src/components/Button.tsx")
        assert parser._is_file_path("./components/test.js")

        # Should not detect non-file paths
        assert not parser._is_file_path("  14:3  warning  Missing return type")
        assert not parser._is_file_path("yarn run v1.22.22")
        assert not parser._is_file_path("✖ 191 problems")

    def test_source_file_and_line_extraction(self):
        """Test source file and line number extraction"""
        parser = ESLintParser()

        # Test with ESLint format message
        error_msg = "517:0  error  Parsing error: Declaration or statement expected"
        file_path, line_number = parser._extract_source_file_and_line(error_msg)
        assert file_path is None  # File path tracked separately in ESLint
        assert line_number == 517

        # Test with full log context
        full_log = """
/builds/product/appjs-document-wizard/src/@DocumentWizard/test.ts
  14:3  warning  Missing return type on function
        """
        file_path, line_number = parser._extract_source_file_and_line(
            "14:3  warning  Missing return type", full_log
        )
        # Should extract file path and line number from context
        if file_path:
            assert "src/@DocumentWizard/test.ts" in file_path
        assert line_number == 14

    def test_empty_trace(self):
        """Test parser handles empty trace gracefully"""
        parser = ESLintParser()
        result = parser.parse("")

        assert result["parser_type"] == "eslint"
        assert result["framework"] == "eslint"
        assert result["error_count"] == 0
        assert result["warning_count"] == 0
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0

    def test_non_eslint_trace(self):
        """Test parser handles non-ESLint trace gracefully"""
        parser = ESLintParser()
        non_eslint_trace = """
        Running tests...
        PASS src/components/Button.test.tsx
        Test Suites: 1 passed, 1 total
        Tests: 3 passed, 3 total
        """
        result = parser.parse(non_eslint_trace)

        assert result["error_count"] == 0
        assert result["warning_count"] == 0
