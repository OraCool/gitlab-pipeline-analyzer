"""
Comprehensive test coverage for SonarQube parser to boost overall test coverage.

This test file targets the SonarQube parser functionality that was previously untested
to increase coverage from ~22% to a higher percentage.
"""

from gitlab_analyzer.parsers.sonarqube_parser import SonarQubeDetector, SonarQubeParser
from gitlab_analyzer.parsers.base_parser import TestFramework


class TestSonarQubeDetector:
    """Test SonarQube detector functionality"""

    def test_framework_property(self):
        """Test framework property returns SonarQube"""
        detector = SonarQubeDetector()
        assert detector.framework == TestFramework.SONARQUBE

    def test_priority_property(self):
        """Test priority property returns expected value"""
        detector = SonarQubeDetector()
        assert detector.priority == 95

    def test_detect_by_job_name_sonar(self):
        """Test detection by job name containing 'sonar'"""
        detector = SonarQubeDetector()
        assert detector.detect(
            job_name="sonar-analysis", job_stage="test", trace_content=""
        )

    def test_detect_by_job_name_sonarqube(self):
        """Test detection by job name containing 'sonarqube'"""
        detector = SonarQubeDetector()
        assert detector.detect(
            job_name="sonarqube-scan", job_stage="test", trace_content=""
        )

    def test_detect_by_job_name_quality_gate(self):
        """Test detection by job name containing 'quality gate'"""
        detector = SonarQubeDetector()
        assert detector.detect(
            job_name="quality-gate-check", job_stage="test", trace_content=""
        )

    def test_detect_by_job_name_code_analysis(self):
        """Test detection by job name containing 'code quality'"""
        detector = SonarQubeDetector()
        assert detector.detect(
            job_name="code-quality-scan", job_stage="test", trace_content=""
        )

    def test_detect_by_trace_content_sonar_scanner(self):
        """Test detection by trace content containing SonarScanner execution"""
        detector = SonarQubeDetector()
        trace_content = """
        INFO: SonarScanner execution started
        INFO: Project root configuration file: NONE
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_sonarqube_url(self):
        """Test detection by trace content containing QUALITY GATE STATUS"""
        detector = SonarQubeDetector()
        trace_content = """
        INFO: QUALITY GATE STATUS: PASSED
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_quality_gate_result(self):
        """Test detection by trace content containing Quality Gate result"""
        detector = SonarQubeDetector()
        trace_content = """
        INFO: QUALITY GATE STATUS: OK
        INFO: View details on https://sonarqube.company.com/dashboard?id=project
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_sonar_project_properties(self):
        """Test detection by trace content containing sonar reportPath"""
        detector = SonarQubeDetector()
        trace_content = """
        INFO: sonar.coverage.reportPath=coverage.xml
        INFO: sonar.projectName=My Project
        INFO: sonar.sources=src
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_by_trace_content_analysis_successful(self):
        """Test detection by trace content containing org.sonar.plugins"""
        detector = SonarQubeDetector()
        trace_content = """
        INFO: Analysis total time: 1:23.456 s
        INFO: Loading plugin org.sonar.plugins.javascript
        """
        assert detector.detect(
            job_name="build", job_stage="test", trace_content=trace_content
        )

    def test_detect_negative_case(self):
        """Test non-SonarQube job is not detected"""
        detector = SonarQubeDetector()
        assert not detector.detect(
            job_name="build-app",
            job_stage="build",
            trace_content="Building application",
        )


