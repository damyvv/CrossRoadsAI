# Copilot Instructions

## Repository State

This repository is in early setup. Currently it contains only the agent skills configuration — no application code, build system, or tests exist yet.

## Agent Skills

Skills are managed via `skills-lock.json` and installed into `.agents/skills/`. They are sourced from `mattpocock/skills` on GitHub.

Installed skills:
- `caveman` — ultra-compressed communication mode
- `diagnose` — disciplined bug/regression diagnosis loop
- `grill-me` — stress-test a plan via relentless questioning
- `grill-with-docs` — grilling session that updates CONTEXT.md and ADRs inline
- `handoff` — compact conversation into a handoff document
- `improve-codebase-architecture` — find refactoring and deepening opportunities
- `prototype` — build throwaway prototypes (terminal app or UI variations)
- `tdd` — test-driven development with red-green-refactor loop
- `to-issues` — break a plan into independently-grabbable issue tracker tickets
- `to-prd` — convert conversation context into a PRD on the issue tracker
- `triage` — manage issues through a triage state machine
- `write-a-skill` — create new agent skills
- `zoom-out` — step back and re-evaluate the current approach

Each skill lives in `.agents/skills/<name>/SKILL.md`. To invoke a skill, ask Copilot to use it by name.

To add or update skills, edit `skills-lock.json` and re-run the skills install command.
