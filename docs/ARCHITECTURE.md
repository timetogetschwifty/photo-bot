# Architecture

## Conversation Flow

```
/start → Main Menu (with balance + persistent reply keyboard)
       ├── ✨ Создать магию → Browse (categories/subcategories/effects) → Photo → Result
       ├── 💳 Пополнить запасы → Package selection → Payment → Confirmation
       ├── 🎁 Промокод → Enter code → Success/Failure
       ├── 👥 Пригласить друга → Show referral link
       └── ℹ️ О проекте → Disclaimer + Support link

/admin → Admin Panel (ADMIN_ID only)
       ├── Статистика → User count, generations, revenue, per-effect stats, per-package breakdown
       └── Создать промокод → Select amount (10/25/50/100) → Show generated code
```

## Conversation States

| State | Description |
|-------|-------------|
| MAIN_MENU | Main menu displayed |
| BROWSING | Navigating categories/subcategories/effects (any depth) |
| WAITING_PHOTO | Awaiting photo upload |
| STORE | Viewing package store |
| WAITING_PAYMENT | Invoice sent |
| PROMO_INPUT | Waiting for promo code text |
| REFERRAL | Viewing referral screen |
| ABOUT | Viewing "О проекте" screen |
| ADMIN_MENU | Admin main menu |
| ADMIN_STATS | Viewing statistics |
| ADMIN_PROMO | Choosing promo credit amount |

## Effect Hierarchy

Effects support 3 levels of nesting via YAML config:
- **Level 0** — no category, shows on "Create" screen directly
- **Level 1** — `category: X`, shows under category X
- **Level 2** — category has `parent: X`, creates subcategories

## Database Schema

| Table | Purpose |
|-------|---------|
| users | User accounts and balances |
| promo_codes | Created promo codes |
| promo_redemptions | Tracks who redeemed which codes |
| generations | Each generation (for per-effect statistics) |
| purchases | Package purchase history (for revenue tracking) |
| notification_log | Tracks sent notifications (prevents spam, measures effectiveness) |

## Key Files

| File | Purpose |
|------|---------|
| `photo_bot.py` | Main bot logic, handlers, conversation flow |
| `database.py` | SQLite database operations |
| `notifications.py` | Notification system (N1, N3, etc.) |
| `effects.yaml` | Effect/category config (labels, order, enabled, hierarchy) |
| `prompts/` | Prompt text files, auto-resolved by `{effect_id}.txt` |
| `images/` | Example images, auto-resolved by `{effect_id}.jpg` |
| `jobs/notification_jobs.py` | Scheduled notification tasks (N1 daily reminder) |
| `migrations/` | Database schema migrations |
| `reports/export_csv.py` | Export data to CSV for analysis |
| `test_prompt.py` | CLI tool to test prompts without running the bot |

## Runtime Config

| Setting | Value | Location |
|---------|-------|----------|
| Gemini model | `gemini-3-pro-image-preview` | `GEMINI_MODEL` in `photo_bot.py` |
