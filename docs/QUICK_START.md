# Quick Start: Weekly Analytics Cheat Sheet

**Purpose:** Copy-paste queries to calculate your 7 core metrics
**Time:** 10 minutes to get all the numbers

---

## 🚀 The 7 Metrics (Copy-Paste Queries)

### **Prerequisites**

First, you need to add `last_active_at` tracking. See [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md) Section 1.

**Until then**, use `created_at` as a proxy (shows signups, not activity).

---

## 📊 SQL Queries (Run These Weekly)

Open your database:
```bash
sqlite3 "Photo bot/photo_bot.db"
```

---

### **1. New Users This Week**

```sql
SELECT COUNT(*) as new_users
FROM users
WHERE created_at >= date('now', '-7 days');
```

**Excel Formula** (if you exported users.csv):
```excel
=COUNTIF(created_at_column, ">="&TODAY()-7)
```

---

### **2. Active Users (7-day)**

**After you add `last_active_at`:**
```sql
SELECT COUNT(*) as active_users
FROM users
WHERE last_active_at >= date('now', '-7 days');
```

**Before `last_active_at` is implemented** (use generations as proxy):
```sql
SELECT COUNT(DISTINCT user_id) as active_users
FROM generations
WHERE created_at >= date('now', '-7 days');
```

---

### **3. 7-Day Retention Rate**

**Formula:** (Users active on day 7) ÷ (Users who signed up 7 days ago) × 100

**After you add `last_active_at`:**
```sql
-- Users who signed up exactly 7 days ago
WITH cohort AS (
  SELECT COUNT(*) as total
  FROM users
  WHERE date(created_at) = date('now', '-7 days')
),
-- How many of them were active today
retained AS (
  SELECT COUNT(*) as active
  FROM users
  WHERE date(created_at) = date('now', '-7 days')
    AND date(last_active_at) >= date('now', '-1 day')
)
SELECT
  retained.active,
  cohort.total,
  ROUND((retained.active * 100.0 / cohort.total), 1) as retention_rate
FROM cohort, retained;
```

**Simplified version (any activity in last 7 days):**
```sql
SELECT
  ROUND(
    (SELECT COUNT(*) FROM users WHERE last_active_at >= date('now', '-7 days')) * 100.0 /
    (SELECT COUNT(*) FROM users)
  , 1) as retention_rate;
```

---

### **4. Churned Users**

```sql
-- Users inactive for 30+ days
SELECT COUNT(*) as churned_users
FROM users
WHERE last_active_at < date('now', '-30 days');
```

**As percentage of total:**
```sql
SELECT
  COUNT(*) as churned_users,
  (SELECT COUNT(*) FROM users) as total_users,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM users), 1) as churn_rate
FROM users
WHERE last_active_at < date('now', '-30 days');
```

---

### **5. Weekly Revenue**

```sql
SELECT COALESCE(SUM(price_rub), 0) as weekly_revenue
FROM purchases
WHERE created_at >= date('now', '-7 days');
```

**Excel Formula:**
```excel
=SUMIF(purchase_date_column, ">="&TODAY()-7, price_column)
```

---

### **6. Conversion Rate (Free → Paid)**

```sql
SELECT
  COUNT(DISTINCT user_id) as paying_users,
  (SELECT COUNT(*) FROM users) as total_users,
  ROUND(COUNT(DISTINCT user_id) * 100.0 / (SELECT COUNT(*) FROM users), 1) as conversion_rate
FROM purchases;
```

**Excel Formula:**
```excel
=COUNTUNIQUE(paying_users) / COUNT(all_users) * 100
```

---

### **7. ARPU (Average Revenue Per User)**

```sql
SELECT
  COALESCE(SUM(price_rub), 0) as total_revenue,
  (SELECT COUNT(*) FROM users) as total_users,
  ROUND(COALESCE(SUM(price_rub), 0) * 1.0 / (SELECT COUNT(*) FROM users), 2) as arpu
FROM purchases;
```

**Excel Formula:**
```excel
=SUM(all_revenue) / COUNT(all_users)
```

---

## 📈 Bonus Queries (Also Useful)

### **Top 5 Effects by Usage**

```sql
SELECT
  effect_id,
  COUNT(*) as uses
FROM generations
GROUP BY effect_id
ORDER BY uses DESC
LIMIT 5;
```

---

### **Failed Generations (if you track status)**

```sql
SELECT
  COUNT(*) as failed,
  (SELECT COUNT(*) FROM generations) as total,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM generations), 1) as failure_rate
FROM generations
WHERE status = 'failed';
```

---

### **Failed Generations by Effect**

```sql
SELECT
  effect_id,
  COUNT(*) as total_uses,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
  ROUND(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as failure_rate
FROM generations
GROUP BY effect_id
ORDER BY failure_rate DESC;
```

---

### **Package Sales Breakdown**

```sql
SELECT
  package_credits,
  COUNT(*) as sold,
  SUM(price_rub) as revenue
FROM purchases
GROUP BY package_credits
ORDER BY package_credits;
```

---

### **User Segments**

