Examples and Use Cases
======================

This section provides practical examples of using the GitLab Pipeline Analyzer MCP Server **version 0.8.0** with its comprehensive toolkit of 12 essential tools, MCP resources, merge request integration, and 13+ intelligent prompts.

.. contents::
   :local:
   :depth: 2

Quick Start Examples
--------------------

NEW in v0.8.0: Merge Request Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Merge request pipeline failed, need to understand context and extract Jira tickets.

**Enhanced MR Pipeline Analysis:**

.. code-block:: text

    User: "MR pipeline failed for project 123, pipeline 1594344. Show me MR context."

    Assistant: "I'll analyze this merge request pipeline with full context."

    # Tool call: failed_pipeline_analysis
    {
        "project_id": "123",
        "pipeline_id": 1594344,
        "store_in_db": true
    }

    # Results include (NEW in v0.8.0):
    # Pipeline Type: "merge_request"
    # MR Title: "PROJ-456: Implement user authentication flow"
    # MR Description: "Fixes authentication issues mentioned in PROJ-456 and PROJ-789"
    # Extracted Jira Tickets: ["PROJ-456", "PROJ-789"]
    # Source Branch: "feature/auth-implementation"
    # Target Branch: "main"
    # Author: "john.doe"
    # Failed Jobs: 2 out of 5
    # Total Errors: 34

**Smart Filtering in Action:**

.. code-block:: text

    # For MR pipelines: Shows MR context + Jira tickets
    Pipeline Type: merge_request → Includes MR data ✅

    # For branch pipelines: Excludes MR data
    Pipeline Type: branch → No MR data shown ✅

Failed Pipeline Investigation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Pipeline #1594344 in project 123 failed. You need a complete analysis.

**Using the failed_pipeline_analysis tool:**

.. code-block:: text

    User: "Pipeline 1594344 in project 123 failed. What went wrong?"

    Assistant: "I'll analyze this failed pipeline comprehensively for you."

    # Tool call: failed_pipeline_analysis
    {
        "project_id": "123",
        "pipeline_id": 1594344,
        "store_in_db": true
    }

    # Results show (NEW in v0.8.0):
    # - Pipeline type: "merge_request"
    # - MR information: "PROJ-456: Fix user authentication flow"
    # - Jira tickets: ["PROJ-456"]
    # - Source branch: "feature/auth-fix"
    # - Target branch: "main"
    # - 3 failed jobs with 127 total errors
    # - Main issues: Import errors, test failures
    # - Resources created for detailed investigation

**Follow-up with MCP Resources:**

.. code-block:: text

    # Access failed jobs directly
    Resource: gl://pipeline/123/pipeline/1594344/failed

    # Get pipeline overview with MR context (NEW in v0.8.0)
    Resource: gl://pipeline/123/1594344
    # Returns: MR title, description, Jira tickets, branch info

    # Examine specific file errors
    Resource: gl://files/123/76474172/src/main.py

Search Repository for Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Errors mention missing imports. Find where they're defined.

**Using search_repository_code tool:**

.. code-block:: text

    # Search for specific function or import
    Tool: search_repository_code
    {
        "project_id": "123",
        "search_keywords": "import pandas",
        "extension_filter": "py",
        "max_results": 10
    }

    # Results show where pandas is used across the codebase
    # Helps identify missing dependencies or import patterns

Clean Job Trace Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Need readable log output without ANSI escape sequences.

**Using get_clean_job_trace tool:**

.. code-block:: text

    Tool: get_clean_job_trace
    {
        "project_id": "123",
        "job_id": 76474172,
        "save_to_file": true,
        "output_format": "text"
    }

    # Returns clean, human-readable trace
    # Saved to local file for further analysis

Using Intelligent Prompts
~~~~~~~~~~~~~~~~~~~~~~~~~

**Performance Investigation Prompt:**

.. code-block:: text

    User: "Our pipelines are too slow. Help me optimize them."

    Assistant: "I'll use the performance-investigation prompt to analyze your pipeline
    efficiency and identify optimization opportunities."

    # Guided analysis includes:
    # 1. Pipeline timing analysis
    # 2. Resource usage patterns
    # 3. Cache effectiveness check
    # 4. Bottleneck identification
    # 5. Optimization recommendations

