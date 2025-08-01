#!/usr/bin/env python3
"""
GitLab Job Result Analyzer

This script uses FastMCP client to connect to        client = Client(self.server_script)
        async with client:
            result = await client.call_tool(
                "get_pipeline_status", {"project_id": str(project_id), "pipeline_id": pipeline_id}
            )
            return self._extract_result(result)itLab Pipeline Analyzer MCP server
and retrieve job results, analyze failed pipelines, and extract errors/warnings.

Usage:
    python get_job_result.py --project-id 12345 --job-id 67890
    python get_job_result.py --project-id 12345 --pipeline-id 11111 --analyze-failures
    python get_job_result.py --help

Requirements:
    - fastmcp>=2.0.0
    - Set GITLAB_URL and GITLAB_TOKEN environment variables
    - MCP server script (server.py) should be available

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if available
except ImportError:
    pass  # python-dotenv not installed, use environment variables directly

from fastmcp import Client


class JobResultAnalyzer:
    """GitLab Job Result Analyzer using FastMCP client"""

    def __init__(self, server_script: str = "server.py"):
        """
        Initialize the analyzer with MCP server script path

        Args:
            server_script: Path to the MCP server script
        """
        self.server_script = server_script
        self._validate_environment()

    def _extract_result(self, mcp_result):
        """Extract the actual result from FastMCP CallToolResult"""
        # If it's already a dict, return as-is
        if isinstance(mcp_result, dict):
            return mcp_result

        if hasattr(mcp_result, "content") and mcp_result.content:
            # FastMCP returns content as a list of TextContent objects
            content = mcp_result.content[0]

            if hasattr(content, "text"):
                import json

                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return {"error": f"Invalid JSON response: {content.text}"}

        # Fallback: return empty dict with error if we can't handle it
        return {"error": f"Unexpected result format: {type(mcp_result)}"}

    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = ["GITLAB_URL", "GITLAB_TOKEN"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            print(
                f"❌ Missing required environment variables: {', '.join(missing_vars)}"
            )
            print("Please set them before running this script.")
            sys.exit(1)

        print("✅ Environment validated")
        print(f"   GitLab URL: {os.getenv('GITLAB_URL')}")
        print(f"   Token: {'*' * 8}...{os.getenv('GITLAB_TOKEN', '')[-4:]}")

    async def get_single_job_result(self, project_id: str | int, job_id: int) -> Any:
        """
        Get result for a single GitLab job

        Args:
            project_id: GitLab project ID or path
            job_id: GitLab job ID

        Returns:
            Job analysis result including errors and warnings
        """
        print(f"🔍 Analyzing single job {job_id} in project {project_id}...")

        client = Client(self.server_script)
        async with client:
            result = await client.call_tool(
                "analyze_single_job", {"project_id": str(project_id), "job_id": job_id}
            )
            return self._extract_result(result)

    async def get_job_trace(self, project_id: str | int, job_id: int) -> Any:
        """
        Get raw trace log for a specific job

        Args:
            project_id: GitLab project ID or path
            job_id: GitLab job ID

        Returns:
            Job trace log
        """
        print(f"📋 Getting trace for job {job_id} in project {project_id}...")

        client = Client(self.server_script)
        async with client:
            result = await client.call_tool(
                "get_job_trace", {"project_id": str(project_id), "job_id": job_id}
            )
            return self._extract_result(result)

    async def get_pipeline_jobs(self, project_id: str | int, pipeline_id: int) -> Any:
        """
        Get all jobs for a pipeline

        Args:
            project_id: GitLab project ID or path
            pipeline_id: GitLab pipeline ID

        Returns:
            All pipeline jobs with their status
        """
        print(
            f"📊 Getting all jobs for pipeline {pipeline_id} in project {project_id}..."
        )

        client = Client(self.server_script)
        async with client:
            result = await client.call_tool(
                "get_pipeline_jobs",
                {"project_id": str(project_id), "pipeline_id": pipeline_id},
            )
            return self._extract_result(result)

    async def get_failed_jobs(self, project_id: str | int, pipeline_id: int) -> Any:
        """
        Get only failed jobs for a pipeline

        Args:
            project_id: GitLab project ID or path
            pipeline_id: GitLab pipeline ID

        Returns:
            Failed pipeline jobs
        """
        print(
            f"❌ Getting failed jobs for pipeline {pipeline_id} in project {project_id}..."
        )

        client = Client(self.server_script)
        async with client:
            result = await client.call_tool(
                "get_failed_jobs",
                {"project_id": str(project_id), "pipeline_id": pipeline_id},
            )
            return self._extract_result(result)

    async def analyze_failed_pipeline(
        self, project_id: str | int, pipeline_id: int
    ) -> Any:
        """
        Analyze a failed pipeline with full error extraction

        Args:
            project_id: GitLab project ID or path
            pipeline_id: GitLab pipeline ID

        Returns:
            Complete pipeline analysis with errors and warnings
        """
        print(f"🔥 Analyzing failed pipeline {pipeline_id} in project {project_id}...")

        client = Client(self.server_script)
        async with client:
            result = await client.call_tool(
                "analyze_failed_pipeline",
                {"project_id": str(project_id), "pipeline_id": pipeline_id},
            )
            return self._extract_result(result)

    async def get_pipeline_status(self, project_id: str | int, pipeline_id: int) -> Any:
        """
        Get pipeline status and basic information

        Args:
            project_id: GitLab project ID or path
            pipeline_id: GitLab pipeline ID

        Returns:
            Pipeline status information
        """
        print(
            f"ℹ️  Getting status for pipeline {pipeline_id} in project {project_id}..."
        )

        client = Client(self.server_script)
        async with client:
            result = await client.call_tool(
                "get_pipeline_status",
                {"project_id": str(project_id), "pipeline_id": pipeline_id},
            )
            return self._extract_result(result)

    def print_job_summary(self, result: Any):
        """Print a formatted summary of job analysis"""
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return

        if "analysis" in result:
            analysis = result["analysis"]
            summary = result.get("summary", {})

            print("\n📊 Job Analysis Summary")
            print(f"   Job ID: {result.get('job_id')}")
            print(f"   Job URL: {result.get('job_url', 'N/A')}")
            print(f"   Errors: {summary.get('total_errors', 0)}")
            print(f"   Warnings: {summary.get('total_warnings', 0)}")
            print(f"   Log entries: {summary.get('total_log_entries', 0)}")
            print(f"   Has trace: {summary.get('has_trace', False)}")

            if analysis.get("errors"):
                print("\n🔴 Errors found:")
                for i, error in enumerate(analysis["errors"][:5], 1):  # Show first 5
                    print(f"   {i}. {error.get('message', 'No message')}")
                if len(analysis["errors"]) > 5:
                    print(f"   ... and {len(analysis['errors']) - 5} more errors")

            if analysis.get("warnings"):
                print("\n🟡 Warnings found:")
                for i, warning in enumerate(
                    analysis["warnings"][:3], 1
                ):  # Show first 3
                    print(f"   {i}. {warning.get('message', 'No message')}")
                if len(analysis["warnings"]) > 3:
                    print(f"   ... and {len(analysis['warnings']) - 3} more warnings")

    def print_pipeline_summary(self, result: Any):
        """Print a formatted summary of pipeline analysis"""
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return

        summary = result.get("summary", {})
        print("\n📊 Pipeline Analysis Summary")
        print(f"   Pipeline ID: {result.get('pipeline_id')}")
        print(f"   Status: {result.get('pipeline_status')}")
        print(f"   Failed jobs: {summary.get('failed_jobs_count', 0)}")
        print(f"   Total errors: {summary.get('total_errors', 0)}")
        print(f"   Total warnings: {summary.get('total_warnings', 0)}")

        if summary.get("failed_stages"):
            print(f"   Failed stages: {', '.join(summary['failed_stages'])}")

        if result.get("failed_jobs"):
            print("\n❌ Failed Jobs:")
            for job in result["failed_jobs"]:
                print(
                    f"   • {job['name']} (Stage: {job['stage']}, Reason: {job.get('failure_reason', 'Unknown')})"
                )


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="GitLab Job Result Analyzer using FastMCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single job
  python get_job_result.py --project-id 12345 --job-id 67890
  
  # Get raw trace for a job
  python get_job_result.py --project-id 12345 --job-id 67890 --trace-only
  
  # Analyze failed pipeline
  python get_job_result.py --project-id 12345 --pipeline-id 11111 --analyze-failures
  
  # Get all jobs in a pipeline
  python get_job_result.py --project-id 12345 --pipeline-id 11111 --all-jobs
  
  # Get only failed jobs
  python get_job_result.py --project-id 12345 --pipeline-id 11111 --failed-jobs-only
  
  # Get pipeline status
  python get_job_result.py --project-id 12345 --pipeline-id 11111 --status-only
  
  # Output as JSON
  python get_job_result.py --project-id 12345 --job-id 67890 --json
        """,
    )

    parser.add_argument(
        "--project-id", type=str, required=True, help="GitLab project ID or path"
    )

    # Job-specific options
    parser.add_argument("--job-id", type=int, help="GitLab job ID to analyze")

    parser.add_argument(
        "--trace-only",
        action="store_true",
        help="Get only the raw trace log (requires --job-id)",
    )

    # Pipeline-specific options
    parser.add_argument("--pipeline-id", type=int, help="GitLab pipeline ID to analyze")

    parser.add_argument(
        "--analyze-failures",
        action="store_true",
        help="Analyze failed pipeline with full error extraction (requires --pipeline-id)",
    )

    parser.add_argument(
        "--all-jobs",
        action="store_true",
        help="Get all jobs in pipeline (requires --pipeline-id)",
    )

    parser.add_argument(
        "--failed-jobs-only",
        action="store_true",
        help="Get only failed jobs in pipeline (requires --pipeline-id)",
    )

    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Get pipeline status only (requires --pipeline-id)",
    )

    # Output options
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    parser.add_argument(
        "--server-script",
        type=str,
        default="server.py",
        help="Path to MCP server script (default: server.py)",
    )

    args = parser.parse_args()

    # Validate argument combinations
    if args.job_id and args.pipeline_id:
        parser.error("Cannot specify both --job-id and --pipeline-id")

    if not args.job_id and not args.pipeline_id:
        parser.error("Must specify either --job-id or --pipeline-id")

    if args.trace_only and not args.job_id:
        parser.error("--trace-only requires --job-id")

    pipeline_flags = [
        args.analyze_failures,
        args.all_jobs,
        args.failed_jobs_only,
        args.status_only,
    ]
    if any(pipeline_flags) and not args.pipeline_id:
        parser.error("Pipeline-specific flags require --pipeline-id")

    # Check if server script exists
    server_path = Path(args.server_script)
    if not server_path.exists():
        print(f"❌ MCP server script not found: {args.server_script}")
        print(f"   Current directory: {Path.cwd()}")
        print(
            "   Please ensure the server script exists or use --server-script to specify the correct path"
        )
        sys.exit(1)

    # Initialize analyzer
    analyzer = JobResultAnalyzer(args.server_script)

    async def run_analysis():
        try:
            result = None

            if args.job_id:
                if args.trace_only:
                    result = await analyzer.get_job_trace(args.project_id, args.job_id)
                else:
                    result = await analyzer.get_single_job_result(
                        args.project_id, args.job_id
                    )

            elif args.pipeline_id:
                if args.analyze_failures:
                    result = await analyzer.analyze_failed_pipeline(
                        args.project_id, args.pipeline_id
                    )
                elif args.all_jobs:
                    result = await analyzer.get_pipeline_jobs(
                        args.project_id, args.pipeline_id
                    )
                elif args.failed_jobs_only:
                    result = await analyzer.get_failed_jobs(
                        args.project_id, args.pipeline_id
                    )
                elif args.status_only:
                    result = await analyzer.get_pipeline_status(
                        args.project_id, args.pipeline_id
                    )
                else:
                    # Default: analyze failed pipeline
                    result = await analyzer.analyze_failed_pipeline(
                        args.project_id, args.pipeline_id
                    )

            # Output results
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                if args.job_id:
                    if args.trace_only:
                        if "error" in result:
                            print(f"❌ Error: {result['error']}")
                        else:
                            print(
                                f"📋 Job Trace (Length: {result.get('trace_length', 0)} chars)"
                            )
                            print(f"{'='*60}")
                            print(result.get("trace", "No trace available"))
                    else:
                        analyzer.print_job_summary(result)
                elif args.pipeline_id:
                    if args.all_jobs or args.failed_jobs_only:
                        if "error" in result:
                            print(f"❌ Error: {result['error']}")
                        else:
                            jobs_key = (
                                "failed_jobs" if args.failed_jobs_only else "jobs"
                            )
                            jobs = result.get(jobs_key, [])
                            print(
                                f"\n📊 {'Failed ' if args.failed_jobs_only else ''}Jobs Summary"
                            )
                            print(f"   Total: {len(jobs)}")
                            for job in jobs:
                                status_emoji = (
                                    "❌"
                                    if job["status"] == "failed"
                                    else "✅" if job["status"] == "success" else "🟡"
                                )
                                print(
                                    f"   {status_emoji} {job['name']} (Stage: {job['stage']}, Status: {job['status']})"
                                )
                    elif args.status_only:
                        if "error" in result:
                            print(f"❌ Error: {result['error']}")
                        else:
                            print("\nℹ️  Pipeline Status")
                            print(f"   ID: {result.get('pipeline_id')}")
                            print(f"   Status: {result.get('status')}")
                            print(f"   Ref: {result.get('ref')}")
                            print(f"   SHA: {result.get('sha')}")
                            print(f"   Created: {result.get('created_at')}")
                            print(f"   Updated: {result.get('updated_at')}")
                            print(f"   URL: {result.get('web_url')}")
                    else:
                        analyzer.print_pipeline_summary(result)

            print("\n✅ Analysis completed successfully!")

        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            if args.json:
                print(json.dumps({"error": str(e)}, indent=2))
            sys.exit(1)

    # Run the analysis
    asyncio.run(run_analysis())


if __name__ == "__main__":
    main()
