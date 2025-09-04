"""
Jira ticket extraction utilities for GitLab merge requests.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re
from typing import Any


def extract_jira_tickets(text: str) -> list[str]:
    """
    Extract Jira ticket references from text.

    Supports common Jira ticket formats:
    - PROJ-123
    - [PROJ-123]
    - (PROJ-123)
    - PROJ-123:
    - #PROJ-123

    Args:
        text: Text to search for Jira tickets

    Returns:
        List of unique Jira ticket IDs found in the text
    """
    if not text:
        return []

    # Pattern for Jira tickets: PROJECT-NUMBER
    # Supports: PROJ-123, [PROJ-123], (PROJ-123), PROJ-123:, #PROJ-123
    # Project key: 2-6 uppercase letters (standard Jira limit)
    # Issue number: 1-8 digits
    patterns = [
        r"\b([A-Z]{2,6}-\d{1,8})\b",  # Basic format: PROJ-123
        r"\[([A-Z]{2,6}-\d{1,8})\]",  # Bracketed: [PROJ-123]
        r"\(([A-Z]{2,6}-\d{1,8})\)",  # Parentheses: (PROJ-123)
        r"#([A-Z]{2,6}-\d{1,8})\b",  # Hash prefixed: #PROJ-123
        r"\b([A-Z]{2,6}-\d{1,8}):",  # Colon suffixed: PROJ-123:
    ]

    tickets = set()

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            ticket = match.group(1).upper()  # Normalize to uppercase
            tickets.add(ticket)

    return sorted(tickets)


def extract_jira_from_mr(mr_data: dict[str, Any]) -> list[str]:
    """
    Extract Jira tickets from merge request data.

    Searches in:
    - Title
    - Description
    - Labels (if they contain Jira patterns)

    Args:
        mr_data: Merge request data from GitLab API

    Returns:
        List of unique Jira ticket IDs found in the MR
    """
    tickets = set()

    # Extract from title
    title = mr_data.get("title", "")
    if title:
        tickets.update(extract_jira_tickets(title))

    # Extract from description
    description = mr_data.get("description", "")
    if description:
        tickets.update(extract_jira_tickets(description))

    # Extract from labels (some teams put Jira tickets in labels)
    labels = mr_data.get("labels", [])
    if labels:
        for label in labels:
            if isinstance(label, str):
                tickets.update(extract_jira_tickets(label))

    return sorted(tickets)


def format_jira_tickets_for_storage(tickets: list[str]) -> str:
    """
    Format Jira tickets for database storage as JSON string.

    Args:
        tickets: List of Jira ticket IDs

    Returns:
        JSON string representation of the tickets list
    """
    import json

    return json.dumps(tickets) if tickets else "[]"


def parse_jira_tickets_from_storage(tickets_json: str) -> list[str]:
    """
    Parse Jira tickets from database storage JSON string.

    Args:
        tickets_json: JSON string of tickets from database

    Returns:
        List of Jira ticket IDs
    """
    import json

    if not tickets_json:
        return []

    try:
        tickets = json.loads(tickets_json)
        if isinstance(tickets, list):
            return [str(ticket) for ticket in tickets]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def validate_jira_ticket_format(ticket: str) -> bool:
    """
    Validate if a string matches standard Jira ticket format.

    Args:
        ticket: Ticket string to validate

    Returns:
        True if ticket matches Jira format, False otherwise
    """
    if not ticket:
        return False

    # Only accept uppercase format for validation
    pattern = r"^[A-Z]{2,6}-\d{1,8}$"
    return bool(re.match(pattern, ticket))
