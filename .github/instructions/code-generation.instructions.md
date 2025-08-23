---
applyTo: "**"
---

Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.

- always use "uv" when running the \*.py files or python based scripts /packages
- always ensure proper cleanup of not needed files before commit
- for terminal commands like "find", "grep" initially identify what command is available in the environment (it may be "fd". "rg". Check parameters for the command)
- do not create big inputs for terminal commands as it freezes the terminal
- do not use cat just to view files as it do not return to the terminal
