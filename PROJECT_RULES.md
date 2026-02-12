# PROJECT_RULES.md

Shared project rules for coding agents working in `Photo bot/`.

## Scope

- Applies to all code and docs in `Photo bot/`.
- Environment and project-wide defaults are defined in this file and reused by agent-specific entrypoints.

## Project Summary

Telegram bot for AI photo transformations using Google Gemini and a credit/payments flow.

## Core Commands

```bash
source .venv/bin/activate
python "Photo bot/photo_bot.py"          # run bot
python "Photo bot/test_prompt.py"        # test a prompt (edit testing/prompt.txt first)
```

## Effects Management

Effects are configured in `effects.yaml`.

- `prompts/{effect_id}.txt` is required for each effect.
- `images/{effect_id}.jpg` is optional (also `.png`/`.webp`).

### Add A New Effect

1. Create `prompts/my_effect.txt`.
2. Optional: add `images/my_effect.jpg`.
3. Register the effect in `effects.yaml`.

```yaml
my_effect:
  enabled: true
  order: 3
  label: "My Effect"
  category: style
```

### Categories And Nesting

Use `parent` in `categories` to create nesting (up to 3 levels):

```yaml
categories:
  hairstyle:
    enabled: true
    order: 1
    label: "💇 Причёски"
    parent: style
```

## Prompt Safety

Avoid prompt wording that commonly triggers Gemini safety blocks.

- Avoid explicit nudity/sexual wording.
- Avoid combinations involving children and body/sexual context.
- Prefer neutral art/style references when intent is stylistic.

## Credits And Referrals

- New users start with `3` free credits.
- Deduct a credit on photo upload.
- Refund the credit if generation fails.
- Referrer receives `+3` when the referred user completes their first successful generation.

## Must-Read Docs By Area

- Conversation flow, FSM, DB schema: `docs/ARCHITECTURE.md`
- Deployment, hosting, storage: `docs/DEPLOYMENT.md`
- Pricing, packages, payments: `docs/PRICING.md`
- Task planning and roadmap: `docs/ROADMAP.md`
- Secrets and repository hygiene: `docs/SECURITY.md`

## Security Baseline

- Never commit secrets.
- Keep credentials/tokens in `.env`.
- Ensure `.env` and credential files are ignored by git.

## Command Execution

- Ask for user confirmation before executing any bash/shell command.
