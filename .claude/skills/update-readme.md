---
name: update-readme
description: Regenerate or update the README.md to reflect the current state of the project, ensuring it remains a complete from-scratch recreation guide.
---

When invoked, review all project files and update README.md so that:

1. The Prerequisites section lists every tool/runtime with version and install command.
2. The Environment Variables section lists every variable with its purpose.
3. The Setup Steps section is a numbered, copy-paste-ready walkthrough.
4. The Architecture section reflects the current src/ layout.
5. The API Coverage section lists all MCP tool names and their mapped endpoints.
6. The Development Log section is up to date (do not remove existing entries).

Read these files before writing: CLAUDE.md, .mcp.json, .claude/claude-style.md, rules/m365/billing-api.md, and any existing src/ files.
