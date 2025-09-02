"""
Tests to increase coverage of trace_utils module

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import Mock


class TestTraceUtilsCoverage:
    """Tests to increase coverage of trace_utils module"""

    def test_extract_error_trace_segment(self):
        """Test error trace segment extraction"""
        from gitlab_analyzer.utils.trace_utils import extract_error_trace_segment

        # Create mock error record
        error = Mock()
        error.line = 5

        trace_lines = [
            "Line 1",
            "Line 2",
            "Line 3",
            "Line 4",
            "Line 5 - ERROR HERE",
            "Line 6",
            "Line 7",
            "Line 8",
        ]

        segment_lines, start_line, end_line = extract_error_trace_segment(
            trace_lines, error, context_lines=2
        )

        assert isinstance(segment_lines, list)
        assert isinstance(start_line, int)
        assert isinstance(end_line, int)
        assert len(segment_lines) > 0

    def test_extract_error_trace_segment_no_line(self):
        """Test error trace segment extraction with error that has no line"""
        from gitlab_analyzer.utils.trace_utils import extract_error_trace_segment

        # Create mock error record without line
        error = Mock()
        error.line = None

        trace_lines = ["Line 1", "Line 2", "Line 3"]

        segment_lines, start_line, end_line = extract_error_trace_segment(
            trace_lines, error, context_lines=1
        )

        assert isinstance(segment_lines, list)
        assert isinstance(start_line, int)
        assert isinstance(end_line, int)

    def test_extract_error_trace_segments_batch(self):
        """Test batch error trace segment extraction"""
        from gitlab_analyzer.utils.trace_utils import extract_error_trace_segments_batch

        # Create mock errors
        error1 = Mock()
        error1.line = 2

        error2 = Mock()
        error2.line = 5

        errors = [error1, error2]

        trace_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6"

        segments = extract_error_trace_segments_batch(
            trace_text, errors, context_lines=1
        )

        assert isinstance(segments, list)
        assert len(segments) == 2

        for error_record, segment_text, start_line, end_line in segments:
            assert error_record in errors
            assert isinstance(segment_text, str)
            assert isinstance(start_line, int)
            assert isinstance(end_line, int)

    def test_extract_trace_excerpt_minimal(self):
        """Test trace excerpt extraction in minimal mode"""
        from gitlab_analyzer.utils.trace_utils import extract_trace_excerpt

        trace_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        error_line = 2

        excerpt = extract_trace_excerpt(trace_text, error_line, mode="minimal")

        assert isinstance(excerpt, str)
        assert ">>>" in excerpt  # Should mark the error line
        assert "3:" in excerpt  # Should include line numbers

    def test_extract_trace_excerpt_balanced(self):
        """Test trace excerpt extraction in balanced mode"""
        from gitlab_analyzer.utils.trace_utils import extract_trace_excerpt

        trace_text = "\n".join([f"Line {i}" for i in range(1, 21)])
        error_line = 10

        excerpt = extract_trace_excerpt(trace_text, error_line, mode="balanced")

        assert isinstance(excerpt, str)
        assert ">>>" in excerpt
        assert "11:" in excerpt  # Error line should be marked (0-indexed)

    def test_extract_trace_excerpt_full(self):
        """Test trace excerpt extraction in full mode"""
        from gitlab_analyzer.utils.trace_utils import extract_trace_excerpt

        trace_text = "\n".join([f"Line {i}" for i in range(1, 50)])
        error_line = 25

        excerpt = extract_trace_excerpt(trace_text, error_line, mode="full")

        assert isinstance(excerpt, str)
        assert ">>>" in excerpt
        assert "26:" in excerpt  # Error line (0-indexed)

    def test_extract_trace_excerpt_invalid_mode(self):
        """Test trace excerpt extraction with invalid mode"""
        from gitlab_analyzer.utils.trace_utils import extract_trace_excerpt

        trace_text = "Line 1\nLine 2\nLine 3"
        error_line = 1

        excerpt = extract_trace_excerpt(trace_text, error_line, mode="invalid")

        assert isinstance(excerpt, str)
        # Should default to balanced mode

    def test_extract_trace_excerpt_edge_cases(self):
        """Test trace excerpt extraction edge cases"""
        from gitlab_analyzer.utils.trace_utils import extract_trace_excerpt

        # Test with error line at beginning
        trace_text = "Line 1\nLine 2\nLine 3"
        excerpt = extract_trace_excerpt(trace_text, 0, mode="balanced")
        assert isinstance(excerpt, str)

        # Test with error line at end
        lines = trace_text.split("\n")
        excerpt = extract_trace_excerpt(trace_text, len(lines) - 1, mode="balanced")
        assert isinstance(excerpt, str)

    def test_extract_error_trace_segment_edge_cases(self):
        """Test error trace segment extraction edge cases"""
        from gitlab_analyzer.utils.trace_utils import extract_error_trace_segment

        # Test with error at beginning of trace
        error = Mock()
        error.line = 0

        trace_lines = ["Line 1", "Line 2", "Line 3"]

        segment_lines, start_line, end_line = extract_error_trace_segment(
            trace_lines, error, context_lines=5
        )

        assert isinstance(segment_lines, list)
        assert start_line >= 0

        # Test with error past end of trace
        error.line = 100

        segment_lines, start_line, end_line = extract_error_trace_segment(
            trace_lines, error, context_lines=5
        )

        assert isinstance(segment_lines, list)
        assert end_line <= len(trace_lines)

    def test_extract_error_trace_segments_batch_empty(self):
        """Test batch extraction with empty errors list"""
        from gitlab_analyzer.utils.trace_utils import extract_error_trace_segments_batch

        trace_text = "Line 1\nLine 2\nLine 3"
        errors = []

        segments = extract_error_trace_segments_batch(
            trace_text, errors, context_lines=1
        )

        assert isinstance(segments, list)
        assert len(segments) == 0
