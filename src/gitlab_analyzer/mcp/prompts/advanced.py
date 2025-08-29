"""
Advanced prompts for enhanced investigation workflows

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_role_specific_tips(role: str) -> str:
    """Get role-specific investigation tips"""
    tips = {
        "developer": """
**Developer Focus:**
- Pay attention to compilation errors and test failures
- Look for import/dependency issues
- Check recent code changes and their impact
- Use search tools to find similar patterns in codebase
        """,
        "devops": """
**DevOps Focus:**
- Monitor infrastructure and environment changes
- Check resource usage and performance metrics
- Analyze deployment pipeline efficiency
- Focus on system-level root causes
        """,
        "manager": """
**Management Focus:**
- Assess business impact and user experience
- Coordinate team response and communication
- Track resolution timeline and resource allocation
- Plan process improvements to prevent recurrence
        """,
    }
    return tips.get(role, tips["developer"])


def _generate_strategy_matrix(
    scope: str, urgency: str, constraints: dict[str, Any]
) -> str:
    """Generate fix strategy matrix based on parameters"""
    return f"""
**Scope: {scope.title()} | Urgency: {urgency.title()}**

| Approach | Time | Risk | Resources |
|----------|------|------|-----------|
| Hotfix   | 1h   | Low  | 1 dev     |
| Targeted | 4h   | Med  | 2 devs    |
| Comprehensive | 1d | High | Team |
    """


def _format_constraints(constraints: dict[str, Any]) -> str:
    """Format team constraints for display"""
    if not constraints:
        return "No specific constraints provided"

    formatted = []
    for key, value in constraints.items():
        formatted.append(f"- **{key.title()}**: {value}")

    return "\n".join(formatted)


def register_advanced_prompts(mcp) -> None:
    """Register advanced investigation prompts with MCP server"""

    @mcp.prompt("investigation-wizard")
    async def investigation_wizard_prompt(
        project_id: str,
        pipeline_id: int,
        user_role: str = "developer",
        investigation_depth: str = "standard",
        previous_context: str = "",
        focus_areas: list[str] | None = None,
    ) -> str:
        """Multi-step investigation wizard with role-based guidance"""

        role_configs = {
            "developer": {
                "focus": ["code_errors", "test_failures", "compilation_issues"],
                "tools_priority": [
                    "failed_pipeline_analysis",
                    "search_repository_code",
                ],
                "depth": "detailed_code_analysis",
            },
            "devops": {
                "focus": ["infrastructure", "deployments", "environment_issues"],
                "tools_priority": ["cache_stats", "get_clean_job_trace"],
                "depth": "system_level_analysis",
            },
            "manager": {
                "focus": ["impact_assessment", "timeline", "resource_allocation"],
                "tools_priority": ["get_mcp_resource", "cache_stats"],
                "depth": "high_level_overview",
            },
        }

        config = role_configs.get(user_role, role_configs["developer"])
        focus_list = focus_areas or config["focus"]

        depth_instructions = {
            "quick": "Focus on immediate blockers and quick wins",
            "standard": "Comprehensive analysis with actionable recommendations",
            "deep": "Exhaustive investigation including root cause analysis",
        }

        continuation = (
            f"\n## 🔄 **Continuing from previous context:**\n{previous_context}\n"
            if previous_context
            else ""
        )

        return f"""
# 🧙‍♂️ Investigation Wizard for {user_role.title()}
## Project {project_id}, Pipeline {pipeline_id}

{continuation}

## 🎯 **Role-Optimized Investigation Path**

### Your Focus Areas: {", ".join(focus_list)}
### Investigation Depth: {depth_instructions[investigation_depth]}

## 📋 **Step-by-Step Workflow**

### Step 1: Context Gathering ({user_role} perspective)
```
Resource: gl://pipeline/{project_id}/{pipeline_id}
```
**Focus for {user_role}:** {config["depth"]}

### Step 2: Priority Analysis
```
Tool: failed_pipeline_analysis
Parameters: project_id="{project_id}", pipeline_id={pipeline_id}
```
**{user_role.title()} Priority:** Look for {", ".join(config["focus"])}

### Step 3: Deep Dive Investigation
Based on your role, prioritize these tools:
{chr(10).join([f"- {tool}" for tool in config["tools_priority"]])}

### Step 4: Action Planning
Generate role-specific recommendations:
- **Immediate Actions**: What needs to be done right now
- **Next Steps**: Sequential investigation tasks
- **Escalation Points**: When to involve other teams

## 🚀 **Role-Specific Tips**

{_get_role_specific_tips(user_role)}

## 📊 **Progress Tracking**
- [ ] Context gathered
- [ ] Priority analysis complete
- [ ] Root cause identified
- [ ] Action plan created
- [ ] Implementation started

## 🔄 **Next Investigation Step**
Use `investigation-wizard` again with `previous_context` parameter to continue where you left off.
        """

    @mcp.prompt("pipeline-comparison")
    async def pipeline_comparison_prompt(
        project_id: str,
        failed_pipeline_id: int,
        reference_pipeline_id: int | None = None,
        comparison_type: str = "failure-analysis",
        time_window: str = "7_days",
    ) -> str:
        """Compare pipelines to identify changes and regressions"""

        comparison_strategies = {
            "failure-analysis": "Focus on what changed between working and broken states",
            "performance": "Compare execution times, resource usage, and efficiency",
            "environment": "Analyze environment differences and configuration changes",
            "dependency": "Track dependency changes and version differences",
        }

        ref_pipeline_text = (
            f"Resource: gl://pipeline/{project_id}/{reference_pipeline_id}"
            if reference_pipeline_id
            else "Use most recent successful pipeline"
        )

        return f"""
