# Data Analysis Strategy (Simplified)

**Last updated:** 2026-02-13
**Purpose:** Practical framework for tracking what matters and making data-driven decisions
**Time commitment:** 30 minutes per week

---

## 🎯 Goal: More Growth, More Revenue, Better Retention

You're optimizing for **all three**:
- More users signing up
- More users coming back
- More revenue from the bot

**Philosophy:** No specific targets. Just track trends and optimize what's working.

---

## 📊 The 7 Core Metrics (Everything You Need)

Track these weekly. That's it.

### **Growth Metrics** (Are we acquiring users?)

**1. New Users This Week**
- How many people signed up?
- **Good trend:** ↗️ Growing week-over-week
- **Action if declining:** Boost referral program, check if bot is discoverable

**2. Active Users (7-day)**
- How many unique users interacted with the bot in last 7 days?
- **Good trend:** ↗️ Growing (means people are coming back)
- **Action if flat:** Add new effects, send re-engagement messages

---

### **Retention Metrics** (Are users coming back?)

**3. 7-Day Retention Rate**
- Of users who signed up 7 days ago, what % are still active?
- **Good trend:** ↗️ Increasing or stable >30%
- **Action if low:** Improve first-time experience, send reminder messages

**4. Churned Users**
- How many users haven't been active in 30+ days?
- **Good trend:** ↘️ Decreasing as % of total users
- **Action if high:** Win-back campaign (send free credits)

---

### **Revenue Metrics** (Are we making money?)

**5. Weekly Revenue**
- How much money did you make this week?
- **Good trend:** ↗️ Growing consistently
- **Action if flat:** Test pricing, promote larger packages, upsell

**6. Conversion Rate (Free → Paid)**
- What % of all users have purchased at least once?
- **Good trend:** ↗️ Increasing (typical target: 10%+)
- **Action if low:** Improve payment UX, adjust pricing, offer discounts

