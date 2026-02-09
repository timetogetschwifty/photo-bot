# CLAUDE.md

Telegram bot — AI photo transformations via Google Gemini, credit-based payments via YooMoney.

## Commands

```bash
source .venv/bin/activate
python "Photo bot/photo_bot.py"          # run bot
python "Photo bot/test_prompt.py"        # test a prompt (edit testing/prompt.txt first)
```

## Managing Effects

Effects defined in `effects.yaml`. Prompts and images auto-resolved by effect ID:
- `prompts/{effect_id}.txt` — Gemini prompt (required)
- `images/{effect_id}.jpg` — example image (optional, also .png/.webp)

### Adding an effect

1. Create `prompts/my_effect.txt`
2. (Optional) Add `images/my_effect.jpg`
3. Add to `effects.yaml`:

```yaml
my_effect:
  enabled: true
  order: 3
  label: "My Effect"
  category: style       # omit for top-level
```

### Subcategories

Categories support `parent` field for nesting (up to 3 levels):

```yaml
categories:
  hairstyle:
    enabled: true
    order: 1
    label: "💇 Причёски"
    parent: style          # makes this a subcategory of style
```

## Prompt Safety

Avoid words that trigger Gemini safety filters: naked, nude, bare, undressed, explicit, children + body terms. Use art style references instead (e.g., "in the style of Kim Casali's Love Is cards").

## Credit System

- 3 free credits for new users
- Credit deducted on photo upload, refunded if Gemini fails
- Referrer gets +3 credits when referred user completes first generation

## Additional Docs

Read these BEFORE working on related areas:

| When working on... | Read |
|---------------------|------|
| Conversation flow, states, DB schema | `docs/ARCHITECTURE.md` |
| Deployment, hosting, storage | `docs/DEPLOYMENT.md` |
| Pricing, packages, payments | `docs/PRICING.md` |
| Tasks, planned features | `docs/ROADMAP.md` |
| Secrets, .env, .gitignore | `docs/SECURITY.md` |
