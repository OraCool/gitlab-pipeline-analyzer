"""
Educational and learning prompts for CI/CD knowledge building

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging

logger = logging.getLogger(__name__)


def register_educational_prompts(mcp) -> None:
    """Register educational and learning prompts with MCP server"""

    @mcp.prompt("learning-path")
    async def learning_path_prompt(
        user_experience: str = "intermediate",
        focus_areas: list[str] | None = None,
        time_commitment: str = "moderate",
        learning_style: str = "hands_on",
    ) -> str:
        """Generate personalized CI/CD learning paths"""

        areas = focus_areas or ["gitlab_ci", "debugging", "optimization"]

        experience_levels = {
            "beginner": "New to CI/CD and GitLab",
            "intermediate": "Some CI/CD experience, want to improve",
            "advanced": "Experienced, looking for optimization and best practices",
            "expert": "Expert level, focusing on cutting-edge practices",
        }

        time_commitments = {
            "light": "1-2 hours per week",
            "moderate": "3-5 hours per week",
            "intensive": "10+ hours per week",
        }

        learning_styles = {
            "theoretical": "Documentation and concept-based learning",
            "hands_on": "Practical examples and experimentation",
            "problem_solving": "Real-world problem analysis and solutions",
            "collaborative": "Team-based learning and knowledge sharing",
        }

        return f"""
# 📚 Personalized CI/CD Learning Path
## Experience Level: {experience_levels[user_experience]}

### 🎯 **Learning Configuration**
- **Focus Areas**: {", ".join(areas)}
- **Time Commitment**: {time_commitments[time_commitment]}
- **Learning Style**: {learning_styles[learning_style]}

## 🗺 **Learning Roadmap**

### Phase 1: Foundation Building
{_get_foundation_curriculum(user_experience, areas)}

### Phase 2: Practical Application
{_get_practical_curriculum(user_experience, areas)}

### Phase 3: Advanced Concepts
{_get_advanced_curriculum(user_experience, areas)}

### Phase 4: Mastery & Teaching
{_get_mastery_curriculum(user_experience, areas)}

## 🛠 **Hands-On Practice Exercises**

### Exercise 1: Pipeline Analysis
```
Use this MCP server to analyze a real pipeline failure:
Tool: failed_pipeline_analysis
Parameters: project_id="[your_project]", pipeline_id="[failed_pipeline]"
```

**Learning Goals:**
- Understanding pipeline structure
- Error identification and categorization
- Root cause analysis techniques

### Exercise 2: Performance Investigation
```
Analyze pipeline performance:
Tool: search_repository_code
Parameters: search_keywords="performance OR optimization", project_id="[your_project]"
```

**Learning Goals:**
- Performance bottleneck identification
- Optimization strategy development
- Resource usage analysis

### Exercise 3: Debugging Workflow
```
Practice systematic debugging:
Prompt: test-failure-debugging
Parameters: project_id="[project]", job_id="[failed_job]"
```

**Learning Goals:**
- Structured debugging approach
- Tool selection and usage
- Problem-solving methodology

## 📖 **Knowledge Building Activities**

### For {learning_style.replace("_", " ").title()} Learners:
{_get_learning_style_activities(learning_style, user_experience)}

## 🎯 **Skill Assessment Checkpoints**

### Checkpoint 1: Basic Competency (Week 2-4)
- [ ] Can read and understand pipeline configurations
- [ ] Can identify common error types
- [ ] Can use basic MCP tools for analysis
- [ ] Understands GitLab CI/CD concepts

### Checkpoint 2: Practical Skills (Week 6-8)
- [ ] Can debug pipeline failures independently
- [ ] Can optimize basic performance issues
- [ ] Can create effective pipeline configurations
- [ ] Can use advanced MCP tools and prompts

### Checkpoint 3: Advanced Proficiency (Week 10-12)
- [ ] Can design complex CI/CD architectures
- [ ] Can lead debugging and optimization efforts
- [ ] Can mentor others in CI/CD practices
- [ ] Can contribute to process improvements

## 🚀 **Next Steps & Continuous Learning**

### Daily Practice:
- Analyze one pipeline failure using MCP tools
- Review team pipeline configurations
- Experiment with optimization techniques

