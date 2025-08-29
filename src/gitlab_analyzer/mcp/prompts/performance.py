"""
Performance and optimization focused prompts

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging

logger = logging.getLogger(__name__)


def register_performance_prompts(mcp) -> None:
    """Register performance and optimization prompts with MCP server"""

    @mcp.prompt("performance-investigation")
    async def performance_investigation_prompt(
        project_id: str,
        pipeline_id: int,
        baseline_pipeline_id: int | None = None,
        performance_threshold: str = "20_percent",
        focus_area: str = "overall",
    ) -> str:
        """Investigate pipeline performance issues and bottlenecks"""

        threshold_descriptions = {
            "10_percent": "Highly sensitive to performance changes",
            "20_percent": "Standard performance monitoring",
            "50_percent": "Only major performance regressions",
            "100_percent": "Extreme performance issues only",
        }

        focus_areas = {
            "overall": "Complete pipeline performance analysis",
            "build_time": "Focus on compilation and build steps",
            "test_time": "Focus on test execution performance",
            "deployment": "Focus on deployment and infrastructure steps",
            "resource_usage": "Focus on CPU, memory, and I/O usage",
        }

        baseline_text = (
            f"Compare against pipeline {baseline_pipeline_id}"
            if baseline_pipeline_id
            else "Use recent successful pipelines as baseline"
        )

        return f"""
# ⚡ Pipeline Performance Investigation
## Project {project_id}, Pipeline {pipeline_id}

### 🎯 **Performance Analysis Configuration**
- **Threshold**: {threshold_descriptions[performance_threshold]}
- **Focus Area**: {focus_areas[focus_area]}
- **Baseline**: {baseline_text}

## 📊 **Step 1: Performance Overview**
```
Resource: gl://pipeline/{project_id}/{pipeline_id}
```
**Initial Assessment:**
- Total pipeline duration
- Job-level timing breakdown
- Resource usage patterns

## 🔍 **Step 2: Bottleneck Identification**

### Pipeline-Wide Analysis:
```
Tool: failed_pipeline_analysis
Parameters: project_id="{project_id}", pipeline_id={pipeline_id}
```

### Performance Metrics Focus:
- **Build Times**: Compilation, dependency resolution
- **Test Execution**: Unit tests, integration tests, E2E tests
- **Deployment**: Infrastructure provisioning, artifact deployment
- **Resource Efficiency**: CPU, memory, disk I/O

## 📈 **Step 3: Performance Comparison**

### Historical Analysis:
```
Tool: search_repository_commits
Parameters: search_keywords="performance OR optimization OR speed", project_id="{project_id}"
```

### Environment Changes:
```
Tool: search_repository_code
Parameters: search_keywords="dockerfile OR requirements OR package", project_id="{project_id}"
```

## 🚀 **Step 4: Optimization Opportunities**

### Common Performance Issues:
1. **Dependency Management**: Slow package installation
2. **Cache Efficiency**: Poor cache hit rates
3. **Parallelization**: Sequential execution bottlenecks
4. **Resource Allocation**: Under/over-provisioned resources
5. **Test Strategy**: Inefficient test organization

### Investigation Checklist:
- [ ] Cache configuration and hit rates
- [ ] Parallel job execution strategy
- [ ] Resource allocation per job
- [ ] Dependency caching and reuse
- [ ] Test execution order and grouping

## 🔧 **Step 5: Performance Recommendations**

### Quick Wins:
- Enable build caching
- Optimize Docker layer caching
- Parallel test execution
- Resource right-sizing

### Medium-term Improvements:
- Test selection and flaky test management
- Incremental builds and testing
- Pipeline stage optimization
- Infrastructure upgrades

### Long-term Strategy:
- Pipeline architecture redesign
- Advanced caching strategies
- Performance monitoring integration
- Resource usage optimization

## 📊 **Step 6: Performance Monitoring**

### Metrics to Track:
- Pipeline execution time trends
- Job-level performance metrics
- Resource utilization patterns
- Cache efficiency rates
- Success rate vs performance trade-offs

### Alert Thresholds:
- Pipeline duration > baseline + {performance_threshold}
- Job failure due to timeouts
- Resource usage spikes
- Cache miss rate increases

