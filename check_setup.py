#!/usr/bin/env python3
"""
Quick test script to verify MCP client functionality

Run this to test if your environment is set up correctly
for using the GitLab Job Result Analyzer MCP client.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License
"""

import os
from pathlib import Path


def check_environment():
    """Check if environment is properly configured"""
    print("🔍 GitLab Job Result Analyzer - Environment Check")
    print("=" * 50)

    # Check environment variables
    gitlab_url = os.getenv("GITLAB_URL")
    gitlab_token = os.getenv("GITLAB_TOKEN")

    print("📋 Environment Variables:")
    if gitlab_url:
        print(f"   ✅ GITLAB_URL: {gitlab_url}")
    else:
        print("   ❌ GITLAB_URL: Not set")

    if gitlab_token:
        token_preview = (
            f"{'*' * 8}...{gitlab_token[-4:]}"
            if len(gitlab_token) > 12
            else "*" * len(gitlab_token)
        )
        print(f"   ✅ GITLAB_TOKEN: {token_preview}")
    else:
        print("   ❌ GITLAB_TOKEN: Not set")

    # Check server script
    server_script = Path("server.py")
    print(f"\n📄 MCP Server Script:")
    if server_script.exists():
        print(f"   ✅ server.py: Found ({server_script.stat().st_size} bytes)")
    else:
        print("   ❌ server.py: Not found")

    # Check Python dependencies
    print(f"\n📦 Python Dependencies:")
    try:
        import fastmcp

        print(f"   ✅ fastmcp: {fastmcp.__version__}")
    except ImportError:
        print("   ❌ fastmcp: Not installed")

    # Overall status
    print(f"\n🎯 Overall Status:")
    if gitlab_url and gitlab_token and server_script.exists():
        print("   ✅ Ready to use GitLab Job Result Analyzer!")
        print("\n📚 Next steps:")
        print("   1. Try: python get_job_result.py --help")
        print(
            "   2. Example: python get_job_result.py --project-id YOUR_PROJECT_ID --pipeline-id YOUR_PIPELINE_ID --status-only"
        )
        print("   3. See CLIENT_README.md for full documentation")
        return True
    else:
        print("   ❌ Environment not ready")
        print("\n🔧 Required setup:")
        if not gitlab_url:
            print("   - Set GITLAB_URL environment variable")
        if not gitlab_token:
            print("   - Set GITLAB_TOKEN environment variable")
        if not server_script.exists():
            print("   - Ensure server.py exists in current directory")
        return False


def show_usage_examples():
    """Show usage examples"""
    print("\n📖 Usage Examples:")
    print("-" * 30)

    examples = [
        (
            "Analyze a single job",
            "python get_job_result.py --project-id 12345 --job-id 67890",
        ),
        (
            "Get pipeline status",
            "python get_job_result.py --project-id 12345 --pipeline-id 11111 --status-only",
        ),
        (
            "Analyze failed pipeline",
            "python get_job_result.py --project-id 12345 --pipeline-id 11111 --analyze-failures",
        ),
        (
            "Get failed jobs only",
            "python get_job_result.py --project-id 12345 --pipeline-id 11111 --failed-jobs-only",
        ),
        (
            "Output as JSON",
            "python get_job_result.py --project-id 12345 --job-id 67890 --json",
        ),
    ]

    for description, command in examples:
        print(f"\n{description}:")
        print(f"   {command}")


def main():
    """Main function"""
    ready = check_environment()

    if ready:
        show_usage_examples()

    print("\n" + "=" * 50)
    print("For full documentation, see CLIENT_README.md")


if __name__ == "__main__":
    main()
