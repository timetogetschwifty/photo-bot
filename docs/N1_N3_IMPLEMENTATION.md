# N1 & N3 Implementation Guide

**Date:** 2026-02-13
**Notifications Implemented:**
- N1: Welcome Reminder (Daily 10 AM MSK / 7 AM UTC)
- N3: Credits Exhausted (Real-time)

**Timezone:** MSK (Moscow, UTC+3) — All scheduled times use Moscow timezone

---

## ✅ What Was Done

### **1. Database Changes**
- Created `notification_log` table to track sends
- Migration: `migrations/004_create_notification_log.sql`

### **2. Core Notification System**
- Created `notifications.py` module
- Functions: `send_welcome_reminder()`, `send_credits_exhausted()`
- Anti-spam: Won't send same notification twice to same user

### **3. N3: Credits Exhausted (Real-time)**
- **Integrated into:** `photo_bot.py` → `select_effect()` function
- **Triggers:** When user with 0 credits tries to generate
- **Condition:** Only if user has never purchased
- **Message:** Upsell (buy credits) + referral option

### **4. N1: Welcome Reminder (Scheduled)**
- **Created:** `jobs/notification_jobs.py`
- **Runs:** Daily (cron/scheduler)
- **Targets:** Users registered 24h ago, 0 generations
- **Message:** Reminder to try first effect

---

## 🧪 Testing

### **Test N3 (Credits Exhausted) - Local**

1. **Run migration:**
```bash
cd "Photo bot"
source ../.venv/bin/activate
sqlite3 photo_bot.db < migrations/004_create_notification_log.sql
```

2. **Verify table created:**
```bash
sqlite3 photo_bot.db ".schema notification_log"
```

3. **Test bot locally:**
```bash
python photo_bot.py
```

4. **Test flow:**
   - Use test account
   - Exhaust all 3 credits (generate 3 times)
   - Try to generate 4th time
   - **Expected:** Bot shows "credits exhausted" message
   - **Expected:** Bot sends N3 notification via DM (separate message)

5. **Verify notification logged:**
```bash
sqlite3 photo_bot.db "SELECT * FROM notification_log WHERE notification_id = 'N3';"
```

6. **Test anti-spam:**
   - Try to generate again (still 0 credits)
   - **Expected:** Should NOT send N3 again (already sent once)

---

### **Test N1 (Welcome Reminder) - Local**

1. **Create test user (registered 24h ago, 0 generations):**
```bash
sqlite3 photo_bot.db "
UPDATE users
SET created_at = datetime('now', '-1 day')
WHERE telegram_id = YOUR_TEST_USER_ID;
"
```

2. **Run notification job:**
```bash
python jobs/notification_jobs.py
```

3. **Expected output:**
```
📅 Running daily notification jobs at 2026-02-13 10:00:00
📬 Found 1 users eligible for N1 (Welcome Reminder)
✅ Sent 1/1 welcome reminders
✅ Daily notification jobs completed
```

4. **Check Telegram:**
   - Should receive N1 welcome reminder message

5. **Verify logged:**
```bash
sqlite3 photo_bot.db "SELECT * FROM notification_log WHERE notification_id = 'N1';"
```

---

## 🚀 Deployment to Railway

### **Step 1: Backup Database**
```bash
railway run cat /data/photo_bot.db > backups/photo_bot_$(date +%Y%m%d).db
```

### **Step 2: Run Migration on Production**
```bash
# Option A: Run migration directly
railway run sqlite3 /data/photo_bot.db < migrations/004_create_notification_log.sql

# Option B: Use Python migration runner (if you created it)
railway run python run_migration.py migrations/004_create_notification_log.sql
```

### **Step 3: Deploy Code**
```bash
git add .
git commit -m "Add N1 and N3 notifications"
git push origin main
```

Railway will auto-deploy.

### **Step 4: Verify Deployment**
```bash
# Check logs for initialization
railway logs --tail

# Should see: "Notification system initialized"
```

### **Step 5: Test N3 in Production**
- Use real user account (not admin)
- Exhaust credits
- Try to generate
- Should receive N3 notification

### **Step 6: Schedule N1 Daily Job**

**Option A: Railway Cron** (if Railway supports cron):
```bash
# Add to railway.toml or Railway dashboard
# Schedule: 0 7 * * * (7 AM UTC = 10 AM MSK)
python jobs/notification_jobs.py
```

**Option B: External Scheduler** (GitHub Actions, Render Cron, etc.):

Create `.github/workflows/daily-notifications.yml`:
```yaml
name: Daily Notifications

on:
  schedule:
    - cron: '0 7 * * *'  # 7 AM UTC = 10 AM MSK (Moscow time)
  workflow_dispatch:  # Manual trigger for testing

jobs:
  send-notifications:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: |
          pip install -r "Photo bot/requirements.txt"
      - name: Run notification jobs
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          BOT_USERNAME: ${{ secrets.BOT_USERNAME }}
          ADMIN_ID: ${{ secrets.ADMIN_ID }}
          DB_PATH: ${{ secrets.RAILWAY_DB_PATH }}
        run: |
          python "Photo bot/jobs/notification_jobs.py"
```