**Investigation Wizard for Beginners:**

.. code-block:: text

    User: "I'm new to CI/CD. This pipeline failed and I don't understand why."

    Assistant: "I'll use the investigation-wizard in beginner mode to guide you
    through the analysis step by step."

    # Educational approach:
    # 1. Explains CI/CD concepts
    # 2. Guides through tool usage
    # 3. Interprets results clearly
    # 4. Suggests learning resources

Advanced Use Cases
------------------

NEW in v0.8.0: Jira Integration Workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Automatic Jira Ticket Detection:**

.. code-block:: text

    # MR Title: "PROJ-123: Fix database connection timeout"
    # MR Description: "Resolves PROJ-123 and addresses PROJ-456 requirements"

    # Automatically extracts: ["PROJ-123", "PROJ-456"]
    # Validates ticket format and removes duplicates
    # Links pipeline failures to specific Jira tickets

**Contextual Error Analysis with Jira Context:**

.. code-block:: python

    # Enhanced analysis includes Jira context
    analysis_result = {
        "pipeline_type": "merge_request",
        "merge_request": {
            "title": "PROJ-123: Fix database timeout",
            "description": "Resolves timeout issues in DB layer",
            "jira_tickets": ["PROJ-123", "PROJ-456"],
            "source_branch": "feature/db-timeout-fix",
            "target_branch": "main",
            "author": "jane.doe"
        },
        "errors": [
            {
                "message": "Connection timeout after 30s",
                "related_jira": "PROJ-123",  # Links error to ticket
                "file_path": "src/database/connection.py"
            }
        ]
    }

**Smart Filtering Examples:**

.. code-block:: text

    # Example 1: MR Pipeline (includes MR data)
    Resource: gl://pipeline/123/1594344
    Returns:
    - Pipeline info ✅
    - MR title, description ✅
    - Jira tickets ✅
    - Source/target branches ✅

    # Example 2: Branch Pipeline (excludes MR data)
    Resource: gl://pipeline/123/1594345
    Returns:
    - Pipeline info ✅
    - Branch info ✅
    - No MR data ❌ (correctly filtered)
    - No Jira tickets ❌ (correctly filtered)

MCP Resources Navigation
~~~~~~~~~~~~~~~~~~~~~~~~

**Complete resource workflow for pipeline investigation:**

.. code-block:: text

    # 1. Start with pipeline overview
    Resource: gl://pipeline/123/1594344

    # 2. Get failed jobs list
    Resource: gl://pipeline/123/pipeline/1594344/failed

    # 3. Analyze specific job
    Resource: gl://pipeline/123/1594344/76474172

    # 4. Check files with errors
    Resource: gl://pipeline/123/pipeline/1594344

    # 5. Examine specific file
    Resource: gl://pipeline/123/76474172/src/main.py

    # 6. Get error details with trace
    Resource: gl://pipeline/123/76474172/src/main.py/trace?mode=detailed&include_trace=true

    # 7. Pipeline-wide error analysis
    Resource: gl://pipeline/123/pipeline/1594344

Repository Investigation Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Finding code patterns and commit history:**

.. code-block:: text

    # 1. Search for error-related code
    Tool: search_repository_code
    {
        "project_id": "123",
        "search_keywords": "import tensorflow",
        "path_filter": "src/*",
        "output_format": "json"
    }

    # 2. Check commit history for recent changes
    Tool: search_repository_commits
    {
        "project_id": "123",
        "search_keywords": "fix import",
        "max_results": 15,
        "output_format": "json"
    }

    # 3. Find recent dependency changes
    Tool: search_repository_code
    {
        "project_id": "123",
        "search_keywords": "requirements",
        "filename_filter": "*.txt"
    }

Cache Management Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~

**Monitoring and optimizing cache performance:**

.. code-block:: text

    # 1. Check cache statistics
    Tool: cache_stats
    # Returns: size, hit rates, storage info

    # 2. Verify cache health
    Tool: cache_health
    # Returns: database integrity, performance metrics

    # 3. Clear old data if needed
    Tool: clear_cache
    {
        "cache_type": "old",
        "max_age_hours": 168  # 7 days
    }

    # 4. Clear specific pipeline data
    Tool: clear_pipeline_cache
    {
        "project_id": "123",
        "pipeline_id": 1594344
    }

