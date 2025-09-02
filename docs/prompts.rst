Intelligent Prompts & Workflows
===============================

The GitLab Pipeline Analyzer MCP Server provides **13+ specialized prompts** across **5 categories** to guide users through complex CI/CD analysis workflows. These prompts combine domain expertise with contextual guidance for efficient problem-solving.

.. toctree::
   :maxdepth: 2
   :caption: Prompt Categories:

Overview
--------

Our intelligent prompt system transforms the MCP server from a simple tool collection into a comprehensive CI/CD intelligence platform. Each prompt is designed with:

- **Role-based customization** - Adapted for different user expertise levels
- **Progressive complexity** - From basic debugging to advanced optimization
- **Contextual awareness** - Leverages current pipeline state and history
- **Collaborative features** - Supports team learning and knowledge sharing

Available Prompt Categories
---------------------------

🔧 **Advanced Workflow Prompts** (3 prompts)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**investigation-wizard**
   Multi-step guided investigation with role-based customization

   - **Purpose**: Progressive analysis workflow from basic to advanced
   - **Roles**: Beginner, Intermediate, Expert, SRE, Manager
   - **Features**: Context continuity, resource optimization, documentation generation
   - **Use Cases**: Complex failure investigation, root cause analysis

**pipeline-comparison**
   Compare failed vs successful pipelines for regression detection

   - **Purpose**: Identify changes that introduced failures
   - **Features**: Branch comparison, commit analysis, configuration drift detection
   - **Use Cases**: Regression analysis, change impact assessment

**fix-strategy-planner**
   Comprehensive fix planning with resource and impact assessment

   - **Purpose**: Strategic approach to pipeline remediation
   - **Features**: Resource planning, timeline estimation, risk assessment
   - **Use Cases**: Large-scale fixes, team coordination, change management

⚡ **Performance & Optimization Prompts** (3 prompts)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**performance-investigation**
   Pipeline performance analysis and bottleneck identification

   - **Purpose**: Optimize pipeline execution time and resource usage
   - **Features**: Timing analysis, resource utilization, optimization recommendations
   - **Use Cases**: Slow pipelines, resource optimization, cost reduction

**ci-cd-optimization**
   Comprehensive pipeline optimization across multiple dimensions

   - **Purpose**: Holistic pipeline efficiency improvement
   - **Features**: Cache optimization, parallelization, artifact management
   - **Use Cases**: Pipeline modernization, efficiency improvement

**resource-efficiency**
   Resource usage optimization and cost analysis

   - **Purpose**: Minimize infrastructure costs while maintaining performance
   - **Features**: Usage pattern analysis, cost calculation, optimization strategies
   - **Use Cases**: Budget optimization, resource planning

📚 **Educational & Learning Prompts** (3 prompts)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**learning-path**
   Personalized CI/CD learning with hands-on practice

   - **Purpose**: Skill development through practical experience
   - **Features**: Progressive learning, practical exercises, skill assessment
   - **Use Cases**: Team training, skill development, onboarding

**knowledge-sharing**
   Documentation and knowledge transfer templates

   - **Purpose**: Capture and share CI/CD expertise across teams
   - **Features**: Documentation templates, best practices, lesson learned capture
   - **Use Cases**: Team knowledge sharing, documentation improvement

**mentoring-guide**
   Mentor guidance for teaching CI/CD concepts

   - **Purpose**: Support mentors in teaching CI/CD skills
   - **Features**: Teaching strategies, concept explanations, progress tracking
   - **Use Cases**: Mentoring programs, skill development, team growth

🎯 **Original Investigation Prompts** (4 prompts)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**pipeline-investigation**
   Comprehensive pipeline failure analysis

   - **Purpose**: Systematic approach to pipeline debugging
   - **Features**: Step-by-step analysis, error categorization
   - **Use Cases**: General pipeline failures, systematic debugging

**error-analysis**
   Detailed error analysis and resolution guidance

   - **Purpose**: Deep-dive into specific error types
   - **Features**: Error pattern recognition, solution recommendations
   - **Use Cases**: Complex errors, recurring issues

**test-failure-debugging**
   Specialized test failure investigation

   - **Purpose**: Focus on test-specific failure patterns
   - **Features**: Test isolation, dependency analysis, test environment issues
   - **Use Cases**: Pytest failures, test environment problems

**build-failure-debugging**
   Build process failure analysis

   - **Purpose**: Compilation and build system issues
   - **Features**: Dependency analysis, build tool troubleshooting
   - **Use Cases**: Build failures, dependency conflicts

Usage Examples
--------------

**Starting an Investigation**

.. code-block:: text

   User: I need help analyzing a failed pipeline. I'm new to CI/CD.
   Assistant: I'll use the investigation-wizard prompt in beginner mode to guide you through
   the analysis step by step.

**Performance Optimization**

.. code-block:: text

   User: Our pipelines are taking too long to complete.
   Assistant: Let me use the performance-investigation prompt to analyze your pipeline
   timing and identify bottlenecks.

**Team Learning**

.. code-block:: text

   User: I want to help my team learn CI/CD best practices.
   Assistant: I'll use the mentoring-guide prompt to create a structured learning plan
   with practical exercises.

Prompt Integration with Tools
-----------------------------

All prompts are designed to work seamlessly with the MCP server's 12 core tools:

- **failed_pipeline_analysis** - Core analysis engine
- **search_repository_code** - Code investigation support
- **search_repository_commits** - Change history analysis
- **get_mcp_resource** - Efficient data access
- **get_clean_job_trace** - Detailed log analysis
- **cache_stats** / **cache_health** - Performance monitoring
- **clear_cache** operations - Maintenance support

Best Practices
--------------

**For Users**
- Start with appropriate role level (beginner/intermediate/expert)
- Use investigation-wizard for complex multi-step analysis
- Leverage educational prompts for skill development

**For Teams**
- Use mentoring-guide for knowledge transfer
- Implement knowledge-sharing for documentation
- Apply performance prompts for optimization initiatives

**For Organizations**
- Use advanced workflow prompts for strategic planning
- Implement educational pathways for team development
- Leverage comparison prompts for regression prevention

Next Steps
----------

To explore specific prompts in detail, see the implementation files:

- ``/src/gitlab_analyzer/mcp/prompts/advanced.py`` - Advanced workflow prompts
- ``/src/gitlab_analyzer/mcp/prompts/performance.py`` - Performance optimization prompts
- ``/src/gitlab_analyzer/mcp/prompts/educational.py`` - Learning and mentoring prompts
- ``/src/gitlab_analyzer/mcp/prompts/original.py`` - Original investigation prompts

For practical examples and integration guidance, see :doc:`examples`.
