"""
Simple pytest parser tests with basic coverage.
Tests the pytest-specific parsing functionality using only existing imports.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import only what we know works
from gitlab_analyzer.parsers.pytest_parser import (
    PytestParser,
    PytestLogParser,
    PytestDetector,
)


class TestPytestClasses:
    """Test pytest classes exist and can be instantiated"""

    def test_pytest_detector_init(self):
        """Test PytestDetector can be created"""
        detector = PytestDetector()
        assert detector is not None

    def test_pytest_parser_init(self):
        """Test PytestParser can be created"""
        parser = PytestParser()
        assert parser is not None

    def test_pytest_log_parser_init(self):
        """Test PytestLogParser can be created"""
        parser = PytestLogParser()
        assert parser is not None

    def test_pytest_detector_has_detect_method(self):
        """Test PytestDetector has detect method"""
        detector = PytestDetector()
        assert hasattr(detector, "detect")
        assert callable(detector.detect)

    def test_pytest_parser_has_parse_method(self):
        """Test PytestParser has parse method"""
        parser = PytestParser()
        assert hasattr(parser, "parse")
        assert callable(parser.parse)

    def test_pytest_log_parser_has_parse_method(self):
        """Test PytestLogParser has parse method"""
        parser = PytestLogParser()
        assert hasattr(parser, "parse")
        assert callable(parser.parse)

    def test_pytest_detector_framework_property(self):
        """Test PytestDetector has framework property"""
        detector = PytestDetector()
        framework = detector.framework()
        assert isinstance(framework, str)
        assert "pytest" in framework.lower()

    def test_pytest_detector_priority_property(self):
        """Test PytestDetector has priority property"""
        detector = PytestDetector()
        priority = detector.priority()
        assert isinstance(priority, int)
        assert priority >= 0

    def test_pytest_parser_detect_basic(self):
        """Test pytest parser detection with basic input"""
        detector = PytestDetector()
        # Test with empty string
        result = detector.detect("")
        assert isinstance(result, bool)

        # Test with pytest-like content
        result = detector.detect(
            "============================= test session starts =============================="
        )
        assert isinstance(result, bool)

        # Test with non-pytest content
        result = detector.detect("This is not a pytest trace")
        assert isinstance(result, bool)

    def test_pytest_parser_parse_basic(self):
        """Test pytest parser parsing with basic input"""
        parser = PytestParser()

        # Test with empty string
        result = parser.parse("")
        assert isinstance(result, dict)

        # Test with basic pytest output
        result = parser.parse("test_file.py::test_function PASSED")
        assert isinstance(result, dict)

        # Test with failure
        result = parser.parse("test_file.py::test_function FAILED")
        assert isinstance(result, dict)

    def test_pytest_log_parser_parse_basic(self):
        """Test pytest log parser parsing with basic input"""
        parser = PytestLogParser()

        # Test with empty string
        result = parser.parse("")
        assert isinstance(result, dict)

        # Test with log content
        result = parser.parse(
            "test_file.py::test_function PASSED\ntest_file.py::test_other FAILED"
        )
        assert isinstance(result, dict)


class TestPytestParsingScenarios:
    """Test various pytest parsing scenarios"""

    def test_parse_simple_passing_test(self):
        """Test parsing simple passing test output"""
        parser = PytestParser()
        output = "test_example.py::test_simple PASSED                                       [100%]"
        result = parser.parse(output)
        assert isinstance(result, dict)

    def test_parse_simple_failing_test(self):
        """Test parsing simple failing test output"""
        parser = PytestParser()
        output = "test_example.py::test_simple FAILED                                       [100%]"
        result = parser.parse(output)
        assert isinstance(result, dict)

    def test_parse_test_session_header(self):
        """Test parsing test session header"""
        parser = PytestParser()
        output = """============================= test session starts ==============================
platform linux -- Python 3.8.10, pytest-6.2.4
collected 1 items"""
        result = parser.parse(output)
        assert isinstance(result, dict)

    def test_parse_test_with_failure_info(self):
        """Test parsing test with failure information"""
        parser = PytestParser()
        output = """test_example.py::test_fail FAILED
================================== FAILURES ===================================
____________________________ test_fail _____________________________

    def test_fail():
>       assert False
E       assert False

test_example.py:2: AssertionError"""
        result = parser.parse(output)
        assert isinstance(result, dict)

    def test_parse_test_summary(self):
        """Test parsing test summary"""
        parser = PytestParser()
        output = """test_example.py::test_pass PASSED
test_example.py::test_fail FAILED
====================== 1 failed, 1 passed in 0.01s ======================"""
        result = parser.parse(output)
        assert isinstance(result, dict)


class TestPytestModuleIntegration:
    """Test pytest module integration"""

    def test_module_has_classes(self):
        """Test module has expected classes"""
        import gitlab_analyzer.parsers.pytest_parser as pytest_module

        assert hasattr(pytest_module, "PytestParser")
        assert hasattr(pytest_module, "PytestDetector")
        assert hasattr(pytest_module, "PytestLogParser")

    def test_classes_are_callable(self):
        """Test classes can be instantiated"""
        # Test that we can create instances
        detector = PytestDetector()
        parser = PytestParser()
        log_parser = PytestLogParser()

        assert detector is not None
        assert parser is not None
        assert log_parser is not None

    def test_classes_have_expected_interface(self):
        """Test classes have expected methods"""
        detector = PytestDetector()
        parser = PytestParser()
        log_parser = PytestLogParser()

        # Detector interface
        assert hasattr(detector, "detect")
        assert hasattr(detector, "framework")
        assert hasattr(detector, "priority")

        # Parser interface
        assert hasattr(parser, "parse")

        # Log parser interface
        assert hasattr(log_parser, "parse")


# Basic test to ensure module imports work correctly
def test_pytest_parser_module_import():
    """Basic test that the module imports correctly"""
    from gitlab_analyzer.parsers import pytest_parser

    assert pytest_parser is not None


# Test that covers different code paths
def test_pytest_detection_coverage():
    """Test different detection scenarios to improve coverage"""
    detector = PytestDetector()

    # Various test inputs to exercise different code paths
    test_inputs = [
        "",
        "random text",
        "============================= test session starts ==============================",
        "FAILED test.py::test_func",
        "PASSED test.py::test_func",
        "ERROR test.py::test_func",
        "collected 5 items",
        "platform darwin",
        "1 failed, 2 passed",
    ]

    for test_input in test_inputs:
        result = detector.detect(test_input)
        assert isinstance(result, bool)


def test_pytest_parsing_coverage():
    """Test different parsing scenarios to improve coverage"""
    parser = PytestParser()

    # Various test inputs to exercise different code paths
    test_inputs = [
        "",
        "test.py::func PASSED",
        "test.py::func FAILED",
        "test.py::func ERROR",
        "test.py::func SKIPPED",
        "===== FAILURES =====",
        "===== ERRORS =====",
        "collected 3 items",
        "1 failed, 2 passed in 1.5s",
        "short test summary info",
    ]

    for test_input in test_inputs:
        result = parser.parse(test_input)
        assert isinstance(result, dict)


# Run the tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
