# CLAUDE.md

This file provides guidance to Claude Code when working with the Photo Bot project.

## Project Overview

A Telegram bot that applies AI-powered photo transformations using Google Gemini, with a credit-based payment system via YooMoney.

**Key Features:**
- 3 free generations for new users
- Package purchases (5/10/25/50/100 credits in RUB)
- Promo code system
- Referral system (+3 credits when invited friend generates first photo)
- Admin panel with statistics (per-effect and per-package breakdown)
- Hybrid keyboard (persistent reply keyboard + inline buttons)
- "О проекте" section with 18+ disclaimer and support link

## Common Commands

**Run the bot:**
```bash
source .venv/bin/activate
python "Photo bot/photo_bot.py"
```

**Admin commands (in Telegram):**
- `/admin` — Open admin panel (requires ADMIN_ID in .env)

## Architecture

### Conversation Flow

```
/start → Main Menu (with balance + persistent reply keyboard)
       ├── ✨ Создать магию → Categories → Тренды / Меняем стиль → Effect → Description → Photo → Result
       ├── 💳 Пополнить запасы → Package selection → Payment → Confirmation
       ├── 🎁 Промокод → Enter code → Success/Failure
       ├── 👥 Пригласить друга → Show referral link
       └── ℹ️ О проекте → Disclaimer + Support link

/admin → Admin Panel (ADMIN_ID only)
       ├── Статистика → User count, generations, revenue, per-effect stats, per-package breakdown
       └── Создать промокод → Select amount (10/25/50/100) → Show generated code
```

### Conversation States

| State | Description |
|-------|-------------|
| MAIN_MENU | Main menu displayed |
| CHOOSING_CATEGORY | Picking effect category |
| CHOOSING_TREND | In "Тренды" submenu |
| CHOOSING_STYLE | In "Меняем стиль" submenu |
| WAITING_PHOTO | Awaiting photo upload |
| STORE | Viewing package store |
| WAITING_PAYMENT | Invoice sent |
| PROMO_INPUT | Waiting for promo code text |
| REFERRAL | Viewing referral screen |
| ABOUT | Viewing "О проекте" screen |
| ADMIN_MENU | Admin main menu |
| ADMIN_STATS | Viewing statistics |
| ADMIN_PROMO | Choosing promo credit amount |

### Effect Categories

Two categories under "Создать магию":
- **Тренды** — seasonal/occasion-based effects (rotates by modifying `category` field)
- **Меняем стиль** — hairstyle/appearance changes (static)

### Credit System

- New users get 3 free credits
- Credit deducted when photo upload starts
- Credit refunded if Gemini fails
- Referrer gets +3 credits when referred user completes first generation

### Database Schema

**users** — User accounts and balances
**promo_codes** — Created promo codes
**promo_redemptions** — Tracks who redeemed which codes
**generations** — Each generation (for per-effect statistics)
**purchases** — Package purchase history (for revenue tracking)

## Configuration

All secrets stored in `Photo bot/.env` and loaded via `python-dotenv`:

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `GEMINI_API_KEY` | Google Gemini API key |
| `YOOMONEY_PROVIDER_TOKEN` | YooMoney payment provider token from BotFather |
| `ADMIN_ID` | Your Telegram user ID (for /admin access) |
| `BOT_USERNAME` | Bot username for referral links (without @) |
| `SUPPORT_USERNAME` | Support account username for "О проекте" (optional, without @) |

## Key Files

| File | Purpose |
|------|---------|
| `photo_bot.py` | Main bot logic, handlers, conversation flow |
| `database.py` | SQLite database operations |
| `effects.yaml` | Effect definitions (labels, prompts, tips, images) |
| `images/` | Example images for effects |
| `photo_bot.db` | SQLite database file (auto-created) |
| `.env` | Environment variables with secrets |
| `requirements.txt` | Python dependencies |
| `Procfile` | Deployment config |

## Dependencies

```
python-telegram-bot==22.5
google-genai>=1.61.0
Pillow>=12.0.0
python-dotenv>=1.0.0
PyYAML>=6.0
```

## Pricing (RUB)

| Package | Price | Per photo |
|---------|-------|-----------|
| 10 фото | 99 ₽ | 9.90 ₽ |
| 25 фото | 229 ₽ | 9.16 ₽ |
| 50 фото | 399 ₽ | 7.98 ₽ |
| 100 фото | 699 ₽ | 6.99 ₽ |

## Managing Effects

Effects are defined in `effects.yaml`. Add new effects there:

```yaml
effect_id:
  enabled: true       # false to hide without deleting (keeps stats)
  order: 10           # display order within category (lower = first)
  label: "🎨 Display Name"
  description: "Description shown to user"
  tips: |
    📸 Рекомендации:
    • Лицо крупным планом
    • Хорошее освещение
  prompt: |
    Detailed prompt for Gemini...
  category: trend     # or: style
  example_image: images/effect_id_example.jpg
```

### Effect Management

| Action | How |
|--------|-----|
| Add new effect | Copy template, fill in fields, set `order` |
| Disable effect | Set `enabled: false` (keeps stats history) |
| Reorder effects | Change `order` values (sorted ascending) |
| Remove effect | Delete from YAML (loses ability to track old stats) |

### Effect Card Structure (shown when user selects effect)

```
┌─────────────────────────────────────────┐
│  [Example Image 800×800]                │
│                                         │
│  💌 Открытка в стиле Love is            │
│                                         │
│  Превращу фото в милую открытку         │
│  в стиле Love is                        │
│                                         │
│  📸 Рекомендации:                       │
│  • Лицо крупным планом                  │
│  • Хорошее освещение                    │
│  • Без очков                            │
│                                         │
│  [❌ Отмена]                            │
└─────────────────────────────────────────┘
```

### Example Image Requirements

| Property | Value |
|----------|-------|
| Size | 800×800 px or 800×1000 px |
| Format | JPG |
| Quality | 80-85% |
| File size | 100-300 KB each |
| Storage | `Photo bot/images/` folder or Telegram file_id |

## Deployment

- Procfile-based (Heroku/Railway/Render ready)
- SQLite database — ensure persistent storage on cloud
- Or migrate to PostgreSQL by modifying `database.py`

## Security Notes

**Protected files (must never be committed to git):**
- `.env` — API keys, bot token, payment provider token
- `photo_bot.db` — User data

`.gitignore` should include `.env`, `*.db`, `__pycache__/`, `.venv/`.

## Session Handoff

**Last updated:** 2026-02-06

**Git status:** Changes pending (effects.yaml added, CLAUDE.md updated)

### Pending Fixes
- [ ] Fix bug: reply keyboard buttons don't work when on layer 2/3 (only work from MAIN_MENU state)
- [ ] Update `SUPPORT_USERNAME` in `.env` — currently set to email, should be Telegram username
- [ ] Update `photo_bot.py` to load effects from `effects.yaml` instead of hardcoded dict

### Content Tasks
- [ ] Add ~50 effects to `effects.yaml` (currently have 4)
- [ ] Add example images to `images/` folder (one per effect)
- [ ] Add welcome screen image (big picture on /start)

### Technical Notes
- Gemini model verified: `gemini-3-pro-image-preview` (Nano Banana Pro)
- Model logging added for debugging
- Effects stored in `effects.yaml` with `enabled` and `order` fields for management
- MVP is feature-complete, ready for content expansion
