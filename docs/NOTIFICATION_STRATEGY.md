# Notification Strategy

**Last updated:** 2026-02-13
**Purpose:** Complete guide to automated notifications for user engagement and retention

---

## 📱 Current State

**Implemented: 2 notifications (N1, N3)**
**Remaining: 8 notifications**

Currently live:
- ✅ **N3: Credits Exhausted** (real-time) - Upsell when users run out of credits
- ✅ **N1: Welcome Reminder** (code ready, cron setup manual) - Activate inactive users

This document outlines the complete notification strategy to improve:
- **Activation:** Get new users to try their first effect
- **Retention:** Bring back inactive users
- **Monetization:** Convert free users to paying users
- **Virality:** Encourage referrals

---

## 🎯 Notification Philosophy

**Good notifications:**
- ✅ Provide value (new content, offers, reminders)
- ✅ Are timely (right moment in user journey)
- ✅ Are actionable (clear next step)
- ✅ Respect user preferences (not spammy)

**Bad notifications:**
- ❌ Generic ("Hey, come back!")
- ❌ Too frequent (daily spam)
- ❌ No value ("Just checking in")
- ❌ Wrong timing (message about free credits to paying user)

---

## 📊 The 10 Core Notifications

Organized by user lifecycle stage:

**Timezone:** All scheduled times are in **MSK (Moscow, UTC+3)**

| ID | Name | Priority | Schedule | Trigger | Expected Impact |
|----|------|----------|----------|---------|-----------------|
| **N1** | Welcome Reminder | P0 | Daily 10 AM MSK | 24h after signup, 0 generations | +30% activation rate |
| **N2** | Credits Running Low | P0 | Real-time | 1 credit remaining | +20% conversion |
| **N3** | Credits Exhausted | P0 | Real-time | 0 credits, never purchased | +15% conversion |
| **N4** | Win-Back Offer | P0 | Weekly (Mon 11 AM MSK) | 30 days inactive | +10% reactivation |
| **N5** | New Effects Available | P1 | Weekly (Fri 12 PM MSK) | New effects added | +5% engagement |
| **N6** | Referral Reminder | P1 | Event-based | After 3rd generation | +40% referral attempts |
| **N7** | First Purchase Thank You | P1 | Real-time | Immediately after 1st purchase | +10% repeat purchase |
| **N8** | Power User VIP | P2 | Event-based | 25+ generations | +20% loyalty |
| **N9** | Abandoned Payment | P2 | Hourly | Invoice sent, no payment after 1h | +5% conversion |
| **N10** | Admin Daily Digest | P0 | Daily 9 AM MSK | Every morning | Better decision-making |

---

## 📋 Detailed Notification Specs

### **N1: Welcome Reminder** (P0 - Critical)

**Purpose:** Activate new users who signed up but never tried the bot

**Trigger:**
- User registered 24 hours ago
- User has 0 generations (never uploaded a photo)
- User still has 3 free credits

**Target:** New inactive users

**Message:**
```
👋 Привет!

Ты получил 3 бесплатных заряда, но ещё не попробовал магию ✨

Попробуй любой эффект — это займёт 1 минуту!

[Кнопка: ✨ Создать магию]
```

**Implementation:**
- Daily cron job at **10 AM MSK** (7 AM UTC) checks for users matching criteria
- Send message via bot API
- Log to `notification_log` table

**Expected Outcome:** 30% of reminded users try their first generation

**Tracking:**
- Metric: Activation rate (users who generate after N1)
- Query: `SELECT COUNT(*) FROM generations WHERE user_id IN (users who received N1) AND created_at > notification_sent_at`

---

### **N2: Credits Running Low** (P0 - Critical)

**Purpose:** Prepare user for upsell, prevent surprise when credits run out

**Trigger:**
- User has exactly 1 credit remaining
- User has generated 2+ times (engaged user)
- Sent immediately after generation that leaves them with 1 credit

**Target:** Engaged users about to run out

**Message:**
```
⚠️ У тебя остался 1 заряд!

Не хочешь остановиться на самом интересном?

💡 Пополни сейчас и получи:
• 10 зарядов — 99 ₽
• 50 зарядов — 399 ₽ (экономия 20%)

[Кнопка: 💳 Пополнить]
```

