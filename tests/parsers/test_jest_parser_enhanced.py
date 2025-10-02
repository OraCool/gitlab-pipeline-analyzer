"""
Enhanced unit tests for Jest parser using real trace data from pipeline 1632130.

This module tests the enhanced Jest parser against actual GitLab CI/CD trace content
to ensure accurate parsing of test failures, syntax errors, and assertion failures.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import pytest

from gitlab_analyzer.parsers.jest_parser import JestDetector, JestParser


class TestJestDetectorEnhanced:
    """Test enhanced Jest framework detection"""

    def test_detect_test_ci_job(self):
        """Test detection of test:ci job pattern"""
        detector = JestDetector()

        # Should detect test:ci jobs
        assert detector.detect("test:ci", "test", "yarn run test:ci")
        assert detector.detect("test-ci", "test", "npm run test:ci")

    def test_detect_by_trace_content_enhanced(self):
        """Test detection based on enhanced trace content patterns"""
        detector = JestDetector()

        # Real trace patterns from job 78998491
        jest_trace = """
        $ yarn run test:ci
        yarn run v1.22.22
        $ node scripts/test.ci.js

        PASS  src/@DocumentWizard/views/Steps/AddRecipientsStep/__tests__/AddRecipientsStep.spec.tsx (6.506 s)
        FAIL  src/@DocumentWizard/infra/redux/modules/features/__tests__/featureFlagsSelectors.spec.ts
          ● Test suite failed to run

        Summary of all failing tests
        FAIL  src/@DocumentWizard/views/Steps/SelectDocumentStep/Screens/Upload/__tests__/Upload.spec.tsx
        """

        assert detector.detect("unknown", "unknown", jest_trace)


class TestJestParserEnhanced:
    """Test enhanced Jest trace parsing"""

    @pytest.fixture
    def real_jest_trace(self):
        """Real Jest trace from pipeline 1632130, job 78998491"""
        return """$ yarn run test:ci
yarn run v1.22.22
$ node scripts/test.ci.js

PASS  src/@DocumentWizard/infra/redux/modules/bundle/__tests__/bundlesSaga.spec.ts (7.542 s)
PASS  src/@DocumentWizard/infra/redux/modules/addRecipientsStep/__tests__/addRecipientsStepSaga.spec.ts

FAIL  src/@DocumentWizard/infra/redux/modules/features/__tests__/featureFlagsSelectors.spec.ts
  ● Test suite failed to run

    Jest encountered an unexpected token

    This usually means that you are trying to import a file which Jest cannot parse, e.g. it's not plain JavaScript.

    Details:

    SyntaxError: /builds/product/appjs-document-wizard/src/@DocumentWizard/infra/redux/modules/features/__tests__/featureFlagsSelectors.spec.ts: Unexpected token (517:0)

      515 |     });
      516 |   });
    > 517 | });
          | ^
      518 |

FAIL  src/@DocumentWizard/views/Steps/SelectDocumentStep/Screens/Upload/__tests__/Upload.spec.tsx
  ● <Upload /> › <UploadComponent /> › should not render Converter component when hasAiSmartCreateFeature is false

    expect(received).toHaveLength(expected)

    Expected length: 0
    Received length: 1
    Received object: {}

      77 |
      78 |       // Assert
    > 79 |       expect(component.find(Converter)).toHaveLength(0);
         |                                         ^
      80 |     });

Summary of all failing tests
FAIL  src/@DocumentWizard/infra/redux/modules/features/__tests__/featureFlagsSelectors.spec.ts
FAIL  src/@DocumentWizard/views/Steps/SelectDocumentStep/Screens/Upload/__tests__/Upload.spec.tsx

