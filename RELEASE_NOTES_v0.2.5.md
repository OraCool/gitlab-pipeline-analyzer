# Release Notes v0.2.5

**Release Date**: August 18, 2025
**Version**: 0.2.5
**GitLab Pipeline Analyzer MCP Server**

## 🎯 Release Highlights

This release focuses on **MCP metadata standardization** and **enhanced tool consistency** across the entire GitLab Pipeline Analyzer MCP server ecosystem.

### 🆕 New Features

#### New Tool: `get_pipeline_info`

- **Comprehensive pipeline information retrieval** with full metadata support
- **Original branch extraction** from pipeline refs for better context
- **MCP metadata integration** for consistent tool tracking
- **Enhanced debugging capabilities** with version and timestamp information

#### MCP Metadata Standardization

- **All 16+ tools** now return consistent MCP metadata structure:
  ```json
  {
    "mcp_info": {
      "name": "GitLab Pipeline Analyzer",
      "version": "0.2.5",
      "analysis_timestamp": "2025-08-18T19:36:35Z"
    }
  }
  ```

### ✨ Enhancements

#### Tool Response Consistency

- **Standardized metadata** across all analysis, pytest, info, log, and pagination tools
- **Enhanced error context** with better categorization and structured responses
- **Improved tool documentation** with AI analysis tips and usage patterns

#### Code Quality Improvements

- **100% Ruff compliance** - All linting issues resolved
- **100% MyPy type safety** - All type checking issues fixed
- **Production readiness** with comprehensive quality assurance

### 🐛 Bug Fixes

#### Type Safety

- **Fixed type annotations** in pagination tools for better IDE support
- **Resolved generator comprehension** issues (C401 violations)
- **Improved function signatures** with proper return type hints

#### Response Standardization

- **Consistent error handling** across all tools
- **Standardized success response formats** for better client integration
- **Enhanced error messages** with more context and debugging information

### 🔧 Technical Improvements

#### Testing & Quality Assurance

- **207 tests passing** with 71.73% coverage maintained
- **Zero security vulnerabilities** detected by Bandit analysis
- **Validated distribution packages** ready for PyPI publishing

#### Developer Experience

- **Complete prepublish validation pipeline** implemented
- **Enhanced version detection** with robust fallback mechanisms
- **Updated documentation** with version 0.2.5 references throughout

## 📊 Quality Metrics

| Metric          | Status             | Details            |
| --------------- | ------------------ | ------------------ |
| **Tests**       | ✅ 207/207 passing | 71.73% coverage    |
| **Type Safety** | ✅ 100% clean      | MyPy validation    |
| **Code Style**  | ✅ 100% compliant  | Ruff linting       |
| **Security**    | ✅ 0 issues        | Bandit analysis    |
| **Build**       | ✅ Validated       | Twine check passed |

## 🚀 Migration Guide

### For Existing Users

**No breaking changes** - all existing tools continue to work exactly as before.

### New MCP Metadata

All tool responses now include additional metadata:

```python
# Before v0.2.5
{
  "project_id": "123",
  "pipeline_id": 456,
  "errors": [...]
}

# After v0.2.5
{
  "project_id": "123",
  "pipeline_id": 456,
  "errors": [...],
  "mcp_info": {
    "name": "GitLab Pipeline Analyzer",
    "version": "0.2.5",
    "analysis_timestamp": "2025-08-18T19:36:35Z"
  }
}
```

### New Tool Available

```python
# Get comprehensive pipeline information
result = await client.call_tool("get_pipeline_info", {
    "project_id": "123",
    "pipeline_id": 456
})

# Returns pipeline details with MCP metadata
print(result["original_branch"])  # e.g., "feature/new-auth"
print(result["mcp_info"]["version"])  # "0.2.5"
```

## 🛠️ Installation

### Via uvx (Recommended)

```bash
uvx --from gitlab-pipeline-analyzer==0.2.5 gitlab-analyzer
```

### Via pip

```bash
pip install gitlab-pipeline-analyzer==0.2.5
```

### Via uv

```bash
uv add gitlab-pipeline-analyzer==0.2.5
```

## 🔍 What's Next

### Upcoming Features (v0.2.6+)

- **Enhanced error grouping** by file and error type
- **Performance optimizations** for large pipeline analysis
- **Additional GitLab API integrations** for merge request context
- **Extended MCP metadata** with more debugging information

### Long-term Roadmap

- **Multi-tenant support** for different GitLab instances
- **Caching mechanisms** for improved performance
- **Real-time pipeline monitoring** capabilities
- **Integration with other CI/CD platforms**

## 📝 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for the complete list of changes.

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: [README.md](README.md)

---

**Thank you for using GitLab Pipeline Analyzer MCP Server!** 🎉
