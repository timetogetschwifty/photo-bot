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
