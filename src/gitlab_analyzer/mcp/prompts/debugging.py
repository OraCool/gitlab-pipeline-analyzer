"""
Debugging prompts for error resolution

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging

logger = logging.getLogger(__name__)


def register_debugging_prompts(mcp) -> None:
    """Register debugging prompts with MCP server"""

    @mcp.prompt("test-failure-debugging")
    async def test_failure_debugging_prompt(
        project_id: str, job_id: int, test_framework: str = "pytest"
    ) -> str:
        """Guide agents through systematic test failure debugging"""

        if test_framework.lower() == "pytest":
            return f"""
# Python Test Failure Debugging for Job {job_id}

## Systematic Pytest Failure Analysis

### Step 1: Get Test Job Details
```
Resource: gl://job/{project_id}/{job_id}
```
This provides:
- Job status and timing
- Raw test output logs
- Test environment details

### Step 2: Extract Pytest Results
```
Tool: analyze_pytest_job_complete
Parameters: project_id="{project_id}", job_id={job_id}
```
This gives you:
- Detailed test failures with tracebacks
- Test statistics (passed/failed/skipped)
- Error categorization

### Step 3: Analyze Specific Failures
For each failing test, examine:
- Exception type and message
- Stack trace and error location
- Test parameters and fixtures used
- Related file context

### Step 4: Group and Prioritize
```
Tool: group_errors_by_file
Parameters: project_id="{project_id}", job_id={job_id}
```
Focus on:
- Files with multiple test failures
- Common error patterns
- Critical test suites

### Step 5: Root Cause Investigation
Common pytest failure patterns:
1. **Import Errors**: Missing dependencies or circular imports
2. **Fixture Issues**: Setup/teardown problems
3. **API Changes**: Function signature mismatches
4. **Environment Issues**: Missing configuration or data
5. **Assertion Failures**: Logic or data problems

### Step 6: Search for Solutions
```
Tool: search_repository_code
Parameters: search_keywords="[error_context]", extension_filter="py"
```

## Quick Diagnosis Checklist:
- [ ] Check if it's an import/dependency issue
- [ ] Verify test fixtures are working
- [ ] Look for recent API changes
- [ ] Check test data and configuration
- [ ] Examine parametrized test issues
- [ ] Review setup/teardown methods
            """
        else:
            return f"""
# General Test Failure Debugging for Job {job_id}

## Systematic Test Analysis

### Step 1: Get Job Information
```
Resource: gl://job/{project_id}/{job_id}
Resource: gl://analysis/{project_id}/{job_id}
```

### Step 2: Extract Test Errors
```
Tool: extract_log_errors
Tool: get_files_with_errors
```

### Step 3: Analyze Patterns
Look for common failure types in your testing framework.

### Step 4: Search Related Code
```
Tool: search_repository_code
```

Framework: {test_framework}
Adapt the investigation approach based on your specific testing framework.
            """

    @mcp.prompt("build-failure-debugging")
    async def build_failure_debugging_prompt(
        project_id: str, job_id: int, build_type: str = "general"
    ) -> str:
        """Guide agents through systematic build failure debugging"""

        return f"""
# Build Failure Debugging for Job {job_id}

## Systematic Build Analysis

### Step 1: Get Build Job Details
```
Resource: gl://job/{project_id}/{job_id}
```

### Step 2: Extract Build Errors
```
Tool: get_cleaned_job_trace
Parameters: project_id="{project_id}", job_id={job_id}

Tool: extract_log_errors
Parameters: log_text="[job_trace_output]"
```

### Step 3: Categorize Build Issues
Common build failure types:
1. **Dependency Issues**: Package resolution, version conflicts
2. **Compilation Errors**: Syntax, type errors, missing imports
3. **Configuration Problems**: Build settings, environment variables
4. **Resource Issues**: Disk space, memory, network timeouts
5. **Permission Issues**: File access, execution permissions

### Step 4: Environment Analysis
Check for:
- Build tool versions (npm, pip, gradle, etc.)
- Environment variable configuration
- Dependency lock file changes
- Build cache issues

### Step 5: Search for Patterns
```
Tool: search_repository_code
Parameters: search_keywords="[build_config_files]"
```

### Step 6: Compare with Working Builds
Look for:
- Recent configuration changes
- Dependency updates
- Environment differences

Build Type: {build_type}
Tailor your investigation to the specific build system and language.
        """

    logger.info("Debugging prompts registered")
