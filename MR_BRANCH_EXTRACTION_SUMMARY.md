## Merge Request Branch Extraction - Implementation Summary

### ✅ **What Was Added**

1. **New Method in GitLab Client** (`src/gitlab_analyzer/api/client.py`):

   ```python
   async def get_merge_request(self, project_id: str | int, merge_request_iid: int) -> dict[str, Any]:
       """Get merge request information by IID"""
   ```

2. **Enhanced `get_pipeline_info` Tool** (`src/gitlab_analyzer/mcp/tools/info_tools.py`):
   - **Detects MR pipelines** by checking if `ref` starts with `"refs/merge-requests/"`
   - **Extracts MR IID** from ref format: `refs/merge-requests/42/head` → IID = `42`
   - **Fetches MR details** using the new `get_merge_request` method
   - **Resolves source branch** for commits: uses `merge_request_info["source_branch"]`

### 🔧 **New Output Fields**

The `get_pipeline_info` tool now returns:

```json
{
  "original_branch": "refs/merge-requests/42/head", // Original pipeline ref
  "target_branch": "feature-new-functionality", // ⭐ USE THIS FOR COMMITS
  "pipeline_type": "merge_request", // "branch" or "merge_request"
  "merge_request_info": {
    // MR details if applicable
    "id": 999,
    "iid": 42,
    "source_branch": "feature-new-functionality",
    "target_branch": "main",
    "title": "Add new functionality",
    "state": "opened"
  },
  "can_auto_fix": true // Whether auto-fix should proceed
}
```

### 🎯 **How It Solves Your Problem**

**Before:**

```yaml
# Workflow tried to commit to virtual ref
git checkout refs/merge-requests/1/head # ❌ FAILS - Not a real branch
```

**After:**

```yaml
# Workflow uses resolved source branch
git checkout feature-branch # ✅ SUCCESS - Real branch
```

### 📋 **Workflow Integration**

Update your workflow to use the new fields:

```yaml
- id: get_pipeline_info
  output_schema: |
    {
      "target_branch": {"type": "string"},      # Use for Git operations
      "pipeline_type": {"type": "string"},      # "branch" or "merge_request"
      "can_auto_fix": {"type": "boolean"}       # Proceed with auto-fix?
    }
  task: |
    Get pipeline info and resolve target branch:
    - For MR pipelines: extracts source branch from merge request
    - For regular pipelines: uses original branch
    - Sets can_auto_fix based on resolution success

# Later in commit step:
- id: commit_fixes
  condition: "can_auto_fix == true"
  task: |
    git checkout {target_branch}     # ← Use this instead of original_branch
    git add .
    git commit -m "Auto-fix errors"
    git push origin {target_branch}
```

### 🧪 **Test Cases Added**

1. **Regular Branch Pipeline**: `feature-branch` → `target_branch: "feature-branch"`
2. **MR Pipeline**: `refs/merge-requests/42/head` → `target_branch: "feature-new-functionality"`
3. **MR Fetch Error**: Falls back gracefully, sets `can_auto_fix: false`
4. **Invalid MR Ref**: Handles parsing errors, sets `can_auto_fix: false`

### 🚀 **Usage Example**

```python
# The tool automatically detects and resolves:
result = await get_pipeline_info(project_id="123", pipeline_id=456)

if result["pipeline_type"] == "merge_request":
    print(f"MR Pipeline: {result['original_branch']}")
    print(f"Commit to: {result['target_branch']}")  # Real source branch
else:
    print(f"Regular Pipeline: {result['target_branch']}")

if result["can_auto_fix"]:
    # Proceed with auto-fix using target_branch
    pass
```

### ✨ **Benefits**

- ✅ **Fixes the core issue**: No more commits to virtual MR refs
- ✅ **Backward compatible**: Regular branch pipelines work as before
- ✅ **Error handling**: Graceful fallback when MR info unavailable
- ✅ **Clear indication**: `can_auto_fix` flag guides workflow decisions
- ✅ **Complete context**: Provides both original ref and resolved branch

The workflow can now confidently use `{target_branch}` for all Git operations, whether it's a regular branch pipeline or a merge request pipeline.
