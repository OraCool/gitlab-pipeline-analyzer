# AI-Optimized System Prompts for GitLab Pipeline Analyzer MCP Tools

## Analysis Tools (Primary Workflow Tools)

### analyze_failed_pipeline
```python
"""
🔍 DIAGNOSE: Complete pipeline failure analysis - your go-to tool for understanding why CI/CD pipelines fail.

WHEN TO USE:
- Pipeline shows "failed" status and you need to understand all failure points
- User asks "what went wrong with pipeline X?"
- Need comprehensive error overview across all failed jobs

WHAT YOU GET:
- Pipeline status and metadata
- List of all failed jobs with extracted errors/warnings
- Categorized error types (build, test, lint, etc.)
- Summary statistics for quick assessment

AI ANALYSIS TIPS:
- Look at error_count and warning_count for severity assessment
- Check parser_type field to understand data quality (pytest > generic)
- Use job failure_reason for initial categorization
- Cross-reference errors across jobs to find root causes

WORKFLOW: Start here for pipeline investigations → drill down with analyze_single_job for details
"""
```

### analyze_single_job
```python
"""
🎯 FOCUS: Deep-dive analysis of a specific job failure - use when you need detailed error context.

WHEN TO USE:
- analyze_failed_pipeline identified a job of interest
- User asks about specific job behavior
- Need full error details with traceback/context for debugging

WHAT YOU GET:
- Complete error extraction with context and line numbers
- Warnings and categorized issues
- Raw and cleaned log access
- Error severity assessment

AI ANALYSIS TIPS:
- context field contains human-readable error descriptions
- line_number helps locate exact failure points
- categorization field suggests error type (build/test/dependency)
- Use for generating fix suggestions and debugging guidance

WORKFLOW: Use after analyze_failed_pipeline → combine with pytest tools for Python jobs
"""
```

## Information Tools (Data Gathering)

### get_pipeline_status
```python
"""
📊 STATUS CHECK: Quick pipeline health check - perfect for initial assessment.

WHEN TO USE:
- User provides pipeline ID without context
- Need to verify pipeline state before deep analysis
- Checking if pipeline is still running vs failed

WHAT YOU GET:
- Pipeline status (running/failed/success/canceled)
- Basic metadata (branch, commit, timing)
- Job count and stage information

AI ANALYSIS TIPS:
- status field determines next action (if "failed" → use analyze_failed_pipeline)
- Check duration for performance issues
- Branch/commit info helps with context

WORKFLOW: Often used first → route to appropriate analysis tools based on status
"""
```

### get_failed_jobs
```python
"""
⚠️ IDENTIFY: List all failed jobs in a pipeline - helps prioritize investigation.

WHEN TO USE:
- Need overview of failure scope before detailed analysis
- Want to identify critical vs non-critical job failures
- Planning investigation strategy

WHAT YOU GET:
- List of failed jobs with basic info
- Stage and timing information
- Failure reasons where available

AI ANALYSIS TIPS:
- failure_reason field provides quick categorization
- stage information shows pipeline progression failures
- Use job names to identify critical path failures

WORKFLOW: Bridge tool between get_pipeline_status and analyze_single_job
"""
```

### get_job_trace / get_cleaned_job_trace
```python
"""
📝 RAW ACCESS: Get complete job logs - use when you need full context or custom parsing.

get_job_trace: Raw logs with all formatting
get_cleaned_job_trace: ANSI-cleaned logs, easier for AI processing

WHEN TO USE:
- Standard analysis tools miss important context
- Need to search for specific patterns or commands
- User asks about specific log content
- Custom error pattern detection needed

WHAT YOU GET:
- Complete job execution logs
- All commands, outputs, and error messages
- (cleaned version): Removes color codes and formatting

AI ANALYSIS TIPS:
- Scan for command execution patterns
- Look for environment setup issues
- Identify infrastructure vs code problems
- Use for context that structured analysis might miss

WORKFLOW: Advanced tool - use when standard analysis insufficient
"""
```

