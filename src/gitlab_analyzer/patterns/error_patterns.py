"""
Dynamic error pattern detection for CI/CD failures.
Analyzes actual error messages to identify common patterns and root causes.
"""

import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


@dataclass
class DynamicErrorPattern:
    """Represents a dynamically discovered error pattern."""

    pattern_id: str
    representative_message: str
    similar_messages: list[str]
    frequency: int
    similarity_threshold: float
    category: str
    affected_files: set[str]
    affected_jobs: set[str]
    severity_score: float

    @property
    def name(self) -> str:
        """Get the pattern name (derived from category)."""
        return f"Dynamic {self.category}"

    @property
    def description(self) -> str:
        """Get a description of this pattern."""
        return f"{self.category} pattern found {self.frequency} times: {self.representative_message[:300]}{'...' if len(self.representative_message) > 300 else ''}"

    @property
    def severity(self) -> str:
        """Get severity level based on frequency and impact."""
        if self.frequency >= 5 or self.severity_score >= 0.8:
            return "high"
        elif self.frequency >= 3 or self.severity_score >= 0.6:
            return "medium"
        else:
            return "low"

    @property
    def fix_template(self) -> str:
        """Get a fix template based on the error category."""
        fix_templates = {
            "Attribute/Method Error": "Verify object attributes and method signatures (affects {affected_files_count} files) - appears {frequency} times",
            "Import/Module Error": "Check import statements and module dependencies (affects {affected_files_count} files) - appears {frequency} times",
            "File/Path Error": "Check file paths and permissions (affects {affected_files_count} files) - appears {frequency} times",
            "Syntax Error": "Fix syntax issues in affected files (affects {affected_files_count} files) - appears {frequency} times",
            "Test Failure": "Review and fix failing test cases (affects {affected_files_count} files) - appears {frequency} times",
            "Network/Connection Error": "Check network connectivity and service availability (affects {affected_files_count} files) - appears {frequency} times",
            "Configuration Error": "Verify configuration settings and environment variables (affects {affected_files_count} files) - appears {frequency} times",
            "Permission Error": "Check file and directory permissions (affects {affected_files_count} files) - appears {frequency} times",
            "Timeout Error": "Optimize performance or increase timeout values (affects {affected_files_count} files) - appears {frequency} times",
            "Memory Error": "Optimize memory usage or increase available memory (affects {affected_files_count} files) - appears {frequency} times",
        }

        template = fix_templates.get(
            self.category,
            "Review and fix errors in affected files (affects {affected_files_count} files) - appears {frequency} times",
        )

        # Handle single occurrence vs multiple occurrences
        occurrence_text = (
            "appears once" if self.frequency == 1 else f"appears {self.frequency} times"
        )

        return template.format(
            affected_files_count=len(self.affected_files), frequency=occurrence_text
        )

    @property
    def common_causes(self) -> list[str]:
        """Get common causes for this type of error."""
        causes_map = {
            "Attribute/Method Error": [
                "Missing object attributes after refactoring",
                "Incorrect method signatures",
                "Object type mismatches",
                "API changes not reflected in code",
            ],
            "Import/Module Error": [
                "Missing dependencies in requirements",
                "Incorrect module paths",
                "Python environment issues",
                "Package installation failures",
            ],
            "File/Path Error": [
                "Missing configuration files",
                "Incorrect file paths",
                "File permission issues",
                "Environment-specific file locations",
            ],
            "Syntax Error": [
                "Code formatting issues",
                "Missing parentheses or brackets",
                "Indentation problems",
                "Invalid Python syntax",
            ],
            "Test Failure": [
                "Test data inconsistencies",
                "Environment setup issues",
                "Code changes breaking test assumptions",
                "Mock or fixture problems",
            ],
            "Network/Connection Error": [
                "Service unavailability",
                "Network timeout issues",
                "Authentication failures",
                "DNS resolution problems",
            ],
            "Configuration Error": [
                "Missing environment variables",
                "Incorrect configuration values",
                "Configuration file format issues",
                "Environment-specific settings",
            ],
            "Permission Error": [
                "File system permission issues",
                "User access restrictions",
                "Directory ownership problems",
                "Security policy restrictions",
            ],
            "Timeout Error": [
                "Slow database queries",
                "Network latency issues",
                "Resource contention",
                "Inefficient algorithms",
            ],
            "Memory Error": [
                "Memory leaks",
                "Large data processing",
                "Insufficient system memory",
                "Inefficient memory usage",
            ],
        }

        return causes_map.get(
            self.category,
            [
                "Code quality issues",
                "Environment configuration problems",
                "Dependencies or library issues",
                "Logic or implementation errors",
            ],
        )

    @property
    def is_significant(self) -> bool:
        """Check if this pattern is significant enough to be a root cause."""
        # Include single-occurrence errors if they have high severity or affect critical paths
        if self.frequency >= 1 and self.severity_score > 0.5:
            return True
        # Also include patterns with multiple occurrences even with lower severity
        return self.frequency > 1 and self.severity_score > 0.3


