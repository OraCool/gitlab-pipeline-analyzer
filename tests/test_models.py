"""
Tests for data models

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.models import JobInfo, LogEntry


class TestJobInfo:
    """Test JobInfo model"""

    def test_job_info_creation(self):
        """Test creating a JobInfo instance"""
        job = JobInfo(
            id=1001,
            name="test-job",
            status="failed",
            stage="test",
            created_at="2025-01-01T10:00:00.000Z",
            started_at="2025-01-01T10:01:00.000Z",
            finished_at="2025-01-01T10:05:00.000Z",
            failure_reason="script_failure",
            web_url="https://gitlab.example.com/project/-/jobs/1001",
        )

        assert job.id == 1001
        assert job.name == "test-job"
        assert job.status == "failed"
        assert job.stage == "test"
        assert job.web_url == "https://gitlab.example.com/project/-/jobs/1001"

    def test_job_info_with_optional_fields(self):
        """Test creating JobInfo with optional fields as None"""
        job = JobInfo(
            id=1002,
            name="build-job",
            status="success",
            stage="build",
            created_at="2025-01-01T10:00:00.000Z",
            started_at=None,
            finished_at=None,
            failure_reason=None,
            web_url="https://gitlab.example.com/project/-/jobs/1002",
        )

        assert job.id == 1002
        assert job.name == "build-job"
        assert job.status == "success"
        assert job.started_at is None
        assert job.finished_at is None

    def test_job_info_serialization(self):
        """Test JobInfo serialization to dict"""
        job = JobInfo(
            id=1003,
            name="deploy-job",
            status="running",
            stage="deploy",
            created_at="2025-01-01T10:00:00.000Z",
            started_at="2025-01-01T10:01:00.000Z",
            finished_at=None,
            failure_reason=None,
            web_url="https://gitlab.example.com/project/-/jobs/1003",
        )

        job_dict = job.dict()

        assert isinstance(job_dict, dict)
        assert job_dict["id"] == 1003
        assert job_dict["name"] == "deploy-job"
        assert job_dict["status"] == "running"
        assert job_dict["stage"] == "deploy"
        assert job_dict["finished_at"] is None

    def test_job_info_from_dict(self):
        """Test creating JobInfo from dictionary data"""
        job_data = {
            "id": 1004,
            "name": "integration-test",
            "status": "failed",
            "stage": "test",
            "created_at": "2025-01-01T10:00:00.000Z",
            "started_at": "2025-01-01T10:01:00.000Z",
            "finished_at": "2025-01-01T10:15:00.000Z",
            "failure_reason": "script_failure",
            "web_url": "https://gitlab.example.com/project/-/jobs/1004",
        }

        job = JobInfo(**job_data)

        assert job.id == 1004
        assert job.name == "integration-test"
        assert job.status == "failed"


class TestLogEntry:
    """Test LogEntry model"""

    def test_log_entry_creation(self):
        """Test creating a LogEntry instance"""
        entry = LogEntry(
            level="error",
            message="npm ERR! code ENOENT",
            line_number=42,
            timestamp="2025-01-01T10:00:00.000Z",
        )

        assert entry.level == "error"
        assert entry.message == "npm ERR! code ENOENT"
        assert entry.line_number == 42
        assert isinstance(entry.timestamp, str)

    def test_log_entry_with_warning_level(self):
        """Test creating LogEntry with warning level"""
        entry = LogEntry(
            level="warning",
            message="npm WARN deprecated package@1.0.0",
            line_number=15,
            timestamp="2025-01-01T10:00:00.000Z",
        )

        assert entry.level == "warning"
        assert entry.message == "npm WARN deprecated package@1.0.0"
        assert entry.line_number == 15

    def test_log_entry_serialization(self):
        """Test LogEntry serialization to dict"""
        timestamp = "2025-01-01T10:00:00.000Z"
        entry = LogEntry(
            level="error", message="Build failed", line_number=100, timestamp=timestamp
        )

        entry_dict = entry.dict()

        assert isinstance(entry_dict, dict)
        assert entry_dict["level"] == "error"
        assert entry_dict["message"] == "Build failed"
        assert entry_dict["line_number"] == 100
        assert entry_dict["timestamp"] == timestamp

    def test_log_entry_with_context(self):
        """Test LogEntry with additional context"""
        entry = LogEntry(
            level="error",
            message="TypeError: Cannot read property 'length' of undefined",
            line_number=25,
            timestamp="2025-01-01T10:00:00.000Z",
            context="src/utils.test.js",
        )

        assert entry.level == "error"
        assert "TypeError" in entry.message
        assert entry.line_number == 25
        assert hasattr(entry, "context")

    def test_log_entry_validation(self):
        """Test LogEntry validation"""
        # Valid levels should work
        valid_entry = LogEntry(
            level="error",
            message="Test error",
            line_number=1,
            timestamp="2025-01-01T10:00:00.000Z",
        )
        assert valid_entry.level == "error"

        valid_warning = LogEntry(
            level="warning",
            message="Test warning",
            line_number=1,
            timestamp="2025-01-01T10:00:00.000Z",
        )
        assert valid_warning.level == "warning"

    def test_log_entry_from_dict(self):
        """Test creating LogEntry from dictionary"""
        timestamp = "2025-01-01T10:00:00.000Z"
        entry_data = {
            "level": "error",
            "message": "Compilation failed",
            "line_number": 55,
            "timestamp": timestamp,
        }

        entry = LogEntry(**entry_data)

        assert entry.level == "error"
        assert entry.message == "Compilation failed"
        assert entry.line_number == 55
        assert entry.timestamp == timestamp
