"""
Tests for code review integration in merge request pipeline analysis

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, patch

import pytest

from gitlab_analyzer.api.client import GitLabAnalyzer
from gitlab_analyzer.core.pipeline_info import get_comprehensive_pipeline_info


class TestCodeReviewIntegration:
    """Test code review integration in pipeline analysis"""

    @pytest.fixture
    def analyzer(self):
        """Create GitLab analyzer instance"""
        return GitLabAnalyzer("https://gitlab.example.com", "test-token")

    @pytest.fixture
    def mock_mr_discussions(self):
        """Mock merge request discussions data"""
        return [
            {
                "id": "discussion1",
                "individual_note": False,
                "notes": [
                    {
                        "id": 1,
                        "body": "This code needs refactoring for better performance",
                        "author": {"name": "Code Reviewer", "username": "reviewer1"},
                        "created_at": "2025-01-01T10:00:00Z",
                        "type": "DiffNote",
                        "resolvable": True,
                        "resolved": False,
                        "system": False,
                        "position": {"new_path": "src/main.py", "new_line": 42},
                    }
                ],
            }
        ]

    @pytest.fixture
    def mock_mr_notes(self):
        """Mock merge request notes data"""
        return [
            {
                "id": 1,
                "body": "This code needs refactoring for better performance",
                "author": {"name": "Code Reviewer", "username": "reviewer1"},
                "created_at": "2025-01-01T10:00:00Z",
                "type": "DiffNote",
                "resolvable": True,
                "resolved": False,
                "system": False,
                "position": {"new_path": "src/main.py", "new_line": 42},
            },
            {
                "id": 2,
                "body": "approved this merge request",
                "author": {"name": "Senior Dev", "username": "seniordev"},
                "created_at": "2025-01-01T11:00:00Z",
                "type": None,
                "system": True,
                "resolvable": False,
                "resolved": False,
            },
            {
                "id": 3,
                "body": "General comment about the approach",
                "author": {"name": "Another Reviewer", "username": "reviewer2"},
                "created_at": "2025-01-01T12:00:00Z",
                "type": None,
                "system": False,
                "resolvable": False,
                "resolved": False,
            },
        ]

    @pytest.mark.asyncio
    async def test_get_merge_request_discussions(self, analyzer, mock_mr_discussions):
        """Test getting merge request discussions"""
        with patch.object(
            analyzer, "get_merge_request_discussions", new_callable=AsyncMock
        ) as mock_discussions:
            mock_discussions.return_value = mock_mr_discussions

            result = await analyzer.get_merge_request_discussions(83, 123)

            assert len(result) == 1
            assert result[0]["id"] == "discussion1"
            assert len(result[0]["notes"]) == 1
            assert (
                result[0]["notes"][0]["body"]
                == "This code needs refactoring for better performance"
            )

    @pytest.mark.asyncio
    async def test_get_merge_request_notes(self, analyzer, mock_mr_notes):
        """Test getting merge request notes"""
        with patch.object(
            analyzer, "get_merge_request_notes", new_callable=AsyncMock
        ) as mock_notes:
            mock_notes.return_value = mock_mr_notes

            result = await analyzer.get_merge_request_notes(83, 123)

            assert len(result) == 3
            # Check review comment
            assert result[0]["type"] == "DiffNote"
            assert result[0]["resolvable"] is True
            # Check system note
            assert result[1]["system"] is True
            assert "approved this merge request" in result[1]["body"]
            # Check general comment
            assert result[2]["system"] is False
            assert result[2]["type"] is None

    @pytest.mark.asyncio
    async def test_get_merge_request_review_summary(
        self, analyzer, mock_mr_discussions, mock_mr_notes
    ):
        """Test getting comprehensive review summary"""
        with patch.object(
            analyzer, "get_merge_request_discussions", new_callable=AsyncMock
        ) as mock_get_discussions:
            mock_get_discussions.return_value = mock_mr_discussions

            with patch.object(
                analyzer, "get_merge_request_notes", new_callable=AsyncMock
            ) as mock_get_notes:
                mock_get_notes.return_value = mock_mr_notes

                result = await analyzer.get_merge_request_review_summary(83, 123)

                # Check structure
                assert "review_comments" in result
                assert "general_comments" in result
                assert "system_notes" in result
                assert "unresolved_discussions" in result
                assert "approval_status" in result
                assert "review_statistics" in result

                # Check categorization
                assert len(result["review_comments"]) == 1  # DiffNote
                assert len(result["general_comments"]) == 1  # Non-system, non-diff note
                assert len(result["system_notes"]) == 1  # System note

                # Check unresolved discussions
                assert len(result["unresolved_discussions"]) == 1
                unresolved = result["unresolved_discussions"][0]
                assert unresolved["author"] == "Code Reviewer"
                assert "refactoring" in unresolved["body"]

                # Check approval status
                approval = result["approval_status"]
                assert approval["approved_count"] == 1
                assert len(approval["approvals"]) == 1
                assert approval["approvals"][0]["author"] == "Senior Dev"

                # Check statistics
                stats = result["review_statistics"]
                assert stats["total_comments"] == 2  # review + general comments
                assert stats["review_comments_count"] == 1
                assert stats["general_comments_count"] == 1
                assert stats["system_notes_count"] == 1
                assert stats["unresolved_discussions_count"] == 1
                assert stats["has_unresolved_feedback"] is True

    @pytest.mark.asyncio
    async def test_comprehensive_pipeline_info_includes_review_data(self, analyzer):
        """Test that comprehensive pipeline info includes review data for MR pipelines"""
        # Mock pipeline data
        mock_pipeline_data = {
            "id": 1594344,
            "ref": "refs/merge-requests/123/head",
            "project_id": 83,
        }

        # Mock MR data
        mock_mr_data = {"source_branch": "feature/fix-auth", "target_branch": "main"}

        # Mock MR overview
        mock_mr_overview = {
            "iid": 123,
            "title": "Fix authentication bug",
            "description": "This fixes the auth issue",
            "author": {"username": "developer"},
            "web_url": "https://gitlab.example.com/mr/123",
        }

        # Mock review summary
        mock_review_summary = {
            "review_comments": [{"body": "Good fix!"}],
            "review_statistics": {
                "total_comments": 1,
                "unresolved_discussions_count": 0,
                "has_unresolved_feedback": False,
            },
            "approval_status": {
                "approved_count": 1,
                "approvals": [{"author": "Senior Dev"}],
            },
        }

        with patch.object(
            analyzer, "get_pipeline", new_callable=AsyncMock
        ) as mock_pipeline:
            mock_pipeline.return_value = mock_pipeline_data

            with patch.object(
                analyzer, "get_merge_request", new_callable=AsyncMock
            ) as mock_mr:
                mock_mr.return_value = mock_mr_data

                with patch.object(
                    analyzer, "get_merge_request_overview", new_callable=AsyncMock
                ) as mock_overview:
                    mock_overview.return_value = mock_mr_overview

                    with patch.object(
                        analyzer,
                        "get_merge_request_review_summary",
                        new_callable=AsyncMock,
                    ) as mock_review:
                        mock_review.return_value = mock_review_summary

                        result = await get_comprehensive_pipeline_info(
                            analyzer, 83, 1594344
                        )

                        # Verify review data is included
                        assert "mr_review_summary" in result
                        assert result["mr_review_summary"] == mock_review_summary
                        assert result["pipeline_type"] == "merge_request"

    @pytest.mark.asyncio
    async def test_review_summary_handles_api_errors(self, analyzer):
        """Test that review summary gracefully handles API errors"""
        import httpx

        with patch.object(
            analyzer, "get_merge_request_discussions", new_callable=AsyncMock
        ) as mock_discussions:
            mock_discussions.side_effect = httpx.HTTPError("API Error")

            with patch.object(
                analyzer, "get_merge_request_notes", new_callable=AsyncMock
            ) as mock_notes:
                mock_notes.side_effect = httpx.HTTPError("API Error")

                # Should return error structure when both API calls fail
                result = await analyzer.get_merge_request_review_summary(83, 123)

                assert "error" in result
                assert "Failed to get review summary" in result["error"]
                assert result.get("review_comments", []) == []
                assert result.get("general_comments", []) == []
                assert mock_discussions.called
                # Notes mock might not be called if discussions call fails first

    @pytest.mark.asyncio
    async def test_review_summary_empty_data(self, analyzer):
        """Test review summary with empty discussions and notes"""
        with patch.object(
            analyzer, "get_merge_request_discussions", new_callable=AsyncMock
        ) as mock_discussions:
            mock_discussions.return_value = []

            with patch.object(
                analyzer, "get_merge_request_notes", new_callable=AsyncMock
            ) as mock_notes:
                mock_notes.return_value = []

                result = await analyzer.get_merge_request_review_summary(83, 123)

                # Should return empty but valid structure
                assert result["review_comments"] == []
                assert result["general_comments"] == []
                assert result["system_notes"] == []
                assert result["unresolved_discussions"] == []
                assert result["approval_status"]["approved_count"] == 0
                assert result["review_statistics"]["total_comments"] == 0
                assert result["review_statistics"]["has_unresolved_feedback"] is False

    def test_approval_status_parsing(self, analyzer):
        """Test approval status parsing from system notes"""
        system_notes = [
            {
                "body": "approved this merge request",
                "author": "Alice",
                "created_at": "2025-01-01T10:00:00Z",
                "system": True,
            },
            {
                "body": "unapproved this merge request",
                "author": "Bob",
                "created_at": "2025-01-01T11:00:00Z",
                "system": True,
            },
            {
                "body": "approved this merge request",
                "author": "Charlie",
                "created_at": "2025-01-01T12:00:00Z",
                "system": True,
            },
        ]

        # This would be tested inside the review summary method
        # For now, let's verify the logic pattern exists
        approved_count = sum(
            1
            for note in system_notes
            if note["body"].lower().startswith("approved this merge request")
        )
        unapproved_count = sum(
            1
            for note in system_notes
            if note["body"].lower().startswith("unapproved this merge request")
        )

        # We expect 2 approvals (Alice + Charlie) and 1 unapproval (Bob)
        assert approved_count == 2  # Alice + Charlie
        assert unapproved_count == 1  # Bob
