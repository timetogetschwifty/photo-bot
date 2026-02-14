"""
Notification system for Photo Bot.
Handles automated user messages for engagement and retention.
"""

import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
import database as db

logger = logging.getLogger(__name__)

# Global bot instance (set on init)
_bot_instance = None


def init_notifications(bot: Bot):
    """Initialize notification system with bot instance."""
    global _bot_instance
    _bot_instance = bot
    logger.info("Notification system initialized")


async def send_notification(
    user_id: int,
    notification_id: str,
    message: str,
    reply_markup=None,
    allow_duplicate: bool = False
) -> bool:
    """
    Send notification to user and log it.

    Args:
        user_id: Telegram user ID
        notification_id: Notification identifier (e.g., 'N1', 'N3')
        message: Message text
        reply_markup: Optional inline keyboard
        allow_duplicate: If False, won't send if already sent to this user

    Returns:
        True if sent successfully, False otherwise
    """
    if not _bot_instance:
        logger.error("Notification system not initialized")
        return False

    # Check if already sent (for non-repeating notifications)
    if not allow_duplicate and _is_notification_sent(user_id, notification_id):
        logger.info(f"Notification {notification_id} already sent to user {user_id}")
        return False

    try:
        await _bot_instance.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        # Log notification
        _log_notification(user_id, notification_id)

        logger.info(f"✅ Sent notification {notification_id} to user {user_id}")
        return True

    except TelegramError as e:
        logger.error(f"❌ Failed to send notification {notification_id} to {user_id}: {e}")
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


# ── Individual Notification Functions ────────────────────────────────────────


async def send_welcome_reminder(user_id: int, username: str, credits: int) -> bool:
    """
    N1: Welcome Reminder
    Sent 24h after signup to users who haven't generated yet.
    """
    name = username or "друг"
    message = (
        f"👋 Привет, {name}!\n\n"
        f"Ты получил <b>{credits} бесплатных заряда</b>, но ещё не попробовал магию ✨\n\n"
        "Попробуй любой эффект — это займёт 1 минуту!"
    )

    # Add inline keyboard button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Создать магию", url=f"https://t.me/{_get_bot_username()}")]
    ])

    return await send_notification(user_id, "N1", message, reply_markup=keyboard)


async def send_credits_exhausted(user_id: int, ref_link: str) -> bool:
    """
    N3: Credits Exhausted
    Sent immediately when user tries to use bot with 0 credits.
    """
    message = (
        "😢 <b>Заряды закончились!</b>\n\n"
        "Но не переживай — продолжить легко:\n\n"
        "🎁 <b>Специальное предложение:</b>\n"
        "10 зарядов всего за 99 ₽\n\n"
        "Или пригласи друга и получи <b>+3 заряда бесплатно</b>! 👥\n\n"
        f"Твоя ссылка:\n<code>{ref_link}</code>"
    )

    # Add inline keyboard with actions
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Купить заряды", url=f"https://t.me/{_get_bot_username()}?start=buy")],
        [InlineKeyboardButton("👥 Пригласить друга", url=f"https://t.me/share/url?url={ref_link}")]
    ])

    return await send_notification(user_id, "N3", message, reply_markup=keyboard)


def _get_bot_username() -> str:
    """Get bot username from environment."""
    import os
    return os.getenv("BOT_USERNAME", "your_bot")


# ── Statistics ────────────────────────────────────────────────────────────────


def get_notification_stats(notification_id: str = None) -> dict:
    """
    Get notification statistics.

    Args:
        notification_id: Optional filter by notification ID

    Returns:
        Dictionary with stats (total_sent, unique_users, etc.)
    """
    conn = db.get_connection()
    cursor = conn.cursor()

    if notification_id:
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_sent,
                COUNT(DISTINCT user_id) as unique_users
            FROM notification_log
            WHERE notification_id = ?
            """,
            (notification_id,)
        )
    else:
        cursor.execute(
            """
            SELECT
                notification_id,
                COUNT(*) as total_sent,
                COUNT(DISTINCT user_id) as unique_users
            FROM notification_log
            GROUP BY notification_id
            """
        )

    result = cursor.fetchall()
    conn.close()

    return result
