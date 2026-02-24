# Notification Strategy

**Last updated:** 2026-02-24

---

## Current State

| Status | Notifications |
|--------|---------------|
| ✅ Implemented | N1, N2, N3, N4, N5, N7, N9 |
| 🚫 Disabled | N6 (overlaps with N2), N8 (reward TBD), N10 (logic TBD) |

**Timezone:** All scheduled times are in **MSK (Moscow, UTC+3)**

---

## All Notifications

| ID | Name | Trigger | Frequency | Type | Schedule |
|----|------|---------|-----------|------|----------|
| **N1** | Welcome Reminder | `created_at <= now-24h AND gen_count = 0 AND credits > 0` | Once/user | Scheduled | Daily 11 AM MSK |
| **N2** | Credits Running Low | `credits = 1 after generation` | Per event | Real-time | — |
| **N3** | Credits Exhausted | `credits = 0 on user action` | Per event | Inline UI | — |
| **N4** | Win-Back Offer | `last_active_at <= now-30d AND gen_count >= 1` | Once/user | Scheduled | Weekly Mon 11 AM MSK |
| **N5** | New Effects Available | `admin triggers, targets last_active_at >= now-14d` | Manual | Admin | — |
| **N6** | ~~Referral Reminder~~ | ~~`gen_count = 3 AND referrals_count = 0`~~ | — | Disabled | — |
| **N7** | First Purchase Thanks | `purchase_count = 1` | Once/user | Real-time | — |
| **N8** | Power User VIP | `gen_count = 25` | Once/user | Real-time | — |
| **N9** | Abandoned Payment | `invoice_sent_at <= now-1h AND paid = 0` | Once/invoice | Scheduled | Daily 11 AM MSK |
| **N10** | Zero Balance Silent | `credits = 0 AND last_active_at <= now-48h` | Once/user | Scheduled | Daily 11 AM MSK |

### Anti-spam rules

- **Scheduled notifications** (N1, N4, N9, N10): Max 1 per user per day. If user already received a scheduled notification today, skip.
- **Real-time notifications** (N2, N6, N7, N8): Not throttled by daily limit — immediate feedback on user action.
- **Inline UI** (N3): Not a push notification — shown in chat as response to user action.
- **Manual** (N5): Not throttled — admin controls when to send.

---

## Detailed Specs

### N1: Welcome Reminder

**Purpose:** Activate new users who signed up but never tried the bot

**Trigger:**
- `created_at <= now-24h`
- `gen_count = 0` (never uploaded a photo)
- `credits > 0` (still has free credits)

**Message:**
```
👋 Привет, {name}!

Ты получил {credits} бесплатных заряда, но ещё не попробовал магию ✨

Попробуй любой эффект — это займёт 1 минуту!

[ ✨ Создать магию ]
```

**Implementation:**
- Cron job at 11 AM MSK (8 AM UTC)
- Log to `notification_log`

---

### N2: Credits Running Low

**Purpose:** Upsell before credits run out

**Trigger:**
- `credits = 1` after generation (real-time check in `handle_photo`)

**Message:**
```
🤫 Никто не знает, что у тебя остался 1 заряд.

Кроме нас. Исправь это — тихо и быстро:

💳 Пополнить → от 99 ₽
👥 Позвать друга → +3 заряда бесплатно

[ 💳 Пополнить     ]
[ 👥 Позвать друга ]
```

**Implementation:**
- Check in `handle_photo()` after deducting credit
- If `remaining == 1`, send notification

---

### N3: Credits Exhausted

**Purpose:** Convert free users to paying users

**Trigger:**
- `credits = 0` when user tries to generate or select effect

**Message:**
```
😮‍💨 Заряды кончились. Бывает.

Но останавливаться необязательно:

💳 Пополнить → от 99 ₽
👥 Позвать друга → +3 заряда бесплатно

[ 💳 Пополнить     ]
[ 👥 Позвать друга ]
```

**Implementation:**
- Inline UI response in `photo_bot.py` (not a push notification)
- Shown in `select_effect()` and `handle_photo()` when credits < 1
- Includes buy button + referral link

---

### N4: Win-Back Offer

**Purpose:** Re-engage churned users

**Trigger:**
- `last_active_at <= now-30d`
- `gen_count >= 1` (was engaged before)
- Not already sent N4

**Message:**
```
👀 Давно не виделись.

Мы не спрашиваем где ты был.
Просто оставили тебе подарок — ⚡ +3 заряда уже на балансе.

Есть новые эффекты. Посмотришь?

[ ✨ Посмотреть ]
```

**Implementation:**
- Runs in daily cron, but only on Mondays (`weekday() == 0`)
- Gives +3 free credits automatically
- Log to `notification_log`

