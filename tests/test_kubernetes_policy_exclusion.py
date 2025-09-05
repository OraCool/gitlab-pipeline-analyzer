"""
Test for verifying Kubernetes policy warnings are properly excluded from error analysis

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.parsers.log_parser import LogParser


class TestKubernetesPolicyExclusion:
    """Test that Kubernetes policy warnings are properly excluded"""

    def test_exclude_require_labels_policy_warnings(self):
        """Test that require-labels policy warnings are excluded"""
        log_text = """
Running with gitlab-runner 15.4.0 (86140c2a)
  on runner-abc123
Preparing the "kubernetes" executor
WARNING: Event retrieved from the cluster: policy require-labels/require-labels fail: validation error: The labels 'company.com/owner', 'company.com/account', 'company.com/component-name' are required and their values must match the scheme https://example.com/Cost-category. rule require-labels failed at path /metadata/labels/company.com/account/
WARNING: Event retrieved from the cluster: policy require-labels/require-labels fail: validation error: The labels 'company.com/owner', 'company.com/account', 'company.com/component-name' are required and their values must match the scheme https://example.com/Cost-category. rule require-labels failed at path /metadata/labels/company.com/component-name/
Running docker image python:3.11-slim
$ python -m pytest tests/ -v
========================= test session starts =========================
collected 5 items

tests/test_example.py::test_passing PASSED                        [ 20%]
tests/test_example.py::test_failing FAILED                        [ 40%]

=========================== FAILURES ===========================
________________________ test_failing ________________________

    def test_failing():
>       assert False, "This test intentionally fails"
E       AssertionError: This test intentionally fails

tests/test_example.py:10: AssertionError
======================== short test summary info ========================
FAILED tests/test_example.py::test_failing - AssertionError: This test intentionally fails
========================= 1 failed, 1 passed in 0.05s =========================
Job failed: exit code 1
        """

        entries = LogParser.extract_log_entries(log_text)

        # Verify that no Kubernetes policy warnings are captured as errors
        policy_warnings = [
            entry
            for entry in entries
            if "require-labels" in entry.message
            or "company.com" in entry.message
            or "Event retrieved from the cluster" in entry.message
        ]

        assert len(policy_warnings) == 0, (
            f"Found policy warnings that should be excluded: {policy_warnings}"
        )

        # Verify that actual test failures are still captured
        test_failures = [
            entry
            for entry in entries
            if "AssertionError" in entry.message or "test_failing" in entry.message
        ]

        assert len(test_failures) > 0, "Expected test failures should still be captured"

    def test_exclude_general_policy_warnings_from_cluster(self):
        """Test that general cluster policy warnings are excluded"""
        log_text = """
Running on runner-xyz789
WARNING: Event retrieved from the cluster: policy security-policy/network-policy fail: validation error: Network policies must be defined
WARNING: Event retrieved from the cluster: policy resource-limits/memory-limits fail: validation error: Memory limits are required
ERROR: ImportError: No module named 'nonexistent_module'
        """

        entries = LogParser.extract_log_entries(log_text)

        # Verify that cluster policy warnings are excluded
        cluster_policy_warnings = [
            entry
            for entry in entries
            if "Event retrieved from the cluster" in entry.message
            and "policy" in entry.message
        ]

        assert len(cluster_policy_warnings) == 0, (
            f"Found cluster policy warnings that should be excluded: {cluster_policy_warnings}"
        )

        # Verify that actual code errors are still captured
        import_errors = [entry for entry in entries if "ImportError" in entry.message]

        assert len(import_errors) > 0, "Expected import errors should still be captured"

    def test_base_parser_classifies_policy_warnings_correctly(self):
        """Test that base parser correctly classifies policy warnings"""
        from gitlab_analyzer.parsers.base_parser import BaseParser

        # Test require-labels policy warning classification
        require_labels_warning = "WARNING: Event retrieved from the cluster: policy require-labels/require-labels fail: validation error: The labels 'company.com/owner' are required"

        error_type = BaseParser.classify_error_type(require_labels_warning)
        assert error_type == "infrastructure_warning", (
            f"Expected 'infrastructure_warning', got '{error_type}'"
        )

        # Test general policy warning classification
        general_policy_warning = "WARNING: policy security-scan failed"

        error_type = BaseParser.classify_error_type(general_policy_warning)
        assert error_type == "policy_warning", (
            f"Expected 'policy_warning', got '{error_type}'"
        )

    def test_mixed_warnings_and_errors(self):
        """Test that code-related warnings are still captured while infrastructure warnings are excluded"""
        log_text = """
WARNING: Event retrieved from the cluster: policy require-labels/require-labels fail: validation error
WARNING: DeprecationWarning: This function is deprecated
WARNING: Event retrieved from the cluster: policy security-policy fail
WARNING: UserWarning: Custom warning message
ERROR: SyntaxError: invalid syntax
        """

        entries = LogParser.extract_log_entries(log_text)

        # Should exclude cluster policy warnings
        cluster_warnings = [
            entry
            for entry in entries
            if "Event retrieved from the cluster" in entry.message
        ]
        assert len(cluster_warnings) == 0, "Cluster policy warnings should be excluded"

        # Should include code-related warnings
        code_warnings = [
            entry
            for entry in entries
            if "DeprecationWarning" in entry.message or "UserWarning" in entry.message
        ]
        assert len(code_warnings) == 2, (
            f"Expected 2 code warnings, got {len(code_warnings)}"
        )

        # Should include syntax errors
        syntax_errors = [entry for entry in entries if "SyntaxError" in entry.message]
        assert len(syntax_errors) == 1, (
            f"Expected 1 syntax error, got {len(syntax_errors)}"
        )

    def test_policy_warning_patterns_coverage(self):
        """Test comprehensive coverage of different policy warning patterns"""
        test_cases = [
            "WARNING: Event retrieved from the cluster: policy require-labels/require-labels fail: validation error: The labels 'company.com/owner', 'company.com/account', 'company.com/component-name' are required",
            "WARNING: Event retrieved from the cluster: policy security-scan fail: validation error: Security scan failed",
            "WARNING: labels 'company.com/environment' are required and their values must match",
            "rule require-labels failed at path /metadata/labels/company.com/account/",
            "WARNING: Event retrieved from the cluster: policy network-security fail",
        ]

        for warning_text in test_cases:
            # Create a minimal log with the warning
            log_text = f"""
Running on runner-test
{warning_text}
ERROR: Real error that should be captured
            """

            entries = LogParser.extract_log_entries(log_text)

            # Verify the specific warning is excluded - use a safer method to check
            excluded_warnings = [
                entry for entry in entries if warning_text in entry.message
            ]

            assert len(excluded_warnings) == 0, (
                f"Warning should be excluded: {warning_text}"
            )

            # Verify real errors are still captured
            real_errors = [
                entry
                for entry in entries
                if "Real error that should be captured" in entry.message
            ]

            assert len(real_errors) > 0, (
                f"Real errors should still be captured for case: {warning_text}"
            )
