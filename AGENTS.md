# AGENTS.md

Codex entrypoint for `Photo bot/`.

## Read First

1. `PROJECT_RULES.md` (shared instructions)
2. Then open area-specific docs from `docs/` based on the task

## Agent Notes

- Follow `PROJECT_RULES.md` as the default behavior.
- Keep edits minimal and localized.
- Prefer updating existing scripts/config over introducing new tooling.

## User Communication Preference

- The user is not a coder; default to plain language.
- Explain actions step by step with clear next clicks/commands.
- Before changes, state what will be changed and why.
- After changes, always include:
  1. What changed
  2. Why it changed
  3. What to do next
- Avoid jargon; if needed, explain it briefly.
- Provide copy-paste-ready commands with exact paths when terminal steps are required.
