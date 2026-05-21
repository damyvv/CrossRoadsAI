---
name: implement-issue
description: Automatically implement a GitHub issue by fetching the issue details, creating a feature branch, implementing changes using TDD, and creating a PR. Use when user provides an issue ID (e.g., #42) and wants the agent to implement the feature end-to-end.
---

# Implement Issue

Automates the full workflow to implement a GitHub feature issue: fetching requirements, branching, implementing with tests, committing, and opening a PR.

## Quick start

```
User: Implement #42
Agent: 
  1. Read issue #42 to understand requirements
  2. Run a grill-with-docs session to validate and clarify requirements and acceptance criteria before implementing
  3. Checkout and pull latest master
  4. Create feature branch (e.g., feat/42-descriptive-name)
  5. Use /tdd skill to implement changes
  6. Commit and push
  7. Create PR back to master
```

## Workflow

### 1. Parse issue ID

Extract issue number from user input (e.g., `#42` → `42`).

### 2. Fetch issue details

Use GitHub API to read:
- Issue title
- Description/acceptance criteria
- Labels
- Any linked PRs/issues

### 3. Run grill-with-docs session

Before writing code, run a `grill-with-docs` session targeting the issue and the project's documentation (CONTEXT.md, ADRs, and relevant docs). The session should:
- Ask clarifying questions about acceptance criteria, edge cases, and ambiguous requirements.
- Confirm which files, configs, or components will change.
- Produce a concise checklist or update to the issue body summarizing the agreed scope.

### 4. Setup feature branch

Unless user specifies a different base branch:
- Fetch latest: `git checkout master && git pull origin master`
- Create feature branch: `git checkout -b feat/<issue-number>-<kebab-case-title>`
  - Example: `#42 Add user authentication` → `feat/42-add-user-authentication`

### 4. Implement with TDD

Use the `/tdd` skill to:
- Write failing tests first
- Implement code to make tests pass
- Follow red-green-refactor cycle
- Ensure all tests pass

### 5. Commit and push

- Stage changes: `git add -A`
- Commit with conventional message: `feat: <description>` (matching issue scope)
- Push feature branch: `git push origin feat/<issue-number>-...`

### 6. Create PR

Open pull request:
- Base: `master` (or user-specified branch)
- Head: feature branch
- Title: Match issue title or customize if needed
- Body: Include `Closes #<issue-number>` so issue auto-closes on merge
- Link any related work

## Customization

**Alternative base branch**: Ask user `Which branch should I base this on?` if not specified.

**Commit message**: Follow project conventions (e.g., Conventional Commits). Include issue reference.

**PR template**: If project has a PR template, use it as a starting point.

## Error handling

- **Issue not found**: Stop and report the issue number was invalid
- **Branch exists**: Ask user: `Feature branch already exists. Continue from there or delete and recreate?`
- **TDD fails**: Report which test failed and show output; ask user to provide clarification on requirements
- **Push fails**: Check for remote tracking issues; guide user on resolution