Comprehensive Error Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Deep-dive error investigation with resources:**

.. code-block:: text

    # 1. Get job-specific errors
    Resource: gl://pipeline/123/76474172

    # 2. Filter by specific file
    Resource: gl://pipeline/123/76474172/tests/test_main.py

    # 3. Get individual error details
    Resource: gl://pipeline/123/76474172/error_001

    # 4. Analysis with different modes
    Resource: gl://pipeline/123/job/76474172?mode=detailed
    Resource: gl://pipeline/123/job/76474172?mode=summary

Educational and Mentoring Scenarios
-----------------------------------

Learning Path Development
~~~~~~~~~~~~~~~~~~~~~~~~~

**Using educational prompts for team development:**

.. code-block:: text

    # Learning Path Prompt
    User: "Create a CI/CD learning curriculum for my team."

    Assistant: "I'll use the learning-path prompt to create a progressive
    curriculum based on your team's skill level."

    # Curriculum includes:
    # 1. Skill assessment using real pipeline data
    # 2. Progressive modules from basic to advanced
    # 3. Hands-on exercises with actual errors
    # 4. Practice scenarios using repository search
    # 5. Progress tracking and milestone evaluation

CI/CD Mentoring Guide
~~~~~~~~~~~~~~~~~~~~~

**Structured mentoring approach:**

.. code-block:: text

    # Mentoring Guide Prompt
    User: "I need to mentor junior developers on CI/CD practices."

    Assistant: "I'll use the mentoring-guide prompt to create an effective
    teaching strategy."

    # Strategy includes:
    # 1. Teaching methodologies for different concepts
    # 2. Explanation frameworks for complex topics
    # 3. Practical exercises using MCP resources
    # 4. Progress tracking approaches
    # 5. Feedback loop establishment

Advanced Investigation Prompts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Regression Analysis:**

.. code-block:: text

    # Pipeline Comparison Prompt
    User: "Pipeline 1594344 was working, but 1594345 is failing. What changed?"

    Assistant: "I'll use the pipeline-comparison prompt to analyze differences."

    # Analysis includes:
    # 1. Job configuration comparison
    # 2. Error pattern analysis
    # 3. Commit difference investigation
    # 4. Configuration drift detection
    # 5. Comprehensive regression report

**Fix Strategy Planning:**

.. code-block:: text

    # Fix Strategy Planner Prompt
    User: "Complex pipeline failure affecting multiple teams. Need a fix strategy."

    Assistant: "I'll use the fix-strategy-planner prompt for comprehensive
    remediation planning."

    # Strategy includes:
    # 1. Failure scope and impact analysis
    # 2. Priority matrix by criticality and effort
    # 3. Resource allocation planning
    # 4. Timeline and dependency estimation
    # 5. Risk mitigation and rollback strategies

Production Monitoring Examples
------------------------------

Real-time Pipeline Monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Continuous monitoring setup:**

.. code-block:: python

    import asyncio
    from mcp_client import MCPClient

    class PipelineMonitor:
        def __init__(self):
            self.client = MCPClient("local-pandado")

        async def monitor_project(self, project_id):
            """Monitor project for failed pipelines"""

            # Check recent pipeline status (would need additional tools)
            # For now, assume we have pipeline IDs to monitor

            failed_pipelines = await self.get_failed_pipelines(project_id)

            for pipeline_id in failed_pipelines:
                # Quick analysis using failed_pipeline_analysis
                result = await self.client.failed_pipeline_analysis(
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    store_in_db=True
                )

                print(f"Pipeline {pipeline_id}: {result['summary']['total_errors']} errors")

                # Store analysis for later detailed investigation
                await self.store_failure_report(project_id, pipeline_id, result)

        async def investigate_failure_trends(self, project_id):
            """Analyze failure patterns over time"""

            # Use cache_stats to understand data volume
            stats = await self.client.cache_stats()
            print(f"Cache contains {stats['total_entries']} analysis entries")

            # Use search tools to find patterns
            commit_patterns = await self.client.search_repository_commits(
                project_id=project_id,
                search_keywords="fix|bug|error",
                max_results=20
            )

            return self.analyze_failure_patterns(commit_patterns)