# 🔍 Pipeline Comparison Analysis
## Failed Pipeline {failed_pipeline_id} vs Reference Pipeline

### 🎯 **Comparison Strategy: {comparison_type}**
{comparison_strategies.get(comparison_type, "General comparison analysis")}

## 📊 **Step 1: Get Pipeline Details**
```
Resource: gl://pipeline/{project_id}/{failed_pipeline_id}
{ref_pipeline_text}
```

## 🔍 **Step 2: Identify Key Differences**

### Failed Pipeline Analysis:
```
Tool: failed_pipeline_analysis
Parameters: project_id="{project_id}", pipeline_id={failed_pipeline_id}
```

### Environment Comparison:
```
Tool: search_repository_code
Parameters: search_keywords="environment OR config OR version", project_id="{project_id}"
```

## 📈 **Step 3: Change Detection**

### Code Changes:
```
Tool: search_repository_commits
Parameters: search_keywords="merge OR fix OR update", project_id="{project_id}"
```

### Configuration Changes:
- Compare CI/CD configurations
- Check environment variable changes
- Analyze dependency file modifications

## 🎯 **Step 4: Regression Analysis**

### Focus Areas:
1. **Timing Differences**: When did the issue first appear?
2. **Scope Impact**: What components are affected?
3. **Change Correlation**: Which changes correlate with failures?
4. **Pattern Recognition**: Is this a recurring issue?

## 🔧 **Step 5: Resolution Strategy**

### Based on comparison results:
- **Revert Strategy**: If recent changes caused the issue
- **Forward Fix**: If reverting is not feasible
- **Environment Fix**: If environment drift is detected
- **Process Improvement**: If systemic issues are found

## 📋 **Comparison Checklist**
- [ ] Pipeline timing comparison
- [ ] Job success/failure patterns
- [ ] Error message differences
- [ ] Environment configuration changes
- [ ] Dependency version differences
- [ ] Resource usage patterns

Time Window: {time_window}
        """

    @mcp.prompt("fix-strategy-planner")
    async def fix_strategy_prompt(
        project_id: str,
        pipeline_id: int,
        error_context: str = "",
        team_constraints: dict[str, Any] | None = None,
        fix_scope: str = "targeted",
        urgency: str = "medium",
    ) -> str:
        """Generate comprehensive fix strategies based on constraints and context"""

        constraints = team_constraints or {}

        scope_strategies = {
            "hotfix": "Minimal, immediate fix to restore functionality",
            "targeted": "Address root cause with focused changes",
            "comprehensive": "Systematic fix including related issues",
            "preventive": "Fix current issue plus implement prevention measures",
        }

        urgency_timelines = {
            "critical": "Immediate action required (< 1 hour)",
            "high": "Urgent fix needed (< 4 hours)",
            "medium": "Important fix (< 24 hours)",
            "low": "Planned fix (< 1 week)",
        }

        return f"""
# 🎯 Fix Strategy Planner
## Project {project_id}, Pipeline {pipeline_id}

### 📋 **Current Context**
Error Context: {error_context or "General pipeline failure"}
Fix Scope: {scope_strategies[fix_scope]}
Urgency: {urgency_timelines[urgency]}

## 🔍 **Step 1: Impact Assessment**
```
Tool: failed_pipeline_analysis
Parameters: project_id="{project_id}", pipeline_id={pipeline_id}
```

### Critical Questions:
- What's the blast radius of this issue?
- How many users/systems are affected?
- Are there workarounds available?

## 🎯 **Step 2: Fix Strategy Selection**

### Strategy Matrix:
{_generate_strategy_matrix(fix_scope, urgency, constraints)}

## 🔧 **Step 3: Implementation Plan**

### Phase 1: Immediate Actions
- [ ] Issue containment
- [ ] Impact mitigation
- [ ] Stakeholder communication

### Phase 2: Root Cause Fix
```
Tool: search_repository_code
Parameters: search_keywords="[derived_from_error_context]", project_id="{project_id}"
```

### Phase 3: Validation
- [ ] Fix verification
- [ ] Regression testing
- [ ] Performance impact check

## 📊 **Step 4: Resource Planning**

### Team Constraints Analysis:
{_format_constraints(constraints)}

### Recommended Resources:
- **Developer Time**: [Based on scope analysis]
- **Testing Requirements**: [Based on impact assessment]
- **Deployment Coordination**: [Based on urgency level]

## 🚀 **Step 5: Execution Workflow**

### Fix Implementation:
1. Create fix branch from stable point
2. Implement targeted changes
3. Local testing and validation
4. Pipeline testing in safe environment
5. Gradual rollout strategy

### Monitoring Plan:
- Error rate monitoring
- Performance metrics tracking
- User impact assessment
- Rollback criteria definition

## 📈 **Step 6: Prevention Measures**

### Short-term:
- Improved error handling
- Better testing coverage
- Enhanced monitoring

### Long-term:
- Process improvements
- Tool enhancements
- Team training

## 🔄 **Continuous Improvement**
Document lessons learned and update this strategy for future similar issues.
        """

    logger.info("Advanced prompts registered")
