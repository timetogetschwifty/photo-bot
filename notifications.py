"""
Notification system for Photo Bot.
Handles automated user messages for engagement and retention.
"""

import logging
import os
from datetime import date

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


# ── Core Send Engine ──────────────────────────────────────────────────────────


async def send_notification(
    user_id: int,
    notification_id: str,
    message: str,
    reply_markup=None,
    allow_duplicate: bool = False,
    scheduled: bool = False,
) -> bool:
    """
    Send notification to user and log it.

    Args:
        user_id: Telegram user ID
        notification_id: Notification identifier (e.g., 'N1', 'N3')
        message: Message text
        reply_markup: Optional inline keyboard
        allow_duplicate: If False, won't send if this notification_id already sent to user
        scheduled: If True, check daily limit (max 1 scheduled notification per user per day)

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

    # Scheduled notifications: max 1 per user per day
    if scheduled and _has_scheduled_notification_today(user_id):
        logger.info(f"User {user_id} already received a scheduled notification today, skipping {notification_id}")
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


def _has_scheduled_notification_today(user_id: int) -> bool:
    """Check if user already received a scheduled notification today."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM notification_log WHERE user_id = ? AND notification_id IN ('N1','N4','N10') AND date(sent_at) = date('now')",
        (user_id,)
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


def _get_bot_username() -> str:
    """Get bot username from environment."""
    return os.getenv("BOT_USERNAME", "your_bot")


# ── Individual Notification Functions ─────────────────────────────────────────


async def send_welcome_reminder(user_id: int, username: str, credits: int) -> bool:
    """N1: Welcome Reminder — sent 24h after signup to inactive users."""
    name = username or "друг"
    message = (
        f"👋 Привет, {name}!\n\n"
        f"Ты получил <b>{credits} бесплатных заряда</b>, но ещё не попробовал магию ✨\n\n"
        "Попробуй любой эффект — это займёт 1 минуту!"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Создать магию", url=f"https://t.me/{_get_bot_username()}?start=browse")]
    ])

    return await send_notification(user_id, "N1", message, reply_markup=keyboard, scheduled=True)


async def send_credits_low_warning(user_id: int) -> bool:
    """N2: Credits Running Low — real-time after generation leaves 1 credit."""
    bot_username = _get_bot_username()
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    message = (
        "🤫 Никто не знает, что у тебя остался 1 заряд.\n\n"
        "Кроме нас. Исправь это — тихо и быстро:\n\n"
        "💳 Пополнить → от 99 ₽\n"
        "👥 Позвать друга → +3 заряда бесплатно"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Пополнить", url=f"https://t.me/{bot_username}?start=buy")],
        [InlineKeyboardButton("👥 Позвать друга", url=f"https://t.me/share/url?url={ref_link}")]
    ])

    return await send_notification(user_id, "N2", message, reply_markup=keyboard, allow_duplicate=True)



async def send_winback_offer(user_id: int) -> bool:
    """N4: Win-Back Offer — re-engage churned users, gives +3 credits."""
    message = (
        "👀 Давно не виделись.\n\n"
        "Мы не спрашиваем где ты был.\n"
        "Просто оставили тебе подарок — ⚡ <b>+3 заряда</b> уже на балансе.\n\n"
        "Есть новые эффекты. Посмотришь?"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Посмотреть", url=f"https://t.me/{_get_bot_username()}?start=browse")]
    ])

    sent = await send_notification(user_id, "N4", message, reply_markup=keyboard, scheduled=True)
    if sent:
        db.add_credits(user_id, 3)
    return sent


async def send_new_effects(user_id: int, drop_name: str) -> bool:
    """N5: New Drop Available — manual admin broadcast."""
    message = drop_name

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Смотреть", url=f"https://t.me/{_get_bot_username()}?start=browse")]
    ])

    return await send_notification(user_id, "N5", message, reply_markup=keyboard, allow_duplicate=True)


async def send_referral_reminder(user_id: int, ref_link: str) -> bool:
    """N6: Referral Reminder — after 3rd generation."""
    message = (
        "🔥 Тебе нравится бот?\n\n"
        "Пригласи друзей и получай <b>+3 заряда</b> за каждого!\n\n"
        f"👥 Твоя реферальная ссылка:\n<code>{ref_link}</code>"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Поделиться ссылкой", url=f"https://t.me/share/url?url={ref_link}")]
    ])

    return await send_notification(user_id, "N6", message, reply_markup=keyboard)


async def send_first_purchase_thanks(user_id: int) -> bool:
    """N7: First Purchase Thank You."""
    message = (
        "🎉 Ты с нами!\n\n"
        "Спасибо — это многое значит.\n\n"
        "Создавай магию без ограничений ✨"
    )

    return await send_notification(user_id, "N7", message)


async def send_power_user_vip(user_id: int, promo_code: str) -> bool:
    """N8: Power User VIP — at 25 generations."""
    message = (
        "👑 Ты стал VIP-пользователем!\n\n"
        "🎉 25 магических трансформаций — впечатляет!\n\n"
        "🎁 Твой эксклюзивный бонус:\n"
        f"Промокод <code>{promo_code}</code> → <b>+5 зарядов бесплатно</b>\n\n"
        "Спасибо, что ты с нами! ✨"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Активировать бонус", url=f"https://t.me/{_get_bot_username()}?start=promo")]
    ])

    return await send_notification(user_id, "N8", message, reply_markup=keyboard)


async def send_abandoned_payment(user_id: int, package_name: str, price: int) -> bool:
    """N9: Abandoned Payment — invoice sent but not paid after 1h."""
    message = (
        "👀 Кто-то не завершил покупку.\n\n"
        f"<b>{package_name}</b> — {price} ₽\n\n"
        "Если передумал — всё нормально.\n"
        "Если нет — вот кнопка 👇"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Завершить покупку", url=f"https://t.me/{_get_bot_username()}?start=buy")]
    ])

    return await send_notification(user_id, "N9", message, reply_markup=keyboard, allow_duplicate=True)


async def send_zero_balance_silent(user_id: int) -> bool:
    """N10: Zero Balance Silent — credits=0 and inactive for 48h."""
    message = (
        "👋 Привет!\n\n"
        "Твой баланс всё ещё на нуле.\n\n"
        "Пополни заряды — и продолжай создавать магию! ✨\n\n"
        "💡 10 зарядов всего за 99 ₽"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Пополнить баланс", url=f"https://t.me/{_get_bot_username()}?start=buy")]
    ])

    return await send_notification(user_id, "N10", message, reply_markup=keyboard, scheduled=True)


# ── Statistics ────────────────────────────────────────────────────────────────


def get_notification_stats(notification_id: str = None) -> list:
    """Get notification statistics."""
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
