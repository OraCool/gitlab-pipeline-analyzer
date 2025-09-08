"""
Tests for merge request resource functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.resources.merge_request import (
    get_merge_request_resource,
    register_merge_request_resources,
)


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing"""
    manager = Mock()
    manager.get_pipeline_by_mr_iid = AsyncMock()
    return manager


@pytest.fixture
def sample_pipeline_data():
    """Sample pipeline data with MR and review information"""
    review_summary = {
        "review_comments": [
            {
                "id": 1001,
                "body": "This looks good but needs a small fix",
                "author": "reviewer1",
                "created_at": "2025-09-08T10:00:00Z",
                "type": "DiffNote",
                "position": {"new_line": 42, "old_line": None},
            }
        ],
        "general_comments": [
            {
                "id": 1002,
                "body": "Overall implementation looks solid",
                "author": "reviewer2",
                "created_at": "2025-09-08T10:30:00Z",
                "type": "DiscussionNote",
                "system": False,
            }
        ],
        "system_notes": [
            {
                "id": 1003,
                "body": "added 1 commit",
                "author": "system",
                "created_at": "2025-09-08T09:00:00Z",
                "system": True,
            }
        ],
        "unresolved_discussions": [
            {
                "discussion_id": "abc123",
                "created_at": "2025-09-08T10:00:00Z",
                "author": "reviewer1",
                "body": "This needs a fix",
                "notes_count": 2,
            }
        ],
        "approval_status": {
            "approved_count": 1,
            "unapproved_count": 0,
            "approvals": [{"user": "approver1", "created_at": "2025-09-08T11:00:00Z"}],
            "rejections": [],
        },
        "review_statistics": {
            "total_comments": 3,
            "review_comments_count": 1,
            "general_comments_count": 1,
            "system_notes_count": 1,
            "unresolved_discussions_count": 1,
            "has_unresolved_feedback": True,
        },
    }

    return {
        "pipeline_id": 12345,
        "project_id": 83,
        "mr_iid": 567,
        "mr_title": "Fix authentication issues",
        "mr_description": "This MR fixes authentication problems in the Django views",
        "mr_author": "developer1",
        "mr_web_url": "https://gitlab.example.com/project/repo/-/merge_requests/567",
        "source_branch": "fix-auth",
        "target_branch": "main",
        "jira_tickets": '["TICKET-123", "TICKET-456"]',
        "review_summary": json.dumps(review_summary),
        "unresolved_discussions_count": 1,
        "review_comments_count": 1,
        "approval_status": json.dumps(review_summary["approval_status"]),
    }


