"""
SQLite database layer for Photo Bot.
Handles users, promo codes, redemptions, and generation tracking.
"""

import os
import sqlite3
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Database file path
# On Railway: uses /data/photo_bot.db (set via DB_PATH env var)
# Locally: uses photo_bot.db in same directory as this script
default_db_path = str(Path(__file__).parent / "photo_bot.db")
DB_PATH = Path(os.getenv("DB_PATH", default_db_path))


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            credits INTEGER DEFAULT 3,
            total_spent INTEGER DEFAULT 0,
            referred_by INTEGER,
            referral_credited INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Promo codes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            credits INTEGER NOT NULL,
            max_uses INTEGER,
            times_used INTEGER DEFAULT 0,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration: add expires_at for existing databases
    try:
        cursor.execute("ALTER TABLE promo_codes ADD COLUMN expires_at TIMESTAMP")
    except Exception:
        pass  # Column already exists

    # Promo redemptions table (tracks who redeemed what)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_redemptions (
            user_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, code)
        )
    """)

    # Generations table (tracks each generation for statistics)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            effect_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Purchases table (tracks package purchases for revenue stats)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_credits INTEGER NOT NULL,
            price_rub INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Notification log table (tracks sent notifications to prevent spam)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notification_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            opened BOOLEAN DEFAULT 0,
            clicked BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )
    """)

    # Create indexes for notification_log
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notif_user
        ON notification_log(user_id, notification_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notif_sent
        ON notification_log(sent_at)
    """)

    conn.commit()
    conn.close()


# ── User Operations ──────────────────────────────────────────────────────────


def get_user(telegram_id: int) -> Optional[sqlite3.Row]:
    """Get user by Telegram ID, or None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def create_user(
    telegram_id: int,
    username: Optional[str] = None,
    referred_by: Optional[int] = None,
) -> sqlite3.Row:
    """Create a new user with 3 free credits."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (telegram_id, username, referred_by)
        VALUES (?, ?, ?)
        """,
        (telegram_id, username, referred_by),
    )
    conn.commit()
    conn.close()
    return get_user(telegram_id)


def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    referred_by: Optional[int] = None,
) -> tuple[sqlite3.Row, bool]:
    """
    Get existing user or create new one.
    Returns (user, is_new) tuple.
    """
    user = get_user(telegram_id)
    if user:
        # Update username if changed
        if username and user["username"] != username:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET username = ? WHERE telegram_id = ?",
                (username, telegram_id),
            )
            conn.commit()
            conn.close()
            user = get_user(telegram_id)
        return user, False
    else:
        return create_user(telegram_id, username, referred_by), True


def add_credits(telegram_id: int, amount: int) -> int:
    """Add credits to user. Returns new balance."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET credits = credits + ? WHERE telegram_id = ?",
        (amount, telegram_id),
    )
    conn.commit()
    cursor.execute("SELECT credits FROM users WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result["credits"] if result else 0


def deduct_credit(telegram_id: int) -> bool:
    """
    Deduct 1 credit from user.
    Returns True if successful, False if insufficient credits.
    """
    user = get_user(telegram_id)
    if not user or user["credits"] < 1:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET credits = credits - 1, total_spent = total_spent + 1
        WHERE telegram_id = ? AND credits > 0
        """,
        (telegram_id,),
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def refund_credit(telegram_id: int) -> int:
    """Refund 1 credit (after Gemini failure). Returns new balance."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET credits = credits + 1, total_spent = total_spent - 1
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )
    conn.commit()
    cursor.execute("SELECT credits FROM users WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result["credits"] if result else 0


def mark_referral_credited(referred_user_id: int) -> Optional[int]:
    """
    Mark that referral bonus was credited for this user.
    Returns the referrer's telegram_id if bonus should be given, None otherwise.
    """
    user = get_user(referred_user_id)
    if not user or not user["referred_by"] or user["referral_credited"]:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET referral_credited = 1 WHERE telegram_id = ?",
        (referred_user_id,),
    )
    conn.commit()
    conn.close()
    return user["referred_by"]


# ── Promo Code Operations ────────────────────────────────────────────────────


def generate_promo_code() -> str:
    """Generate a random promo code like 'PROMO-A7X3'."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(4))
    return f"PROMO-{suffix}"