**Implementation:**
- Check after every generation (`handle_photo` function)
- If credits == 1 after deduction, send notification
- Don't send if user already bought (check purchases table)

**Expected Outcome:** 20% of users purchase before exhausting credits

---

### **N3: Credits Exhausted** (P0 - Critical)

**Purpose:** Convert free users to paying users

**Trigger:**
- User has 0 credits
- User has never purchased
- User attempted to use bot (clicked "Create" or tried to generate)
- Sent immediately when user hits 0 credits

**Target:** Free users who exhausted credits

**Message:**
```
😢 Заряды закончились!

Но не переживай — продолжить легко:

🎁 Специальное предложение:
10 зарядов всего за 99 ₽

Или пригласи друга и получи +3 заряда бесплатно! 👥

[Кнопка: 💳 Купить заряды]
[Кнопка: 👥 Пригласить друга]
```

**Implementation:**
- Check when user tries to generate with 0 credits
- Or daily job for users with 0 credits who didn't receive this yet
- Mark as sent to avoid spam

**Expected Outcome:** 15% conversion to first purchase

---

### **N4: Win-Back Offer** (P0 - Critical)

**Purpose:** Re-engage users who churned

**Trigger:**
- User hasn't been active for 30 days
- User generated at least 1 time (was engaged before)
- Not sent more than once per user

**Target:** Churned users

**Message:**
```
🎁 Мы скучали по тебе!

С момента твоего последнего визита мы добавили:
• 🆕 10 новых эффектов
• ⚡ +3 бесплатных заряда (подарок от нас!)

Попробуй что-то новое?

[Кнопка: ✨ Посмотреть новое]
```

**Implementation:**
- Weekly cron job (every Monday)
- Query: Users with `last_active_at < date('now', '-30 days')` AND `total_spent > 0`
- Give +3 credits automatically
- Log in promo_redemptions or similar table

**Expected Outcome:** 10% of churned users return

---

### **N5: New Effects Available** (P1 - Important)

**Purpose:** Drive engagement by announcing new content

**Trigger:**
- Weekly notification (every Friday)
- Only to users active in last 14 days
- Only if new effects were added this week

**Target:** Active users

**Message:**
```
🆕 Новые эффекты доступны!

На этой неделе мы добавили:
• 🎭 Гангстер из 90-х
• 👑 Египетский фараон
• 🌟 Голливудская звезда

Попробуй прямо сейчас! ⚡ Доступно зарядов: {credits}

[Кнопка: ✨ Попробовать]
```

**Implementation:**
- Manual: Send via admin panel after adding effects
- Or automated: Weekly job sends if effects added
- Target: `last_active_at > date('now', '-14 days')`

**Expected Outcome:** 5% increase in weekly engagement

---

### **N6: Referral Reminder** (P1 - Important)

**Purpose:** Drive viral growth through referrals

**Trigger:**
- User completed 3rd generation (is now engaged)
- User has never shared referral link (no referrals in database)

**Target:** Engaged users who haven't referred anyone

**Message:**
```
🔥 Тебе нравится бот?

Пригласи друзей и получай +3 заряда за каждого!

👥 Твоя реферальная ссылка:
{referral_link}

Уже пригласил: 0 друзей
Заработал: 0 зарядов

[Кнопка: 👥 Поделиться ссылкой]
```

**Implementation:**
- Check after 3rd generation
- Send once per user
- Button opens Telegram share sheet

**Expected Outcome:** 40% of users attempt to share, 10% succeed

---

### **N7: First Purchase Thank You** (P1 - Important)

**Purpose:** Encourage repeat purchases, build loyalty

**Trigger:**
- Immediately after first successful purchase
- Sent automatically via payment success handler

**Target:** First-time buyers

**Message:**
```
🎉 Спасибо за покупку!

Ты поддерживаешь развитие бота — каждую неделю мы добавляем новые эффекты!

💡 Совет: Пригласи друзей и получай дополнительные заряды бесплатно

⚡ Доступно зарядов: {new_balance}

[Кнопка: ✨ Создать магию]
```