class TestGetMergeRequestResource:
    """Test the get_merge_request_resource function"""

    @pytest.mark.asyncio
    async def test_successful_mr_retrieval(
        self, mock_cache_manager, sample_pipeline_data
    ):
        """Test successful merge request data retrieval"""
        mock_cache_manager.get_pipeline_by_mr_iid.return_value = sample_pipeline_data

        with patch(
            "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
            return_value=mock_cache_manager,
        ):
            result = await get_merge_request_resource("83", "567")

        # Verify basic structure
        assert "merge_request" in result
        assert "metadata" in result
        assert "mcp_info" in result
        assert "code_review" in result
        assert "jira_tickets" in result

        # Verify merge request info
        mr_info = result["merge_request"]
        assert mr_info["iid"] == 567
        assert mr_info["title"] == "Fix authentication issues"
        assert mr_info["author"] == "developer1"
        assert mr_info["source_branch"] == "fix-auth"
        assert mr_info["target_branch"] == "main"

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["resource_type"] == "merge_request"
        assert metadata["project_id"] == "83"
        assert metadata["mr_iid"] == 567
        assert metadata["data_source"] == "database"
        assert metadata["pipeline_id"] == 12345

        # Verify code review data
        code_review = result["code_review"]
        assert "review_comments" in code_review
        assert "general_comments" in code_review
        assert "unresolved_discussions" in code_review
        assert "approval_status" in code_review
        assert len(code_review["review_comments"]) == 1
        assert len(code_review["unresolved_discussions"]) == 1

        # Verify Jira tickets
        assert result["jira_tickets"] == ["TICKET-123", "TICKET-456"]

        # Verify cache manager was called correctly
        mock_cache_manager.get_pipeline_by_mr_iid.assert_called_once_with(83, 567)

    @pytest.mark.asyncio
    async def test_mr_not_found(self, mock_cache_manager):
        """Test behavior when merge request is not found"""
        mock_cache_manager.get_pipeline_by_mr_iid.return_value = None

        with patch(
            "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
            return_value=mock_cache_manager,
        ):
            result = await get_merge_request_resource("83", "999")

        # Verify error response
        assert result["error"] == "mr_not_analyzed"
        assert "not been analyzed yet" in result["message"]
        assert result["mr_iid"] == 999
        assert result["project_id"] == "83"
        assert result["metadata"]["resource_type"] == "merge_request"
        assert result["metadata"]["data_source"] == "none"
        assert result["metadata"]["status"] == "not_analyzed"

        # Verify cache manager was called
        mock_cache_manager.get_pipeline_by_mr_iid.assert_called_once_with(83, 999)

    @pytest.mark.asyncio
    async def test_mr_without_review_data(self, mock_cache_manager):
        """Test MR retrieval when review data is not available"""
        pipeline_data_no_review = {
            "pipeline_id": 12345,
            "project_id": 83,
            "mr_iid": 567,
            "mr_title": "Basic MR",
            "mr_description": "Simple merge request",
            "mr_author": "developer1",
            "mr_web_url": "https://gitlab.example.com/project/repo/-/merge_requests/567",
            "source_branch": "feature",
            "target_branch": "main",
            "jira_tickets": None,
            "review_summary": None,
        }

        mock_cache_manager.get_pipeline_by_mr_iid.return_value = pipeline_data_no_review

        with patch(
            "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
            return_value=mock_cache_manager,
        ):
            result = await get_merge_request_resource("83", "567")

        # Should have basic MR info but no code review or Jira data
        assert "merge_request" in result
        assert "metadata" in result
        assert "mcp_info" in result
        assert "code_review" not in result
        assert "jira_tickets" not in result

        # Verify basic MR info
        mr_info = result["merge_request"]
        assert mr_info["iid"] == 567
        assert mr_info["title"] == "Basic MR"

    @pytest.mark.asyncio
    async def test_mr_with_invalid_json_review_data(self, mock_cache_manager):
        """Test handling of invalid JSON in review data"""
        pipeline_data_invalid_json = {
            "pipeline_id": 12345,
            "project_id": 83,
            "mr_iid": 567,
            "mr_title": "MR with invalid JSON",
            "mr_description": "Testing invalid JSON handling",
            "mr_author": "developer1",
            "mr_web_url": "https://gitlab.example.com/project/repo/-/merge_requests/567",
            "source_branch": "feature",
            "target_branch": "main",
            "jira_tickets": '["TICKET-123"]',
            "review_summary": "invalid json string {",  # Invalid JSON
        }

        mock_cache_manager.get_pipeline_by_mr_iid.return_value = (
            pipeline_data_invalid_json
        )

        with patch(
            "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
            return_value=mock_cache_manager,
        ):
            result = await get_merge_request_resource("83", "567")

        # Should handle invalid JSON gracefully
        assert "merge_request" in result
        assert "jira_tickets" in result  # Valid JSON should still be parsed
        assert "code_review" not in result  # Invalid JSON should be skipped

    @pytest.mark.asyncio
    async def test_mr_with_review_data_containing_error(self, mock_cache_manager):
        """Test handling when review data contains an error field"""
        review_summary_with_error = {
            "error": "review_fetch_failed",
            "message": "Could not fetch review data",
        }

        pipeline_data_with_error = {
            "pipeline_id": 12345,
            "project_id": 83,
            "mr_iid": 567,
            "mr_title": "MR with review error",
            "mr_description": "Testing error handling",
            "mr_author": "developer1",
            "mr_web_url": "https://gitlab.example.com/project/repo/-/merge_requests/567",
            "source_branch": "feature",
            "target_branch": "main",
            "review_summary": json.dumps(review_summary_with_error),
        }

        mock_cache_manager.get_pipeline_by_mr_iid.return_value = (
            pipeline_data_with_error
        )

        with patch(
            "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
            return_value=mock_cache_manager,
        ):
            result = await get_merge_request_resource("83", "567")

        # Should not include code review data when it contains an error
        assert "merge_request" in result
        assert "code_review" not in result


