# Analytics Implementation Guide

**Last updated:** 2026-02-13
**Purpose:** Technical implementation guide for data collection, reports, and analytics infrastructure
**Prerequisite:** Read `DATA_ANALYSIS.md` first for strategic context

---

## Table of Contents

1. [Database Schema Changes](#1-database-schema-changes)
2. [SQL Migration Scripts](#2-sql-migration-scripts)
3. [Database Helper Functions](#3-database-helper-functions)
4. [Report Scripts](#4-report-scripts)
5. [Admin Dashboard Enhancements](#5-admin-dashboard-enhancements)
6. [Export Tools](#6-export-tools)
7. [Testing & Validation](#7-testing--validation)
8. [Deployment Checklist](#8-deployment-checklist)

---

## 1. Database Schema Changes

### Phase 1: Critical Tables & Columns

#### Add `last_active_at` to Users Table
```sql
ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

**When to update:**
- On every bot interaction (message, callback, command)
- Update via: `UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE telegram_id = ?`

---

#### Modify Generations Table
```sql
-- Add status tracking
ALTER TABLE generations ADD COLUMN status TEXT DEFAULT 'success';
-- Values: 'success', 'failed', 'refunded'

-- Add error tracking
ALTER TABLE generations ADD COLUMN error_type TEXT;
-- Values: 'gemini_api_error', 'safety_block', 'timeout', 'invalid_image', null (if success)

-- Add processing time (optional but useful)
ALTER TABLE generations ADD COLUMN processing_time_ms INTEGER;
```

**Record logic:**
- `status = 'success'` → Generation completed, image sent
- `status = 'failed'` → Error occurred, credit refunded
- `status = 'refunded'` → Manual admin refund (future use)

---

#### Create User Activity Log Table
```sql
CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    -- Action types: 'view_store', 'view_effect', 'browse_category',
    --               'invoice_sent', 'payment_cancelled', 'payment_completed',
    --               'promo_entered', 'referral_viewed', 'share_clicked'

    metadata TEXT,
    -- JSON string with context:
    -- For 'view_effect': {"effect_id": "afro"}
    -- For 'browse_category': {"category_id": "hairstyle"}
    -- For 'invoice_sent': {"package_id": "pkg_50", "price": 39900}

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

-- Index for fast queries
CREATE INDEX idx_activity_user_time ON user_activity(user_id, created_at);
CREATE INDEX idx_activity_action ON user_activity(action_type, created_at);
```

---

#### Create Sessions Table (Optional - Phase 2)
```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    actions_count INTEGER DEFAULT 0,
    generations_count INTEGER DEFAULT 0,

    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

CREATE INDEX idx_sessions_user ON sessions(user_id, started_at);
```

**Session logic:**
- New session if >30 minutes since last activity
- Update `ended_at` and `actions_count` on each interaction

---

#### Create A/B Tests Table (Optional - Phase 3)
```sql
CREATE TABLE IF NOT EXISTS ab_tests (
    user_id INTEGER PRIMARY KEY,
    test_variant TEXT NOT NULL,
    -- Example: 'pricing_v1', 'pricing_v2', 'onboarding_a', 'onboarding_b'

    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);
```

---

### Complete Schema After Phase 1

```sql
-- users table (modified)
CREATE TABLE users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    credits INTEGER DEFAULT 3,
    total_spent INTEGER DEFAULT 0,
    referred_by INTEGER,
    referral_credited INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- NEW
);

-- generations table (modified)
CREATE TABLE generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    effect_id TEXT NOT NULL,
    status TEXT DEFAULT 'success',           -- NEW
    error_type TEXT,                         -- NEW
    processing_time_ms INTEGER,              -- NEW
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- user_activity table (new)
CREATE TABLE user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. SQL Migration Scripts

### Migration Script: `migrations/001_add_retention_tracking.sql`

```sql
-- Migration: Add retention tracking
-- Date: 2026-02-13
-- Description: Add last_active_at for retention analysis

-- Add column if it doesn't exist
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so check first

PRAGMA table_info(users);

-- If last_active_at doesn't exist, run:
ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Backfill existing users with their created_at
UPDATE users SET last_active_at = created_at WHERE last_active_at IS NULL;
```

---

### Migration Script: `migrations/002_add_generation_status.sql`

```sql
-- Migration: Track generation success/failure
-- Date: 2026-02-13

ALTER TABLE generations ADD COLUMN status TEXT DEFAULT 'success';
ALTER TABLE generations ADD COLUMN error_type TEXT;
ALTER TABLE generations ADD COLUMN processing_time_ms INTEGER;

-- Backfill existing generations as 'success' (assume all historical were successful)
UPDATE generations SET status = 'success' WHERE status IS NULL;
```

---

### Migration Script: `migrations/003_create_activity_log.sql`

```sql
-- Migration: User activity tracking
-- Date: 2026-02-13

CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

CREATE INDEX idx_activity_user_time ON user_activity(user_id, created_at);
CREATE INDEX idx_activity_action ON user_activity(action_type, created_at);
```

---

### How to Run Migrations

**Option A: Manual (Local Development)**
```bash
# Activate environment
source .venv/bin/activate

# Open local database
sqlite3 "Photo bot/photo_bot.db"

# Run migration
.read migrations/001_add_retention_tracking.sql
.read migrations/002_add_generation_status.sql
.read migrations/003_create_activity_log.sql

# Verify
.schema users
.schema generations
.schema user_activity

# Exit
.quit
```

**On Railway (Production):**
```bash
# Download database first
railway run cat /data/photo_bot.db > photo_bot_production.db

# Run migrations locally on downloaded database
sqlite3 photo_bot_production.db < migrations/001_add_retention_tracking.sql

# Or run Python migration script on Railway
railway run python run_migration.py migrations/001_add_retention_tracking.sql
```

**Option B: Python Migration Script** (recommended for production)

Create `Photo bot/run_migration.py`:
```python
"""
Database migration runner.
Usage: python run_migration.py migrations/001_add_retention_tracking.sql
"""

import os
import sqlite3
import sys
from pathlib import Path

# Use same DB_PATH logic as database.py
default_db_path = str(Path(__file__).parent / "photo_bot.db")
DB_PATH = Path(os.getenv("DB_PATH", default_db_path))

def run_migration(sql_file: str):
    """Execute SQL migration file."""
    if not Path(sql_file).exists():
        print(f"Error: Migration file not found: {sql_file}")
        sys.exit(1)

    with open(sql_file, 'r') as f:
        sql = f.read()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # SQLite doesn't support multiple statements with execute()
        # Split by semicolon and execute individually
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                cursor.execute(statement)

        conn.commit()
        print(f"✅ Migration applied: {sql_file}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_migration.py <migration_file.sql>")
        sys.exit(1)

    run_migration(sys.argv[1])
```

**Usage:**
```bash
python "Photo bot/run_migration.py" "Photo bot/migrations/001_add_retention_tracking.sql"
```

---

## 3. Database Helper Functions

Add these functions to `database.py`:

### Update Last Active Timestamp
```python
def update_last_active(telegram_id: int) -> None:
    """Update user's last_active_at timestamp."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE telegram_id = ?",
        (telegram_id,)
    )
    conn.commit()
    conn.close()
```

**Call this:** At the start of every handler (start, callbacks, messages)

---

### Record Generation with Status
```python
def record_generation(
    telegram_id: int,
    effect_id: str,
    status: str = 'success',
    error_type: str = None,
    processing_time_ms: int = None
) -> None:
    """Record a generation with status tracking."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO generations (user_id, effect_id, status, error_type, processing_time_ms)
        VALUES (?, ?, ?, ?, ?)
        """,
        (telegram_id, effect_id, status, error_type, processing_time_ms)
    )
    conn.commit()
    conn.close()
```

**Update bot code:** Modify `handle_photo()` in `photo_bot.py`:
```python
# On success:
db.record_generation(user.id, effect_id, status='success', processing_time_ms=elapsed_ms)

# On failure:
db.record_generation(user.id, effect_id, status='failed', error_type='gemini_api_error')
```

---

### Log User Activity
```python
import json

def log_activity(
    telegram_id: int,
    action_type: str,
    metadata: dict = None
) -> None:
    """Log user activity event."""
    conn = get_connection()
    cursor = conn.cursor()

    metadata_json = json.dumps(metadata) if metadata else None

    cursor.execute(
        "INSERT INTO user_activity (user_id, action_type, metadata) VALUES (?, ?, ?)",
        (telegram_id, action_type, metadata_json)
    )
    conn.commit()
    conn.close()
```

**Usage examples:**
```python
# User views store
db.log_activity(user.id, 'view_store')

# User views effect
db.log_activity(user.id, 'view_effect', {'effect_id': 'afro'})

# User browses category
db.log_activity(user.id, 'browse_category', {'category_id': 'hairstyle'})

# Invoice sent
db.log_activity(user.id, 'invoice_sent', {'package_id': 'pkg_50', 'price': 39900})

# Payment cancelled
db.log_activity(user.id, 'payment_cancelled', {'package_id': 'pkg_50'})
```

---

### Get Retention Metrics
```python
def get_retention_stats(days: int = 7) -> dict:
    """
    Calculate retention statistics.

    Returns:
        {
            'active_users': int,  # Users active in last N days
            'total_users': int,   # Total users registered
            'retention_rate': float  # Percentage active
        }
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Users active in last N days
    cursor.execute(
        f"SELECT COUNT(*) as count FROM users WHERE last_active_at > date('now', '-{days} days')"
    )
    active_users = cursor.fetchone()['count']

    # Total users
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']

    conn.close()

    retention_rate = (active_users / total_users * 100) if total_users > 0 else 0

    return {
        'active_users': active_users,
        'total_users': total_users,
        'retention_rate': round(retention_rate, 2)
    }
```

---

### Get User Segments
```python
def get_user_segments() -> dict:
    """
    Segment users by behavior.

    Returns:
        {
            'new_users': int,            # Registered <7 days ago
            'active_free': int,          # Active, never purchased
            'exhausted_free': int,       # 0 credits, never purchased
            'paying_users': int,         # Made ≥1 purchase
            'churned': int,              # Inactive >30 days
            'power_users': int           # 10+ generations
        }
    """
    conn = get_connection()
    cursor = conn.cursor()

    # New users (<7 days)
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE created_at > date('now', '-7 days')")
    new_users = cursor.fetchone()['count']

    # Active free users (active in last 7 days, never purchased)
    cursor.execute("""
        SELECT COUNT(*) as count FROM users
        WHERE last_active_at > date('now', '-7 days')
        AND telegram_id NOT IN (SELECT DISTINCT user_id FROM purchases)
        AND credits > 0
    """)
    active_free = cursor.fetchone()['count']

    # Exhausted free users (0 credits, never purchased)
    cursor.execute("""
        SELECT COUNT(*) as count FROM users
        WHERE credits = 0
        AND telegram_id NOT IN (SELECT DISTINCT user_id FROM purchases)
    """)
    exhausted_free = cursor.fetchone()['count']

    # Paying users (made ≥1 purchase)
    cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM purchases")
    paying_users = cursor.fetchone()['count']

    # Churned users (inactive >30 days)
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE last_active_at < date('now', '-30 days')")
    churned = cursor.fetchone()['count']

    # Power users (10+ generations)
    cursor.execute("""
        SELECT COUNT(*) as count FROM (
            SELECT user_id FROM generations
            GROUP BY user_id
            HAVING COUNT(*) >= 10
        )
    """)
    power_users = cursor.fetchone()['count']

    conn.close()

    return {
        'new_users': new_users,
        'active_free': active_free,
        'exhausted_free': exhausted_free,
        'paying_users': paying_users,
        'churned': churned,
        'power_users': power_users
    }
```

---

## 4. Report Scripts

### Daily Report Script

Create `Photo bot/reports/daily_report.py`:

```python
"""
Daily stats report generator.
Usage: python reports/daily_report.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db

def generate_daily_report():
    """Generate daily statistics report."""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    conn = db.get_connection()
    cursor = conn.cursor()

    # New users today
    cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE date(created_at) = '{today}'")
    new_users_today = cursor.fetchone()['count']

    cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE date(created_at) = '{yesterday}'")
    new_users_yesterday = cursor.fetchone()['count']

    # Active users today
    cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE date(last_active_at) = '{today}'")
    active_users_today = cursor.fetchone()['count']

    cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE date(last_active_at) = '{yesterday}'")
    active_users_yesterday = cursor.fetchone()['count']

    # Generations today
    cursor.execute(f"SELECT COUNT(*) as count FROM generations WHERE date(created_at) = '{today}'")
    generations_today = cursor.fetchone()['count']

    cursor.execute(f"SELECT COUNT(*) as count FROM generations WHERE date(created_at) = '{yesterday}'")
    generations_yesterday = cursor.fetchone()['count']

    # Revenue today (in rubles)
    cursor.execute(f"SELECT COALESCE(SUM(price_rub), 0) as revenue FROM purchases WHERE date(created_at) = '{today}'")
    revenue_today = cursor.fetchone()['revenue']

    cursor.execute(f"SELECT COALESCE(SUM(price_rub), 0) as revenue FROM purchases WHERE date(created_at) = '{yesterday}'")
    revenue_yesterday = cursor.fetchone()['revenue']

    # Top effect today
    cursor.execute(f"""
        SELECT effect_id, COUNT(*) as count
        FROM generations
        WHERE date(created_at) = '{today}'
        GROUP BY effect_id
        ORDER BY count DESC
        LIMIT 1
    """)
    top_effect = cursor.fetchone()
    top_effect_id = top_effect['effect_id'] if top_effect else 'N/A'
    top_effect_count = top_effect['count'] if top_effect else 0

    # Purchases today
    cursor.execute(f"SELECT COUNT(*) as count FROM purchases WHERE date(created_at) = '{today}'")
    purchases_today = cursor.fetchone()['count']

    # Promo redemptions today
    cursor.execute(f"SELECT COUNT(*) as count FROM promo_redemptions WHERE date(redeemed_at) = '{today}'")
    promo_today = cursor.fetchone()['count']

    conn.close()

    # Format report
    report = f"""📊 Daily Stats — {today}

New Users: {new_users_today} ({'+' if new_users_today >= new_users_yesterday else ''}{new_users_today - new_users_yesterday} vs yesterday)
Active Users: {active_users_today} ({'+' if active_users_today >= active_users_yesterday else ''}{active_users_today - active_users_yesterday} vs yesterday)
Generations: {generations_today} ({'+' if generations_today >= generations_yesterday else ''}{generations_today - generations_yesterday} vs yesterday)
Revenue: {revenue_today} ₽ ({'+' if revenue_today >= revenue_yesterday else ''}{revenue_today - revenue_yesterday} ₽ vs yesterday)

🔥 Top Effect: {top_effect_id} ({top_effect_count} uses)
💰 Purchases: {purchases_today} packages sold
🎁 Promo Redemptions: {promo_today}
"""

    return report

if __name__ == "__main__":
    print(generate_daily_report())
```

**Usage:**
```bash
python "Photo bot/reports/daily_report.py"
```

**Automate:** Add to cron or Railway cron job to send daily via Telegram

---

### Weekly Report Script

Create `Photo bot/reports/weekly_report.py`:

```python
"""
Weekly analytics report.
Usage: python reports/weekly_report.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db

def generate_weekly_report():
    """Generate weekly analytics report."""
    today = datetime.now()
    week_start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    prev_week_start = (today - timedelta(days=14)).strftime('%Y-%m-%d')
    prev_week_end = week_start

    conn = db.get_connection()
    cursor = conn.cursor()

    # New users this week
    cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE created_at >= '{week_start}'")
    new_users_week = cursor.fetchone()['count']

    cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE created_at >= '{prev_week_start}' AND created_at < '{prev_week_end}'")
    new_users_prev = cursor.fetchone()['count']

    # Revenue this week
    cursor.execute(f"SELECT COALESCE(SUM(price_rub), 0) as revenue FROM purchases WHERE created_at >= '{week_start}'")
    revenue_week = cursor.fetchone()['revenue']

    cursor.execute(f"SELECT COALESCE(SUM(price_rub), 0) as revenue FROM purchases WHERE created_at >= '{prev_week_start}' AND created_at < '{prev_week_end}'")
    revenue_prev = cursor.fetchone()['revenue']

    # Calculate WoW growth
    new_users_growth = ((new_users_week - new_users_prev) / new_users_prev * 100) if new_users_prev > 0 else 0
    revenue_growth = ((revenue_week - revenue_prev) / revenue_prev * 100) if revenue_prev > 0 else 0

    # WAPU (Weekly Active Paying Users)
    cursor.execute(f"""
        SELECT COUNT(DISTINCT user_id) as count
        FROM purchases
        WHERE created_at >= '{week_start}'
    """)
    wapu = cursor.fetchone()['count']

    # Retention
    retention = db.get_retention_stats(7)

    # ARPU
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']
    cursor.execute("SELECT COALESCE(SUM(price_rub), 0) as revenue FROM purchases")
    total_revenue = cursor.fetchone()['revenue']
    arpu = round(total_revenue / total_users) if total_users > 0 else 0

    # Conversion rate
    cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM purchases")
    paying_users = cursor.fetchone()['count']
    conversion_rate = round((paying_users / total_users * 100), 1) if total_users > 0 else 0

    # Top 3 effects this week
    cursor.execute(f"""
        SELECT effect_id, COUNT(*) as count
        FROM generations
        WHERE created_at >= '{week_start}'
        GROUP BY effect_id
        ORDER BY count DESC
        LIMIT 3
    """)
    top_effects = cursor.fetchall()

    # Failed generations this week
    cursor.execute(f"""
        SELECT COUNT(*) as failed FROM generations WHERE status = 'failed' AND created_at >= '{week_start}'
    """)
    failed_count = cursor.fetchone()['failed']

    cursor.execute(f"SELECT COUNT(*) as total FROM generations WHERE created_at >= '{week_start}'")
    total_generations = cursor.fetchone()['total']

    failure_rate = round((failed_count / total_generations * 100), 1) if total_generations > 0 else 0

    # User segments
    segments = db.get_user_segments()

    conn.close()

    # Format report
    report = f"""📈 Weekly Report — Week ending {today.strftime('%Y-%m-%d')}

── Growth ──
New Users: {new_users_week} ({'+' if new_users_growth >= 0 else ''}{round(new_users_growth, 1)}% WoW)
WAPU: {wapu}
7-Day Retention: {retention['retention_rate']}%

── Revenue ──
Total: {revenue_week} ₽ ({'+' if revenue_growth >= 0 else ''}{round(revenue_growth, 1)}% WoW)
ARPU: {arpu} ₽
Conversion Rate: {conversion_rate}%

── Product ──
Top 3 Effects:
"""

    for i, effect in enumerate(top_effects, 1):
        report += f"{i}. {effect['effect_id']} ({effect['count']} uses)\n"

    report += f"\nFailed Generations: {failed_count} ({failure_rate}% failure rate)\n"

    report += f"""
── User Segments ──
Churned Users: {segments['churned']}
Exhausted Free Users: {segments['exhausted_free']}
Power Users: {segments['power_users']}

── Recommended Actions ──
"""

    # Add actionable recommendations
    if segments['exhausted_free'] > 10:
        report += f"• Target {segments['exhausted_free']} exhausted free users with discount offer\n"
    if failure_rate > 5:
        report += f"• Investigate effects with high failure rate\n"
    if conversion_rate < 10:
        report += f"• Test new pricing or payment UX improvements\n"
    if segments['churned'] > total_users * 0.5:
        report += f"• Launch re-engagement campaign for {segments['churned']} churned users\n"

    return report

if __name__ == "__main__":
    print(generate_weekly_report())
```

---

## 5. Admin Dashboard Enhancements

Modify `/admin` stats in `photo_bot.py`:

```python
async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show enhanced bot statistics."""
    query = update.callback_query
    await query.answer()

    stats = db.get_stats()
    retention = db.get_retention_stats(7)
    segments = db.get_user_segments()

    # Build effect stats text
    effect_lines = []
    for effect_id, effect in TRANSFORMATIONS.items():
        count = stats["effect_stats"].get(effect_id, 0)
        emoji = effect["label"].split()[0]
        name = " ".join(effect["label"].split()[1:])
        effect_lines.append(f"{emoji} {name}: {count}")

    effects_text = "\n".join(effect_lines) if effect_lines else "No data"

    # Build package stats text
    package_lines = []
    package_stats = stats.get("package_stats", {})
    for pkg_id, pkg in PACKAGES.items():
        credits = pkg["credits"]
        pkg_data = package_stats.get(credits, {"count": 0, "revenue": 0})
        package_lines.append(f"{credits} зарядов: {pkg_data['count']} шт. ({pkg_data['revenue']} ₽)")

    packages_text = "\n".join(package_lines) if package_lines else "No purchases"

    # Calculate conversion rate
    paying_users = len(set(stats.get('purchase_users', [])))  # Unique paying users
    conversion_rate = round((paying_users / stats['total_users'] * 100), 1) if stats['total_users'] > 0 else 0

    text = (
        f"📊 Статистика бота\n\n"
        f"── Пользователи ──\n"
        f"Всего: {stats['total_users']}\n"
        f"Активных (7 дней): {retention['active_users']}\n"
        f"Retention 7d: {retention['retention_rate']}%\n"
        f"Оплативших: {paying_users} ({conversion_rate}%)\n\n"
        f"── Сегменты ──\n"
        f"Новые (<7 дней): {segments['new_users']}\n"
        f"Закончились кредиты: {segments['exhausted_free']}\n"
        f"Power users (10+ gen): {segments['power_users']}\n"
        f"Churned (>30 дней): {segments['churned']}\n\n"
        f"── Генерации ──\n"
        f"Всего: {stats['total_generations']}\n\n"
        f"── Финансы ──\n"
        f"Продаж: {stats['total_purchases']}\n"
        f"Доход: {stats['total_revenue']} ₽\n\n"
        f"── По эффектам ──\n{effects_text}\n\n"
        f"── По пакетам ──\n{packages_text}"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")],
        ]),
    )
    return ADMIN_STATS
```

---

## 6. Export Tools

### CSV Export Script

Create `Photo bot/reports/export_csv.py`:

```python
"""
Export database tables to CSV for analysis in Excel/Google Sheets.
Usage: python reports/export_csv.py [table_name]
"""

import sys
import csv
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db

def export_table_to_csv(table_name: str, output_dir: str = "exports"):
    """Export a database table to CSV."""
    Path(output_dir).mkdir(exist_ok=True)

    conn = db.get_connection()
    cursor = conn.cursor()

    # Get all rows
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    if not rows:
        print(f"Table {table_name} is empty.")
        conn.close()
        return

    # Get column names
    columns = [description[0] for description in cursor.description]

    # Write to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{output_dir}/{table_name}_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"✅ Exported {len(rows)} rows to {filename}")
    conn.close()

def export_all():
    """Export all tables."""
    tables = ['users', 'generations', 'purchases', 'promo_codes', 'promo_redemptions', 'user_activity']
    for table in tables:
        try:
            export_table_to_csv(table)
        except Exception as e:
            print(f"❌ Failed to export {table}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        table = sys.argv[1]
        export_table_to_csv(table)
    else:
        print("Exporting all tables...")
        export_all()
```

**Usage:**
```bash
# Export single table
python "Photo bot/reports/export_csv.py" users

# Export all tables
python "Photo bot/reports/export_csv.py"
```

---

## 7. Testing & Validation

### Test Checklist After Migration

```bash
# 1. Verify schema changes
sqlite3 "Photo bot/photo_bot.db" ".schema users"
sqlite3 "Photo bot/photo_bot.db" ".schema generations"
sqlite3 "Photo bot/photo_bot.db" ".schema user_activity"

# 2. Test database functions
python -c "import database as db; print(db.get_retention_stats())"
python -c "import database as db; print(db.get_user_segments())"

# 3. Test report generation
python "Photo bot/reports/daily_report.py"
python "Photo bot/reports/weekly_report.py"

# 4. Test CSV export
python "Photo bot/reports/export_csv.py" users

# 5. Test bot with test token (verify no errors)
# Update .env with test token, run bot, interact with it
```

---

## 8. Deployment Checklist

### Pre-Deployment

```markdown
- [ ] Run all migrations locally
- [ ] Test database functions
- [ ] Test report scripts
- [ ] Backup production database
- [ ] Review code changes (git diff)
- [ ] Update ROADMAP.md with completed tasks
```

### Deployment Steps

```bash
# 1. Backup production database from Railway volume
railway run cat /data/photo_bot.db > ./backups/photo_bot_$(date +%Y%m%d).db

# 2. Commit changes
git add .
git commit -m "Add analytics infrastructure: retention tracking, failed generations, activity log"

# 3. Push to GitHub (Railway auto-deploys)
git push origin main

# 4. Run migrations on Railway
# (If using Railway CLI)
railway run python run_migration.py migrations/001_add_retention_tracking.sql
railway run python run_migration.py migrations/002_add_generation_status.sql
railway run python run_migration.py migrations/003_create_activity_log.sql

# 5. Verify deployment
railway logs --tail

# 6. Test critical flows
# - Send test message to bot
# - Create test generation
# - Check /admin dashboard
```

### Post-Deployment Validation

```markdown
- [ ] Bot responds to /start
- [ ] Admin dashboard shows new metrics
- [ ] No errors in Railway logs
- [ ] Test generation flow end-to-end
- [ ] Verify data is being logged (check user_activity table)
- [ ] Run daily report script manually
```

---

## 9. Maintenance

### Daily Tasks
```bash
# Check logs for errors
railway logs --tail=100 | grep ERROR

# Generate daily report
python reports/daily_report.py
```

### Weekly Tasks
```bash
# Generate weekly report
python reports/weekly_report.py

# Export data for manual analysis
python reports/export_csv.py

# Backup database from Railway volume
railway run cat /data/photo_bot.db > photo_bot_backup_$(date +%Y%m%d).db
```

### Monthly Tasks
```bash
# Full database export
python reports/export_csv.py

# Review and clean old activity logs (optional, if table gets large)
# Keep last 90 days only
sqlite3 photo_bot.db "DELETE FROM user_activity WHERE created_at < date('now', '-90 days')"
```

---

## 10. Next Steps

After Phase 1 implementation:

1. **Test in production for 1 week**
   - Verify data accuracy
   - Adjust queries if needed

2. **Phase 2: Advanced Features**
   - Session tracking
   - Effect performance scorecard
   - Automated campaigns (re-engagement, upsells)

3. **Phase 3: Visualization**
   - Build dashboard (Metabase or custom web app)
   - Real-time metrics display

---

**Questions or Issues?**
- Check Railway logs: `railway logs --tail=200`
- Test queries in SQLite browser
- Review `DATA_ANALYSIS.md` for strategic context
