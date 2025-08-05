#!/usr/bin/env python3
"""Check the log analysis results to see what errors remain."""

from pathlib import Path

from src.gitlab_analyzer.parsers.log_parser import LogParser


def main():
    log_file = "log-examples/pytest_with_failures.log"
    parser = LogParser()

    with Path(log_file).open(encoding="utf-8") as f:
        content = f.read()

    entries = parser.extract_log_entries(content)

    print("=== ALL LOG ENTRIES ===")
    for i, entry in enumerate(entries, 1):
        print(f"{i}. {entry.level.upper()}: {entry.message}")
        if hasattr(entry, "line_number") and entry.line_number:
            print(f"   Line: {entry.line_number}")
        print()

    print(f"\nTotal entries: {len(entries)}")

    # Check for specific patterns
    print("\n=== ANALYSIS ===")
    test_failures = [
        e for e in entries if "test_" in e.message and "in test_" in e.message
    ]
    general_errors = [e for e in entries if e not in test_failures]

    print(f"Test failures: {len(test_failures)}")
    for tf in test_failures:
        print(f"  - {tf.message}")

    print(f"\nGeneral errors: {len(general_errors)}")
    for ge in general_errors:
        print(f"  - {ge.message}")


if __name__ == "__main__":
    main()