class TestRegisterMergeRequestResources:
    """Test the resource registration function"""

    def test_resource_registration(self):
        """Test that merge request resources are properly registered"""
        mock_mcp = Mock()
        mock_mcp.resource = Mock()

        # Call the registration function
        register_merge_request_resources(mock_mcp)

        # Verify the resource decorator was called with correct pattern
        mock_mcp.resource.assert_called_once_with("gl://mr/{project_id}/{mr_iid}")

        # Verify the decorator was used (it should have been called as a decorator)
        assert mock_mcp.resource.call_count == 1


class TestMergeRequestResourceIntegration:
    """Integration tests for merge request resource functionality"""

    @pytest.mark.asyncio
    async def test_resource_function_with_mock_mcp(
        self, mock_cache_manager, sample_pipeline_data
    ):
        """Test the actual resource function that would be registered with MCP"""
        mock_cache_manager.get_pipeline_by_mr_iid.return_value = sample_pipeline_data

        # Mock the MCP registration
        mock_mcp = Mock()
        resource_functions = []

        def capture_resource_function(pattern):
            def decorator(func):
                resource_functions.append((pattern, func))
                return func

            return decorator

        mock_mcp.resource = capture_resource_function

        # Register resources
        register_merge_request_resources(mock_mcp)

        # Verify we captured the function
        assert len(resource_functions) == 1
        pattern, resource_func = resource_functions[0]
        assert pattern == "gl://mr/{project_id}/{mr_iid}"

        # Test the actual resource function
        with patch(
            "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
            return_value=mock_cache_manager,
        ):
            result = await resource_func("83", "567")

        # Verify it returns a TextResourceContents object
        assert hasattr(result, "uri")
        assert hasattr(result, "text")
        assert str(result.uri) == "gl://mr/83/567"

        # Verify the text content contains JSON
        content = json.loads(result.text)
        assert "merge_request" in content
        assert content["merge_request"]["iid"] == 567


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_string_project_id_conversion(
        self, mock_cache_manager, sample_pipeline_data
    ):
        """Test that string project IDs are properly converted to integers"""
        mock_cache_manager.get_pipeline_by_mr_iid.return_value = sample_pipeline_data

        with patch(
            "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
            return_value=mock_cache_manager,
        ):
            result = await get_merge_request_resource("83", "567")

        # Verify conversion happened correctly
        mock_cache_manager.get_pipeline_by_mr_iid.assert_called_once_with(83, 567)
        assert (
            result["metadata"]["project_id"] == "83"
        )  # Should remain string in result
        assert result["metadata"]["mr_iid"] == 567  # Should be int in result

    @pytest.mark.asyncio
    async def test_jira_tickets_parsing_error(self, mock_cache_manager):
        """Test handling of invalid Jira tickets JSON"""
        pipeline_data_invalid_jira = {
            "pipeline_id": 12345,
            "project_id": 83,
            "mr_iid": 567,
            "mr_title": "MR with invalid Jira JSON",
            "mr_description": "Testing",
            "mr_author": "developer1",
            "mr_web_url": "https://gitlab.example.com/project/repo/-/merge_requests/567",
            "source_branch": "feature",
            "target_branch": "main",
            "jira_tickets": "invalid json",  # Invalid JSON
        }

        mock_cache_manager.get_pipeline_by_mr_iid.return_value = (
            pipeline_data_invalid_jira
        )

        # Mock the Jira parsing function to simulate error handling
        with (
            patch(
                "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.utils.jira_utils.parse_jira_tickets_from_storage",
                return_value=[],
            ),
        ):
            result = await get_merge_request_resource("83", "567")

        # Should handle invalid Jira JSON gracefully
        assert "merge_request" in result
        # jira_tickets should not be included if parsing returns empty list
        assert "jira_tickets" not in result

    @pytest.mark.asyncio
    async def test_cache_manager_exception(self, mock_cache_manager):
        """Test handling of cache manager exceptions"""
        mock_cache_manager.get_pipeline_by_mr_iid.side_effect = Exception(
            "Database error"
        )

        with (
            patch(
                "gitlab_analyzer.mcp.resources.merge_request.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            pytest.raises(Exception, match="Database error"),
        ):
            await get_merge_request_resource("83", "567")


if __name__ == "__main__":
    pytest.main([__file__])