**Implementation:**
- Add to `successful_payment()` function
- Send after crediting purchase
- Log as `first_purchase_thanks_sent`

**Expected Outcome:** 10% higher repeat purchase rate

---

### **N8: Power User VIP** (P2 - Nice to Have)

**Purpose:** Retain and reward high-value users

**Trigger:**
- User reaches 25 generations
- Sent once per user

**Target:** Power users

**Message:**
```
👑 Ты стал VIP-пользователем!

🎉 25 магических трансформаций — впечатляет!

🎁 Твой эксклюзивный бонус:
• Промокод VIP25 → +5 зарядов бесплатно
• Ранний доступ к новым эффектам

Спасибо, что ты с нами! ✨

[Кнопка: 🎁 Активировать бонус]
```

**Implementation:**
- Check after every generation
- If generation count == 25, trigger notification
- Auto-create promo code VIP25-{user_id} with 5 credits

**Expected Outcome:** 20% increase in user loyalty (return rate)

---

### **N9: Abandoned Payment** (P2 - Nice to Have)

**Purpose:** Recover lost revenue from incomplete purchases

**Trigger:**
- User clicked "Buy package" (invoice sent)
- User didn't complete payment within 1 hour
- Sent once per invoice

**Target:** Users who started checkout but didn't pay

**Message:**
```
💳 Забыл завершить покупку?

Пакет ждёт тебя:
{package_name} — {price} ₽

Не упусти — предложение действует 24 часа!

[Кнопка: 💳 Завершить покупку]
```

**Implementation:**
- Log when invoice sent (in user_activity)
- Hourly cron job: Check invoices sent >1h ago without payment
- Send recovery message
- Track with `abandoned_payment_recovered`

**Expected Outcome:** 5% of abandoned payments recovered

---

### **N10: Admin Daily Digest** (P0 - Critical)

**Purpose:** Monitor bot health and make informed decisions

**Trigger:**
- Daily at 9:00 AM (your timezone)
- Sent to admin Telegram ID

**Target:** You (admin)

**Message:**
```
📊 Daily Stats — {date}

👥 Users:
New: {new_users} (+{change} vs yesterday)
Active (7d): {active_users}

💰 Revenue:
Today: {revenue_today} ₽
This week: {revenue_week} ₽

⚡ Generations:
Today: {gen_today}
Failed: {failed_today} ({failure_rate}%)

🔥 Top Effect: {top_effect} ({uses} uses)

🚨 Alerts:
{any_issues}

[Кнопка: 📊 View Dashboard]
```

**Implementation:**
- Use daily report script from ANALYTICS_IMPLEMENTATION.md
- Send via bot.send_message() to ADMIN_ID
- Include alerts (e.g., "Failure rate >10%", "No new users today")

**Expected Outcome:** You stay informed and can act quickly on issues

---

## 🗓️ Notification Schedule

### **Real-Time Notifications** (Immediate)
- N2: Credits Running Low → After generation leaves 1 credit
- N3: Credits Exhausted → When user tries to use bot with 0 credits
- N7: First Purchase Thank You → After successful payment
- N8: Power User VIP → When user hits 25 generations

### **Daily Notifications**
- N1: Welcome Reminder → Daily job at 10 AM, check signups from 24h ago
- N10: Admin Daily Digest → Daily at 9 AM

### **Weekly Notifications**
- N4: Win-Back Offer → Every Monday at 11 AM
- N5: New Effects Available → Every Friday at 12 PM (if new effects added)

### **Hourly Notifications**
- N9: Abandoned Payment → Hourly job, check invoices >1h old

### **Event-Based Notifications**
- N6: Referral Reminder → After 3rd generation

---

## 🛠️ Implementation Roadmap

### **Phase 1: Critical Notifications (Week 1-2)**

Implement these first for maximum impact:

**Priority 0 (Must Have):**
1. **N3: Credits Exhausted** (highest conversion potential)
2. **N10: Admin Daily Digest** (stay informed)
3. **N1: Welcome Reminder** (activate new users)
4. **N2: Credits Running Low** (prevent churn at critical moment)

**Success Metric:** See 10%+ improvement in conversion rate

---