### Weekly Goals:
- Complete learning exercises
- Share knowledge with team members
- Document lessons learned

### Monthly Reviews:
- Assess skill progression
- Update learning goals
- Plan advanced topics

Time Commitment: {time_commitment}
        """

    @mcp.prompt("knowledge-sharing")
    async def knowledge_sharing_prompt(
        project_id: str,
        investigation_context: str = "",
        sharing_scope: str = "team",
        documentation_level: str = "detailed",
    ) -> str:
        """Generate knowledge sharing documentation from investigations"""

        sharing_scopes = {
            "personal": "Personal learning notes and reference",
            "team": "Team knowledge base and shared learnings",
            "organization": "Company-wide best practices and patterns",
            "community": "Public documentation and community contribution",
        }

        documentation_levels = {
            "minimal": "Basic problem and solution summary",
            "standard": "Detailed analysis with steps and reasoning",
            "detailed": "Comprehensive documentation with examples",
            "tutorial": "Step-by-step educational content",
        }

        return f"""
# 📝 Knowledge Sharing Documentation
## Project {project_id}

### 🎯 **Documentation Configuration**
- **Context**: {investigation_context or "General CI/CD knowledge"}
- **Sharing Scope**: {sharing_scopes[sharing_scope]}
- **Documentation Level**: {documentation_levels[documentation_level]}

## 📋 **Documentation Template**

### Problem Summary
**What happened?**
- Brief description of the issue
- Impact assessment
- Timeline of events

**Investigation Context:**
{investigation_context}

### Investigation Process
**Tools and Prompts Used:**
```
Tool: failed_pipeline_analysis
Parameters: project_id="{project_id}", pipeline_id="[pipeline_id]"

Prompt: pipeline-investigation
Parameters: project_id="{project_id}", pipeline_id="[pipeline_id]"
```

**Step-by-Step Analysis:**
1. Initial problem identification
2. Data gathering and analysis
3. Root cause investigation
4. Solution development
5. Implementation and validation

### Key Findings
**Root Cause:**
- Technical cause
- Contributing factors
- Environmental conditions

**Contributing Factors:**
- Process issues
- Knowledge gaps
- Tool limitations

### Solution Implementation
**Immediate Fix:**
- What was done to resolve the immediate issue
- Validation steps taken
- Impact verification

**Long-term Prevention:**
- Process improvements
- Monitoring enhancements
- Team training needs

### Lessons Learned
**Technical Insights:**
- New tool techniques discovered
- Effective investigation patterns
- Optimization opportunities identified

**Process Improvements:**
- Communication enhancements
- Documentation gaps filled
- Training needs identified

## 🎓 **Educational Value**

### Key Concepts Demonstrated:
- CI/CD best practices
- Debugging methodologies
- Tool usage patterns
- Problem-solving approaches

### Reusable Patterns:
- Investigation workflows
- Tool combinations
- Solution templates
- Prevention strategies

## 🔄 **Knowledge Transfer Activities**

### For {sharing_scope.title()} Sharing:
{_get_sharing_activities(sharing_scope, documentation_level)}

## 📚 **Related Resources**

### MCP Tools for Similar Issues:
- `failed_pipeline_analysis` - Primary analysis tool
- `search_repository_code` - Code pattern investigation
- `pipeline-investigation` - Structured investigation workflow
- `fix-strategy-planner` - Solution development guidance

### Documentation Templates:
- Post-mortem reports
- Investigation runbooks
- Tool usage guides
- Best practice documentation

## 🎯 **Follow-Up Actions**

### Immediate:
- [ ] Document current investigation
- [ ] Share with intended audience
- [ ] Update team knowledge base
- [ ] Create prevention measures

### Long-term:
- [ ] Review effectiveness of shared knowledge
- [ ] Update documentation based on feedback
- [ ] Create additional learning materials
- [ ] Contribute to community knowledge