**7. ARPU (Average Revenue Per User)**
- Total revenue ÷ Total users
- **Good trend:** ↗️ Increasing (means you're monetizing better)
- **Action if low:** Upsell larger packages, increase prices

---

## 🗓️ Weekly Review Workflow (30 Minutes)

Every week, spend 30 minutes doing this:

### **Step 1: Export Data (5 min)**
```bash
# Run this command
python "Photo bot/reports/export_csv.py"
```

This creates CSV files with all your data. Open in Excel/Google Sheets.

---

### **Step 2: Calculate The 7 Metrics (10 min)**

Open a spreadsheet and fill in this template:

| Metric | This Week | Last Week | Trend | Action Needed? |
|--------|-----------|-----------|-------|----------------|
| New Users | ___ | ___ | ↗️/↘️ | |
| Active Users (7d) | ___ | ___ | ↗️/↘️ | |
| 7-Day Retention | ___% | ___% | ↗️/↘️ | |
| Churned Users | ___ | ___ | ↗️/↘️ | |
| Weekly Revenue | ___ ₽ | ___ ₽ | ↗️/↘️ | |
| Conversion Rate | ___% | ___% | ↗️/↘️ | |
| ARPU | ___ ₽ | ___ ₽ | ↗️/↘️ | |

**How to calculate:** See QUICK_START.md for SQL queries or Excel formulas

---

### **Step 3: Look for Patterns (10 min)**

Ask yourself:
- **What's working?** (Anything growing faster than expected?)
- **What's broken?** (Anything declining?)
- **What surprises you?** (Unexpected spikes or drops?)

Check:
- **Top 5 effects by usage** - Which effects are most popular?
- **Failed generations** - Are any effects failing a lot?
- **Package sales** - Which packages are people buying?

---

### **Step 4: Pick ONE Action (5 min)**

Based on what you learned, pick **one thing** to do this week:

**If growth is slow:**
- Add 2-3 new effects
- Send referral reminders to power users
- Post bot in relevant Telegram channels

**If retention is low:**
- Send "we miss you" message to churned users
- Add more variety to effects
- Send reminder to users who got free credits but never used them

**If revenue is low:**
- Test discount on 50-credit package
- Upsell after successful generation ("Buy 25 credits, get 5 free!")
- Create limited-time promo code

**The key:** Only change ONE thing per week so you can measure impact.

---

## 📈 What "Good" Looks Like (Rough Benchmarks)

Since you said "no specific targets," here are just **directional benchmarks** to calibrate against:

| Metric | Healthy Range | Warning Zone |
|--------|---------------|--------------|
| 7-Day Retention | 25-40% | <20% |
| Conversion Rate | 8-15% | <5% |
| Churned % | 40-60% | >70% |
| Weekly Revenue Growth | +10-30% WoW | Flat or negative |

These aren't targets—just reference points. **Your goal: See improvement trends over time.**

---

## 🔍 Monthly Deep Dive (1 Hour, Once Per Month)

Once a month, do a deeper analysis:

### **1. User Segments (Who are your users?)**

Count how many users in each bucket:
- **New Users** (<7 days old) → Focus on activation
- **Active Free Users** (active, never purchased) → Conversion target
- **Exhausted Free Users** (0 credits, never bought) → Send offer
- **Paying Users** (bought ≥1 time) → Retain & upsell
- **Power Users** (10+ generations) → VIP treatment
- **Churned Users** (inactive >30 days) → Win-back campaign

**Action:** Create a targeted campaign for ONE segment.

---

### **2. Effect Performance**

For each effect, calculate:
- **Total uses** (popularity)
- **Failure rate** (quality)
- **Revenue attribution** (did users buy credits after using this effect?)

**Action:**
- Remove effects with >10% failure rate
- Create more effects similar to top performers
- Hide or improve underperforming effects

---

### **3. Cohort Analysis (Are newer users better?)**

Compare users by signup month:
- February signups: Retention rate? Revenue per user?
- January signups: Same metrics
- December signups: Same metrics

**Question:** Are recent cohorts performing better or worse?
- If better → You're improving, keep going
- If worse → Something broke, investigate

---

### **4. Revenue Analysis**

- Which package is most popular? (By count)
- Which package generates most revenue? (By total ₽)
- What's the average time from signup to first purchase?
- Are repeat purchases happening?

**Action:** Optimize package pricing based on what sells.

---

## 🛠️ Tools You'll Use

### **Excel/Google Sheets** (Your Main Tool)
- Import CSV exports weekly
- Create simple charts (line charts for trends)
- Pivot tables for segmentation
- Keep a running log of weekly metrics

**Template Structure:**
```
Sheet 1: Weekly Metrics (7 core metrics over time)
Sheet 2: Users (raw export)
Sheet 3: Generations (raw export)
Sheet 4: Purchases (raw export)
Sheet 5: Monthly Deep Dive Notes
```

---

### **Admin Dashboard** (Quick Glance)
The `/admin` command in your bot shows:
- Current stats
- Top effects
- Revenue

**Use this for:** Daily quick checks (2 minutes)

---

### **CSV Exports** (Deep Dive)
Run `python reports/export_csv.py` to get raw data

**Use this for:** Weekly analysis (30 minutes)

---

## 📅 3-Month Roadmap

### **Month 1: Foundation (Weeks 1-4)**
**Goal:** Start tracking the basics

**Week 1-2:**
- Set up data collection (add `last_active_at` to database)
- Run first export, calculate the 7 metrics manually
- Establish baseline (where are we today?)

**Week 3-4:**
- Continue weekly tracking
- Create Excel template for tracking trends
- Start noticing patterns

**Success Metric:** You know your 7 metrics every week

---

### **Month 2: Patterns (Weeks 5-8)**
**Goal:** Understand what drives results

**Activities:**
- Track trends (are metrics improving?)
- Identify top-performing effects
- Segment users (who's valuable, who's churned)
- Run first experiment (e.g., discount offer to exhausted users)

**Success Metric:** You made ONE data-driven decision that improved metrics

---

### **Month 3: Optimize (Weeks 9-12)**
**Goal:** Double down on what works

**Activities:**
- Cut underperforming effects
- Add more effects like your top performers
- Launch targeted campaigns (re-engagement, upsells)
- Optimize pricing based on package sales data

**Success Metric:** You see measurable improvement in ≥3 of the 7 metrics

---

## 🚨 Common Mistakes to Avoid

### ❌ **Tracking too much**
- Don't track 50 metrics. Stick to the 7.
- More data ≠ better decisions

### ❌ **Changing too many things at once**
- Test ONE thing per week
- Otherwise you won't know what worked

### ❌ **Analysis without action**
- Tracking is useless if you don't act on it
- Every weekly review must end with ONE action item

### ❌ **Reacting to noise**
- One bad week isn't a trend
- Look at 4-week moving averages

### ❌ **Perfectionism**
- Don't need perfect data to make decisions
- Directional accuracy is good enough

---

## ✅ Success Criteria (After 3 Months)

You'll know this is working if:

✅ You can answer these questions instantly:
- How many active users do I have?
- What's my retention rate?
- How much revenue did I make this month?
- Which effects are most popular?

✅ You've made data-driven decisions:
- Removed at least 1 underperforming effect
- Added effects similar to top performers
- Ran at least 1 experiment (pricing, campaign, etc.)

✅ You see trends improving:
- At least 3 of the 7 metrics trending ↗️
- Revenue growing month-over-month
- User base growing

---

## 📖 Appendix: Key Terms

**DAU/MAU:** Daily/Monthly Active Users (users who interact with bot)
**Retention:** % of users who come back after signup
**Churn:** Users who stopped using the bot
**ARPU:** Average Revenue Per User (total revenue ÷ total users)
**Conversion Rate:** % of users who made a purchase
**Cohort:** Group of users who signed up in the same time period
**WoW:** Week-over-Week (comparing this week to last week)

---

## 🔗 Related Docs

- **[QUICK_START.md](QUICK_START.md)** - 1-page cheat sheet for weekly reviews (SQL queries, formulas)
- **[ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md)** - Technical guide for setting up tracking
- **[ROADMAP.md](ROADMAP.md)** - Overall project roadmap

---

**Next Step:** Read QUICK_START.md for the practical "how-to" on calculating metrics.
