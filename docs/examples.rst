Examples and Use Cases
======================

This section provides practical examples of using the GitLab Pipeline Analyzer MCP Server in various scenarios.

.. contents::
   :local:
   :depth: 2

Basic Usage Examples
--------------------

Analyzing a Failed Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** You receive a notification that pipeline #456 in project "myorg/myproject" has failed and need to understand what went wrong.

.. code-block:: python

    from fastmcp import Client

    async def investigate_pipeline_failure():
        async with Client("http://localhost:8000/mcp") as client:
            # Start with a quick overview
            summary = await client.call_tool("analyze_failed_pipeline_summary", {
                "project_id": "myorg/myproject",
                "pipeline_id": 456
            })

            print(f"Pipeline {summary['pipeline_id']} has {summary['summary']['total_failed_jobs']} failed jobs")
            print(f"Total errors: {summary['summary']['total_errors']}")

            # Get detailed analysis if needed
            if summary['summary']['total_errors'] < 50:  # Avoid overwhelming output
                detailed = await client.call_tool("analyze_failed_pipeline", {
                    "project_id": "myorg/myproject",
                    "pipeline_id": 456
                })

                # Show parser usage
                for parser_type, info in detailed['parser_analysis']['usage_summary'].items():
                    print(f"{parser_type} parser used for {info['count']} jobs with {info['total_errors']} total errors")

Investigating a Specific Job
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Pipeline analysis shows that job #789 has the most errors, and you want to focus on it.

.. code-block:: python

    async def analyze_problematic_job():
        async with Client("http://localhost:8000/mcp") as client:
            # Get detailed job analysis
            job_analysis = await client.call_tool("analyze_single_job", {
                "project_id": "myorg/myproject",
                "job_id": 789
            })

            print(f"Job {job_analysis['job_id']} has {job_analysis['error_count']} errors")
            print(f"Parser type: {job_analysis['parser_type']}")

            # If it's a pytest job, get more detailed test information
            if job_analysis['parser_type'] == 'pytest':
                pytest_details = await client.call_tool("analyze_pytest_job_complete", {
                    "project_id": "myorg/myproject",
                    "job_id": 789
                })

                stats = pytest_details['statistics']
                print(f"Test Results: {stats['passed']} passed, {stats['failed']} failed, {stats['skipped']} skipped")
                print(f"Duration: {stats['duration_formatted']}")

Working with Large Error Sets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** A job has many errors and you need to process them systematically without overwhelming the response.

.. code-block:: python

    async def handle_large_error_set():
        async with Client("http://localhost:8000/mcp") as client:
            project_id = "myorg/myproject"
            job_id = 789

            # Start with limited analysis to gauge size
            limited = await client.call_tool("analyze_single_job_limited", {
                "project_id": project_id,
                "job_id": job_id,
                "max_errors": 5,
                "include_traceback": False
            })

            total_errors = limited.get('total_available_errors', limited['error_count'])
            print(f"Total errors available: {total_errors}")

            if total_errors > 20:
                # Use batch processing for large error sets
                batch_size = 3
                for start_idx in range(0, min(total_errors, 15), batch_size):  # Process first 15 errors
                    batch = await client.call_tool("get_error_batch", {
                        "project_id": project_id,
                        "job_id": job_id,
                        "start_index": start_idx,
                        "batch_size": batch_size,
                        "include_traceback": True
                    })

                    print(f"\\nBatch {start_idx//batch_size + 1}: {len(batch['errors'])} errors")
                    for error in batch['errors']:
                        print(f"  - {error.get('exception_type', 'Error')}: {error.get('exception_message', error.get('message', 'No message'))}")

Advanced Use Cases
------------------

File-Based Error Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** You want to fix errors systematically by working on one file at a time.

