#!/usr/bin/env python3
"""
Parse and display MCP tools in a readable format
"""

import json

# The tools response from the MCP server
tools_json = '''{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"analyze_failed_pipeline","description":"Analyze a failed GitLab CI/CD pipeline and extract errors/warnings from all \\nfailed jobs. Uses optimized API calls to fetch only failed jobs.\\n\\nArgs:\\n    project_id: The GitLab project ID or path\\n    pipeline_id: The ID of the GitLab pipeline to analyze\\n    \\nReturns:\\n    Complete analysis including pipeline info, failed jobs, and extracted \\n    errors/warnings","inputSchema":{"properties":{"project_id":{"anyOf":[{"type":"string"},{"type":"integer"}],"title":"Project Id"},"pipeline_id":{"title":"Pipeline Id","type":"integer"}},"required":["project_id","pipeline_id"],"type":"object"},"outputSchema":{"additionalProperties":true,"type":"object"}},{"name":"analyze_single_job","description":"Analyze a single GitLab CI/CD job and extract errors/warnings from its\\ntrace.\\n\\nArgs:\\n    project_id: The GitLab project ID or path\\n    job_id: The ID of the specific job to analyze\\n    \\nReturns:\\n    Analysis of the single job including extracted errors/warnings","inputSchema":{"properties":{"project_id":{"anyOf":[{"type":"string"},{"type":"integer"}],"title":"Project Id"},"job_id":{"title":"Job Id","type":"integer"}},"required":["project_id","job_id"],"type":"object"},"outputSchema":{"additionalProperties":true,"type":"object"}},{"name":"get_pipeline_jobs","description":"Get all jobs for a specific GitLab pipeline.\\n\\nArgs:\\n    project_id: The GitLab project ID or path\\n    pipeline_id: The ID of the GitLab pipeline\\n    \\nReturns:\\n    List of all jobs in the pipeline with their status and details","inputSchema":{"properties":{"project_id":{"anyOf":[{"type":"string"},{"type":"integer"}],"title":"Project Id"},"pipeline_id":{"title":"Pipeline Id","type":"integer"}},"required":["project_id","pipeline_id"],"type":"object"},"outputSchema":{"additionalProperties":true,"type":"object"}},{"name":"get_job_trace","description":"Get the trace log for a specific GitLab CI/CD job.\\n\\nArgs:\\n    project_id: The GitLab project ID or path\\n    job_id: The ID of the GitLab job\\n    \\nReturns:\\n    The complete trace log for the job","inputSchema":{"properties":{"project_id":{"anyOf":[{"type":"string"},{"type":"integer"}],"title":"Project Id"},"job_id":{"title":"Job Id","type":"integer"}},"required":["project_id","job_id"],"type":"object"},"outputSchema":{"additionalProperties":true,"type":"object"}},{"name":"extract_log_errors","description":"Extract errors and warnings from log text.\\n\\nArgs:\\n    log_text: The log text to analyze\\n    \\nReturns:\\n    Extracted errors and warnings with context","inputSchema":{"properties":{"log_text":{"title":"Log Text","type":"string"}},"required":["log_text"],"type":"object"},"outputSchema":{"additionalProperties":true,"type":"object"}},{"name":"get_pipeline_status","description":"Get the current status and basic information of a GitLab pipeline.\\n\\nArgs:\\n    project_id: The GitLab project ID or path\\n    pipeline_id: The ID of the GitLab pipeline\\n    \\nReturns:\\n    Pipeline status and basic information","inputSchema":{"properties":{"project_id":{"anyOf":[{"type":"string"},{"type":"integer"}],"title":"Project Id"},"pipeline_id":{"title":"Pipeline Id","type":"integer"}},"required":["project_id","pipeline_id"],"type":"object"},"outputSchema":{"additionalProperties":true,"type":"object"}}]}}'''

def display_tools():
    response = json.loads(tools_json)
    tools = response["result"]["tools"]
    
    print("🛠️  GitLab Pipeline Analyzer MCP Server - Available Tools")
    print("=" * 70)
    print(f"Found {len(tools)} tools:")
    print()
    
    for i, tool in enumerate(tools, 1):
        print(f"{i}. 🔧 {tool['name']}")
        print("-" * 50)
        
        # Clean up description
        desc = tool['description'].replace('\\n', '\n').replace('\\', '')
        print(f"📝 Description:")
        for line in desc.split('\n'):
            if line.strip():
                print(f"   {line.strip()}")
        print()
        
        # Parameters
        if 'inputSchema' in tool and 'properties' in tool['inputSchema']:
            print("📋 Parameters:")
            props = tool['inputSchema']['properties']
            required = tool['inputSchema'].get('required', [])
            
            for param_name, param_info in props.items():
                param_type = param_info.get('type', 'unknown')
                if 'anyOf' in param_info:
                    types = [t['type'] for t in param_info['anyOf']]
                    param_type = ' or '.join(types)
                
                required_text = " (required)" if param_name in required else " (optional)"
                print(f"   • {param_name}: {param_type}{required_text}")
        
        print()

if __name__ == "__main__":
    display_tools()
