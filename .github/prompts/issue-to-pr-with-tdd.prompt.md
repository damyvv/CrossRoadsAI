---
name: issue-to-pr-with-tdd
description: "Implement a GitHub issue with /tdd workflow, create a feature branch, and prepare a PR summary"
argument-hint: "Issue reference and short scope (example: #42 add yellow-all-red safety tick)"
agent: agent
---
Create and execute a focused implementation workflow for the provided GitHub issue using the `/tdd` skill.

Input:
- User argument: issue reference and scope details

Workflow:
1. Parse the issue reference and summarize acceptance criteria.
2. Detect whether the issue links to a parent PRD and parse that PRD for product context, constraints, and non-goals.
3. Use `/tdd` to implement the issue with red-green-refactor discipline, grounded in both issue and parent PRD context.
4. Create a feature branch before code changes using this naming rule:
   - `feature/issue-<number>-<short-kebab-summary>` when issue number is known
   - `feature/<short-kebab-summary>` when issue number is not known
5. Run the relevant test suite and ensure it passes.
6. If `gh` CLI is available and authenticated, create the PR (`gh pr create`) using the generated title/body.
7. Produce a ready-to-paste PR package that includes:
   - PR title
   - PR body with: problem, solution, tests, and risks/notes
   - Commit message suggestion
   - Verification commands executed and outcomes

Execution rules:
- Keep scope limited to the issue.
- Prefer smallest safe change set.
- If acceptance criteria are missing or ambiguous, ask targeted follow-up questions before coding.
- If tests fail for unrelated pre-existing reasons, report them separately and continue only when safe.
- If `gh` is unavailable, provide exact commands for branch push and manual PR creation.
- If issue and parent PRD conflict, prefer the issue for implementation details and call out the conflict in `Open Questions`.

Output format:
- `Branch:` <name>
- `Context Sources:` issue link + parent PRD link (or `No PRD linked`)
- `Plan:` concise bullets
- `Changes:` files and key modifications
- `Tests:` commands and pass/fail
- `PR Title:` ...
- `PR Body:` markdown
- `PR URL:` ... (or `Not created`)
- `Commit Message:` ...
- `Open Questions:` only if blockers remain
