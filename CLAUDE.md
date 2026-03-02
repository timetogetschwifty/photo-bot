# CLAUDE.md

Claude entrypoint for `Photo bot/`.

## Read First

1. `PROJECT_RULES.md` (shared instructions for all agents)
2. Then open area-specific docs from `docs/` based on the task

## Agent Notes

- Follow `PROJECT_RULES.md` as the source of truth.
- Keep task-specific reasoning and outputs concise.

## SQLite Gotchas

- `ALTER TABLE ADD COLUMN` does NOT support `DEFAULT CURRENT_TIMESTAMP` (or any non-constant default). Add the column without a default, then backfill with `UPDATE`.

## Code Change Rules

- **Keep scope tight.** Change only what is required for the requested task. Do not touch adjacent code, even if it looks improvable.
- **No refactors.** Do not refactor, rename, clean up, or reformat any code. If a refactor appears genuinely necessary to implement the change, stop and ask first.
- **No UI/flow side effects.** Do not change button visibility, labels, navigation, routing, menu structure, auto-selection, auto-jumps, redirects, or conversation flow unless explicitly part of the task.
- **No silent removals.** Do not remove, hide, or repurpose existing controls or flows unless explicitly requested.
- **No additions beyond the task.** Do not add error handling, logging, validation, comments, imports, or new dependencies unless explicitly asked.
- **Read before editing.** Inspect the relevant code before making any changes.
- **State plan before acting.** State what will be edited and what will remain unchanged. For changes touching UI, shared logic, or user-visible flows, wait for confirmation before proceeding.
- **Stop on scope expansion.** If completing the task requires changes outside the requested scope, stop and ask before editing.
- **Respect existing work.** Do not revert or rewrite unrelated uncommitted changes in the worktree.
- **Report on completion.** List all changed files and functions. Explicitly call out any behavior changes outside the original request.
- **UI changes require spec check.** Before any change touching buttons, copy, navigation, or state transitions, read `docs/UI_FLOW_v3.md`, identify the affected screen(s) by name, and confirm the change is within spec. If it deviates, stop and ask.

