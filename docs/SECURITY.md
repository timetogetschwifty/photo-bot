# Security

## Protected files (must never be committed)
- `.env` — API keys, bot token, payment provider token
- `photo_bot.db` — User data

## .gitignore must include
`.env`, `*.db`, `__pycache__/`, `.venv/`

## Personal Data Collection

**⚠️ IMPORTANT: When adding new personal data fields, update this section immediately!**

### Data Stored in Database (`photo_bot.db`)

| Data Type | Location | Purpose | Retention |
|-----------|----------|---------|-----------|
| **Telegram User ID** | `users.telegram_id` | Required for bot operation, user identification | Permanent (until user deletion) |
| **Telegram Username** | `users.username` | Display purposes, referral tracking | Permanent (updates automatically) |
| **Referral Chain** | `users.referred_by` | Credit referrer when new users join | Permanent |
| **Usage History** | `generations.user_id`, `generations.effect_id` | Statistics, analytics | Permanent |
| **Purchase History** | `purchases.user_id`, `purchases.package_credits`, `purchases.price_rub` | Revenue tracking, analytics | Permanent |
| **Promo Code Redemptions** | `promo_redemptions.user_id`, `promo_redemptions.code` | Prevent duplicate redemptions | Permanent |

### Data NOT Stored

| Data Type | How Handled |
|-----------|-------------|
| **User Photos** | Processed in memory only, immediately discarded after transformation |
| **Generated Images** | Sent to user via Telegram, not stored on server |
| **Chat History** | Not logged or stored |
| **Payment Details** | Handled by YooMoney, not stored locally |
| **Session Data** | Stored in memory only (cleared on bot restart) |

### Privacy Principles

1. **No Persistence** - Bot does not use disk-based session persistence to avoid storing chat IDs and session state
2. **Minimal Collection** - Only collect data required for bot operation and basic analytics
3. **No Photo Storage** - User photos are never saved to disk
4. **Database Storage** - All data stored in SQLite file (`photo_bot.db`)
   - **Local development**: Stored in project directory
   - **Production (Railway)**: Stored on persistent volume at `/data/photo_bot.db`
5. **No Third-Party Analytics** - No external tracking services (except Telegram, Google Gemini for image processing, YooMoney for payments)

### When to Update This Document

**You MUST update this section when:**
- Adding new columns to any database table
- Storing any new user-identifiable information
- Changing data retention policies
- Adding new third-party services that process user data
- Implementing any form of logging that includes user data

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `GEMINI_API_KEY` | Google Gemini API key |
| `YOOMONEY_PROVIDER_TOKEN` | YooMoney payment provider token from BotFather |
| `ADMIN_ID` | Your Telegram user ID (for /admin access) |
| `BOT_USERNAME` | Bot username for referral links (without @) |
| `SUPPORT_USERNAME` | Support account username for "О проекте" (optional, without @) |
| `DB_PATH` | Database file path (Railway: `/data/photo_bot.db`, local: auto-detected) |