### **Phase 2: Growth Notifications (Week 3-4)**

Add viral and retention features:

**Priority 1 (Should Have):**
5. **N6: Referral Reminder** (drive viral growth)
6. **N4: Win-Back Offer** (recover churned users)
7. **N7: First Purchase Thank You** (build loyalty)
8. **N5: New Effects Available** (engagement driver)

**Success Metric:** 20%+ increase in referrals, 10%+ churned users return

---

### **Phase 3: Optimization (Month 2)**

Fine-tune and add advanced features:

**Priority 2 (Nice to Have):**
9. **N8: Power User VIP** (retain whales)
10. **N9: Abandoned Payment** (revenue recovery)

**Success Metric:** Higher LTV, lower payment drop-off

---

## 💻 Technical Implementation

### **Database Changes Needed**

Add notification tracking table:

```sql
CREATE TABLE IF NOT EXISTS notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    notification_id TEXT NOT NULL,  -- 'N1', 'N2', etc.
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    opened BOOLEAN DEFAULT 0,
    clicked BOOLEAN DEFAULT 0,

    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

CREATE INDEX idx_notif_user ON notification_log(user_id, notification_id);
CREATE INDEX idx_notif_sent ON notification_log(sent_at);
```

**Why:** Track which notifications were sent to prevent spam, measure effectiveness

---

### **New File: `notifications.py`**

Create `Photo bot/notifications.py`:

```python
"""
Notification system for Photo Bot.
Handles all automated user messages.
"""

import logging
from telegram import Bot
from telegram.error import TelegramError
import database as db

logger = logging.getLogger(__name__)

# Store bot instance globally (set on init)
_bot_instance = None

def init_notifications(bot: Bot):
    """Initialize notification system with bot instance."""
    global _bot_instance
    _bot_instance = bot

async def send_notification(
    user_id: int,
    notification_id: str,
    message: str,
    reply_markup=None
) -> bool:
    """
    Send notification to user and log it.

    Returns True if sent successfully, False otherwise.
    """
    if not _bot_instance:
        logger.error("Notification system not initialized")
        return False

    # Check if already sent (for non-repeating notifications)
    if _is_notification_sent(user_id, notification_id):
        logger.info(f"Notification {notification_id} already sent to user {user_id}")
        return False

    try:
        await _bot_instance.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup
        )

        # Log notification
        _log_notification(user_id, notification_id)

        logger.info(f"Sent notification {notification_id} to user {user_id}")
        return True

    except TelegramError as e:
        logger.error(f"Failed to send notification {notification_id} to {user_id}: {e}")
        return False

def _is_notification_sent(user_id: int, notification_id: str) -> bool:
    """Check if notification was already sent to user."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM notification_log WHERE user_id = ? AND notification_id = ?",
        (user_id, notification_id)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

def _log_notification(user_id: int, notification_id: str):
    """Log that notification was sent."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notification_log (user_id, notification_id) VALUES (?, ?)",
        (user_id, notification_id)
    )
    conn.commit()
    conn.close()


# ── Individual Notification Functions ────────────────────────────────────

async def send_welcome_reminder(user_id: int, credits: int) -> bool:
    """N1: Welcome Reminder"""
    message = (
        "👋 Привет!\n\n"
        f"Ты получил {credits} бесплатных заряда, но ещё не попробовал магию ✨\n\n"
        "Попробуй любой эффект — это займёт 1 минуту!"
    )
    # TODO: Add inline keyboard button
    return await send_notification(user_id, "N1", message)


async def send_credits_low_warning(user_id: int, remaining: int) -> bool:
    """N2: Credits Running Low"""
    message = (
        f"⚠️ У тебя остался {remaining} заряд!\n\n"
        "Не хочешь остановиться на самом интересном?\n\n"
        "💡 Пополни сейчас и получи:\n"
        "• 10 зарядов — 99 ₽\n"
        "• 50 зарядов — 399 ₽ (экономия 20%)"
    )
    return await send_notification(user_id, "N2", message)


async def send_credits_exhausted(user_id: int, ref_link: str) -> bool:
    """N3: Credits Exhausted"""
    message = (
        "😢 Заряды закончились!\n\n"
        "Но не переживай — продолжить легко:\n\n"
        "🎁 Специальное предложение:\n"
        "10 зарядов всего за 99 ₽\n\n"
        f"Или пригласи друга и получи +3 заряда бесплатно! 👥\n\n"
        f"Твоя ссылка: {ref_link}"
    )
    return await send_notification(user_id, "N3", message)


# Add more notification functions for N4-N10...
```

