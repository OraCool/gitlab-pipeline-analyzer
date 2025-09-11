"""AI-optimized error summarization for GitLab Pipeline Analyzer.

This module provides tools to generate concise, actionable error summaries
designed for AI assistant consumption with minimal context.
"""

from dataclasses import dataclass
from typing import Any

from .error_model import Error
from .root_cause_analyzer import ErrorGroup, RootCauseAnalysis


@dataclass
class MinimalErrorSummary:
    """Minimal error summary optimized for AI assistants."""

    issue: str  # One-line description of the main problem
    location: str  # Primary file:line where error occurs
    fix_suggestion: str  # Short, actionable fix suggestion
    confidence: float  # Confidence in the analysis (0.0-1.0)
    error_count: int  # Total number of related errors
    affected_files: int  # Number of files affected


@dataclass
class RootCauseSummary:
    """Root cause summary with categorized insights."""

    primary_issue: str  # Main root cause description
    category: str  # Error category (imports, attributes, etc.)
    severity: str  # Severity level (low, medium, high, critical)
    quick_fix: str  # Immediate action to take
    broader_fix: str  # Longer-term solution if different
    impact_assessment: str  # Brief impact description
    related_errors: int  # Count of related/cascading errors
    key_insights: list[str]  # Key insights from the analysis
    context_reduction_percentage: (
        float  # How much context was reduced for AI consumption
    )


