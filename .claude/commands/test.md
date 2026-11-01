---
description: Run the test suite and summarize any failures
allowed-tools: Bash(pytest*), Bash(python3 -m pytest*), Bash(npm test*), Read, Grep, Glob
---
Run the full test suite for this project.

Steps:
1. Run the tests (use `pytest` for Python, `npm test` for Node).
2. If everything passes, report the count and stop.
3. If anything fails, list each failing test with the file:line and the specific assertion that broke.
4. Do NOT fix anything yet — just diagnose.

Extra context from the user: $ARGUMENTS