---

### **New File: `notification_jobs.py`**

Create `Photo bot/notification_jobs.py`:

```python
"""
Scheduled notification jobs (cron-like tasks).
Run these daily/weekly to send automated notifications.
"""

import asyncio
from datetime import datetime, timedelta
import database as db
import notifications as notif
from telegram import Bot
import os

# Initialize bot
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

async def run_daily_jobs():
    """Run all daily notification jobs."""
    bot = Bot(token=BOT_TOKEN)
    notif.init_notifications(bot)

    # N1: Welcome Reminder (users registered 24h ago, 0 generations)
    await send_welcome_reminders()

    # N10: Admin Daily Digest
    await send_admin_digest()

    print("✅ Daily notification jobs completed")


async def send_welcome_reminders():
    """N1: Send welcome reminders to inactive new users."""
    conn = db.get_connection()
    cursor = conn.cursor()

    # Users registered 24h ago with 0 generations
    cursor.execute("""
        SELECT u.telegram_id, u.credits
        FROM users u
        WHERE date(u.created_at) = date('now', '-1 day')
          AND u.telegram_id NOT IN (SELECT DISTINCT user_id FROM generations)
          AND u.credits > 0
    """)

    users = cursor.fetchall()
    conn.close()

    for user in users:
        await notif.send_welcome_reminder(user['telegram_id'], user['credits'])
        await asyncio.sleep(0.1)  # Rate limit: 10 messages/second

    print(f"✅ Sent {len(users)} welcome reminders")


async def send_admin_digest():
    """N10: Send daily digest to admin."""
    # Use daily_report.py logic
    from reports.daily_report import generate_daily_report

    report = generate_daily_report()

    ADMIN_ID = int(os.getenv("ADMIN_ID"))
    bot = Bot(token=BOT_TOKEN)

    await bot.send_message(chat_id=ADMIN_ID, text=report)
    print("✅ Sent admin daily digest")


# Entry point for cron/scheduler
if __name__ == "__main__":
    asyncio.run(run_daily_jobs())
```

---

### **Integration with Bot Code**

Modify `photo_bot.py` to trigger notifications:

```python
# At top of file
import notifications as notif

# In main() function, after app is built:
notif.init_notifications(app.bot)

# In handle_photo() function, after successful generation:
db_user = db.get_user(user.id)
remaining = db_user["credits"]

# N2: Warn if 1 credit remaining
if remaining == 1:
    await notif.send_credits_low_warning(user.id, remaining)

# In select_effect() function, when credits == 0:
# N3: Upsell exhausted free users
if credits < 1:
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    await notif.send_credits_exhausted(user.id, ref_link)
```

---

### **Scheduling Notifications**

**On Railway (Production):**

Use Railway Cron Jobs or an external scheduler (like Render Cron Jobs):

```yaml
# railway.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "python photo_bot.py"

# Add cron job
[[cron]]
schedule = "0 9 * * *"  # Every day at 9 AM
command = "python notification_jobs.py"
```

**Locally (Testing):**
```bash
# Run manually
python "Photo bot/notification_jobs.py"

# Or use cron
# crontab -e
# Add: 0 9 * * * cd /path/to/project && python "Photo bot/notification_jobs.py"
```

---

## 📊 Measuring Notification Effectiveness

### **Key Metrics Per Notification**

| Notification | Success Metric | How to Measure |
|--------------|----------------|----------------|
| N1: Welcome | Activation rate | % of recipients who generate within 48h |
| N2: Low Credits | Purchase rate | % who buy before exhausting credits |
| N3: Exhausted | Conversion rate | % who purchase after notification |
| N4: Win-Back | Return rate | % who become active again within 7 days |
| N5: New Effects | Engagement lift | Generations increase after notification |
| N6: Referral | Referral rate | % who share link, % of successful referrals |
| N7: Thank You | Repeat purchase | % who buy again within 30 days |
| N8: VIP | Retention | % still active after 90 days |
| N9: Abandoned | Recovery rate | % who complete purchase |
| N10: Admin | Decision quality | Are you taking action based on data? |

