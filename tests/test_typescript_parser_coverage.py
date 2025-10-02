"""Coverage improvement tests for TypeScript parser."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gitlab_analyzer.parsers.typescript_parser import TypeScriptParser


class TestTypeScriptParserCoverage:
    """Test TypeScript parser to improve coverage."""

    def test_import(self):
        """Test module can be imported."""
        assert TypeScriptParser is not None

    def test_parser_creation(self):
        """Test TypeScript parser can be created."""
        parser = TypeScriptParser()
        assert parser is not None

    def test_basic_parsing(self):
        """Test basic TypeScript error parsing."""
        parser = TypeScriptParser()

        # Test with TypeScript compilation error
        trace_content = """
        error TS2322: Type 'string' is not assignable to type 'number'.
        src/utils/math.ts(42,15): error TS2345: Argument of type 'string' is not assignable to parameter of type 'number'
        """

        result = parser.parse(trace_content)
        assert isinstance(result, dict)
        assert "error_count" in result
        assert "errors" in result

    def test_empty_trace(self):
        """Test parsing empty trace content."""
        parser = TypeScriptParser()
        result = parser.parse("")
        assert isinstance(result, dict)
        assert result["error_count"] == 0
        assert result["errors"] == []

    def test_no_typescript_errors(self):
        """Test parsing trace with no TypeScript errors."""
        parser = TypeScriptParser()
        trace_content = "Build successful! No errors found."
        result = parser.parse(trace_content)
        assert isinstance(result, dict)
        assert result["error_count"] == 0
