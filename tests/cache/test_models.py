"""
Tests for cache models

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import UTC, datetime

from gitlab_analyzer.mcp.cache.models import (
    CacheData,
    CacheEntry,
    CacheStats,
    generate_cache_key,
    generate_error_id,
)


class TestCacheEntry:
    """Test CacheEntry dataclass"""

    def test_cache_entry_creation(self):
        """Test creating a cache entry"""
        entry = CacheEntry(key="test-key", data_type="pipeline", project_id="123")

        assert entry.key == "test-key"
        assert entry.data_type == "pipeline"
        assert entry.project_id == "123"
        assert entry.created_at is not None
        assert isinstance(entry.created_at, datetime)

    def test_cache_entry_with_all_fields(self):
        """Test creating a cache entry with all fields"""
        created_at = datetime.now(UTC)
        entry = CacheEntry(
            key="test-key",
            data_type="job",
            project_id="456",
            pipeline_id=789,
            job_id=101112,
            file_path="test/file.py",
            parser_type="pytest",
            created_at=created_at,
            data_size=1024,
        )

        assert entry.pipeline_id == 789
        assert entry.job_id == 101112
        assert entry.file_path == "test/file.py"
        assert entry.parser_type == "pytest"
        assert entry.created_at == created_at
        assert entry.data_size == 1024


class TestCacheStats:
    """Test CacheStats dataclass"""

    def test_cache_stats_creation(self):
        """Test creating cache stats"""
        stats = CacheStats(
            total_entries=10,
            total_size_bytes=5000,
            entries_by_type={"pipeline": 5, "job": 5},
            oldest_entry=datetime.now(UTC),
            newest_entry=datetime.now(UTC),
        )

        assert stats.total_entries == 10
        assert stats.total_size_bytes == 5000
        assert stats.entries_by_type["pipeline"] == 5


class TestCacheData:
    """Test CacheData serialization"""

    def test_serialize_deserialize(self):
        """Test data serialization and deserialization"""
        data = {
            "test": "value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        # Serialize
        serialized = CacheData.serialize(data)
        assert isinstance(serialized, str)

        # Deserialize
        deserialized = CacheData.deserialize(serialized)
        assert deserialized == data

    def test_calculate_size(self):
        """Test size calculation"""
        data = {"test": "value", "number": 42}
        size = CacheData.calculate_size(data)

        # Should be positive and reasonable
        assert size > 0
        assert size < 1000  # Simple data shouldn't be too large

    def test_unicode_handling(self):
        """Test unicode character handling"""
        data = {"unicode": "тест", "emoji": "🚀", "chinese": "测试"}

        serialized = CacheData.serialize(data)
        deserialized = CacheData.deserialize(serialized)

        assert deserialized == data


class TestGenerateCacheKey:
    """Test cache key generation"""

    def test_basic_key_generation(self):
        """Test basic cache key generation"""
        key = generate_cache_key("pipeline", "123", pipeline_id=456)
        assert key == "gl:pipeline:123:456"

    def test_key_with_job(self):
        """Test cache key with job ID"""
        key = generate_cache_key("job", "123", job_id=789)
        assert key == "gl:job:123:789"

    def test_key_with_file_path(self):
        """Test cache key with file path (should be hashed)"""
        key = generate_cache_key(
            "file_errors", "123", job_id=456, file_path="very/long/path/to/file.py"
        )

        assert key.startswith("gl:file_errors:123:456:")
        assert len(key.split(":")[-1]) == 12  # Hash should be 12 chars

    def test_key_with_kwargs(self):
        """Test cache key with additional parameters"""
        key = generate_cache_key(
            "analysis",
            "123",
            pipeline_id=456,
            parser_type="pytest",
            include_traces=True,
        )

        # Should include sorted kwargs
        assert "include_traces:True" in key
        assert "parser_type:pytest" in key


class TestGenerateErrorId:
    """Test error ID generation"""

    def test_basic_error_id(self):
        """Test basic error ID generation"""
        error_id = generate_error_id(
            "TypeError", "Function signature mismatch", "test/file.py"
        )

        assert isinstance(error_id, str)
        assert len(error_id) == 12

    def test_error_id_with_line_number(self):
        """Test error ID with line number"""
        error_id = generate_error_id(
            "TypeError", "Function signature mismatch", "test/file.py", line_number=45
        )

        assert isinstance(error_id, str)
        assert len(error_id) == 12

    def test_error_id_consistency(self):
        """Test that same inputs generate same error ID"""
        error_id1 = generate_error_id(
            "TypeError", "Function signature mismatch", "test/file.py", line_number=45
        )

        error_id2 = generate_error_id(
            "TypeError", "Function signature mismatch", "test/file.py", line_number=45
        )

        assert error_id1 == error_id2

    def test_error_id_different_inputs(self):
        """Test that different inputs generate different error IDs"""
        error_id1 = generate_error_id(
            "TypeError", "Function signature mismatch", "test/file.py"
        )

        error_id2 = generate_error_id(
            "ValueError", "Function signature mismatch", "test/file.py"
        )

        assert error_id1 != error_id2