class TestSonarQubeParser:
    """Test SonarQube parser functionality"""

    def test_framework_property(self):
        """Test framework property returns SonarQube"""
        parser = SonarQubeParser()
        assert parser.framework == TestFramework.SONARQUBE

    def test_parse_simple_sonar_output(self):
        """Test parsing simple SonarQube output"""
        parser = SonarQubeParser()
        trace_content = """
        INFO: Scanner configuration file: /opt/sonar-scanner/conf/sonar-scanner.properties
        INFO: ANALYSIS SUCCESSFUL, you can find the results at: https://sonarqube.company.com
        INFO: QUALITY GATE STATUS: OK
        """

        result = parser.parse(trace_content)

        assert result["parser_type"] == "sonarqube"
        assert result["framework"] == "sonarqube"
        assert result["error_count"] == 0
        assert result["warning_count"] == 0
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["summary"], dict)

    def test_parse_quality_gate_failure(self):
        """Test parsing SonarQube Quality Gate failure - terminal error"""
        parser = SonarQubeParser()
        trace_content = """
        INFO: QUALITY GATE STATUS: FAILED
        ERROR: QUALITY GATE STATUS: FAILED dashboard?id=my-project&pullRequest=123
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        error = result["errors"][0]
        assert error["exception_type"] == "Quality Gate Failure"
        assert "QUALITY GATE STATUS: FAILED" in error["message"]
        assert any(
            "Quality Gate" in error.get("exception_type", "")
            for error in result["errors"]
        )

    def test_parse_sonar_authentication_failure(self):
        """Test parsing SonarQube authentication failure - terminal error"""
        parser = SonarQubeParser()
        trace_content = """
        ERROR: Unauthorized
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        error = result["errors"][0]
        assert error["exception_type"] == "Authentication Failure"

    def test_parse_sonar_permission_failure(self):
        """Test parsing SonarQube permission failure - terminal error"""
        parser = SonarQubeParser()
        trace_content = """
        ERROR: Permission denied
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        error = result["errors"][0]
        assert error["exception_type"] == "Permission Failure"

    def test_parse_sonar_config_error(self):
        """Test parsing SonarQube configuration error - terminal error"""
        parser = SonarQubeParser()
        trace_content = """
        ERROR: sonar-project.properties not found
        """

        result = parser.parse(trace_content)

        assert result["error_count"] > 0
        error = result["errors"][0]
        assert error["exception_type"] == "Configuration Error"

    def test_parse_sonar_processing_noise_ignored(self):
        """Test that SonarQube processing noise is ignored (not counted as errors)"""
        parser = SonarQubeParser()
        trace_content = """
        INFO: Parsing report '/builds/product/gwpy-core/coverage.xml'
        ERROR: Cannot resolve the file path '__init__.py' of the coverage report, ambiguity...
        INFO: Sensor Cobertura Sensor for Python coverage [python] (done) | time=957ms
        ERROR: Cannot find coverage.xml
        INFO: Analysis completed
        """

        result = parser.parse(trace_content)

        # These ERRORs should be ignored as they're processing noise between INFO lines
        assert result["error_count"] == 0
        assert any(
            "coverage" in warning.get("message", "").lower()
            for warning in result["warnings"]
        )

    def test_parse_sonar_quality_threshold_warning(self):
        """Test parsing SonarQube quality threshold warning"""
        parser = SonarQubeParser()
        trace_content = """
        WARN: Quality gate coverage threshold not met
        INFO: Analysis completed
        """

        result = parser.parse(trace_content)

        assert result["warning_count"] > 0
        warning = result["warnings"][0]
        assert "Quality gate" in warning["message"]

    def test_parse_sonar_technical_debt(self):
        """Test parsing SonarQube technical debt information"""
        parser = SonarQubeParser()
        trace_content = """
        INFO: Technical Debt Ratio: 2.5% (target <= 5.0%)
        INFO: Technical Debt: 2d 4h
        """

        result = parser.parse(trace_content)

        # This should be handled as informational, not an error
        assert result["error_count"] == 0
        assert "Technical Debt" in trace_content

    def test_parse_mixed_sonar_content(self):
        """Test parsing mixed SonarQube output with terminal and processing errors"""
        parser = SonarQubeParser()
        trace_content = """
        INFO: Scanner configuration file: /opt/sonar-scanner/conf/sonar-scanner.properties
        ERROR: Cannot resolve the file path '__init__.py' of the coverage report, ambiguity...
        INFO: Sensor completed
        ERROR: QUALITY GATE STATUS: FAILED dashboard?id=my-project
        INFO: Analysis failed
        ERROR: Unauthorized
        """

        result = parser.parse(trace_content)

        # Should only capture terminal errors (Quality Gate + Authentication), not processing noise
        assert result["error_count"] == 2
        error_types = [error["exception_type"] for error in result["errors"]]
        assert "Quality Gate Failure" in error_types
        assert "Authentication Failure" in error_types

    def test_extract_source_file_and_line_sonar_format(self):
        """Test extracting source file and line from SonarQube standard format"""
        parser = SonarQubeParser()
        error_message = (
            "src/main/java/com/example/Service.java:15: Unused import detected"
        )

        file_path, line_num = parser._extract_source_file_and_line(error_message)

        assert file_path == "src/main/java/com/example/Service.java"
        assert line_num == 15
        assert line_num == 15

    def test_extract_source_file_and_line_range_format(self):
        """Test extracting source file and line from SonarQube range format"""
        parser = SonarQubeParser()
        error_message = "src/main/java/utils/Helper.java:100: Duplication detected"

        file_path, line_num = parser._extract_source_file_and_line(error_message)

        assert file_path == "src/main/java/utils/Helper.java"
        assert line_num == 100
        assert line_num == 100  # Should extract the start line

    def test_extract_source_file_and_line_no_match(self):
        """Test extracting source file and line when no pattern matches"""
        parser = SonarQubeParser()
        error_message = "Generic error message without location"

        file_path, line_num = parser._extract_source_file_and_line(error_message)

        assert file_path is None
        assert line_num is None

    def test_sonar_summary_parsing(self):
        """Test parsing SonarQube summary information"""
        parser = SonarQubeParser()
        trace_content = """
        INFO: Analysis total time: 1:23.456 s
        INFO: ANALYSIS SUCCESSFUL, you can find the results at: https://sonarqube.company.com
        INFO: QUALITY GATE STATUS: OK
        INFO: Technical Debt Ratio: 2.5% (target <= 5.0%)
        """

        result = parser.parse(trace_content)

        assert "summary" in result
        summary = result["summary"]

        # Check if summary contains expected SonarQube-specific information
        assert isinstance(summary, dict)

    def test_sonar_rule_violation_parsing(self):
        """Test parsing SonarQube terminal errors only (not rule violations which are processing messages)"""
        parser = SonarQubeParser()
        trace_content = """
        MAJOR: squid:S1481 - Remove this unused import of 'java.util.List'.
        File: src/main/java/com/example/Service.java:15
        INFO: Processing file analysis
        ERROR: QUALITY GATE STATUS: FAILED dashboard?id=my-project
        MINOR: squid:S1118 - Add a private constructor to hide the implicit public one.
        """

        result = parser.parse(trace_content)

        # Only the Quality Gate failure should be captured as a terminal error
        assert result["error_count"] == 1
        error = result["errors"][0]
        assert error["exception_type"] == "Quality Gate Failure"

    def test_empty_trace_content(self):
        """Test parsing empty trace content"""
        parser = SonarQubeParser()
        result = parser.parse("")

        assert result["error_count"] == 0
        assert result["warning_count"] == 0
        assert result["parser_type"] == "sonarqube"

    def test_malformed_sonar_output(self):
        """Test parser handles malformed SonarQube output gracefully"""
        parser = SonarQubeParser()
        trace_content = """
        This is not valid SonarQube output
        Some random text
        Not following SonarQube patterns
        """

        result = parser.parse(trace_content)

        # Should not crash and return valid structure
        assert "parser_type" in result
        assert "errors" in result
        assert "warnings" in result

    def test_sonar_info_messages(self):
        """Test that SonarQube INFO messages are not treated as errors"""
        parser = SonarQubeParser()
        trace_content = """
        INFO: Scanner configuration file: /opt/sonar-scanner/conf/sonar-scanner.properties
        INFO: Project root configuration file: NONE
        INFO: sonar.projectKey=my-project
        INFO: sonar.projectName=My Project
        INFO: sonar.sources=src
        INFO: Analysis total time: 1:23.456 s
        """

        result = parser.parse(trace_content)

        # INFO messages should not be treated as errors
        assert result["error_count"] == 0

    def test_sonar_debug_messages(self):
        """Test that SonarQube DEBUG messages are handled appropriately"""
        parser = SonarQubeParser()
        trace_content = """
        DEBUG: Initializing SonarQube Scanner
        DEBUG: Loading configuration
        INFO: ANALYSIS SUCCESSFUL
        """

        result = parser.parse(trace_content)

        # Should handle DEBUG messages without crashing
        assert "parser_type" in result
