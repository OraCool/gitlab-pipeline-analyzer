"""Root cause analyzer implementation with dynamic pattern detection."""

from dataclasses import dataclass
from typing import Any

from ..patterns.error_patterns import DynamicErrorPattern, pattern_matcher
from ..utils.debug import debug_print, verbose_debug_print, very_verbose_debug_print
from .error_model import Error


@dataclass
class ErrorGroup:
    """A group of related errors with common root cause."""

    pattern: DynamicErrorPattern
    errors: list[Error]
    confidence: float
    impact_score: int

    @property
    def affected_files(self) -> set[str]:
        """Get all files affected by this error group."""
        return {error.file_path for error in self.errors if error.file_path}

    @property
    def error_count(self) -> int:
        """Number of errors in this group."""
        return len(self.errors)


@dataclass
class RootCauseAnalysis:
    """Complete root cause analysis for a set of errors."""

    primary_cause: ErrorGroup | None
    secondary_causes: list[ErrorGroup]
    summary: dict[str, Any]
    fix_suggestions: list[str]
    confidence: float

    @property
    def total_errors(self) -> int:
        """Total number of errors analyzed."""
        primary_count = self.primary_cause.error_count if self.primary_cause else 0
        return primary_count + sum(group.error_count for group in self.secondary_causes)

    @property
    def affected_files(self) -> set[str]:
        """All files affected by the analyzed errors."""
        files = (
            self.primary_cause.affected_files.copy() if self.primary_cause else set()
        )
        for group in self.secondary_causes:
            files.update(group.affected_files)
        return files