.. code-block:: python

    async def systematic_file_fixing():
        async with Client("http://localhost:8000/mcp") as client:
            project_id = "myorg/myproject"
            pipeline_id = 456

            # Get overview of files with errors
            files_overview = await client.call_tool("get_files_with_errors", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "max_files": 10,
                "exclude_file_patterns": ["*.pyc", "__pycache__", ".pytest_cache"]
            })

            print("Files with errors:")
            for file_info in files_overview['files_with_errors']:
                print(f"  {file_info['file_path']}: {file_info['error_count']} errors ({file_info['file_type']})")

            # Group errors by file for systematic fixing
            grouped_errors = await client.call_tool("group_errors_by_file", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "max_files": 5,
                "max_errors_per_file": 10,
                "include_traceback": True
            })

            # Process highest priority files first
            for file_group in grouped_errors['file_groups']:
                file_path = file_group['file_path']
                error_count = file_group['error_count']

                print(f"\\n=== Processing {file_path} ({error_count} errors) ===")

                # Get specific job with errors for this file
                if file_group['errors']:
                    first_error = file_group['errors'][0]
                    job_id = first_error['job_id']

                    # Get all errors for this specific file
                    file_errors = await client.call_tool("get_file_errors", {
                        "project_id": project_id,
                        "job_id": job_id,
                        "file_path": file_path,
                        "max_errors": 15,
                        "include_traceback": True
                    })

                    print(f"Found {len(file_errors['errors'])} errors in {file_path}")
                    for error in file_errors['errors']:
                        line = error.get('line_number', 'unknown')
                        error_type = error.get('exception_type', 'Error')
                        message = error.get('exception_message', error.get('message', 'No message'))
                        print(f"  Line {line}: {error_type} - {message}")

Repository Search Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Errors mention missing functions or imports, and you need to find where they should be defined or used.

.. code-block:: python

    async def search_for_missing_dependencies():
        async with Client("http://localhost:8000/mcp") as client:
            project_id = "myorg/myproject"
            job_id = 789

            # Analyze errors to find missing imports
            job_analysis = await client.call_tool("analyze_single_job", {
                "project_id": project_id,
                "job_id": job_id
            })

            import_errors = []
            for error in job_analysis.get('errors', []):
                message = error.get('exception_message', error.get('message', ''))
                if 'No module named' in message or 'cannot import' in message:
                    import_errors.append(error)

            print(f"Found {len(import_errors)} import-related errors")

            # Search for each missing module in the codebase
            for error in import_errors[:3]:  # Process first 3 import errors
                message = error.get('exception_message', error.get('message', ''))

                # Extract module name (basic parsing)
                if "No module named '" in message:
                    module_name = message.split("No module named '")[1].split("'")[0]

                    print(f"\\nSearching for module: {module_name}")

                    # Search for the module in code
                    search_results = await client.call_tool("search_repository_code", {
                        "project_id": project_id,
                        "search_keywords": module_name,
                        "extension_filter": "py",
                        "max_results": 5
                    })

                    if "Found 0 total matches" not in search_results:
                        print("Found potential matches:")
                        print(search_results)
                    else:
                        print(f"Module {module_name} not found in codebase - might need to be installed")

Test Failure Investigation
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Test jobs are failing and you need detailed analysis of test failures with full context.

