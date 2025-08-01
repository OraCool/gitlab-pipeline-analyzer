#!/usr/bin/env python3
"""
Test runner script for MCP server tests

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import os
import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all tests for the MCP server"""
    # Change to the project root directory
    project_root = Path(__file__).parent.resolve()
    os.chdir(project_root)

    print("🚀 Running MCP Server Tests")
    print("=" * 50)

    # Check if pytest is available
    try:
        import pytest

        print("✅ pytest is available")
    except ImportError:
        print("❌ pytest not found. Installing pytest...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"],
            check=True,
        )
        import pytest

    # Run tests with pytest
    test_args = [
        "-v",  # verbose output
        "--tb=short",  # shorter traceback format
        "tests/",  # test directory
        "--asyncio-mode=auto",  # enable asyncio support
    ]

    print("\n🧪 Running tests...")
    print("-" * 30)

    result = pytest.main(test_args)

    if result == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {result}")

    return result


def run_coverage():
    """Run tests with coverage reporting"""
    print("\n📊 Running tests with coverage...")
    print("-" * 40)

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=gitlab_analyzer",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "tests/",
            ],
            check=True,
        )
        print("✅ Coverage report generated in htmlcov/")
    except subprocess.CalledProcessError as e:
        print(f"❌ Coverage run failed: {e}")
        return 1
    except FileNotFoundError:
        print("⚠️  pytest-cov not found. Install with: pip install pytest-cov")
        return 1

    return 0


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--coverage":
        return run_coverage()
    else:
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())
