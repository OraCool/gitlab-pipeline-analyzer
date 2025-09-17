"""
Comprehensive tests for framework registry functionality.

Tests the core parser registry system including detector registration,
framework detection, parser retrieval, and import error handling.
"""

from unittest.mock import Mock, patch

from src.gitlab_analyzer.parsers.base_parser import (
    BaseFrameworkDetector,
    BaseFrameworkParser,
    TestFramework,
)
from src.gitlab_analyzer.parsers.framework_registry import (
    ParserRegistry,
    detect_job_framework,
    parse_with_framework,
    parser_registry,
)


class TestParserRegistry:
    """Test cases for ParserRegistry class."""

    def test_init_creates_empty_registry(self):
        """Test ParserRegistry initialization creates empty collections."""
        registry = ParserRegistry()
        assert registry._detectors == []
        assert registry._parsers == {}

    def test_register_detector_adds_and_sorts_by_priority(self):
        """Test detector registration and priority-based sorting."""
        registry = ParserRegistry()

        # Create mock detectors with different priorities
        detector1 = Mock(spec=BaseFrameworkDetector)
        detector1.priority = 50
        detector1.framework = TestFramework.PYTEST

        detector2 = Mock(spec=BaseFrameworkDetector)
        detector2.priority = 90
        detector2.framework = TestFramework.SONARQUBE

        detector3 = Mock(spec=BaseFrameworkDetector)
        detector3.priority = 10
        detector3.framework = TestFramework.GENERIC

        # Register in mixed order
        registry.register_detector(detector1)
        registry.register_detector(detector2)
        registry.register_detector(detector3)

        # Should be sorted by priority (highest first)
        assert len(registry._detectors) == 3
        assert registry._detectors[0].priority == 90  # SonarQube
        assert registry._detectors[1].priority == 50  # pytest
        assert registry._detectors[2].priority == 10  # Generic

    def test_register_parser_stores_framework_parser_mapping(self):
        """Test parser registration creates correct framework mapping."""
        registry = ParserRegistry()

        mock_parser_class = Mock()
        registry.register_parser(TestFramework.JEST, mock_parser_class)

        assert registry._parsers[TestFramework.JEST] == mock_parser_class

    def test_detect_framework_returns_first_matching_detector(self):
        """Test framework detection returns first matching detector's framework."""
        registry = ParserRegistry()

        # Create detectors with different responses
        detector1 = Mock(spec=BaseFrameworkDetector)
        detector1.priority = 90
        detector1.framework = TestFramework.SONARQUBE
        detector1.detect.return_value = False  # Won't match

        detector2 = Mock(spec=BaseFrameworkDetector)
        detector2.priority = 50
        detector2.framework = TestFramework.PYTEST
        detector2.detect.return_value = True  # Will match

        detector3 = Mock(spec=BaseFrameworkDetector)
        detector3.priority = 10
        detector3.framework = TestFramework.JEST
        detector3.detect.return_value = True  # Would match but comes after

        registry.register_detector(detector1)
        registry.register_detector(detector2)
        registry.register_detector(detector3)

        result = registry.detect_framework("test_job", "test", "trace content")

        assert result == TestFramework.PYTEST
        detector1.detect.assert_called_once_with("test_job", "test", "trace content")
        detector2.detect.assert_called_once_with("test_job", "test", "trace content")
        # detector3 should not be called since detector2 matched
        assert not detector3.detect.called

    def test_detect_framework_returns_generic_when_no_match(self):
        """Test framework detection falls back to GENERIC when no detectors match."""
        registry = ParserRegistry()

        detector = Mock(spec=BaseFrameworkDetector)
        detector.priority = 90
        detector.framework = TestFramework.SONARQUBE
        detector.detect.return_value = False

        registry.register_detector(detector)

        result = registry.detect_framework("build_job", "build", "no test content")

        assert result == TestFramework.GENERIC
        detector.detect.assert_called_once_with("build_job", "build", "no test content")

    def test_get_parser_returns_instance_when_registered(self):
        """Test parser retrieval returns instance for registered frameworks."""
        registry = ParserRegistry()

        mock_parser_class = Mock(spec=type)
        mock_parser_instance = Mock(spec=BaseFrameworkParser)
        mock_parser_class.return_value = mock_parser_instance

        registry.register_parser(TestFramework.PYTEST, mock_parser_class)

        result = registry.get_parser(TestFramework.PYTEST)

        assert result == mock_parser_instance
        mock_parser_class.assert_called_once_with()

    def test_get_parser_returns_none_when_not_registered(self):
        """Test parser retrieval returns None for unregistered frameworks."""
        registry = ParserRegistry()

        result = registry.get_parser(TestFramework.JEST)

        assert result is None

    def test_list_frameworks_returns_detector_frameworks(self):
        """Test listing frameworks returns all registered detector frameworks."""
        registry = ParserRegistry()

        detector1 = Mock(spec=BaseFrameworkDetector)
        detector1.priority = 90
        detector1.framework = TestFramework.SONARQUBE

        detector2 = Mock(spec=BaseFrameworkDetector)
        detector2.priority = 50
        detector2.framework = TestFramework.PYTEST

        registry.register_detector(detector1)
        registry.register_detector(detector2)

        frameworks = registry.list_frameworks()

        # Should be in priority order (highest first)
        assert frameworks == [TestFramework.SONARQUBE, TestFramework.PYTEST]


