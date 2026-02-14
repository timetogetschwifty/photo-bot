"""
Scheduled notification jobs for Photo Bot.
Run daily to send automated notifications.

Schedule: Daily at 10 AM MSK (7 AM UTC)
Timezone: All times in MSK (Moscow, UTC+3)

Usage:
    python jobs/notification_jobs.py

Cron schedule (for 10 AM MSK):
    0 7 * * *  (7 AM UTC = 10 AM MSK)
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


async def run_daily_jobs():
    """Run all daily notification jobs."""
    print(f"📅 Running daily notification jobs at {datetime.now()}")

    # Initialize bot and notification system
    bot = Bot(token=BOT_TOKEN)
    notif.init_notifications(bot)

    # Run jobs
    await send_welcome_reminders(bot)

    print("✅ Daily notification jobs completed")


async def send_welcome_reminders(bot: Bot):
    """
    N1: Send welcome reminders to inactive new users.

    Criteria:
    - Registered exactly 24 hours ago (date(created_at) = yesterday)
    - Has 0 generations (never uploaded a photo)
    - Still has credits available
    """
    conn = db.get_connection()
    cursor = conn.cursor()

    # Users registered 24h ago with 0 generations
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

        # Rate limit: 10 messages per second max
        await asyncio.sleep(0.1)

    print(f"✅ Sent {sent_count}/{len(users)} welcome reminders")

    # Send summary to admin
    if ADMIN_ID and sent_count > 0:
        summary = f"📊 Daily N1 Report\n\n" \
                  f"Welcome reminders sent: {sent_count}\n" \
                  f"Date: {datetime.now().strftime('%Y-%m-%d')}"
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
