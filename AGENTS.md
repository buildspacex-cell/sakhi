# AGENTS.md

## Persistent Workflow Rule

For all coding and code-review tasks in this repository:

1. Use `CLAUDE.md` as the default execution guide before implementing changes.
2. Follow project conventions and commands from `CLAUDE.md` for build, test, lint, and verification.
3. Include a `CLAUDE checklist` section in every final coding-task update.
4. Apply the `Documentation Sync Policy` below on every code change.

## Context Bootstrap (Required For Coding Tasks)

Before implementing changes, use these docs as baseline context:

- `CLAUDE.md`
- `CHANGELOG.md` (`[Unreleased]` section)
- `docs/CODEBASE_CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/WHAT_WE_BUILT.md`
- `docs/BUILD_PLAN.md`
- `docs/TEST_STATUS.md`
- `docs/EXECUTION_PRIORITY.md`

When relevant to the area being changed, also load feature docs in `docs/features/`.

For substantial implementation/debugging tasks, run:

- `./scripts/context-audit.sh`

and use its output to verify current counts, routing shape, simulation data health, and test harness validity before editing.

## Documentation Sync Policy

If code changes, documentation impact must be evaluated in the same task.

Change-to-doc mapping:

- API routes/services/workers/engines changed:
  - Update `docs/ARCHITECTURE.md` and `docs/WHAT_WE_BUILT.md` if counts/structure changed.
- Simulation/demo/governance flow changed:
  - Update `docs/BUILD_PLAN.md`, `docs/WHAT_WE_BUILT.md`, and related `docs/features/*`.
- Test counts/coverage/status changed:
  - Update `docs/TEST_STATUS.md`.
- Priority or rollout sequencing changed:
  - Update `docs/EXECUTION_PRIORITY.md`.
- User-visible milestone shipped:
  - Update `CHANGELOG.md` (`[Unreleased]`).
- Repository structure/service inventory changed:
  - Update `CLAUDE.md`.

Rule:

- If any mapped doc is not updated, final response must explicitly state `No doc update` with a reason.

## CLAUDE Checklist (Required In Final Coding Updates)

- `CLAUDE.md consulted`: yes/no
- `Canonical paths used`: yes/no
- `Validation run`: list commands executed and results
- `DB/Migration impact`: none or summarized with safeguards
- `Residual risks / follow-ups`: brief list

## Documentation Checklist (Required In Final Coding Updates)

- `Docs reviewed for context`: list
- `Docs updated`: list of files changed (or `none`)
- `Reason for no doc updates`: required when `none`
- `Changelog updated`: yes/no + reason
- `Counts/dates verified`: yes/no

## Scope

- Applies to coding, debugging, refactors, tests, and code reviews.
- Not required for casual chat or non-coding conversation.