Sharing Level: {sharing_scope}
Documentation Depth: {documentation_level}
        """

    @mcp.prompt("mentoring-guide")
    async def mentoring_guide_prompt(
        mentee_experience: str = "beginner",
        mentoring_focus: str = "general",
        session_type: str = "investigation",
        learning_objectives: list[str] | None = None,
    ) -> str:
        """Guide for mentoring others in CI/CD and debugging skills"""

        objectives = learning_objectives or [
            "debugging_skills",
            "tool_usage",
            "problem_solving",
        ]

        experience_approaches = {
            "beginner": "Focus on fundamental concepts and guided practice",
            "intermediate": "Emphasize independent problem-solving with guidance",
            "advanced": "Collaborative investigation and knowledge sharing",
        }

        mentoring_focuses = {
            "general": "Broad CI/CD and debugging skills",
            "tools": "Specific tool usage and techniques",
            "process": "Investigation processes and methodologies",
            "troubleshooting": "Problem-solving and critical thinking",
        }

        return f"""
# 👥 CI/CD Mentoring Guide
## Mentee Level: {mentee_experience.title()}

### 🎯 **Mentoring Session Configuration**
- **Focus Area**: {mentoring_focuses[mentoring_focus]}
- **Session Type**: {session_type}
- **Learning Objectives**: {", ".join(objectives)}
- **Approach**: {experience_approaches[mentee_experience]}

## 📋 **Session Structure**

### Opening (10 minutes)
- Review previous learning
- Set session objectives
- Introduce current problem/topic

### Guided Investigation (30-40 minutes)
{_get_guided_investigation_structure(mentee_experience, mentoring_focus)}

### Knowledge Consolidation (10-15 minutes)
- Summarize key learnings
- Document insights
- Plan follow-up practice

## 🛠 **Hands-On Learning Activities**

### Activity 1: Tool Exploration
**Objective**: Familiarize with MCP tools
```
Start with basic analysis:
Tool: failed_pipeline_analysis
Parameters: project_id="[safe_project]", pipeline_id="[example_failure]"
```

**Mentoring Points:**
- Explain tool purpose and output
- Guide interpretation of results
- Connect to broader concepts

### Activity 2: Structured Investigation
**Objective**: Learn systematic debugging
```
Use investigation prompt:
Prompt: pipeline-investigation
Parameters: project_id="[project]", pipeline_id="[pipeline]", focus_area="[area]"
```

**Mentoring Points:**
- Emphasize systematic approach
- Explain decision-making process
- Encourage questioning and exploration

### Activity 3: Independent Problem-Solving
**Objective**: Build confidence and skills
- Present a new problem
- Guide through investigation process
- Provide feedback and suggestions

## 🎓 **Teaching Strategies**

### For {mentee_experience.title()} Mentees:
{_get_teaching_strategies(mentee_experience, mentoring_focus)}

## 📊 **Progress Assessment**

### Knowledge Check Questions:
1. What tools would you use for [specific scenario]?
2. How would you approach [type of problem]?
3. What patterns do you see in [investigation results]?
4. How would you prevent [identified issue]?

### Practical Skills Assessment:
- [ ] Can navigate MCP tools independently
- [ ] Understands investigation methodology
- [ ] Can explain technical concepts clearly
- [ ] Shows problem-solving progression

## 🚀 **Skill Building Progression**

### Session 1-3: Foundation
- Basic tool usage
- Understanding pipeline structure
- Simple error identification

### Session 4-6: Application
- Independent investigation
- Complex problem analysis
- Tool combination techniques

### Session 7-9: Mastery
- Advanced optimization
- Mentoring others
- Process improvement

## 🔄 **Continuous Improvement**

### Feedback Collection:
- Session effectiveness
- Learning pace assessment
- Tool usage confidence
- Knowledge retention

### Adaptation Strategies:
- Adjust pace based on progress
- Focus on challenging areas
- Provide additional resources
- Encourage peer learning

Focus: {mentoring_focus}
Experience Level: {mentee_experience}
        """


def _get_foundation_curriculum(experience: str, areas: list[str]) -> str:
    """Generate foundation curriculum based on experience and focus areas"""
    curriculums = {
        "beginner": """
**Week 1-2: CI/CD Fundamentals**
- Understanding pipelines and jobs
- GitLab CI/CD basics
- Common failure types
- Introduction to MCP tools

**Week 3-4: Basic Debugging**
- Reading error messages
- Using failed_pipeline_analysis
- Simple investigation workflows
        """,
        "intermediate": """