**Option C: Manual Testing** (while setting up automation):
```bash
# SSH into Railway or run locally against production DB
railway run python jobs/notification_jobs.py
```

---

## 📊 Monitoring

### **Check Notification Stats**

**SQL Queries:**

```sql
-- Total notifications sent
SELECT notification_id, COUNT(*) as sent
FROM notification_log
GROUP BY notification_id;

-- Recent N3 sends (last 24h)
SELECT COUNT(*) as sent_today
FROM notification_log
WHERE notification_id = 'N3'
  AND sent_at > datetime('now', '-1 day');

-- Users who received N3 but didn't buy (within 7 days)
SELECT
  nl.user_id,
  nl.sent_at,
  (SELECT COUNT(*) FROM purchases p WHERE p.user_id = nl.user_id AND p.created_at > nl.sent_at) as purchased
FROM notification_log nl
WHERE nl.notification_id = 'N3'
  AND nl.sent_at > datetime('now', '-7 days');
```

### **Expected Metrics (After 1 Week)**

**N3: Credits Exhausted**
- Sent to: 50-100% of users who exhaust credits
- Conversion rate: 10-15% (should purchase within 7 days)
- If below 5%: Message too weak, adjust copy

**N1: Welcome Reminder**
- Sent to: ~30-50% of signups (those who don't activate)
- Activation rate: 20-30% (should generate within 48h)
- If below 10%: Message not compelling enough

---

## 🐛 Troubleshooting

### **N3 not sending**

**Check:**
1. Bot initialized? `notif.init_notifications(app.bot)` in `main()`
2. Notification logged? Query `notification_log` table
3. User has purchased before? N3 only sends to never-purchased users
4. Bot permissions? Check Telegram error logs

**Debug:**
```python
# Add logging to select_effect function
logger.info(f"Credits exhausted for user {user.id}, has_purchased={has_purchased}")
```

### **N1 not sending**

**Check:**
1. Cron job running? Check Railway logs or scheduler logs
2. Users exist? Query eligible users manually
3. Bot token valid? Test with simple send_message
4. Rate limiting? Job sleeps 0.1s between sends

**Manual test:**
```bash
# Run job manually
python jobs/notification_jobs.py

# Should see output with user count
```

### **notification_log table doesn't exist**

```bash
# Run migration
sqlite3 photo_bot.db < migrations/004_create_notification_log.sql

# Verify
sqlite3 photo_bot.db ".tables"
# Should show: notification_log
```

---

## 📈 Success Criteria

**After 1 week, you should see:**

✅ N3 sent to 10-20 users (depending on volume)
✅ 2-3 purchases directly attributed to N3 (10-15% conversion)
✅ N1 sent to 20-50 users
✅ 5-10 activations from N1 (20-30% activation)

**After 1 month:**

✅ Clear trend: N3 → purchase correlation
✅ Clear trend: N1 → activation correlation
✅ Revenue uplift: +15-20% from N3 alone
✅ Activation uplift: +30% from N1

---

## 🔄 Next Steps

### **Phase 2 Notifications (Week 3-4)**
1. **N2: Credits Running Low** (real-time, after generation leaves 1 credit)
2. **N6: Referral Reminder** (after 3rd generation)
3. **N4: Win-Back Offer** (weekly, to churned users)

### **Optimization**
- A/B test N3 message copy
- Adjust N1 timing (24h vs 48h vs 12h)
- Add buttons to notifications for direct action
- Track click-through rate on inline buttons

---

## 📁 Files Created/Modified

**New Files:**
- `migrations/004_create_notification_log.sql`
- `notifications.py`
- `jobs/notification_jobs.py`
- `docs/N1_N3_IMPLEMENTATION.md` (this file)

**Modified Files:**
- `photo_bot.py`:
  - Added `import notifications as notif`
  - Added `notif.init_notifications(app.bot)` in `main()`
  - Added N3 trigger in `select_effect()` when credits < 1

---

## 🆘 Support

**Issues?**
1. Check Railway logs: `railway logs --tail`
2. Check bot logs locally: Run bot with increased logging
3. Query notification_log table to see what was sent
4. Review NOTIFICATION_STRATEGY.md for context

**Questions?**
- How often should N1 run? Daily at 10 AM
- Can I test without waiting 24h? Yes, manually update user created_at
- Will this spam users? No, each notification sent only once per user
- What if user blocks bot? Telegram API will return error, skip user

---

**Status:** ✅ Ready to deploy
**Estimated Impact:** +20-30% conversion and activation rates
**Time to Value:** Immediate for N3, 24h for N1
