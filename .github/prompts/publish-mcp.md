---
mode: "agent"
tools:
  [
    "githubRepo",
    "codebase",
    "runTests",
    "testFailure",
    "findTestFiles",
    "runCommands",
    "editFiles",
    "changes",
    "activePullRequest",
  ]
description: "Publish a new version of the mcp to pypi using githab actions approach"
---

Your goal is to prepare and release a new version of the mcp to publish to pypi.

Use the following steps:

1. Please review github actions for process
2. Update version everywhere (do not forget uv.lock to be synchronised)
3. Pass all the needed checks (tests, lints, etc....)
   - in case ony of linters/tests are failing - try to fix them
4. Update release changes doc
5. Commit all changes with right commit message based on changes - and push
6. Wait until cicd process is completed on github
   - if eny errors - analyse using tox and fix
7. Create tag after cicd on the github will complete succesfully
8. push tag
