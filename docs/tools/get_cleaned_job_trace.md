# New MCP Tool: `get_cleaned_job_trace`

## Overview

A new MCP tool has been added to the GitLab Pipeline Analyzer that returns cleaned job traces with ANSI escape sequences removed.

## Tool Details

### Name
`get_cleaned_job_trace`

### Description
Get the trace log for a specific GitLab CI/CD job with ANSI codes removed. This tool fetches the raw job trace and automatically cleans it by removing ANSI escape sequences, making it more suitable for automated analysis and human reading.

### Parameters
- `project_id` (str | int): The GitLab project ID or path
- `job_id` (int): The ID of the GitLab job

### Returns
- `project_id`: The project ID that was analyzed
- `job_id`: The job ID that was analyzed  
- `cleaned_trace`: The trace log with ANSI codes removed
- `cleaning_stats`: Statistics about the cleaning process
  - `original_length`: Number of characters in original trace
  - `cleaned_length`: Number of characters after cleaning
  - `chars_removed`: Number of characters removed
  - `reduction_percentage`: Percentage reduction (rounded to 1 decimal)
  - `ansi_sequences_found`: Total number of ANSI sequences detected
  - `unique_ansi_types`: Number of different ANSI sequence types
  - `most_common_ansi`: Most frequently occurring ANSI sequence and its count
- `has_content`: Boolean indicating if trace has actual content
- `ansi_sequences_detected`: Boolean indicating if ANSI sequences were found

## Example Usage

```python
from fastmcp import Client

async def get_cleaned_trace():
    client = Client("server.py")
    async with client:
        result = await client.call_tool(
            "get_cleaned_job_trace",
            {"project_id": "19133", "job_id": 2009734}
        )
        return result
```

## Example Response

```json
{
  "project_id": "19133",
  "job_id": 2009734,
  "cleaned_trace": "Running with gitlab-runner 17.8.5...",
  "cleaning_stats": {
    "original_length": 37276,
    "cleaned_length": 34509,
    "chars_removed": 2767,
    "reduction_percentage": 7.4,
    "ansi_sequences_found": 348,
    "unique_ansi_types": 18,
    "most_common_ansi": ["\\x1b[0;m", 68]
  },
  "has_content": true,
  "ansi_sequences_detected": true
}
```

## Benefits

### ✨ **Clean Output**
- Removes ANSI escape sequences that can clutter log analysis
- Provides pure text content suitable for processing

### 🔍 **Better Analysis**
- Improves accuracy of error extraction algorithms
- Eliminates false positives caused by ANSI codes

### 📖 **Human Readable**
- Makes traces easier to read and understand
- Removes control sequences that can cause display issues

### 🤖 **Automation Friendly**
- Clean input for automated log processing
- Consistent text format for pattern matching

### 📊 **Statistics**
- Provides detailed cleaning statistics
- Shows efficiency of ANSI code removal
- Identifies most common ANSI sequences

## Comparison with Raw Trace

| Aspect | Raw Trace (`get_job_trace`) | Cleaned Trace (`get_cleaned_job_trace`) |
|--------|---------------------------|----------------------------------------|
| **Content** | Contains ANSI escape sequences | ANSI sequences removed |
| **Size** | Larger (includes control codes) | Smaller (7-25% reduction typical) |
| **Readability** | May have formatting artifacts | Clean, readable text |
| **Processing** | Requires preprocessing | Ready for analysis |
| **Statistics** | Basic length info | Detailed cleaning metrics |

## Test Results

Based on pipeline 625483 testing:

### Job 2009734 (Test Job)
- **Original**: 37,276 characters
- **Cleaned**: 34,509 characters  
- **Reduction**: 2,767 characters (7.4%)
- **ANSI Sequences**: 348 removed (18 unique types)

### Job 2009732 (Lint Job)  
- **Original**: 44,199 characters
- **Cleaned**: 36,237 characters
- **Reduction**: 7,962 characters (18.0%)
- **ANSI Sequences**: 930 removed

## Integration

The tool is fully integrated into the MCP server and is available alongside existing tools:

1. `analyze_failed_pipeline` - Analyze complete failed pipeline
2. `analyze_single_job` - Analyze single job
3. `get_pipeline_jobs` - Get all pipeline jobs
4. `get_failed_jobs` - Get only failed jobs
5. `get_job_trace` - Get raw job trace
6. **`get_cleaned_job_trace`** - **Get cleaned job trace** ⭐ **NEW**
7. `extract_log_errors` - Extract errors from logs
8. `get_pipeline_status` - Get pipeline status

## Implementation Details

- Uses `LogParser._clean_ansi_sequences()` for ANSI removal
- Regex pattern: `r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'`
- Provides comprehensive statistics about cleaning process
- Handles all standard ANSI escape sequences including colors, cursor control, and formatting

## Files Created

- **Tool Implementation**: `src/gitlab_analyzer/mcp/tools.py` (new tool added)
- **Test Scripts**: 
  - `test_cleaned_trace_tool.py` - Basic functionality test
  - `compare_trace_tools.py` - Comparison between raw and cleaned
  - `demo_cleaned_workflow.py` - Complete workflow demonstration
  - `save_cleaned_trace.py` - Save traces to files for analysis
  - `list_mcp_tools.py` - List all available tools

The new tool enhances the GitLab Pipeline Analyzer by providing clean, ANSI-free log content that is optimized for both human readability and automated processing.
