"""
Scheduled notification jobs for Photo Bot.
Run daily to send automated notifications.

Schedule: Daily at 11 AM MSK (8 AM UTC)

Usage:
    python jobs/notification_jobs.py

Cron schedule (for 11 AM MSK):
    0 8 * * *  (8 AM UTC = 11 AM MSK)
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path so we can import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Bot
from dotenv import load_dotenv
import database as db
import notifications as notif

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Package info for N9 abandoned payment messages
PACKAGES = {
    "pkg_10": {"credits": 10, "price": 99, "label": "10 зарядов"},
    "pkg_25": {"credits": 25, "price": 229, "label": "25 зарядов"},
    "pkg_50": {"credits": 50, "price": 399, "label": "50 зарядов"},
    "pkg_100": {"credits": 100, "price": 699, "label": "100 зарядов"},
}


async def run_daily_jobs():
    """Run all daily notification jobs."""
    print(f"📅 Running daily notification jobs at {datetime.now()}")

    # Initialize bot and notification system
    bot = Bot(token=BOT_TOKEN)
    notif.init_notifications(bot)

    # Run jobs and collect results
    results = {}

    results["N1"] = await send_welcome_reminders()
    results["N9"] = await send_abandoned_payment_reminders()

    # N4: Win-Back runs only on Mondays
    if datetime.now().weekday() == 0:
        results["N4"] = await send_winback_offers()

    # Send combined admin summary
    await send_admin_summary(bot, results)

    print("✅ Daily notification jobs completed")


async def send_welcome_reminders() -> int:
    """
    N1: Send welcome reminders to inactive new users.

    Trigger: created_at <= now-24h AND gen_count = 0 AND credits > 0
    """
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.telegram_id, u.username, u.credits
        FROM users u
        WHERE date(u.created_at) = date('now', '-1 day')
          AND u.telegram_id NOT IN (SELECT DISTINCT user_id FROM generations)
          AND u.credits > 0
    """)

    users = cursor.fetchall()
    conn.close()

    print(f"📬 Found {len(users)} users eligible for N1 (Welcome Reminder)")

    sent_count = 0
    for user in users:
        success = await notif.send_welcome_reminder(
            user['telegram_id'],
            user['username'],
            user['credits']
        )
        if success:
            sent_count += 1
        await asyncio.sleep(0.1)

    print(f"✅ N1: Sent {sent_count}/{len(users)}")
    return sent_count


async def send_zero_balance_silent() -> int:
    """
    N10: Zero Balance Silent — re-engage users with 0 credits who went silent.

    Trigger: credits = 0 AND last_active_at <= now-48h AND NOT already sent N10
    """
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.telegram_id
        FROM users u
        WHERE u.credits = 0
          AND u.last_active_at <= datetime('now', '-48 hours')
          AND u.telegram_id NOT IN (
              SELECT user_id FROM notification_log WHERE notification_id = 'N10'
          )
    """)

    users = cursor.fetchall()
    conn.close()

    print(f"📬 Found {len(users)} users eligible for N10 (Zero Balance Silent)")

    sent_count = 0
    for user in users:
        success = await notif.send_zero_balance_silent(user['telegram_id'])
        if success:
            sent_count += 1
        await asyncio.sleep(0.1)

    print(f"✅ N10: Sent {sent_count}/{len(users)}")
    return sent_count


async def send_winback_offers() -> int:
    """
    N4: Win-Back Offer — re-engage churned users (Mondays only).

    Trigger: last_active_at <= now-30d AND gen_count >= 1 AND NOT already sent N4
    """
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.telegram_id
        FROM users u
        WHERE u.last_active_at <= datetime('now', '-30 days')
          AND u.telegram_id IN (
              SELECT DISTINCT user_id FROM generations WHERE status = 'success'
          )
          AND u.telegram_id NOT IN (
              SELECT user_id FROM notification_log WHERE notification_id = 'N4'
          )
    """)

    users = cursor.fetchall()
    conn.close()

    print(f"📬 Found {len(users)} users eligible for N4 (Win-Back)")

    sent_count = 0
    for user in users:
        success = await notif.send_winback_offer(user['telegram_id'])
        if success:
            sent_count += 1
        await asyncio.sleep(0.1)

    print(f"✅ N4: Sent {sent_count}/{len(users)}")
    return sent_count


async def send_abandoned_payment_reminders() -> int:
    """
    N9: Abandoned Payment — remind users who started checkout but didn't pay.

    Trigger: invoice sent >1h ago, not paid, not already notified for this invoice
    """
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.id, i.user_id, i.package_id
        FROM invoices i
        WHERE i.paid = 0
          AND i.notified = 0
          AND i.sent_at <= datetime('now', '-1 hour')
    """)

    invoices = cursor.fetchall()
    conn.close()

    print(f"📬 Found {len(invoices)} unpaid invoices eligible for N9 (Abandoned Payment)")

    sent_count = 0
    for inv in invoices:
        package = PACKAGES.get(inv['package_id'], {})
        package_name = package.get("label", "Пакет зарядов")
        price = package.get("price", 99)

        success = await notif.send_abandoned_payment(
            inv['user_id'], package_name, price
        )
        if success:
            sent_count += 1
            # Mark invoice as notified
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE invoices SET notified = 1 WHERE id = ?",
                (inv['id'],)
            )
            conn.commit()
            conn.close()

        await asyncio.sleep(0.1)

    print(f"✅ N9: Sent {sent_count}/{len(invoices)}")
    return sent_count


async def send_admin_summary(bot: Bot, results: dict):
    """Send combined admin summary after all jobs complete."""
    if not ADMIN_ID:
        return

    lines = ["📊 Daily Notifications Report\n"]
    for notif_id, count in results.items():
        lines.append(f"{notif_id}: {count} sent")
    lines.append(f"\nDate: {datetime.now().strftime('%Y-%m-%d')}")

    summary = "\n".join(lines)

    try:
        await bot.send_message(chat_id=ADMIN_ID, text=summary)
    except Exception as e:
        print(f"⚠️ Could not send admin summary: {e}")


# Entry point
if __name__ == "__main__":
    try:
        asyncio.run(run_daily_jobs())
    except Exception as e:
        print(f"❌ Error running daily jobs: {e}")
        sys.exit(1)