## Pytest Tools (Python-Specific Analysis)

### analyze_pytest_job_complete
```python
"""
🐍 COMPREHENSIVE: Complete pytest job analysis - one-stop tool for Python test failures.

WHEN TO USE:
- Job identified as Python/pytest (look for pytest indicators in logs)
- Need complete test failure analysis with statistics
- User asks about test failures, coverage, or Python issues

WHAT YOU GET:
- Detailed failure analysis with full tracebacks
- Test statistics (passed/failed/skipped counts)
- Short summary of all failures
- Success rate and critical failure identification

AI ANALYSIS TIPS:
- detailed_failures contains full debugging context
- statistics help assess test suite health
- traceback field provides exact failure locations
- critical_failures count indicates severity

WORKFLOW: Primary tool for Python test analysis → provides all needed context
"""
```

### extract_pytest_detailed_failures
```python
"""
🔬 DETAILED: Focused pytest failure extraction with complete debugging context.

WHEN TO USE:
- Need only failure details without statistics
- Generating specific fix recommendations
- User asks about specific test failures

WHAT YOU GET:
- Full test failure details with tracebacks
- Exception types and messages
- File and line number locations
- Platform and Python version context

AI ANALYSIS TIPS:
- Use full_error_text for complete context
- traceback provides call stack for debugging
- exception_type helps categorize failure types
- file/line info essential for fix suggestions

WORKFLOW: Use when you only need failure details, not full test suite analysis
"""
```

### extract_pytest_statistics
```python
"""
📈 METRICS: Test suite health metrics - perfect for quality assessment.

WHEN TO USE:
- Assessing test suite overall health
- User asks about test coverage or performance
- Need success rate for quality evaluation

WHAT YOU GET:
- Test counts (total, passed, failed, skipped)
- Execution duration and success rate
- Error and warning counts

AI ANALYSIS TIPS:
- success_rate indicates code quality trend
- duration_seconds helps identify performance issues
- Compare failed vs total for impact assessment
- Use for quality gates and recommendations

WORKFLOW: Complement to detailed failure analysis for complete picture
"""
```

## Log Tools (Generic Analysis)

### extract_log_errors
```python
"""
🔍 GENERIC: Extract errors from any log format - fallback for non-Python jobs.

WHEN TO USE:
- Job is not Python/pytest based
- Standard analysis tools don't detect errors
- Need custom error pattern detection
- Analyzing build logs, deployment logs, etc.

WHAT YOU GET:
- Extracted error and warning messages
- Line numbers and context where available
- Generic categorization

AI ANALYSIS TIPS:
- Less structured than pytest analysis
- Focus on error messages for pattern recognition
- Use context field for understanding
- May need manual interpretation

WORKFLOW: Fallback tool when specialized analysis unavailable
"""
```

## 🚀 **AI Usage Workflow Guide**

### Standard Pipeline Investigation Flow:
1. **get_pipeline_status** → assess situation
2. **analyze_failed_pipeline** → get complete picture
3. **analyze_single_job** → drill down on specific failures
4. **analyze_pytest_job_complete** → for Python jobs
5. **get_job_trace** → if more context needed

### Quick Python Test Analysis:
1. **analyze_pytest_job_complete** → one-stop analysis
2. **extract_pytest_detailed_failures** → if need only failures

### Custom Investigation:
1. **get_failed_jobs** → identify targets
2. **get_cleaned_job_trace** → raw log access
3. **extract_log_errors** → custom parsing

## 🎯 **Key AI Guidelines**

- **Start broad, narrow down**: Use pipeline-level tools first, then job-specific
- **Check parser_type**: "pytest" analysis is more reliable than "generic"
- **Use context fields**: They contain human-readable summaries perfect for AI analysis
- **Look for patterns**: Cross-reference errors across jobs for root cause analysis
- **Provide actionable insights**: Combine technical details with fix suggestions