Automated Error Classification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Classify and prioritize errors automatically:**

.. code-block:: python

    class ErrorClassifier:
        def __init__(self):
            self.client = MCPClient("local-pandado")

        async def classify_pipeline_errors(self, project_id, pipeline_id):
            """Classify errors by type and priority"""

            # Get comprehensive error analysis
            resource_uri = f"gl://errors/{project_id}/pipeline/{pipeline_id}"
            errors = await self.client.get_mcp_resource(resource_uri)

            classification = {
                "critical": [],     # Import/syntax errors
                "test_failures": [], # Test-specific failures
                "warnings": [],     # Non-blocking issues
                "config_issues": [] # Configuration problems
            }

            for error in errors.get('errors', []):
                error_type = error.get('error_type', '')
                message = error.get('message', '')

                if 'ImportError' in error_type or 'ModuleNotFoundError' in error_type:
                    classification['critical'].append(error)
                elif 'AssertionError' in error_type or 'test_' in error.get('file_path', ''):
                    classification['test_failures'].append(error)
                elif 'Warning' in error_type:
                    classification['warnings'].append(error)
                else:
                    classification['config_issues'].append(error)

            return classification

        async def generate_fix_priorities(self, classification):
            """Generate prioritized fix list"""

            priorities = []

            # Critical issues first
            for error in classification['critical']:
                file_path = error.get('file_path', '')

                # Search for related code to understand scope
                search_result = await self.client.search_repository_code(
                    project_id=error.get('project_id'),
                    search_keywords=file_path.split('/')[-1].replace('.py', ''),
                    extension_filter='py'
                )

                impact_score = self.calculate_impact(search_result)

                priorities.append({
                    'error': error,
                    'priority': 'P0',
                    'impact_score': impact_score,
                    'fix_complexity': 'low' if 'import' in error.get('message', '') else 'medium'
                })

            return sorted(priorities, key=lambda x: x['impact_score'], reverse=True)

Integration Examples
--------------------

Claude Desktop Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Complete Claude Desktop setup:**

.. code-block:: json

    {
        "mcpServers": {
            "gitlab-analyzer": {
                "command": "uv",
                "args": ["run", "gitlab-analyzer"],
                "env": {
                    "GITLAB_URL": "https://gitlab.com",
                    "GITLAB_TOKEN": "your-token-here",
                    "MCP_DATABASE_PATH": "analysis_cache.db",
                    "AUTO_CLEANUP_ENABLED": "true",
                    "AUTO_CLEANUP_INTERVAL_HOURS": "24"
                }
            }
        }
    }

**Usage patterns in Claude Desktop:**

.. code-block:: text

    # Quick pipeline analysis
    "Analyze failed pipeline 1594344 in project 123"

    # Resource-based investigation
    "Show me errors from gl://errors/123/pipeline/1594344"

    # Repository investigation
    "Search for 'async def process' in project 123 Python files"

    # Cache management
    "Check cache health and clean old data"

VS Code Extension Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**MCP server integration in VS Code:**

.. code-block:: typescript

    // VS Code extension using MCP client
    import { MCPClient } from 'mcp-client';

    export class GitLabAnalyzer {
        private client: MCPClient;

        constructor() {
            this.client = new MCPClient({
                transport: 'stdio',
                command: 'uv',
                args: ['run', 'gitlab-analyzer']
            });
        }

        async analyzeCurrentPipeline() {
            // Get current branch pipeline info from Git
            const branch = await this.getCurrentBranch();
            const projectId = await this.getProjectId();

            // Find recent pipeline for branch (would need additional tools)
            const pipelineId = await this.getLatestPipelineId(projectId, branch);

            if (pipelineId) {
                const analysis = await this.client.call('failed_pipeline_analysis', {
                    project_id: projectId,
                    pipeline_id: pipelineId,
                    store_in_db: true
                });

                // Display results in VS Code
                this.showAnalysisResults(analysis);
            }
        }

        async searchInRepository(searchTerm: string) {
            const projectId = await this.getProjectId();

            const results = await this.client.call('search_repository_code', {
                project_id: projectId,
                search_keywords: searchTerm,
                extension_filter: 'py',
                output_format: 'json'
            });

            return this.parseSearchResults(results);
        }
    }

