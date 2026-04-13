---
name: log-step
description: Append a dated development log entry to README.md under the Development Log section.
---

The user wants to log a completed step to README.md.

Instructions:
1. Read the current README.md.
2. Find the "## Development Log" section.
3. Append a new entry at the TOP of the log (most recent first) in this format:

```
### [YYYY-MM-DD] <Short title of what was done>

**What changed:**
- <Bullet 1>
- <Bullet 2>

**Files affected:**
- `<file path>` — <why it was changed>

**Commands run (if any):**
```bash
<command>
```
```

4. Write the updated README.md back.
5. If any other files were changed as part of this step (CLAUDE.md, rules files, .mcp.json, etc.), update their content to reflect the new state too.

Today's date: use the currentDate from context.