```sql
-- New users (<7 days)
SELECT COUNT(*) FROM users WHERE created_at >= date('now', '-7 days');

-- Exhausted free users (0 credits, never purchased)
SELECT COUNT(*)
FROM users
WHERE credits = 0
  AND telegram_id NOT IN (SELECT DISTINCT user_id FROM purchases);

-- Paying users
SELECT COUNT(DISTINCT user_id) FROM purchases;

-- Power users (10+ generations)
SELECT COUNT(*)
FROM (
  SELECT user_id, COUNT(*) as gen_count
  FROM generations
  GROUP BY user_id
  HAVING gen_count >= 10
);

-- Churned (inactive >30 days)
SELECT COUNT(*) FROM users WHERE last_active_at < date('now', '-30 days');
```

---

## 📊 Weekly Tracking Template (Excel/Google Sheets)

Create a spreadsheet with this structure:

### **Sheet 1: Weekly Metrics**

| Week Ending | New Users | Active Users | 7-Day Retention | Churned | Revenue | Conversion | ARPU |
|-------------|-----------|--------------|-----------------|---------|---------|------------|------|
| 2026-02-13  | 15        | 45           | 32%             | 23      | 1,247 ₽ | 12%        | 85 ₽ |
| 2026-02-20  | ...       | ...          | ...             | ...     | ...     | ...        | ...  |
| 2026-02-27  | ...       | ...          | ...             | ...     | ...     | ...        | ...  |

**Add charts:**
- Line chart: Revenue over time
- Line chart: Active Users over time
- Line chart: Retention Rate over time

---

### **Sheet 2: Effect Performance**

| Effect ID | Total Uses | Failed | Failure Rate | Last Week Uses |
|-----------|------------|--------|--------------|----------------|
| afro      | 127        | 3      | 2.4%         | 18             |
| mafiosi   | 89         | 7      | 7.9%         | 12             |
| carpet    | 12         | 4      | 33.3%        | 1              |

**Sort by:** Total Uses (descending) to see top performers

---

### **Sheet 3: Actions Taken**

Track what you changed each week and the result:

| Week | Action Taken | Metric Targeted | Result (Next Week) |
|------|--------------|-----------------|-------------------|
| Feb 13 | Added 3 new effects | Growth | +8 new users |
| Feb 20 | Removed "carpet" effect (33% fail) | Quality | Failure rate dropped to 5% |
| Feb 27 | Sent discount to exhausted users | Revenue | +5 conversions |

This helps you learn what works.

---

## 🚀 Quick Start Workflow

### **Every Monday Morning (30 min):**

**1. Export data (5 min)**
```bash
cd "Photo bot"
python reports/export_csv.py
```

**2. Open your tracking spreadsheet**
- Import/refresh the CSV data
- Calculate the 7 metrics (copy-paste SQL results or use Excel formulas)
- Fill in the weekly row

**3. Check trends (5 min)**
- Is revenue growing?
- Is retention improving?
- Are active users increasing?

**4. Look for issues (10 min)**
- Any effects with high failure rate? (>10%)
- Any metrics dropping sharply?
- What surprised you?

**5. Pick ONE action (5 min)**
- Based on what you saw, what's the ONE thing to improve this week?
- Write it in your "Actions Taken" sheet

**6. Do the action (5 min)**
- If it's quick (e.g., remove bad effect, create promo code), do it now
- If it takes longer, schedule it for this week

---

## 🔧 Before First Review: Setup Checklist

Before your first weekly review, make sure:

- [ ] **Database has `last_active_at` column**
  - See [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md) Migration 001
  - Or use `created_at` / generation timestamps as proxy for now

- [ ] **CSV export script exists**
  - See [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md) Section 6
  - Test it: `python "Photo bot/reports/export_csv.py"`

- [ ] **Excel/Google Sheets template created**
  - Sheet 1: Weekly Metrics
  - Sheet 2: Effect Performance
  - Sheet 3: Actions Taken

- [ ] **Baseline established**
  - Run queries once to know your starting point
  - Week 1 is just capturing "where we are"
  - Week 2+ is when you start tracking trends

---

## 📱 Mobile/Quick Check Version

If you just want a quick pulse check (2 minutes), run these 3 queries:

```sql
-- Quick Stats
SELECT
  (SELECT COUNT(*) FROM users) as total_users,
  (SELECT COUNT(*) FROM users WHERE last_active_at >= date('now', '-7 days')) as active_7d,
  (SELECT COALESCE(SUM(price_rub), 0) FROM purchases WHERE created_at >= date('now', '-7 days')) as revenue_7d,
  (SELECT COUNT(DISTINCT user_id) FROM purchases) as paying_users;
```

This gives you: Total users, Active users, Weekly revenue, Paying users.

---

## 🆘 Troubleshooting

### **Query returns 0 for active users**
- You haven't implemented `last_active_at` yet
- Use generation timestamps as proxy (see query in #2)

### **Can't calculate retention**
- Need at least 7 days of data after adding `last_active_at`
- First week: Skip this metric, focus on others

### **CSV export doesn't exist**
- Create it using code in [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md) Section 6

### **Excel formulas not working**
- Use SQL queries directly - they're more reliable
- Copy SQL results into Excel manually

---

## 📚 Next Steps

1. **Read [DATA_ANALYSIS.md](DATA_ANALYSIS.md)** - Understand the "why" behind metrics
2. **Implement Phase 1** - Add `last_active_at` tracking (see [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md))
3. **Run your first weekly review** - Establish baseline
4. **Track for 4 weeks** - Start seeing trends
5. **Make first data-driven decision** - Improve ONE thing

---

**Questions?** Check [DATA_ANALYSIS.md](DATA_ANALYSIS.md) for strategic context or [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md) for technical details.