---

### **Tracking Queries**

```sql
-- N1 effectiveness (activation after welcome reminder)
SELECT
  COUNT(DISTINCT nl.user_id) as sent,
  COUNT(DISTINCT g.user_id) as activated,
  ROUND(COUNT(DISTINCT g.user_id) * 100.0 / COUNT(DISTINCT nl.user_id), 1) as activation_rate
FROM notification_log nl
LEFT JOIN generations g ON g.user_id = nl.user_id
  AND g.created_at > nl.sent_at
  AND g.created_at < datetime(nl.sent_at, '+48 hours')
WHERE nl.notification_id = 'N1';

-- N3 effectiveness (purchase after credits exhausted notification)
SELECT
  COUNT(DISTINCT nl.user_id) as sent,
  COUNT(DISTINCT p.user_id) as purchased,
  ROUND(COUNT(DISTINCT p.user_id) * 100.0 / COUNT(DISTINCT nl.user_id), 1) as conversion_rate
FROM notification_log nl
LEFT JOIN purchases p ON p.user_id = nl.user_id
  AND p.created_at > nl.sent_at
  AND p.created_at < datetime(nl.sent_at, '+7 days')
WHERE nl.notification_id = 'N3';
```

---

## ⚠️ Best Practices

### **Do's:**
✅ Test notifications on yourself first
✅ Personalize with user's name and data
✅ Include clear call-to-action button
✅ Respect frequency (don't spam)
✅ A/B test message variations
✅ Track open and click rates
✅ Adjust based on data

### **Don'ts:**
❌ Send generic "come back" messages
❌ Send multiple notifications in same day
❌ Use notification as punishment ("You haven't used us!")
❌ Send to users who explicitly churned (blocked bot)
❌ Forget to log notifications (creates spam risk)
❌ Over-promise ("FREE UNLIMITED CREDITS" if not true)

---

## 🚀 Quick Start: Implement First Notification

**Goal:** Get N3 (Credits Exhausted) working in 1 hour

### **Step 1: Add notification_log table (5 min)**
```bash
sqlite3 "Photo bot/photo_bot.db"
```

```sql
CREATE TABLE notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    notification_id TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Step 2: Create notifications.py (10 min)**
Copy the code from "Technical Implementation" section above

### **Step 3: Integrate with bot (10 min)**
Modify `photo_bot.py`:
```python
import notifications as notif

# In main()
notif.init_notifications(app.bot)

# In select_effect() when credits == 0
if credits < 1:
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    await notif.send_credits_exhausted(user.id, ref_link)
```

### **Step 4: Test (10 min)**
- Use test account
- Exhaust all 3 credits
- Try to generate again
- Should receive N3 notification

### **Step 5: Deploy (5 min)**
```bash
git add .
git commit -m "Add N3: Credits Exhausted notification"
git push origin main
```

**Success:** You now have your first automated notification!

---

## 📚 Related Documentation

- **[DATA_ANALYSIS.md](DATA_ANALYSIS.md)** - Track notification effectiveness metrics
- **[ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md)** - Database changes for tracking
- **[ROADMAP.md](ROADMAP.md)** - Overall project timeline

---

## 🎯 Success Criteria (After 1 Month)

You'll know notifications are working if:

✅ **Activation rate improves** (N1)
- Before: ~40% of signups try bot
- After: ~60%+ try bot

✅ **Conversion rate improves** (N2, N3)
- Before: ~5% of free users buy
- After: ~10-15% buy

✅ **Churn rate decreases** (N4)
- Before: 70% of users never return
- After: 60% or less

✅ **Referrals increase** (N6)
- Before: 0-1 referrals per week
- After: 5-10 referrals per week

✅ **You're informed** (N10)
- You check stats daily
- You make data-driven decisions

---

**Next Step:** Choose which notification to implement first (recommend N3: Credits Exhausted for immediate conversion impact)
