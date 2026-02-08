# duo

A minimal two-agent fullstack template for Claude Code + Antigravity.

## What's in the box

```
CLAUDE.md              # Always-loaded instructions for Claude Code
PLAN.md                # Living plan — single source of truth for both agents
FRONTEND_AGENT.md      # System prompt you paste into Antigravity
.claude/skills/prompt/ # Skill to regenerate the frontend agent prompt
```

## Setup

1. Copy these files into your project root.
2. Fill in `PLAN.md` with your project overview, stack, and initial tasks.
3. Run `/prompt` in Claude Code to tailor `FRONTEND_AGENT.md` to your stack.
4. Paste `FRONTEND_AGENT.md` contents into Antigravity as your system prompt.
5. Start building.

## How it works

- Claude Code handles backend + orchestration. Antigravity handles frontend + visual verification.
- Both agents read `PLAN.md` for tasks and API contracts.
- When backend changes affect frontend contracts, Claude Code flags them with `⚠️ CONTRACT CHANGED`.
- The frontend agent builds against contracts, screenshots its work, and verifies visually.

## Rules of thumb

- If PLAN.md isn't scannable in 30 seconds, simplify it.
- Don't add files to this system unless you've hit a real problem that requires it.
- Git is your history. PLAN.md is your present.
```