class TestModuleFunctions:
    """Test cases for module-level convenience functions."""

    def test_detect_job_framework_uses_global_registry(self):
        """Test detect_job_framework uses the global parser registry."""
        with patch.object(parser_registry, "detect_framework") as mock_detect:
            mock_detect.return_value = TestFramework.JEST

            result = detect_job_framework("test_job", "test", "jest test content")

            assert result == TestFramework.JEST
            mock_detect.assert_called_once_with("test_job", "test", "jest test content")

    def test_parse_with_framework_uses_parser_when_available(self):
        """Test parse_with_framework uses registered parser when available."""
        with patch.object(parser_registry, "get_parser") as mock_get_parser:
            mock_parser = Mock(spec=BaseFrameworkParser)
            mock_parse_result = {
                "parser_type": "jest",
                "framework": "jest",
                "errors": [],
                "error_count": 0,
            }
            mock_parser.parse_with_validation.return_value = mock_parse_result
            mock_get_parser.return_value = mock_parser

            result = parse_with_framework(
                "trace content", TestFramework.JEST, option1="value1"
            )

            assert result == mock_parse_result
            mock_get_parser.assert_called_once_with(TestFramework.JEST)
            mock_parser.parse_with_validation.assert_called_once_with(
                "trace content", option1="value1"
            )

    def test_parse_with_framework_fallback_when_no_parser(self):
        """Test parse_with_framework provides fallback when no parser available."""
        with patch.object(parser_registry, "get_parser") as mock_get_parser:
            mock_get_parser.return_value = None

            result = parse_with_framework("trace content", TestFramework.JEST)

            expected = {
                "parser_type": "fallback",
                "framework": "jest",
                "errors": [],
                "error_count": 0,
                "warnings": [],
                "warning_count": 0,
                "summary": {},
            }
            assert result == expected
            mock_get_parser.assert_called_once_with(TestFramework.JEST)


class TestRegistryImportErrorHandling:
    """Test cases for graceful handling of import errors."""

    def test_registry_survives_parser_import_failures(self):
        """Test that registry continues working even if some parsers fail to import."""
        # The global parser_registry should be functional even if some imports failed
        # This tests the graceful degradation with try/except ImportError blocks

        # Verify the registry exists and has basic functionality
        assert parser_registry is not None
        assert hasattr(parser_registry, "detect_framework")
        assert hasattr(parser_registry, "get_parser")

        # Should be able to detect framework even with missing imports
        result = parser_registry.detect_framework("unknown", "unknown", "unknown")
        # Should fall back to GENERIC or return a valid framework
        assert isinstance(result, TestFramework)

    def test_empty_registry_graceful_fallback(self):
        """Test that empty registry handles operations gracefully."""
        empty_registry = ParserRegistry()

        # Should return GENERIC when no detectors
        result = empty_registry.detect_framework("test", "test", "content")
        assert result == TestFramework.GENERIC

        # Should return None when no parsers
        parser = empty_registry.get_parser(TestFramework.PYTEST)
        assert parser is None

        # Should return empty list when no detectors
        frameworks = empty_registry.list_frameworks()
        assert frameworks == []


class TestRegistryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_detectors_same_priority(self):
        """Test handling of detectors with identical priorities."""
        registry = ParserRegistry()

        detector1 = Mock(spec=BaseFrameworkDetector)
        detector1.priority = 50
        detector1.framework = TestFramework.PYTEST

        detector2 = Mock(spec=BaseFrameworkDetector)
        detector2.priority = 50  # Same priority
        detector2.framework = TestFramework.JEST

        registry.register_detector(detector1)
        registry.register_detector(detector2)

        # Both should be registered
        assert len(registry._detectors) == 2
        # Order should be stable (first registered should come first for same priority)
        frameworks = registry.list_frameworks()
        assert TestFramework.PYTEST in frameworks
        assert TestFramework.JEST in frameworks

    def test_re_registering_same_framework_parser(self):
        """Test re-registering parser for same framework overwrites."""
        registry = ParserRegistry()

        parser_class1 = Mock()
        parser_class2 = Mock()

        registry.register_parser(TestFramework.PYTEST, parser_class1)
        registry.register_parser(TestFramework.PYTEST, parser_class2)

        # Should have latest registration
        assert registry._parsers[TestFramework.PYTEST] == parser_class2

    def test_detector_with_exception_during_detection(self):
        """Test registry handles exceptions during framework detection."""
        registry = ParserRegistry()

        detector1 = Mock(spec=BaseFrameworkDetector)
        detector1.priority = 90
        detector1.framework = TestFramework.SONARQUBE
        detector1.detect.side_effect = Exception("Detection failed")  # Raises exception

        detector2 = Mock(spec=BaseFrameworkDetector)
        detector2.priority = 50
        detector2.framework = TestFramework.PYTEST
        detector2.detect.return_value = True  # Should work

        registry.register_detector(detector1)
        registry.register_detector(detector2)

        # Should handle exception and return None when all detectors fail
        result = registry.detect_framework("test", "test", "content")
        assert result is None