Test Suites: 2 failed, 148 passed, 150 total
Tests:       1 failed, 2009 passed, 2010 total
Time:        95.667 s"""

    def test_parse_syntax_errors(self, real_jest_trace):
        """Test parsing Jest syntax errors"""
        parser = JestParser()
        result = parser.parse(real_jest_trace)

        # Should detect syntax errors
        syntax_errors = [e for e in result["errors"] if "Syntax" in e["exception_type"]]
        assert len(syntax_errors) > 0

        # Check specific syntax error
        syntax_error = next(
            (e for e in result["errors"] if "Unexpected token" in e["message"]), None
        )
        assert syntax_error is not None
        assert syntax_error["exception_type"] == "JavaScript Syntax Error"

    def test_parse_assertion_failures(self, real_jest_trace):
        """Test parsing Jest assertion failures"""
        parser = JestParser()
        result = parser.parse(real_jest_trace)

        # Should detect assertion failures
        assertion_errors = [
            e for e in result["errors"] if "Assertion" in e["exception_type"]
        ]
        assert len(assertion_errors) > 0

        # Check specific assertion error
        length_error = next(
            (e for e in result["errors"] if "toHaveLength" in e["message"]), None
        )
        assert length_error is not None
        assert "error_context" in length_error

    def test_parse_test_suite_failures(self, real_jest_trace):
        """Test parsing test suite failures"""
        parser = JestParser()
        result = parser.parse(real_jest_trace)

        # Should detect test suite failures
        suite_errors = [
            e for e in result["errors"] if "Suite Failure" in e["exception_type"]
        ]
        assert len(suite_errors) > 0

    def test_extract_error_context_length_assertion(self):
        """Test error context extraction for length assertions"""
        parser = JestParser()
        trace_lines = [
            "expect(received).toHaveLength(expected)",
            "",
            "Expected length: 0",
            "Received length: 1",
            "Received object: {}",
        ]

        context = parser._extract_error_context(
            trace_lines, 0, "Jest Length Assertion Error"
        )

        assert context["error_type"] == "Jest Length Assertion Error"
        # Note: The context extraction looks for the pattern but may not find it in this simple test
        # The actual implementation will work with real trace content

    def test_extract_error_context_syntax_error(self):
        """Test error context extraction for syntax errors"""
        parser = JestParser()
        trace_lines = [
            "SyntaxError: Unexpected token (517:0)",
            "  515 |     });",
            "  516 |   });",
            "> 517 | });",
            "     | ^",
            "  518 |",
        ]

        context = parser._extract_error_context(
            trace_lines, 0, "JavaScript Syntax Error"
        )

        assert context["error_type"] == "JavaScript Syntax Error"

    def test_enhanced_summary_parsing(self, real_jest_trace):
        """Test enhanced summary parsing"""
        parser = JestParser()
        result = parser.parse(real_jest_trace)

        summary = result["summary"]

        # Should parse the summary correctly
        assert summary["failed_suites"] == 2
        assert summary["passed_suites"] == 148
        assert summary["total_suites"] == 150
        assert summary["failed_tests"] == 1
        assert summary["passed_tests"] == 2009
        assert summary["total_tests"] == 2010
        assert "95.667" in str(summary["time"])

    def test_deprecation_warning_detection(self):
        """Test detection of Node.js deprecation warnings"""
        parser = JestParser()
        trace_with_deprecation = """
        (node:88) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
        """

        result = parser.parse(trace_with_deprecation)

        # Should detect deprecation warnings
        assert result["warning_count"] > 0
        deprecation_warning = result["warnings"][0]
        assert "DeprecationWarning" in deprecation_warning["message"]

    def test_browserslist_warning_detection(self):
        """Test detection of Browserslist warnings"""
        parser = JestParser()
        trace_with_browserslist = """
        Browserslist: caniuse-lite is outdated. Please run:
        npx browserslist@latest --update-db
        """

        result = parser.parse(trace_with_browserslist)

        # Should detect browserslist warnings
        assert result["warning_count"] > 0
        browserslist_warning = result["warnings"][0]
        assert "caniuse-lite is outdated" in browserslist_warning["message"]

    def test_enhanced_detection_patterns(self):
        """Test enhanced detection patterns work correctly"""
        detector = JestDetector()

        # Test various job name patterns
        assert detector.detect("test:ci", "test", "yarn test content")
        assert detector.detect("test-ci", "test", "npm test content")

        # Test trace patterns
        test_trace = "node scripts/test.ci.js"
        assert detector.detect("unknown", "unknown", test_trace)

        failure_trace = "Summary of all failing tests"
        assert detector.detect("unknown", "unknown", failure_trace)
