# Project Instructions

## Workflow
- This project uses a two-agent workflow: Claude Code (backend + orchestration) and an Antigravity agent (frontend + visual verification).
- Both agents coordinate through `PLAN.md` at the project root. This is the single source of truth.
- When you complete a task, update `PLAN.md` to reflect current status.
- When I say "sync", re-read `PLAN.md` and pick up the next incomplete task.
- When API contracts change, update them inline in `PLAN.md` under the relevant task so the frontend agent stays in sync.

## PLAN.md Format
- Tasks are split into `## Backend` and `## Frontend` sections.
- Each task has a status: `[ ]` todo, `[~]` in progress, `[x]` done.
- API contracts (endpoint, method, request/response shape) live inline under the task that introduces them.
- Keep it scannable. If I can't understand project state in 30 seconds, it's too verbose.

## Frontend Agent
- The frontend agent is a separate context (Antigravity/Gemini) that reads `PLAN.md` for contracts and task assignments.
- Do NOT do frontend work unless I explicitly ask. Frontend tasks belong to the other agent.
- If a backend change affects a frontend contract, update `PLAN.md` and flag it with `⚠️ CONTRACT CHANGED` so the frontend agent notices.

## Skills
- `/prompt` — Generates or updates `FRONTEND_AGENT.md`, the system prompt for the Antigravity agent. Run this at project start or when the stack/scope changes significantly.

## General
- Prefer simple solutions over clever ones.
- Don't overplan small tasks. If it's a one-file change, just do it.
- Ask me before making architectural decisions that affect both agents.
