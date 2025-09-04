"""
Tests for Jira ticket extraction utilities

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.utils.jira_utils import (
    extract_jira_from_mr,
    extract_jira_tickets,
    format_jira_tickets_for_storage,
    parse_jira_tickets_from_storage,
    validate_jira_ticket_format,
)


class TestJiraTicketExtraction:
    """Test Jira ticket extraction from text"""

    def test_extract_basic_ticket_format(self):
        """Test extraction of basic PROJ-123 format"""
        text = "This is a fix for PROJ-123 issue"
        tickets = extract_jira_tickets(text)
        assert tickets == ["PROJ-123"]

    def test_extract_multiple_tickets(self):
        """Test extraction of multiple tickets"""
        text = "Fix for PROJ-123 and PROJ-124, also addresses TEST-456"
        tickets = extract_jira_tickets(text)
        assert tickets == ["PROJ-123", "PROJ-124", "TEST-456"]

    def test_extract_bracketed_tickets(self):
        """Test extraction of bracketed tickets [PROJ-123]"""
        text = "This fixes [PROJ-123] and (TEST-456)"
        tickets = extract_jira_tickets(text)
        assert tickets == ["PROJ-123", "TEST-456"]

    def test_extract_hash_prefixed_tickets(self):
        """Test extraction of hash-prefixed tickets #PROJ-123"""
        text = "Closing #PROJ-123 and resolving TASK-789:"
        tickets = extract_jira_tickets(text)
        assert tickets == ["PROJ-123", "TASK-789"]

    def test_case_insensitive_extraction(self):
        """Test that extraction is case insensitive but normalizes to uppercase"""
        text = "Fix for proj-123 and TEST-456"
        tickets = extract_jira_tickets(text)
        assert tickets == ["PROJ-123", "TEST-456"]

    def test_duplicate_removal(self):
        """Test that duplicate tickets are removed"""
        text = "PROJ-123 and PROJ-123 again, plus proj-123 once more"
        tickets = extract_jira_tickets(text)
        assert tickets == ["PROJ-123"]

    def test_invalid_formats_ignored(self):
        """Test that invalid formats are ignored"""
        text = "A-1 X-12345678901 TOOLONG-123 123-456"
        tickets = extract_jira_tickets(text)
        assert tickets == []

    def test_empty_text(self):
        """Test handling of empty text"""
        assert extract_jira_tickets("") == []
        assert extract_jira_tickets(None) == []

    def test_no_tickets_found(self):
        """Test when no tickets are found"""
        text = "This is just regular text with no tickets"
        tickets = extract_jira_tickets(text)
        assert tickets == []

    def test_project_key_boundaries(self):
        """Test project key length boundaries"""
        text = "AB-123 ABCDEF-456 A-789"  # 2, 6, 1 letter keys
        tickets = extract_jira_tickets(text)
        assert tickets == [
            "AB-123",
            "ABCDEF-456",
        ]  # A-789 should be rejected (too short)


class TestJiraFromMR:
    """Test Jira extraction from merge request data"""

    def test_extract_from_title(self):
        """Test extraction from MR title"""
        mr_data = {
            "title": "Fix bug PROJ-123: Database connection issue",
            "description": "",
            "labels": [],
        }
        tickets = extract_jira_from_mr(mr_data)
        assert tickets == ["PROJ-123"]

    def test_extract_from_description(self):
        """Test extraction from MR description"""
        mr_data = {
            "title": "Bug fix",
            "description": "This MR fixes PROJ-456 and addresses TEST-789",
            "labels": [],
        }
        tickets = extract_jira_from_mr(mr_data)
        assert tickets == ["PROJ-456", "TEST-789"]

    def test_extract_from_labels(self):
        """Test extraction from MR labels"""
        mr_data = {
            "title": "Feature",
            "description": "New feature",
            "labels": ["PROJ-999", "enhancement", "TASK-111"],
        }
        tickets = extract_jira_from_mr(mr_data)
        assert tickets == ["PROJ-999", "TASK-111"]

    def test_extract_from_all_sources(self):
        """Test extraction from all sources combined"""
        mr_data = {
            "title": "Fix PROJ-123",
            "description": "Resolves TEST-456",
            "labels": ["TASK-789", "bug"],
        }
        tickets = extract_jira_from_mr(mr_data)
        assert tickets == ["PROJ-123", "TASK-789", "TEST-456"]

    def test_missing_fields(self):
        """Test handling of missing fields"""
        mr_data = {}
        tickets = extract_jira_from_mr(mr_data)
        assert tickets == []

    def test_none_values(self):
        """Test handling of None values"""
        mr_data = {"title": None, "description": None, "labels": None}
        tickets = extract_jira_from_mr(mr_data)
        assert tickets == []


class TestJiraStorage:
    """Test Jira ticket storage and parsing"""

    def test_format_for_storage(self):
        """Test formatting tickets for storage"""
        tickets = ["PROJ-123", "TEST-456"]
        result = format_jira_tickets_for_storage(tickets)
        assert result == '["PROJ-123", "TEST-456"]'

    def test_format_empty_list(self):
        """Test formatting empty list"""
        result = format_jira_tickets_for_storage([])
        assert result == "[]"

    def test_format_none(self):
        """Test formatting None"""
        result = format_jira_tickets_for_storage(None)
        assert result == "[]"

    def test_parse_from_storage(self):
        """Test parsing tickets from storage"""
        json_str = '["PROJ-123", "TEST-456"]'
        tickets = parse_jira_tickets_from_storage(json_str)
        assert tickets == ["PROJ-123", "TEST-456"]

    def test_parse_empty_storage(self):
        """Test parsing empty storage"""
        assert parse_jira_tickets_from_storage("[]") == []
        assert parse_jira_tickets_from_storage("") == []
        assert parse_jira_tickets_from_storage(None) == []

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        result = parse_jira_tickets_from_storage("invalid json")
        assert result == []

    def test_roundtrip_storage(self):
        """Test roundtrip storage and parsing"""
        original_tickets = ["PROJ-123", "TEST-456", "TASK-789"]
        stored = format_jira_tickets_for_storage(original_tickets)
        parsed = parse_jira_tickets_from_storage(stored)
        assert parsed == original_tickets


class TestJiraValidation:
    """Test Jira ticket format validation"""

    def test_valid_tickets(self):
        """Test validation of valid tickets"""
        valid_tickets = ["PROJ-123", "AB-1", "ABCDEF-12345678"]
        for ticket in valid_tickets:
            assert validate_jira_ticket_format(ticket), f"{ticket} should be valid"

    def test_invalid_tickets(self):
        """Test validation of invalid tickets"""
        invalid_tickets = [
            "A-123",  # Project key too short
            "ABCDEFG-123",  # Project key too long
            "PROJ-",  # No issue number
            "PROJ-123456789",  # Issue number too long
            "-123",  # No project key
            "PROJ123",  # Missing dash
            "proj-123",  # Lowercase
            "",  # Empty
            None,  # None
        ]
        for ticket in invalid_tickets:
            assert not validate_jira_ticket_format(ticket), (
                f"{ticket} should be invalid"
            )

    def test_case_normalization(self):
        """Test case normalization during extraction (not validation)"""
        # Extraction should normalize to uppercase
        text = "proj-123 and TEST-456"
        tickets = extract_jira_tickets(text)
        assert tickets == ["PROJ-123", "TEST-456"]

        # But validation requires uppercase
        assert validate_jira_ticket_format("PROJ-123")  # Should pass
        assert not validate_jira_ticket_format("proj-123")  # Should fail