**Week 1: Advanced Pipeline Concepts**
- Complex pipeline patterns
- Resource optimization basics
- Error categorization

**Week 2: Tool Mastery**
- All MCP tools overview
- Advanced search techniques
- Resource-based navigation
        """,
        "advanced": """
**Week 1: Architecture Patterns**
- Pipeline design principles
- Performance optimization
- Security considerations
        """,
    }
    return curriculums.get(experience, curriculums["intermediate"])


def _get_practical_curriculum(experience: str, areas: list[str]) -> str:
    """Generate practical curriculum"""
    return f"""
**Hands-on Practice with {", ".join(areas)}:**
- Real-world problem solving
- Tool combination techniques
- Investigation methodology
- Performance analysis
    """


def _get_advanced_curriculum(experience: str, areas: list[str]) -> str:
    """Generate advanced curriculum"""
    return """
**Advanced Topics:**
- Complex debugging scenarios
- Performance optimization
- Architecture design
- Best practices development
    """


def _get_mastery_curriculum(experience: str, areas: list[str]) -> str:
    """Generate mastery curriculum"""
    return """
**Mastery Level:**
- Teaching and mentoring others
- Contributing to tools and processes
- Leading optimization initiatives
- Creating best practices
    """


def _get_learning_style_activities(style: str, experience: str) -> str:
    """Generate learning style specific activities"""
    activities = {
        "hands_on": """
**Practical Activities:**
- Live pipeline debugging sessions
- Tool experimentation and exploration
- Real problem-solving exercises
- Build and break scenarios
        """,
        "theoretical": """
**Conceptual Learning:**
- Documentation deep-dives
- Architecture pattern studies
- Best practices research
- Tool capability analysis
        """,
        "problem_solving": """
**Challenge-Based Learning:**
- Complex debugging scenarios
- Performance optimization challenges
- Investigation competitions
- Root cause analysis exercises
        """,
        "collaborative": """
**Team Learning:**
- Pair debugging sessions
- Knowledge sharing presentations
- Tool technique exchanges
- Collaborative problem solving
        """,
    }
    return activities.get(style, activities["hands_on"])


def _get_sharing_activities(scope: str, level: str) -> str:
    """Generate sharing activities based on scope and level"""
    activities = {
        "team": """
**Team Knowledge Sharing:**
- Weekly debugging sessions
- Tool technique sharing
- Best practices documentation
- Peer mentoring programs
        """,
        "organization": """
**Organizational Knowledge:**
- Cross-team learning sessions
- Best practices standardization
- Tool training programs
- Process improvement initiatives
        """,
        "community": """
**Community Contribution:**
- Public documentation
- Open source contributions
- Conference presentations
- Blog posts and tutorials
        """,
    }
    return activities.get(scope, activities["team"])


def _get_guided_investigation_structure(experience: str, focus: str) -> str:
    """Generate guided investigation structure"""
    structures = {
        "beginner": """
**Guided Discovery:**
- Start with tool demonstration
- Walk through each step together
- Explain reasoning behind each action
- Encourage questions throughout
        """,
        "intermediate": """
**Collaborative Investigation:**
- Present problem together
- Guide tool selection
- Support independent analysis
- Provide feedback and corrections
        """,
        "advanced": """
**Peer Collaboration:**
- Discuss complex scenarios
- Share advanced techniques
- Collaborative problem solving
- Knowledge exchange
        """,
    }
    return structures.get(experience, structures["intermediate"])


def _get_teaching_strategies(experience: str, focus: str) -> str:
    """Generate teaching strategies"""
    strategies = {
        "beginner": """
**Scaffolded Learning:**
- Start with simple, clear examples
- Use consistent terminology
- Provide step-by-step guidance
- Celebrate small victories
        """,
        "intermediate": """
**Guided Independence:**
- Provide frameworks and patterns
- Support decision-making process
- Encourage experimentation
- Review and refine techniques
        """,
        "advanced": """
**Collaborative Exploration:**
- Discuss complex scenarios
- Share cutting-edge techniques
- Peer learning and teaching
- Innovation and improvement
        """,
    }
    return strategies.get(experience, strategies["intermediate"])


logger.info("Educational prompts registered")