CI/CD Pipeline Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

**GitHub Actions monitoring workflow:**

.. code-block:: yaml

    name: GitLab Pipeline Monitor

    on:
      schedule:
        - cron: '0 */2 * * *'  # Every 2 hours
      workflow_dispatch:

    jobs:
      monitor:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4

          - name: Setup Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.11'

          - name: Install GitLab Analyzer
            run: pip install gitlab-pipeline-analyzer

          - name: Monitor Projects
            run: |
              # Start MCP server
              gitlab-analyzer --transport http --host 127.0.0.1 --port 8000 &
              sleep 5

              # Run monitoring script
              python monitor_pipelines.py
            env:
              GITLAB_URL: ${{ secrets.GITLAB_URL }}
              GITLAB_TOKEN: ${{ secrets.GITLAB_TOKEN }}
              MCP_DATABASE_PATH: "monitor_cache.db"

          - name: Upload Reports
            uses: actions/upload-artifact@v3
            with:
              name: pipeline-reports
              path: "reports/*.json"

Best Practices and Patterns
---------------------------

Error Handling Patterns
~~~~~~~~~~~~~~~~~~~~~~~

**Robust error handling with fallbacks:**

.. code-block:: python

    async def robust_analysis(project_id, pipeline_id):
        try:
            # Try comprehensive analysis first
            result = await client.failed_pipeline_analysis(
                project_id=project_id,
                pipeline_id=pipeline_id,
                store_in_db=True
            )
            return result

        except Exception as e:
            print(f"Comprehensive analysis failed: {e}")

            # Fallback to resource-based access
            try:
                resource_uri = f"gl://pipeline/{project_id}/{pipeline_id}"
                return await client.get_mcp_resource(resource_uri)

            except Exception as e:
                print(f"Resource access failed: {e}")

                # Final fallback to basic tools
                return await client.get_clean_job_trace(
                    project_id=project_id,
                    job_id=pipeline_id  # Assuming job ID same as pipeline
                )

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

**Efficient resource usage:**

.. code-block:: text

    # 1. Use summary first, details only if needed
    Resource: gl://pipeline/123/pipeline/1594344?mode=summary

    # 2. Filter file patterns to reduce noise
    Tool: failed_pipeline_analysis with exclude_file_patterns=["node_modules/", "*.pyc"]

    # 3. Limit search results appropriately
    Tool: search_repository_code with max_results=10

    # 4. Use pagination for large datasets
    Resource: gl://pipeline/123/pipeline/1594344/page/1/limit/20

    # 5. Clear cache regularly
    Tool: clear_cache with cache_type="old" and max_age_hours=48

Resource Navigation Patterns
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Efficient investigation workflows:**

.. code-block:: text

    # Pattern 1: Top-down investigation
    gl://pipeline/123/1594344                    # Overview
    ↓
    gl://pipeline/123/pipeline/1594344/failed        # Failed jobs
    ↓
    gl://pipeline/123/1594344/76474172               # Specific job
    ↓
    gl://pipeline/123/76474172                    # Job errors

    # Pattern 2: File-focused investigation
    gl://pipeline/123/pipeline/1594344             # Files with errors
    ↓
    gl://pipeline/123/76474172/src/main.py         # Specific file
    ↓
    gl://pipeline/123/76474172/src/main.py/trace?mode=detailed&include_trace=true

    # Pattern 3: Error-centric investigation
    gl://pipeline/123/pipeline/1594344           # All pipeline errors
    ↓
    gl://pipeline/123/76474172/src/main.py      # File-specific errors
    ↓
    gl://pipeline/123/76474172/error_001         # Individual error

This comprehensive examples guide demonstrates the full power of the GitLab Pipeline Analyzer MCP Server with its 12 essential tools, MCP resources, and intelligent prompt system for effective CI/CD pipeline analysis and debugging.

Next Steps
----------

- Review :doc:`tools_and_resources` for complete tool reference and MCP resources
- Check :doc:`prompts` for all 13+ intelligent prompts with usage examples
- See :doc:`environment_variables` for complete configuration options
- Visit :doc:`installation` for deployment guidance
- Read :doc:`troubleshooting` for common issues and solutions