.. code-block:: python

    async def investigate_test_failures():
        async with Client("http://localhost:8000/mcp") as client:
            project_id = "myorg/myproject"
            job_id = 789  # Test job ID

            # Get comprehensive pytest analysis
            pytest_analysis = await client.call_tool("analyze_pytest_job_complete", {
                "project_id": project_id,
                "job_id": job_id
            })

            stats = pytest_analysis['statistics']
            print(f"Test Summary: {stats['total_tests']} total, {stats['failed']} failed")
            print(f"Pass rate: {stats['passed']}/{stats['total_tests']} ({(stats['passed']/stats['total_tests']*100):.1f}%)")

            if stats['failed'] > 0:
                print(f"\\n=== Failed Tests ===")

                # Get detailed failure information
                detailed_failures = await client.call_tool("extract_pytest_detailed_failures", {
                    "project_id": project_id,
                    "job_id": job_id
                })

                for failure in detailed_failures['detailed_failures']:
                    print(f"\\nTest: {failure['test_name']}")
                    print(f"File: {failure['test_file']}:{failure['line_number']}")
                    print(f"Error: {failure['exception_type']} - {failure['exception_message']}")

                    # Show relevant traceback entries (filtered)
                    if failure.get('traceback'):
                        print("Traceback (relevant parts):")
                        for frame in failure['traceback'][-3:]:  # Show last 3 frames
                            if '/builds/' not in frame.get('file_path', ''):  # Skip CI build paths
                                print(f"  {frame.get('file_path', 'unknown')}:{frame.get('line_number', '?')}")
                                if frame.get('code_line'):
                                    print(f"    {frame['code_line']}")

            # Check for patterns in failures
            if len(pytest_analysis['detailed_failures']) > 1:
                print(f"\\n=== Failure Analysis ===")

                # Group by exception type
                error_types = {}
                for failure in pytest_analysis['detailed_failures']:
                    error_type = failure['exception_type']
                    if error_type not in error_types:
                        error_types[error_type] = []
                    error_types[error_type].append(failure)

                for error_type, failures in error_types.items():
                    print(f"{error_type}: {len(failures)} occurrences")
                    if len(failures) > 2:
                        print(f"  Common error type - investigate {error_type} issues")

Commit History Analysis
~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Errors appeared recently and you want to find related commits that might have introduced the issues.

.. code-block:: python

    async def investigate_recent_changes():
        async with Client("http://localhost:8000/mcp") as client:
            project_id = "myorg/myproject"

            # Get pipeline info to understand what branch we're working with
            pipeline_info = await client.call_tool("get_pipeline_info", {
                "project_id": project_id,
                "pipeline_id": 456
            })

            target_branch = pipeline_info['target_branch']
            print(f"Investigating recent changes on branch: {target_branch}")

            # Search for recent commits that might be related to the failures
            search_terms = [
                "fix", "bug", "error", "test", "import",
                "refactor", "update", "change"
            ]

            for term in search_terms[:3]:  # Check first 3 terms
                print(f"\\nSearching commits for: {term}")

                commit_results = await client.call_tool("search_repository_commits", {
                    "project_id": project_id,
                    "search_keywords": term,
                    "branch": target_branch,
                    "max_results": 5
                })

                if "Found 0 total matches" not in commit_results:
                    # Parse results to find recent commits
                    lines = commit_results.split('\\n')
                    for line in lines:
                        if 'Date:' in line and '2025-01' in line:  # Recent commits
                            print(f"  Recent commit found: {line}")

Integration Examples
--------------------

VS Code Claude Desktop Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Configuration for Claude Desktop:**

.. code-block:: json

    {
      "servers": {
        "gitlab-analyzer": {
          "type": "stdio",
          "command": "uvx",
          "args": ["--from", "gitlab-pipeline-analyzer", "gitlab-analyzer"],
          "env": {
            "GITLAB_URL": "${input:gitlab_url}",
            "GITLAB_TOKEN": "${input:gitlab_token}"
          }
        }
      },
      "inputs": [
        {
          "id": "gitlab_url",
          "type": "promptString",
          "description": "GitLab Instance URL"
        },
        {
          "id": "gitlab_token",
          "type": "promptString",
          "description": "GitLab Personal Access Token"
        }
      ]
    }

**Usage in Claude Desktop:**

.. code-block:: text

    User: "Pipeline 456 in project myorg/myproject failed. Can you analyze what went wrong?"

    Claude: I'll analyze the failed pipeline for you. Let me start with an overview and then dive into the details.

    [Claude calls analyze_failed_pipeline tool and provides analysis]

Automated Monitoring Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Script for monitoring multiple projects:**

