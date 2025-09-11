"""
Error Analysis Service

Handles complex error analysis and enhancement logic.
Responsible for:
- Adding fix guidance to errors
- Enhancing errors with trace context
- Applying analysis modes and filtering

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ErrorAnalysisService:
    """Service for advanced error analysis and enhancement"""

    def enhance_error_with_fix_guidance(
        self, error: dict[str, Any], mode: str = "balanced"
    ) -> dict[str, Any]:
        """
        Enhance an error with fix guidance based on analysis mode.

        Args:
            error: Error data dictionary
            mode: Analysis mode (minimal, balanced, fixing, detailed)

        Returns:
            Enhanced error with fix guidance
        """
        if not error or mode not in ["fixing", "detailed"]:
            return error or {}

        try:
            from gitlab_analyzer.utils.utils import _generate_fix_guidance

            fix_guidance_error = {
                "exception_type": error.get("error_type")
                or error.get("exception_type"),
                "exception_message": error.get("message"),
                "file_path": error.get("file_path") or error.get("file"),
                "line_number": str(error.get("line") or error.get("line_number") or ""),
                "message": error.get("message"),
            }

            # Add test-specific info if available
            detail = error.get("detail", {})
            if isinstance(detail, dict):
                fix_guidance_error.update(
                    {
                        "test_function": detail.get("test_function"),
                        "test_name": detail.get("test_name"),
                    }
                )

            enhanced_error = error.copy()
            enhanced_error["fix_guidance"] = _generate_fix_guidance(fix_guidance_error)
            return enhanced_error

        except Exception as fix_error:
            logger.warning("Failed to generate fix guidance: %s", fix_error)
            if error:
                enhanced_error = error.copy()
                enhanced_error["fix_guidance"] = {
                    "error": f"Failed to generate fix guidance: {fix_error}"
                }
                return enhanced_error
            return {}

    def enhance_errors_batch(
        self, errors: list[dict[str, Any]], mode: str = "balanced"
    ) -> list[dict[str, Any]]:
        """
        Enhance a batch of errors with analysis mode-specific enhancements.

        Args:
            errors: List of error dictionaries
            mode: Analysis mode (minimal, balanced, fixing, detailed)

        Returns:
            List of enhanced errors
        """
        enhanced_errors = []
        for error in errors:
            enhanced_error = self.enhance_error_with_fix_guidance(error, mode)
            enhanced_errors.append(enhanced_error)
        return enhanced_errors

    def filter_errors_by_mode(
        self, errors: list[dict[str, Any]], mode: str = "balanced"
    ) -> list[dict[str, Any]]:
        """
        Filter and prioritize errors based on analysis mode.

        Args:
            errors: List of error dictionaries
            mode: Analysis mode (minimal, balanced, fixing, detailed)

        Returns:
            Filtered and prioritized errors
        """
        if mode == "minimal":
            # Only return critical errors for minimal mode
            return [
                error
                for error in errors
                if error.get("severity", "error") in ["error", "critical"]
            ]

        elif mode == "balanced":
            # Return all errors but prioritize by type
            critical_errors = [
                e
                for e in errors
                if e.get("exception_type")
                in ["SyntaxError", "ImportError", "ModuleNotFoundError"]
            ]
            other_errors = [e for e in errors if e not in critical_errors]
            return critical_errors + other_errors

        else:  # fixing, detailed
            # Return all errors with full context
            return errors

    def calculate_error_statistics(
        self, errors: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Calculate comprehensive error statistics.

        Args:
            errors: List of error dictionaries

        Returns:
            Error statistics dictionary
        """
        if not errors:
            return {
                "total_errors": 0,
                "error_types": [],
                "affected_files": [],
                "severity_distribution": {},
                "file_error_counts": {},
            }

        error_types = set()
        affected_files = set()
        severity_counts: dict[str, int] = {}
        file_error_counts: dict[str, int] = {}

        for error in errors:
            # Track error types
            error_type = error.get("error_type") or error.get("exception_type")
            if error_type:
                error_types.add(error_type)

            # Track affected files
            file_path = error.get("file_path") or error.get("file")
            if file_path:
                affected_files.add(file_path)
                file_error_counts[file_path] = file_error_counts.get(file_path, 0) + 1

            # Track severity distribution
            severity = error.get("severity", "error")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_errors": len(errors),
            "error_types": list(error_types),
            "affected_files": list(affected_files),
            "affected_file_count": len(affected_files),
            "error_type_count": len(error_types),
            "severity_distribution": severity_counts,
            "file_error_counts": file_error_counts,
            "most_affected_files": sorted(
                file_error_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def prioritize_errors_for_fixing(
        self, errors: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Prioritize errors based on their likelihood to cause cascading failures.

        Args:
            errors: List of error dictionaries

        Returns:
            Prioritized list of errors
        """
        # Define priority weights for different error types
        priority_weights = {
            "SyntaxError": 100,
            "ImportError": 90,
            "ModuleNotFoundError": 90,
            "IndentationError": 85,
            "NameError": 80,
            "AttributeError": 70,
            "TypeError": 65,
            "ValueError": 60,
            "KeyError": 55,
            "IndexError": 50,
        }

        def get_error_priority(error):
            error_type = error.get("error_type") or error.get("exception_type", "")
            base_priority = priority_weights.get(error_type, 30)

            # Boost priority for errors in test files (they're often easier to fix)
            file_path = error.get("file_path") or error.get("file", "")
            if "test" in file_path.lower():
                base_priority += 10

            # Boost priority for errors with line numbers (more actionable)
            if error.get("line_number") or error.get("line"):
                base_priority += 5

            return base_priority

        return sorted(errors, key=get_error_priority, reverse=True)


# Create a singleton instance for easy import
error_analysis_service = ErrorAnalysisService()
