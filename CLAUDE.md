# CLAUDE.md

This file provides guidance to Claude Code when working with the Photo Bot project.

## Project Overview

A Telegram bot that applies AI-powered photo transformations using Google Gemini, with YooMoney payments ($1.00 per transformation).

## Common Commands

**Run the bot:**
```bash
source .venv/bin/activate
python "Photo bot/photo_bot.py"
```

## Architecture

### Conversation Flow

```
/start → Inline keyboard (pick transformation)
       → User sends photo → Bot stores in memory (user_data)
       → Bot sends YooMoney invoice via Telegram Payments API
       → User pays → Bot sends photo + prompt to Gemini
       → Returns transformed PNG → Cleanup, conversation ends
```

### Conversation States

| State | Trigger | Next State |
|-------|---------|------------|
| CHOOSING | User taps transformation button | WAITING_PHOTO |
| WAITING_PHOTO | User sends a photo | WAITING_PAYMENT |
| WAITING_PAYMENT | Successful payment | END (restart with /start) |

### Available Transformations

Defined in the `TRANSFORMATIONS` dict in `photo_bot.py`:
- **cat_phone** — Replace phone with a cat
- **big_afro** — Big afro haircut

Adding a new transformation only requires adding a new entry with `label` and `prompt` keys.

### Payment Integration

Uses Telegram's native Payments API with YooMoney as the provider:
- Price: $1.00 USD (100 cents) per transformation
- `PreCheckoutQueryHandler` registered at app level (outside ConversationHandler) for immediate response
- Invoice sent inline after photo upload
- No refund logic currently implemented

### Gemini Integration

- Model: `gemini-3-pro-image-preview`
- Input: user photo (PIL Image) + transformation prompt text
- Output: PNG image extracted from response parts
- Synchronous call via `google-genai` SDK

## Configuration

All secrets stored in `Photo bot/.env` and loaded via `python-dotenv`:

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `GEMINI_API_KEY` | Google Gemini API key |
| `YOOMONEY_PROVIDER_TOKEN` | YooMoney payment provider token from BotFather |

Application constants (price, currency, model name, transformations) are defined in `photo_bot.py`.

## Key Files

- `Photo bot/photo_bot.py` — Entire bot logic (single-file architecture)
- `Photo bot/.env` — Environment variables with secrets (not tracked in git)
- `Photo bot/requirements.txt` — Python dependencies
- `Photo bot/Procfile` — Deployment config (`worker: python photo_bot.py`)

## Dependencies

```
python-telegram-bot==22.5
google-genai>=1.61.0
Pillow>=12.0.0
python-dotenv>=1.0.0
```

## Deployment

- Procfile-based (Heroku-ready)
- Runs as a worker process using long polling
- No webhook setup currently — would need to switch for production

## Security Notes

**Protected files (must never be committed to git):**
- `Photo bot/.env` — API keys, bot token, payment provider token

`.gitignore` covers `.env`, `__pycache__/`, `*.pyc`, `.venv/`.

## Known Limitations

- Photos stored in memory (`user_data`) — lost on restart
- No transaction logging or usage analytics
- No per-user rate limiting
- If Gemini fails after payment succeeds, user loses money (no refund flow)