def create_promo_code(
    credits: int,
    max_uses: Optional[int] = None,
    expires_at: Optional[datetime] = None,
) -> str:
    """Create a new promo code. Returns the generated code."""
    code = generate_promo_code()

    # Ensure uniqueness
    while get_promo_code(code):
        code = generate_promo_code()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO promo_codes (code, credits, max_uses, expires_at) VALUES (?, ?, ?, ?)",
        (code, credits, max_uses, expires_at.isoformat() if expires_at else None),
    )
    conn.commit()
    conn.close()
    return code


def get_promo_code(code: str) -> Optional[sqlite3.Row]:
    """Get promo code info, or None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promo_codes WHERE code = ?", (code.upper(),))
    promo = cursor.fetchone()
    conn.close()
    return promo


def redeem_promo_code(telegram_id: int, code: str) -> tuple[bool, str, int]:
    """
    Attempt to redeem a promo code.
    Returns (success, message, credits_added).
    """
    code = code.upper().strip()
    promo = get_promo_code(code)

    if not promo:
        return False, "Промокод не найден", 0

    # Check if already redeemed by this user
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM promo_redemptions WHERE user_id = ? AND code = ?",
        (telegram_id, code),
    )
    if cursor.fetchone():
        conn.close()
        return False, "Ты уже использовал этот промокод", 0

    # Check expiry
    if promo["expires_at"] is not None:
        expires_at = datetime.fromisoformat(promo["expires_at"])
        # Handle both naive and timezone-aware stored timestamps safely.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            conn.close()
            return False, "Срок действия промокода истёк", 0

    # Check max uses
    if promo["max_uses"] is not None and promo["times_used"] >= promo["max_uses"]:
        conn.close()
        return False, "Промокод больше не действителен", 0

    # Redeem it
    cursor.execute(
        "INSERT INTO promo_redemptions (user_id, code) VALUES (?, ?)",
        (telegram_id, code),
    )
    cursor.execute(
        "UPDATE promo_codes SET times_used = times_used + 1 WHERE code = ?",
        (code,),
    )
    conn.commit()
    conn.close()

    # Add credits to user
    credits = promo["credits"]
    add_credits(telegram_id, credits)

    return True, "Промокод активирован!", credits


# ── Generation Tracking ──────────────────────────────────────────────────────


def record_generation(telegram_id: int, effect_id: str) -> None:
    """Record a generation for statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO generations (user_id, effect_id) VALUES (?, ?)",
        (telegram_id, effect_id),
    )
    conn.commit()
    conn.close()


# ── Purchase Tracking ────────────────────────────────────────────────────────


def record_purchase(telegram_id: int, package_credits: int, price_rub: int) -> None:
    """Record a package purchase."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO purchases (user_id, package_credits, price_rub) VALUES (?, ?, ?)",
        (telegram_id, package_credits, price_rub),
    )
    conn.commit()
    conn.close()


# ── Statistics ───────────────────────────────────────────────────────────────


def get_stats() -> dict:
    """Get bot statistics for admin panel."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total users
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()["count"]

    # Total generations
    cursor.execute("SELECT COUNT(*) as count FROM generations")
    total_generations = cursor.fetchone()["count"]

    # Total purchases and revenue
    cursor.execute(
        "SELECT COUNT(*) as count, COALESCE(SUM(price_rub), 0) as revenue FROM purchases"
    )
    purchase_stats = cursor.fetchone()
    total_purchases = purchase_stats["count"]
    total_revenue = purchase_stats["revenue"]

    # Per-effect stats
    cursor.execute(
        """
        SELECT effect_id, COUNT(*) as count
        FROM generations
        GROUP BY effect_id
        """
    )
    effect_stats = {row["effect_id"]: row["count"] for row in cursor.fetchall()}

    # Per-package stats (breakdown by credits purchased)
    cursor.execute(
        """
        SELECT package_credits, COUNT(*) as count, COALESCE(SUM(price_rub), 0) as revenue
        FROM purchases
        GROUP BY package_credits
        ORDER BY package_credits
        """
    )
    package_stats = {
        row["package_credits"]: {"count": row["count"], "revenue": row["revenue"]}
        for row in cursor.fetchall()
    }

    conn.close()

    return {
        "total_users": total_users,
        "total_generations": total_generations,
        "total_purchases": total_purchases,
        "total_revenue": total_revenue,
        "effect_stats": effect_stats,
        "package_stats": package_stats,
    }


# Initialize database on import
init_db()
