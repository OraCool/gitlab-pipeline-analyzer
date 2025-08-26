"""
Investigation prompts for pipeline failure analysis

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging

logger = logging.getLogger(__name__)


def register_investigation_prompts(mcp) -> None:
    """Register investigation prompts with MCP server"""

    @mcp.prompt("pipeline-investigation")
    async def pipeline_investigation_prompt(
        project_id: str, pipeline_id: int, focus_area: str = "overview"
    ) -> str:
        """Guide agents through systematic pipeline failure investigation"""

        base_prompt = f"""
# Pipeline Investigation Workflow for Project {project_id}, Pipeline {pipeline_id}

## Systematic Approach to Pipeline Failure Analysis

### Step 1: Get Pipeline Overview
Start with the pipeline resource to understand the big picture:
```
Resource: gl://pipeline/{project_id}/{pipeline_id}
```
This provides:
- Pipeline status and timing
- Complete jobs list with statuses
- Basic failure counts and metadata

### Step 2: Analyze Overall Failures
Get comprehensive failure analysis:
```
Tool: analyze_failed_pipeline
Parameters: project_id="{project_id}", pipeline_id={pipeline_id}
```
This gives you:
- All failed jobs with extracted errors
- Error categorization and patterns
- Priority recommendations

### Step 3: Deep Dive into Critical Jobs
For each high-priority failed job, get detailed analysis:
```
Resource: gl://job/{{project_id}}/{{job_id}}
Resource: gl://analysis/{{project_id}}/{{job_id}}
```

### Step 4: File-Level Investigation
Focus on specific files with many errors:
```
Tool: get_files_with_errors
Tool: get_file_errors (for specific files)
Resource: gl://file/{{project_id}}/{{job_id}}/{{file_path}}
```
The file resource provides:
- File-specific error analysis with context
- Error filtering and categorization
- Line numbers and exception details

### Step 5: Generate Solutions
Use analysis results to generate fixes:
```
Tool: search_repository_code (to find related implementations)
Tool: generate_fix_suggestions (when available)
```

## Key Resources Available:
- `gl://pipeline/{project_id}/{pipeline_id}` - Pipeline overview
- `gl://job/{project_id}/{{job_id}}` - Individual job details
- `gl://analysis/{project_id}/{pipeline_id}` - Pipeline-wide analysis
- `gl://analysis/{project_id}/{{job_id}}` - Job-specific analysis
- `gl://error/{project_id}/{{error_id}}` - Individual error deep-dive

## Best Practices:
1. Always start with pipeline resource for context
2. Use analysis resources for structured error data
3. Follow error references to dive deeper
4. Group errors by file for systematic fixing
5. Search repository for similar patterns before proposing fixes
        """

        if focus_area == "pytest":
            base_prompt += """

## Python/Pytest Specific Investigation:
When dealing with Python test failures:

1. **Use Pytest-Specific Tools:**
   ```
   Tool: analyze_pytest_job_complete
   Tool: extract_pytest_detailed_failures
   Tool: extract_pytest_statistics
   ```

2. **Look for Common Python Issues:**
   - Import errors (missing dependencies)
   - Function signature mismatches
   - API parameter changes
   - Environment/configuration issues

3. **Check Test Structure:**
   - Fixture problems
   - Parametrized test issues
   - Setup/teardown failures
            """

        elif focus_area == "build":
            base_prompt += """

## Build/Compilation Specific Investigation:
When dealing with build failures:

1. **Focus on Build Logs:**
   ```
   Tool: get_cleaned_job_trace
   Tool: extract_log_errors
   ```

2. **Common Build Issues:**
   - Dependency resolution failures
   - Compilation errors
   - Configuration problems
   - Environment setup issues

3. **Check Build Configuration:**
   - CI/CD file syntax
   - Build script errors
   - Environment variable issues
            """

        return base_prompt

    @mcp.prompt("error-analysis")
    async def error_analysis_prompt(
        project_id: str, error_context: str = "", error_type: str = "general"
    ) -> str:
        """Guide agents through systematic error analysis"""

        return f"""
# Error Analysis Workflow for Project {project_id}

## Context: {error_context or "General error investigation"}

### Step 1: Identify Error Patterns
Look for similar errors across the pipeline:
```
Tool: search_repository_code
Parameters: search_keywords="{error_context}", project_id="{project_id}"
```

### Step 2: Get Error Details
If you have a specific error ID:
```
Resource: gl://error/{project_id}/{{error_id}}
```

### Step 3: Find All Occurrences
Search for all files affected by this error type:
```
Tool: get_files_with_errors
Tool: group_errors_by_file
```

### Step 4: Root Cause Analysis
Analyze the error in context:
- Check recent commits for related changes
- Look for environment or dependency changes
- Identify if it's a widespread or isolated issue

### Step 5: Solution Development
Based on error type and context:
- Search for working examples in the codebase
- Identify fix patterns from similar resolved issues
- Propose targeted solutions

## Error Type Specific Guidance:
{f"Focus on {error_type}-specific investigation patterns" if error_type != "general" else "Apply general error analysis patterns"}
        """

    logger.info("Investigation prompts registered")