.. code-block:: python

    import asyncio
    import json
    from datetime import datetime
    from fastmcp import Client

    class GitLabMonitor:
        def __init__(self, mcp_url="http://localhost:8000/mcp"):
            self.mcp_url = mcp_url
            self.projects = [
                {"id": "group/project1", "name": "Project 1"},
                {"id": "group/project2", "name": "Project 2"},
            ]

        async def check_recent_pipelines(self, project_id, limit=5):
            """Check recent pipelines for a project (would need additional API)"""
            # This would require additional MCP tools for listing recent pipelines
            # For now, assume we have pipeline IDs to check
            pipeline_ids = [456, 457, 458]  # Example IDs

            failed_pipelines = []

            async with Client(self.mcp_url) as client:
                for pipeline_id in pipeline_ids:
                    try:
                        status = await client.call_tool("get_pipeline_status", {
                            "project_id": project_id,
                            "pipeline_id": pipeline_id
                        })

                        if status['status'] == 'failed':
                            failed_pipelines.append({
                                "pipeline_id": pipeline_id,
                                "status": status,
                                "project_id": project_id
                            })
                    except Exception as e:
                        print(f"Error checking pipeline {pipeline_id}: {e}")

            return failed_pipelines

        async def generate_failure_report(self, failed_pipeline):
            """Generate a summary report for a failed pipeline"""
            async with Client(self.mcp_url) as client:
                summary = await client.call_tool("analyze_failed_pipeline_summary", {
                    "project_id": failed_pipeline["project_id"],
                    "pipeline_id": failed_pipeline["pipeline_id"]
                })

                return {
                    "timestamp": datetime.now().isoformat(),
                    "project_id": failed_pipeline["project_id"],
                    "pipeline_id": failed_pipeline["pipeline_id"],
                    "pipeline_url": failed_pipeline["status"]["web_url"],
                    "total_errors": summary["summary"]["total_errors"],
                    "failed_jobs": summary["summary"]["total_failed_jobs"],
                    "summary": summary
                }

        async def monitor_all_projects(self):
            """Monitor all configured projects"""
            all_failures = []

            for project in self.projects:
                print(f"Checking {project['name']}...")
                failed_pipelines = await self.check_recent_pipelines(project["id"])

                for failed_pipeline in failed_pipelines:
                    report = await self.generate_failure_report(failed_pipeline)
                    all_failures.append(report)

                    print(f"  ❌ Pipeline {failed_pipeline['pipeline_id']}: {report['total_errors']} errors")

            # Save report
            if all_failures:
                with open(f"failure_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                    json.dump(all_failures, f, indent=2)

                print(f"\\nGenerated failure report with {len(all_failures)} failed pipelines")
            else:
                print("\\n✅ No failed pipelines found")

    # Usage
    async def main():
        monitor = GitLabMonitor()
        await monitor.monitor_all_projects()

    if __name__ == "__main__":
        asyncio.run(main())

CI/CD Integration Example
~~~~~~~~~~~~~~~~~~~~~~~~~

**GitHub Actions workflow using the MCP server:**

.. code-block:: yaml

    name: GitLab Pipeline Monitor

    on:
      schedule:
        - cron: '*/30 * * * *'  # Every 30 minutes
      workflow_dispatch:

    jobs:
      monitor:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4

          - name: Set up Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.11'

          - name: Install dependencies
            run: |
              pip install gitlab-pipeline-analyzer fastmcp

          - name: Start MCP Server
            run: |
              gitlab-analyzer --transport http --host 127.0.0.1 --port 8000 &
              sleep 5  # Wait for server to start
            env:
              GITLAB_URL: ${{ secrets.GITLAB_URL }}
              GITLAB_TOKEN: ${{ secrets.GITLAB_TOKEN }}

          - name: Monitor Pipelines
            run: |
              python monitoring_script.py

          - name: Upload Reports
            uses: actions/upload-artifact@v3
            if: always()
            with:
              name: pipeline-reports
              path: "*.json"

Error Handling Patterns
-----------------------

Robust Error Handling
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def robust_pipeline_analysis(project_id, pipeline_id):
        async with Client("http://localhost:8000/mcp") as client:
            try:
                # Start with basic status check
                status = await client.call_tool("get_pipeline_status", {
                    "project_id": project_id,
                    "pipeline_id": pipeline_id
                })

                if 'error' in status:
                    print(f"Error getting pipeline status: {status['error']}")
                    return None

                if status['status'] != 'failed':
                    print(f"Pipeline status is '{status['status']}', not failed")
                    return status

                # Try detailed analysis
                try:
                    analysis = await client.call_tool("analyze_failed_pipeline", {
                        "project_id": project_id,
                        "pipeline_id": pipeline_id
                    })

                    if 'error' in analysis:
                        # Fallback to summary if detailed analysis fails
                        print("Detailed analysis failed, trying summary...")
                        analysis = await client.call_tool("analyze_failed_pipeline_summary", {
                            "project_id": project_id,
                            "pipeline_id": pipeline_id
                        })

                    return analysis

                except Exception as e:
                    print(f"Analysis failed: {e}")
                    # Final fallback - just get failed jobs
                    failed_jobs = await client.call_tool("get_failed_jobs", {
                        "project_id": project_id,
                        "pipeline_id": pipeline_id
                    })
                    return failed_jobs

            except Exception as e:
                print(f"Connection error: {e}")
                return None

Retry Logic with Backoff
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from typing import Optional

    async def analyze_with_retry(project_id: str, pipeline_id: int, max_retries: int = 3) -> Optional[dict]:
        async with Client("http://localhost:8000/mcp") as client:
            for attempt in range(max_retries):
                try:
                    result = await client.call_tool("analyze_failed_pipeline", {
                        "project_id": project_id,
                        "pipeline_id": pipeline_id
                    })

                    if 'error' not in result:
                        return result

                    print(f"Attempt {attempt + 1} failed: {result['error']}")

                except Exception as e:
                    print(f"Attempt {attempt + 1} exception: {e}")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

            print(f"Failed after {max_retries} attempts")
            return None

Performance Optimization
------------------------

Concurrent Analysis
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def analyze_multiple_jobs_concurrently(project_id: str, job_ids: list[int]):
        async with Client("http://localhost:8000/mcp") as client:

            async def analyze_single_job_with_id(job_id: int):
                try:
                    result = await client.call_tool("analyze_single_job_limited", {
                        "project_id": project_id,
                        "job_id": job_id,
                        "max_errors": 5,
                        "include_traceback": False
                    })
                    return {"job_id": job_id, "result": result, "error": None}
                except Exception as e:
                    return {"job_id": job_id, "result": None, "error": str(e)}

            # Limit concurrency to avoid overwhelming the server
            semaphore = asyncio.Semaphore(3)

            async def analyze_with_semaphore(job_id: int):
                async with semaphore:
                    return await analyze_single_job_with_id(job_id)

            # Analyze all jobs concurrently
            results = await asyncio.gather(
                *[analyze_with_semaphore(job_id) for job_id in job_ids]
            )

            # Process results
            successful = [r for r in results if r["error"] is None]
            failed = [r for r in results if r["error"] is not None]

            print(f"Successfully analyzed {len(successful)} jobs")
            if failed:
                print(f"Failed to analyze {len(failed)} jobs:")
                for failure in failed:
                    print(f"  Job {failure['job_id']}: {failure['error']}")

            return successful

These examples demonstrate the flexibility and power of the GitLab Pipeline Analyzer MCP Server for various real-world scenarios. The tools can be combined in creative ways to build sophisticated analysis and monitoring solutions.

Next Steps
----------

- See :doc:`tool_reference` for complete parameter documentation
- Check :doc:`configuration` for advanced setup options
- Review :doc:`deployment` for production deployment strategies