class ErrorSummarizer:
    """Generates AI-optimized summaries from root cause analysis."""

    def __init__(self):
        """Initialize the error summarizer."""
        pass

    def generate_minimal_summary(
        self, analysis: RootCauseAnalysis
    ) -> MinimalErrorSummary:
        """Generate a minimal error summary for quick AI consumption."""
        if not analysis.primary_cause or not analysis.primary_cause.errors:
            return MinimalErrorSummary(
                issue="No errors found to analyze",
                location="N/A",
                fix_suggestion="No action needed",
                confidence=0.0,
                error_count=0,
                affected_files=0,
            )

        primary = analysis.primary_cause
        representative_error = primary.errors[0]

        return MinimalErrorSummary(
            issue=self._generate_one_liner(primary),
            location=self._format_primary_location(representative_error),
            fix_suggestion=self._extract_quick_fix(primary),
            confidence=analysis.confidence,
            error_count=analysis.total_errors,
            affected_files=len(analysis.affected_files),
        )

    def generate_root_cause_summary(
        self, analysis: RootCauseAnalysis
    ) -> RootCauseSummary:
        """Generate a comprehensive root cause summary."""
        if not analysis.primary_cause or not analysis.primary_cause.errors:
            return RootCauseSummary(
                primary_issue="No clear root cause identified",
                category="Unknown",
                severity="low",
                quick_fix="Review logs for more details",
                broader_fix="No specific recommendations",
                impact_assessment="Minimal impact - no errors found",
                related_errors=0,
                key_insights=["No significant patterns found"],
                context_reduction_percentage=95.0,
            )

        primary = analysis.primary_cause

        # Generate key insights
        key_insights = []
        key_insights.append(f"Primary issue: {primary.pattern.description}")
        key_insights.append(
            f"Affects {len(primary.affected_files)} files with {len(primary.errors)} errors"
        )
        if analysis.secondary_causes:
            key_insights.append(
                f"Additional {len(analysis.secondary_causes)} secondary issues identified"
            )
        key_insights.append(f"Overall confidence: {analysis.confidence:.1%}")

        # Calculate context reduction (estimate)
        total_original_context = (
            len(primary.errors) * 200
        )  # Rough estimate of original error data
        reduced_context = len(key_insights) * 50  # Reduced to key insights
        reduction_percentage = max(
            0, (1 - reduced_context / max(total_original_context, 1)) * 100
        )

        return RootCauseSummary(
            primary_issue=primary.pattern.description,
            category=primary.pattern.category,
            severity=primary.pattern.severity,
            quick_fix=self._extract_quick_fix(primary),
            broader_fix=self._extract_broader_fix(primary),
            impact_assessment=self._assess_impact(analysis),
            related_errors=len(analysis.secondary_causes),
            key_insights=key_insights,
            context_reduction_percentage=reduction_percentage,
        )

    def format_for_ai_assistant(self, analysis: RootCauseAnalysis) -> dict[str, Any]:
        """Format analysis results optimized for AI assistant responses."""
        minimal = self.generate_minimal_summary(analysis)
        root_cause = self.generate_root_cause_summary(analysis)

        return {
            "summary": {
                "problem": minimal.issue,
                "location": minimal.location,
                "confidence": f"{minimal.confidence:.0%}",
                "scope": f"{minimal.error_count} errors in {minimal.affected_files} files",
            },
            "root_cause": {
                "issue": root_cause.primary_issue,
                "category": root_cause.category,
                "severity": root_cause.severity,
            },
            "action_plan": {
                "immediate": root_cause.quick_fix,
                "comprehensive": root_cause.broader_fix,
                "impact": root_cause.impact_assessment,
            },
            "context": {
                "primary_pattern": (
                    analysis.primary_cause.pattern.name
                    if analysis.primary_cause
                    else "unknown"
                ),
                "related_issues": root_cause.related_errors,
                "analysis_confidence": analysis.confidence,
            },
        }

    def _generate_one_liner(self, error_group: ErrorGroup) -> str:
        """Generate a concise one-line description of the error group."""
        pattern = error_group.pattern
        error_count = len(error_group.errors)

        # Customize based on pattern type
        if "attribute" in pattern.name.lower():
            return f"Missing attribute causing {error_count} failures"
        elif "import" in pattern.name.lower():
            return f"Import/dependency issue affecting {error_count} locations"
        elif "function" in pattern.name.lower():
            return f"Function call problem in {error_count} places"
        elif "uuid" in pattern.name.lower():
            return f"UUID string conversion error ({error_count} occurrences)"
        else:
            return f"{pattern.category} error affecting {error_count} locations"

    def _format_primary_location(self, error: Error) -> str:
        """Format the primary error location for display."""
        if not error.file_path:
            return "Unknown location"

        # Extract just the filename for brevity
        filename = error.file_path.split("/")[-1]

        if error.line_number:
            return f"{filename}:{error.line_number}"
        else:
            return filename

    def _extract_quick_fix(self, error_group: ErrorGroup) -> str:
        """Extract a quick, actionable fix suggestion."""
        template = error_group.pattern.fix_template

        # Simplify and make more actionable
        if "Check if" in template:
            return template.replace("Check if", "Verify").split(".")[0]
        elif "Ensure" in template or "Add" in template or "Import" in template:
            return template.split(".")[0]
        else:
            # Generic fallback
            return f"Fix {error_group.pattern.category.lower()} issue in affected files"

    def _extract_broader_fix(self, error_group: ErrorGroup) -> str:
        """Extract a broader, more comprehensive fix suggestion."""
        pattern = error_group.pattern

        # Generate broader recommendations based on pattern
        if pattern.common_causes:
            cause = pattern.common_causes[0]
            return f"Address {cause.lower()} to prevent similar issues"
        else:
            return f"Review and refactor {pattern.category.lower()} handling"

    def _assess_impact(self, analysis: RootCauseAnalysis) -> str:
        """Assess the impact of the errors."""
        total_errors = analysis.total_errors
        affected_files = len(analysis.affected_files)

        if total_errors > 20 or affected_files > 5:
            return "High impact - multiple files and many errors"
        elif total_errors > 10 or affected_files > 2:
            return "Medium impact - several files affected"
        elif total_errors > 5:
            return "Low-medium impact - localized but multiple errors"
        else:
            return "Low impact - few errors in limited scope"