---

### N5: New Effects Available

**Purpose:** Announce new content to active users

**Trigger:**
- Admin triggers manually from admin panel
- Targets users with `last_active_at >= now-14d`

**Message:**
```
🔥 Новый дроп!

{drop_name}

[ ✨ Смотреть ]
```

**Implementation:**
- Admin panel button "📢 Announce new effects"
- Admin confirms effect list before sending

---

### N6: Referral Reminder

**Purpose:** Drive viral growth

**Trigger:**
- `gen_count = 3` (user just completed 3rd generation)
- `referrals_count = 0` (hasn't referred anyone yet)

**Message:**
```
🔥 Тебе нравится бот?

Пригласи друзей и получай +3 заряда за каждого!

👥 Твоя реферальная ссылка:
{ref_link}

[ 👥 Поделиться ссылкой ]
```

**Implementation:**
- Check after each generation in `handle_photo()`
- Send once per user
- Button opens Telegram share sheet

---

### N7: First Purchase Thank You

**Purpose:** Welcome first-time buyers

**Trigger:**
- `purchase_count = 1` (just made first purchase)

**Message:**
```
🎉 Ты с нами!

Спасибо — это многое значит.

Создавай магию без ограничений ✨
```

**Implementation:**
- Check in `successful_payment()` handler
- Send once per user

---

### N8: Power User VIP

**Purpose:** Retain and reward power users

**Trigger:**
- `gen_count = 25` (just reached 25 generations)

**Message:**
```
👑 Ты стал VIP-пользователем!

🎉 25 магических трансформаций — впечатляет!

🎁 Твой эксклюзивный бонус:
Промокод {promo_code} → +5 зарядов бесплатно

Спасибо, что ты с нами! ✨

[ 🎁 Активировать бонус ]
```

**Implementation:**
- Check after each generation in `handle_photo()`
- Auto-create promo code `VIP25-{user_id}` with 5 credits
- Send once per user

---

### N9: Abandoned Payment

**Purpose:** Recover incomplete purchases

**Trigger:**
- `invoice_sent_at <= now-1h`
- `paid = 0` (payment not completed)

**Message:**
```
👀 Кто-то не завершил покупку.

{package_name} — {price} ₽

Если передумал — всё нормально.
Если нет — вот кнопка 👇

[ 💳 Завершить покупку ]
```

**Implementation:**
- Invoice tracked in `invoices` table (recorded in `buy_package()`, marked paid in `successful_payment()`)
- Checked in daily cron job
- Send once per invoice

---

### N10: Zero Balance Silent

**Purpose:** Re-engage users who ran out of credits and went silent

**Trigger:**
- `credits = 0`
- `last_active_at <= now-48h` (no activity for 48 hours)
- Not already sent N10

**Message:**
```
👋 Привет!

Твой баланс всё ещё на нуле.

Пополни заряды — и продолжай создавать магию! ✨

💡 10 зарядов всего за 99 ₽

[ 💳 Пополнить баланс ]
```

**Implementation:**
- Daily cron job at 11 AM MSK (8 AM UTC)
- Log to `notification_log`

---

## Technical Architecture

### Notification types

| Type | Notifications | Where | Throttling |
|------|---------------|-------|------------|
| Scheduled | N1, N4, N9, N10 | `jobs/notification_jobs.py` | Max 1 scheduled/user/day |
| Real-time | N2, N6, N7, N8 | `photo_bot.py` handlers | Per-notification dedup only |
| Inline UI | N3 | `photo_bot.py` inline response | None (direct response) |
| Manual | N5 | Admin panel in `photo_bot.py` | None (admin-controlled) |

### Files

| File | Role |
|------|------|
| `docs/NOTIFICATION_STRATEGY.md` | Message UI (edit here to change wording) |
| `notifications.py` | Send + log + dedup engine (strings live inline) |
| `jobs/notification_jobs.py` | Cron entry point for scheduled notifications |
| `photo_bot.py` | Real-time triggers + inline UI + admin panel |

### Database tables

- `notification_log` — tracks sent notifications (dedup + analytics)
- `invoices` — tracks sent invoices for N9 abandoned payment detection
- `users.last_active_at` — tracks last user interaction for N4, N5, N10

### Cron schedule

```
0 8 * * *  →  11 AM MSK  →  runs N1, N4 (Mon only), N9, N10
```

Admin summary sent to ADMIN_ID after all jobs complete.

---

## Related Documentation

- **[DATA_ANALYSIS.md](DATA_ANALYSIS.md)** — Metrics and analytics
- **[PROMO_AND_REFERRALS.md](PROMO_AND_REFERRALS.md)** — Promo codes and referral system