Focus Area: {focus_area}
        """

    @mcp.prompt("ci-cd-optimization")
    async def ci_cd_optimization_prompt(
        project_id: str,
        optimization_goal: str = "speed",
        current_pain_points: list[str] | None = None,
        team_size: str = "medium",
        deployment_frequency: str = "daily",
    ) -> str:
        """Comprehensive CI/CD pipeline optimization guidance"""

        pain_points = current_pain_points or [
            "slow_builds",
            "flaky_tests",
            "complex_debugging",
        ]

        optimization_strategies = {
            "speed": "Minimize pipeline execution time",
            "reliability": "Maximize pipeline success rate and stability",
            "cost": "Optimize resource usage and reduce infrastructure costs",
            "developer_experience": "Improve developer productivity and workflow",
            "security": "Enhance security scanning and compliance checks",
        }

        team_contexts = {
            "small": "1-5 developers, simple workflows",
            "medium": "5-20 developers, moderate complexity",
            "large": "20+ developers, complex enterprise workflows",
        }

        return f"""
# 🚀 CI/CD Pipeline Optimization Guide
## Project {project_id}

### 🎯 **Optimization Strategy**
- **Primary Goal**: {optimization_strategies[optimization_goal]}
- **Team Context**: {team_contexts[team_size]}
- **Deployment Frequency**: {deployment_frequency}
- **Current Pain Points**: {", ".join(pain_points)}

## 📋 **Step 1: Current State Assessment**

### Pipeline Analysis:
```
Tool: search_repository_code
Parameters: search_keywords=".gitlab-ci OR workflow OR pipeline", project_id="{project_id}"
```

### Performance Baseline:
- Current pipeline duration
- Success/failure rates
- Resource utilization
- Developer feedback

## 🔍 **Step 2: Optimization Areas**

### Speed Optimization:
- **Parallel Execution**: Identify parallelizable jobs
- **Caching Strategy**: Implement multi-level caching
- **Resource Allocation**: Right-size compute resources
- **Pipeline Stages**: Optimize stage dependencies

### Reliability Improvement:
- **Flaky Test Management**: Identify and fix unstable tests
- **Error Handling**: Improve failure recovery mechanisms
- **Environment Consistency**: Standardize environments
- **Monitoring**: Enhanced observability and alerting

### Cost Optimization:
- **Resource Efficiency**: Optimize compute usage
- **Caching ROI**: Maximize cache effectiveness
- **Infrastructure**: Right-size infrastructure
- **Waste Reduction**: Eliminate redundant processes

## 🛠 **Step 3: Implementation Roadmap**

### Phase 1: Quick Wins (1-2 weeks)
- [ ] Enable Docker layer caching
- [ ] Implement dependency caching
- [ ] Optimize job resource allocation
- [ ] Add pipeline monitoring

### Phase 2: Structural Improvements (1-2 months)
- [ ] Redesign pipeline stages for parallelism
- [ ] Implement advanced caching strategies
- [ ] Add comprehensive error handling
- [ ] Integrate performance monitoring

### Phase 3: Advanced Optimization (3-6 months)
- [ ] Implement incremental builds
- [ ] Advanced test selection strategies
- [ ] Infrastructure as Code optimization
- [ ] CI/CD pipeline as code best practices

## 📊 **Step 4: Metrics and Monitoring**

### Key Performance Indicators:
- **Speed**: Average pipeline duration, P95 execution time
- **Reliability**: Success rate, mean time to recovery
- **Cost**: Resource utilization, infrastructure costs
- **Developer Experience**: Time to feedback, deployment frequency

### Monitoring Setup:
```
Tool: cache_stats
```
Track cache effectiveness and resource usage patterns.

## 🎯 **Step 5: Team-Specific Recommendations**

### For {team_size.title()} Teams:
{_get_team_specific_recommendations(team_size, deployment_frequency)}

## 🔄 **Step 6: Continuous Improvement**

### Regular Reviews:
- Monthly performance analysis
- Quarterly optimization planning
- Annual architecture review
- Continuous developer feedback

### Optimization Cycles:
1. **Measure**: Collect performance data
2. **Analyze**: Identify bottlenecks
3. **Improve**: Implement optimizations
4. **Validate**: Measure improvement impact