class DynamicErrorPatternMatcher:
    """Analyzes error messages to identify patterns dynamically."""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.patterns: list[DynamicErrorPattern] = []

    def analyze_errors(self, errors: list[Any]) -> list[DynamicErrorPattern]:
        """Analyze a list of errors to identify common patterns."""
        from ..utils.debug import debug_print, verbose_debug_print

        debug_print(f"🔍 Starting dynamic pattern analysis for {len(errors)} errors")

        # Extract error messages and metadata
        error_data = []
        for error in errors:
            message = getattr(error, "message", str(error))
            file_path = getattr(error, "file_path", "")
            job_id = getattr(error, "job_id", "unknown")

            error_data.append(
                {
                    "message": message,
                    "file_path": file_path,
                    "job_id": str(job_id),
                    "original_error": error,
                }
            )

        verbose_debug_print(
            f"📊 Extracted {len(error_data)} error messages for analysis"
        )

        # Group similar error messages
        patterns = self._group_similar_messages(error_data)

        # Analyze patterns for significance
        significant_patterns = []
        for pattern in patterns:
            if pattern.is_significant:
                significant_patterns.append(pattern)
                debug_print(
                    f"✅ Significant pattern found: '{pattern.representative_message[:50]}...' ({pattern.frequency} occurrences)"
                )
            else:
                verbose_debug_print(
                    f"⚠️ Pattern not significant: '{pattern.representative_message[:50]}...' ({pattern.frequency} occurrences)"
                )

        debug_print(
            f"🎯 Identified {len(significant_patterns)} significant patterns from {len(patterns)} total patterns"
        )
        self.patterns = significant_patterns
        return significant_patterns

    def _group_similar_messages(
        self, error_data: list[dict]
    ) -> list[DynamicErrorPattern]:
        """Group similar error messages into patterns."""
        from ..utils.debug import verbose_debug_print, very_verbose_debug_print

        verbose_debug_print("🔗 Grouping similar error messages...")

        # Normalize messages for better matching
        normalized_messages = []
        for data in error_data:
            normalized = self._normalize_message(data["message"])
            normalized_messages.append({**data, "normalized": normalized})

        # Group similar messages
        groups = []
        processed = set()

        for i, data in enumerate(normalized_messages):
            if i in processed:
                continue

            # Start a new group
            group = [data]
            processed.add(i)

            # Find similar messages
            for j, other_data in enumerate(normalized_messages[i + 1 :], i + 1):
                if j in processed:
                    continue

                similarity = self._calculate_similarity(
                    data["normalized"], other_data["normalized"]
                )
                very_verbose_debug_print(
                    f"     📏 Similarity between messages {i} and {j}: {similarity:.2f}"
                )

                if similarity >= self.similarity_threshold:
                    group.append(other_data)
                    processed.add(j)

            if len(group) > 0:
                groups.append(group)
                verbose_debug_print(
                    f"   📦 Created group with {len(group)} similar messages"
                )

        # Convert groups to patterns
        patterns = []
        for group_id, group in enumerate(groups):
            pattern = self._create_pattern_from_group(
                f"dynamic_pattern_{group_id}", group
            )
            patterns.append(pattern)

        return patterns

    def _normalize_message(self, message: str | None) -> str:
        """Normalize error message for better pattern matching."""
        if message is None:
            return ""

        # Remove timestamps, line numbers, and specific values
        normalized = re.sub(r"\d{4}-\d{2}-\d{2}", "[DATE]", message)
        normalized = re.sub(r"\d{2}:\d{2}:\d{2}", "[TIME]", message)
        normalized = re.sub(r"line \d+", "line [NUM]", normalized)
        normalized = re.sub(r":\d+:", ":[NUM]:", normalized)
        normalized = re.sub(r"/[^/\s]+/[^/\s]+/[^/\s]+", "[PATH]", normalized)
        normalized = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "[UUID]",
            normalized,
        )
        normalized = re.sub(r"\b\d+\b", "[NUM]", normalized)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized.lower()

    def _calculate_similarity(self, msg1: str, msg2: str) -> float:
        """Calculate similarity between two normalized messages."""
        from ..utils.debug import very_verbose_debug_print

        very_verbose_debug_print("       Calculating similarity between:")
        very_verbose_debug_print(f"         MSG1: '{msg1[:50]}...'")
        very_verbose_debug_print(f"         MSG2: '{msg2[:50]}...'")

        # Basic check for identical messages
        if msg1 == msg2:
            very_verbose_debug_print("       Identical messages, returning 1.0")
            return 1.0

        # Use sequence matcher for similarity (with safety check)
        try:
            similarity = SequenceMatcher(None, msg1, msg2).ratio()
            very_verbose_debug_print(f"       Base similarity: {similarity:.3f}")
        except Exception as e:
            very_verbose_debug_print(f"       SequenceMatcher error: {e}, using 0.0")
            similarity = 0.0

        # Boost similarity for messages with same exception type
        try:
            exc1 = self._extract_exception_type(msg1)
            exc2 = self._extract_exception_type(msg2)
            if exc1 == exc2 and exc1 != "unknown":
                similarity += 0.1
                very_verbose_debug_print(
                    f"       Exception type bonus: +0.1 (both {exc1})"
                )
        except Exception as e:
            very_verbose_debug_print(f"       Exception type extraction error: {e}")

        # Boost similarity for messages with same key terms
        try:
            key_terms_1 = set(self._extract_key_terms(msg1))
            key_terms_2 = set(self._extract_key_terms(msg2))
            if key_terms_1 and key_terms_2:
                term_overlap = len(key_terms_1 & key_terms_2) / len(
                    key_terms_1 | key_terms_2
                )
                bonus = term_overlap * 0.2
                similarity += bonus
                very_verbose_debug_print(f"       Key terms bonus: +{bonus:.3f}")
        except Exception as e:
            very_verbose_debug_print(f"       Key terms extraction error: {e}")

        final_similarity = min(1.0, similarity)
        very_verbose_debug_print(f"       Final similarity: {final_similarity:.3f}")

        return final_similarity

    def _extract_exception_type(self, message: str) -> str:
        """Extract exception type from error message."""
        # Look for common exception patterns
        patterns = [
            r"(\w+Error):",
            r"(\w+Exception):",
            r"(\w+Warning):",
            r"FAILED.*?(\w+Error)",
            r"(\w+Error)\s",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).lower()

        return "unknown"

    def _extract_key_terms(self, message: str) -> list[str]:
        """Extract key terms from error message."""
        # Remove common words and extract meaningful terms
        common_words = {
            "error",
            "failed",
            "exception",
            "warning",
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "by",
        }

        # Split into words and filter
        words = re.findall(r"\b[a-zA-Z]{3,}\b", message.lower())
        key_terms = [word for word in words if word not in common_words]

        return key_terms[:5]  # Top 5 key terms

    def _create_pattern_from_group(
        self, pattern_id: str, group: list[dict]
    ) -> DynamicErrorPattern:
        """Create a pattern from a group of similar errors."""
        # Choose representative message (shortest or most common)
        messages = [item["message"] for item in group if item["message"]]
        if not messages:
            messages = ["Unknown error"]
        representative = min(
            messages, key=len
        )  # Use shortest message as representative

        # Collect metadata
        affected_files = {item["file_path"] for item in group if item["file_path"]}
        affected_jobs = {item["job_id"] for item in group}

        # Calculate severity based on frequency and affected scope
        frequency = len(group)
        file_diversity = len(affected_files)
        job_diversity = len(affected_jobs)

        # Categorize based on message content (before severity calculation)
        category = self._categorize_pattern(representative)

        # Enhanced severity score: higher for more frequent, more widespread errors
        # Base score from frequency (min 0.4 for single errors to make them significant)
        frequency_score = min(1.0, 0.4 + (frequency - 1) * 0.2)

        # File diversity bonus
        file_bonus = min(0.3, file_diversity * 0.1)

        # Job diversity bonus
        job_bonus = min(0.2, job_diversity * 0.1)

        # Category-based bonus for critical error types
        critical_categories = {
            "Test Error": 0.2,  # Test failures are often critical for CI/CD
            "Import/Module Error": 0.15,
            "Attribute/Method Error": 0.15,
            "Syntax Error": 0.1,
            "Connection Error": 0.1,
        }
        category_bonus = critical_categories.get(category, 0.05)

        severity_score = min(
            1.0, frequency_score + file_bonus + job_bonus + category_bonus
        )

        return DynamicErrorPattern(
            pattern_id=pattern_id,
            representative_message=representative,
            similar_messages=messages,
            frequency=frequency,
            similarity_threshold=self.similarity_threshold,
            category=category,
            affected_files=affected_files,
            affected_jobs=affected_jobs,
            severity_score=severity_score,
        )

    def _categorize_pattern(self, message: str) -> str:
        """Categorize pattern based on message content."""
        message_lower = message.lower()

        if any(term in message_lower for term in ["import", "module", "package"]):
            return "Import/Module Error"
        elif any(term in message_lower for term in ["attribute", "method", "function"]):
            return "Attribute/Method Error"
        elif any(term in message_lower for term in ["type", "convert", "cast"]):
            return "Type Error"
        elif any(term in message_lower for term in ["file", "directory", "path"]):
            return "File/Path Error"
        elif any(term in message_lower for term in ["test", "assert", "expect"]):
            return "Test Error"
        elif any(term in message_lower for term in ["syntax", "parse", "invalid"]):
            return "Syntax Error"
        elif any(
            term in message_lower for term in ["connection", "network", "timeout"]
        ):
            return "Connection Error"
        elif any(
            term in message_lower for term in ["permission", "access", "forbidden"]
        ):
            return "Permission Error"
        else:
            return "Other Error"

    def match_error(self, error_message: str) -> DynamicErrorPattern | None:
        """Find the best matching pattern for an error message."""
        if not self.patterns:
            return None

        best_match = None
        best_similarity = 0.0

        normalized_message = self._normalize_message(error_message)

        for pattern in self.patterns:
            # Check similarity with representative message
            representative_normalized = self._normalize_message(
                pattern.representative_message
            )
            similarity = self._calculate_similarity(
                normalized_message, representative_normalized
            )

            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = pattern

        return best_match

    def get_pattern_insights(self) -> dict[str, Any]:
        """Get insights about discovered patterns."""
        if not self.patterns:
            return {"message": "No patterns analyzed yet"}

        # Sort patterns by significance (frequency * severity)
        sorted_patterns = sorted(
            self.patterns, key=lambda p: p.frequency * p.severity_score, reverse=True
        )

        insights = {
            "total_patterns": len(self.patterns),
            "significant_patterns": len([p for p in self.patterns if p.is_significant]),
            "top_patterns": [
                {
                    "id": p.pattern_id,
                    "category": p.category,
                    "frequency": p.frequency,
                    "severity": p.severity_score,
                    "representative_message": (
                        p.representative_message[:300] + "..."
                        if len(p.representative_message) > 300
                        else p.representative_message
                    ),
                    "affected_files": len(p.affected_files),
                    "affected_jobs": len(p.affected_jobs),
                }
                for p in sorted_patterns[:5]
            ],
            "category_breakdown": self._get_category_breakdown(),
        }

        return insights

    def _get_category_breakdown(self) -> dict[str, int]:
        """Get breakdown of patterns by category."""
        categories = Counter(pattern.category for pattern in self.patterns)
        return dict(categories.most_common())


# Global pattern matcher instance
pattern_matcher = DynamicErrorPatternMatcher()
