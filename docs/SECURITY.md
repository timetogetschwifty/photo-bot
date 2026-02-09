# Security

## Protected files (must never be committed)
- `.env` — API keys, bot token, payment provider token
- `photo_bot.db` — User data

## .gitignore must include
`.env`, `*.db`, `__pycache__/`, `.venv/`

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `GEMINI_API_KEY` | Google Gemini API key |
| `YOOMONEY_PROVIDER_TOKEN` | YooMoney payment provider token from BotFather |
| `ADMIN_ID` | Your Telegram user ID (for /admin access) |
| `BOT_USERNAME` | Bot username for referral links (without @) |
| `SUPPORT_USERNAME` | Support account username for "О проекте" (optional, without @) |