Current Focus: {optimization_goal}
        """

    @mcp.prompt("resource-efficiency")
    async def resource_efficiency_prompt(
        project_id: str,
        pipeline_id: int,
        cost_concern: str = "medium",
        resource_type: str = "compute",
        optimization_timeframe: str = "immediate",
    ) -> str:
        """Analyze and optimize pipeline resource usage"""

        cost_levels = {
            "low": "Minor cost optimization needed",
            "medium": "Moderate cost reduction opportunities",
            "high": "Significant cost optimization required",
            "critical": "Immediate cost reduction essential",
        }

        resource_types = {
            "compute": "CPU and memory optimization",
            "storage": "Disk and artifact storage optimization",
            "network": "Network bandwidth and transfer optimization",
            "time": "Execution time and scheduling optimization",
        }

        return f"""
# 💰 Resource Efficiency Analysis
## Project {project_id}, Pipeline {pipeline_id}

### 🎯 **Resource Optimization Focus**
- **Cost Priority**: {cost_levels[cost_concern]}
- **Resource Type**: {resource_types[resource_type]}
- **Timeframe**: {optimization_timeframe}

## 📊 **Step 1: Resource Usage Analysis**

### Current Resource Consumption:
```
Resource: gl://pipeline/{project_id}/{pipeline_id}
```

### Detailed Job Analysis:
```
Tool: failed_pipeline_analysis
Parameters: project_id="{project_id}", pipeline_id={pipeline_id}
```

## 🔍 **Step 2: Efficiency Opportunities**

### Compute Optimization:
- **Right-sizing**: Match resource allocation to actual usage
- **Scheduling**: Optimize job scheduling and queuing
- **Parallelization**: Maximize concurrent execution
- **Resource Pooling**: Share resources across jobs

### Storage Optimization:
- **Artifact Management**: Optimize artifact size and retention
- **Cache Strategy**: Implement efficient caching
- **Data Transfer**: Minimize unnecessary data movement
- **Storage Tiers**: Use appropriate storage classes

### Time Optimization:
- **Critical Path**: Identify and optimize longest job chains
- **Idle Time**: Minimize resource idle time
- **Queue Management**: Optimize job queuing and execution

## 💡 **Step 3: Cost Reduction Strategies**

### Immediate Actions:
- [ ] Review job resource allocations
- [ ] Implement basic caching
- [ ] Optimize artifact retention policies
- [ ] Right-size compute resources

### Short-term Improvements:
- [ ] Advanced caching strategies
- [ ] Pipeline parallelization
- [ ] Resource sharing optimization
- [ ] Monitoring and alerting setup

### Long-term Optimization:
- [ ] Infrastructure architecture review
- [ ] Advanced scheduling strategies
- [ ] Cost monitoring and budgeting
- [ ] Resource usage optimization

## 📈 **Step 4: ROI Analysis**

### Cost-Benefit Assessment:
- **Current Costs**: Resource usage patterns
- **Optimization Investment**: Time and effort required
- **Expected Savings**: Projected cost reduction
- **Risk Assessment**: Potential impacts

### Optimization Priority Matrix:
| Action | Effort | Impact | Priority |
|--------|--------|--------|----------|
| Resource right-sizing | Low | High | P0 |
| Cache implementation | Medium | High | P1 |
| Pipeline parallelization | High | Medium | P2 |

## 🎯 **Step 5: Implementation Plan**

### Week 1-2: Assessment and Quick Wins
- Complete resource usage analysis
- Implement basic optimizations
- Set up monitoring

### Week 3-4: Strategic Improvements
- Implement caching strategies
- Optimize pipeline structure
- Begin parallelization

### Month 2+: Advanced Optimization
- Full pipeline redesign if needed
- Advanced resource management
- Continuous optimization process

Resource Focus: {resource_type}
Cost Priority: {cost_concern}
        """

    def _get_team_specific_recommendations(team_size: str, frequency: str) -> str:
        """Generate team-specific optimization recommendations"""
        recommendations = {
            "small": f"""
**Small Team Optimizations:**
- Simple, maintainable pipeline configurations
- Focus on developer productivity over complex optimization
- Use managed services to reduce maintenance overhead
- Deploy {frequency} with minimal friction
            """,
            "medium": f"""
**Medium Team Optimizations:**
- Balanced approach between simplicity and efficiency
- Implement role-based pipeline access and reviews
- Moderate parallelization and caching strategies
- Deploy {frequency} with proper testing gates
            """,
            "large": f"""
**Large Team Optimizations:**
- Complex but highly efficient pipeline architectures
- Advanced parallelization and resource management
- Comprehensive testing and deployment strategies
- Deploy {frequency} with enterprise-grade controls
            """,
        }
        return recommendations.get(team_size, recommendations["medium"])

    logger.info("Performance prompts registered")