class RootCauseAnalyzer:
    """Analyzes errors to identify root causes and generate insights."""

    def __init__(self):
        self.pattern_matcher = pattern_matcher

    def analyze(self, errors: list[Error]) -> RootCauseAnalysis:
        """Perform complete root cause analysis on a list of errors using dynamic pattern detection."""
        debug_print(f"🔍 Starting dynamic root cause analysis for {len(errors)} errors")

        if not errors:
            debug_print("⚠️ No errors to analyze, returning empty analysis")
            return self._empty_analysis()

        # Step 1: Dynamically analyze errors to find patterns
        verbose_debug_print("🤖 Performing dynamic pattern analysis...")
        dynamic_patterns = self.pattern_matcher.analyze_errors(errors)
        debug_print(f"📊 Dynamic analysis found {len(dynamic_patterns)} patterns")

        # Step 2: Create error groups from dynamic patterns
        verbose_debug_print("� Creating error groups from dynamic patterns...")
        error_groups = self._create_groups_from_dynamic_patterns(
            dynamic_patterns, errors
        )
        debug_print(f"📊 Created {len(error_groups)} error groups")

        # Step 3: Rank groups by impact and significance
        verbose_debug_print("🎯 Ranking error groups by impact...")
        ranked_groups = self._rank_error_groups(error_groups)
        for i, group in enumerate(ranked_groups[:3]):  # Show top 3
            debug_print(
                f"  #{i + 1}: {group.pattern.pattern_id} (impact: {group.impact_score}, confidence: {group.confidence:.2f}, errors: {group.error_count})"
            )

        # Step 4: Identify primary and secondary causes
        primary_cause = ranked_groups[0] if ranked_groups else None
        secondary_causes = ranked_groups[1:] if len(ranked_groups) > 1 else []

        if primary_cause:
            debug_print(
                f"🎯 Primary cause identified: {primary_cause.pattern.category}"
            )
            verbose_debug_print(
                f"   Pattern: {primary_cause.pattern.representative_message[:100]}..."
            )
            verbose_debug_print(f"   Affects {len(primary_cause.affected_files)} files")

        if secondary_causes:
            debug_print(
                f"📋 Secondary causes: {len(secondary_causes)} additional patterns"
            )
            for i, cause in enumerate(secondary_causes[:2]):  # Show top 2 secondary
                verbose_debug_print(
                    f"   #{i + 1}: {cause.pattern.category} ({cause.error_count} errors)"
                )

        # Step 5: Generate summary and suggestions
        verbose_debug_print("📝 Generating summary and fix suggestions...")
        summary = self._generate_summary(primary_cause, secondary_causes, errors)
        fix_suggestions = self._generate_fix_suggestions(ranked_groups)
        confidence = self._calculate_confidence(ranked_groups)

        debug_print(
            f"✅ Analysis complete: confidence={confidence:.2f}, {len(fix_suggestions)} suggestions"
        )

        return RootCauseAnalysis(
            primary_cause=primary_cause,
            secondary_causes=secondary_causes,
            summary=summary,
            fix_suggestions=fix_suggestions,
            confidence=confidence,
        )

    def _create_groups_from_dynamic_patterns(
        self, patterns: list[DynamicErrorPattern], all_errors: list[Error]
    ) -> list[ErrorGroup]:
        """Create error groups from dynamically discovered patterns."""
        groups = []

        for pattern in patterns:
            # Find errors that match this pattern
            matching_errors = []
            for error in all_errors:
                # Check if error message is in the pattern's similar messages
                if any(
                    error.message in similar_msg or similar_msg in error.message
                    for similar_msg in pattern.similar_messages
                ):
                    matching_errors.append(error)

            if matching_errors:
                # Calculate confidence based on pattern strength and error consistency
                confidence = min(
                    1.0, pattern.severity_score + (pattern.frequency / len(all_errors))
                )

                # Calculate impact score using existing method
                impact_score = self._calculate_impact_score(matching_errors)

                group = ErrorGroup(
                    pattern=pattern,
                    errors=matching_errors,
                    confidence=confidence,
                    impact_score=impact_score,
                )
                groups.append(group)

                verbose_debug_print(
                    f"   📦 Created group for {pattern.category}: {len(matching_errors)} errors"
                )

        return groups

    def _rank_error_groups(self, groups: list[ErrorGroup]) -> list[ErrorGroup]:
        """Rank error groups by impact and confidence."""
        verbose_debug_print(
            f"🏆 Ranking {len(groups)} error groups by impact and confidence..."
        )

        def ranking_key(group: ErrorGroup) -> tuple[int, float, int]:
            # Sort by: impact_score (desc), confidence (desc), error_count (desc)
            key = (-group.impact_score, -group.confidence, -group.error_count)
            very_verbose_debug_print(
                f"   📊 {group.pattern.pattern_id}: impact={group.impact_score}, confidence={group.confidence:.2f}, errors={group.error_count}"
            )
            return key

        ranked = sorted(groups, key=ranking_key)

        if ranked:
            debug_print(
                f"🥇 Top ranked group: {ranked[0].pattern.pattern_id} (impact: {ranked[0].impact_score})"
            )
            if len(ranked) > 1:
                debug_print(
                    f"🥈 Second ranked: {ranked[1].pattern.pattern_id} (impact: {ranked[1].impact_score})"
                )

        return ranked

    def _calculate_impact_score(self, errors: list[Error]) -> int:
        """Calculate impact score based on error characteristics."""
        score = len(errors)  # Base score from error count
        very_verbose_debug_print(
            f"     💯 Base score from {len(errors)} errors: {score}"
        )

        # Add weight for unique files affected
        unique_files = len({error.file_path for error in errors if error.file_path})
        file_bonus = unique_files * 2
        score += file_bonus
        very_verbose_debug_print(
            f"     📁 File impact bonus: {unique_files} files × 2 = +{file_bonus}"
        )

        # Add weight for test failures (higher impact)
        test_failures = sum(1 for error in errors if self._is_test_failure(error))
        test_bonus = test_failures * 3
        score += test_bonus
        if test_bonus > 0:
            very_verbose_debug_print(
                f"     🧪 Test failure bonus: {test_failures} failures × 3 = +{test_bonus}"
            )

        # Add weight for critical paths (services, models, etc.)
        critical_files = sum(1 for error in errors if self._is_critical_file(error))
        critical_bonus = critical_files * 2
        score += critical_bonus
        if critical_bonus > 0:
            very_verbose_debug_print(
                f"     🎯 Critical file bonus: {critical_files} files × 2 = +{critical_bonus}"
            )

        very_verbose_debug_print(f"     🏁 Final impact score: {score}")
        return score

    def _generate_summary(
        self,
        primary: ErrorGroup | None,
        secondary: list[ErrorGroup],
        all_errors: list[Error],
    ) -> dict[str, Any]:
        """Generate a summary of the root cause analysis."""
        if not primary:
            return {
                "issue": "No clear pattern identified",
                "total_errors": len(all_errors),
            }

        # Get representative error from primary cause
        primary_error = primary.errors[0] if primary.errors else None

        return {
            "issue": (
                primary.pattern.representative_message[:100] + "..."
                if len(primary.pattern.representative_message) > 100
                else primary.pattern.representative_message
            ),
            "primary_error": self._format_primary_error(primary_error),
            "affected_files": len(primary.affected_files),
            "error_groups": len(secondary) + 1,
            "total_errors": len(all_errors),
            "confidence": primary.confidence,
            "category": primary.pattern.category,
            "severity_score": primary.pattern.severity_score,
            "frequency": primary.pattern.frequency,
        }

    def _generate_fix_suggestions(self, groups: list[ErrorGroup]) -> list[str]:
        """Generate actionable fix suggestions from dynamic patterns."""
        suggestions = []
        verbose_debug_print(
            f"💡 Generating fix suggestions from {len(groups)} error groups..."
        )

        for i, group in enumerate(groups[:3]):  # Top 3 groups only
            very_verbose_debug_print(
                f"   🔍 Processing group #{i + 1}: {group.pattern.category} (confidence: {group.confidence:.2f})"
            )

            # Lower confidence threshold to include single-occurrence critical errors
            min_confidence = 0.3 if group.pattern.frequency == 1 else 0.5

            if group.confidence > min_confidence:
                # Generate fix suggestion based on pattern category and frequency
                suggestion = self._generate_dynamic_fix_suggestion(group)
                if suggestion:
                    suggestions.append(suggestion)
                    debug_print(
                        f"   ✅ Added suggestion for {group.pattern.category}: {suggestion[:50]}..."
                    )
                else:
                    very_verbose_debug_print(
                        f"   ❌ No suggestion generated for {group.pattern.category}"
                    )
            else:
                very_verbose_debug_print(
                    f"   ⚠️ Skipping {group.pattern.category}: confidence too low ({group.confidence:.2f} < {min_confidence})"
                )

        debug_print(f"💡 Generated {len(suggestions)} fix suggestions")
        return suggestions

    def _generate_dynamic_fix_suggestion(self, group: ErrorGroup) -> str | None:
        """Generate fix suggestion based on dynamic pattern analysis."""
        pattern = group.pattern
        category = pattern.category.lower()

        # Generate suggestions based on pattern category
        base_suggestion = ""
        if "import" in category or "module" in category:
            base_suggestion = "Check import statements and module dependencies"
        elif "attribute" in category or "method" in category:
            base_suggestion = "Verify object attributes and method signatures"
        elif "type" in category:
            base_suggestion = "Review data types and type conversions"
        elif "file" in category or "path" in category:
            base_suggestion = "Check file paths and permissions"
        elif "test" in category:
            base_suggestion = "Review test setup and assertions"
        elif "syntax" in category:
            base_suggestion = "Fix syntax errors and code formatting"
        elif "connection" in category:
            base_suggestion = "Check network connectivity and service availability"
        elif "permission" in category:
            base_suggestion = "Verify access permissions and authentication"
        else:
            base_suggestion = "Review error pattern and affected code areas"

        # Add context from the pattern
        if pattern.affected_files:
            files_count = len(pattern.affected_files)
            if files_count == 1:
                file_list = list(pattern.affected_files)
                base_suggestion += f" (affects file: {file_list[0]})"
            else:
                base_suggestion += f" (affects {files_count} files)"

        # Add frequency context with proper grammar
        if pattern.frequency == 1:
            base_suggestion += " - appears once"
        elif pattern.frequency > 1:
            base_suggestion += f" - appears {pattern.frequency} times"

        return base_suggestion

    def _customize_fix_suggestion(self, group: ErrorGroup) -> str | None:
        """Customize fix suggestion based on actual error details."""
        import re

        if not group.errors:
            return None

        template = group.pattern.fix_template
        error = group.errors[0]  # Use first error as representative

        # For DynamicErrorPattern, we don't have regex patterns but we can still extract details
        # Replace placeholders in template with actual values from pattern metadata
        template = template.replace(
            "{affected_files_count}", str(len(group.pattern.affected_files))
        )
        template = template.replace("{frequency}", str(group.pattern.frequency))

        # Try to extract specific details from error message using simple text analysis
        error_message = error.message.lower()

        # Common replacements based on error category and message content
        def safe_replace(
            text: str, placeholder: str, value: str | None, fallback: str
        ) -> str:
            replacement = value if value is not None else fallback
            return text.replace(placeholder, replacement)

        # Extract class/object names (look for patterns like "AttributeError: 'ClassName' object")
        if (
            "object has no attribute" in error_message
            or "attributeerror" in error_message
        ):
            # Try to extract class name from error messages like "'ClassName' object has no attribute"
            class_match = re.search(r"'([^']+)'\s+object", error_message)
            class_name = class_match.group(1) if class_match else None
            template = safe_replace(template, "{class}", class_name, "Object")

            # Extract attribute name
            attr_match = re.search(r"no attribute\s+'([^']+)'", error_message)
            attr_name = attr_match.group(1) if attr_match else None
            template = safe_replace(template, "{attribute}", attr_name, "attribute")

        # Extract method names for method-related errors
        if "method" in error_message:
            method_match = re.search(
                r"method\s+'?([a-zA-Z_][a-zA-Z0-9_]*)'?", error_message
            )
            method_name = method_match.group(1) if method_match else None
            template = safe_replace(template, "{method}", method_name, "method")

        # Extract function names for function-related errors
        if "function" in error_message or "callable" in error_message:
            func_match = re.search(
                r"function\s+'?([a-zA-Z_][a-zA-Z0-9_]*)'?", error_message
            )
            func_name = func_match.group(1) if func_match else None
            template = safe_replace(template, "{function}", func_name, "function")

        # Extract module names for import errors
        if "import" in error_message or "module" in error_message:
            module_match = re.search(
                r"module\s+'?([a-zA-Z_][a-zA-Z0-9_.]*)'?", error_message
            )
            if not module_match:
                module_match = re.search(
                    r"import\s+([a-zA-Z_][a-zA-Z0-9_.]*)", error_message
                )
            module_name = module_match.group(1) if module_match else None
            template = safe_replace(template, "{module}", module_name, "module")

        # Add file context if available
        if error.file_path:
            template += f" (see: {error.file_path}"
            if error.line_number:
                template += f":{error.line_number}"
            template += ")"

        return template

    def _calculate_confidence(self, groups: list[ErrorGroup]) -> float:
        """Calculate overall confidence in the root cause analysis."""
        if not groups:
            return 0.0

        # Weight confidence by group impact
        total_weight = sum(group.impact_score for group in groups)
        if total_weight == 0:
            return 0.0

        weighted_confidence = (
            sum(group.confidence * group.impact_score for group in groups)
            / total_weight
        )

        return weighted_confidence

    def _format_primary_error(self, error: Error | None) -> str:
        """Format the primary error for display."""
        if not error:
            return "No primary error identified"

        location = ""
        if error.file_path:
            file_name = error.file_path.split("/")[-1]  # Just filename
            location = f"{file_name}"
            if error.line_number:
                location += f":{error.line_number}"
            location += " - "

        # Shorten message if too long
        message = error.message
        if len(message) > 100:
            message = message[:97] + "..."

        return f"{location}{message}"

    def _is_test_failure(self, error: Error) -> bool:
        """Check if error represents a test failure."""
        return (
            "test" in error.file_path.lower()
            if error.file_path
            else False or "FAILED" in error.message or "AssertionError" in error.message
        )

    def _is_critical_file(self, error: Error) -> bool:
        """Check if error is in a critical file (services, models, etc.)."""
        if not error.file_path:
            return False

        critical_patterns = ["service", "model", "view", "api", "core"]
        return any(pattern in error.file_path.lower() for pattern in critical_patterns)

    def _create_generic_pattern(self) -> DynamicErrorPattern:
        """Create a generic pattern for when no patterns are found."""
        return DynamicErrorPattern(
            pattern_id="generic_error",
            representative_message="Unclassified error pattern",
            similar_messages=[],
            frequency=0,
            similarity_threshold=0.3,
            category="Unknown",
            affected_files=set(),
            affected_jobs=set(),
            severity_score=0.3,
        )

    def _empty_analysis(self) -> RootCauseAnalysis:
        """Return empty analysis for no errors."""
        empty_group = ErrorGroup(
            pattern=self._create_generic_pattern(),
            errors=[],
            confidence=0.0,
            impact_score=0,
        )

        return RootCauseAnalysis(
            primary_cause=empty_group,
            secondary_causes=[],
            summary={"issue": "No errors to analyze"},
            fix_suggestions=[],
            confidence=0.0,
        )
