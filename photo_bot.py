"""
Photo Bot — AI Photo Transformations with Credit System

A Telegram bot that applies AI-powered photo transformations using Google Gemini.
Features: credit system, promo codes, referrals, package purchases via YooMoney.
"""

import os
import io
import logging

from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

import database as db

# ── Configuration ──────────────────────────────────────────────────────────────

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
YOOMONEY_PROVIDER_TOKEN = os.environ["YOOMONEY_PROVIDER_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "your_bot")

GEMINI_MODEL = "gemini-3-pro-image-preview"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Transformations ──────────────────────────────────────────────────────────

TRANSFORMATIONS = {
    "love_is": {
        "label": "💌 Открытка в стиле Love is",
        "description": "Превращу фото в милую открытку в стиле Love is",
        "prompt": (
            "Transform this photo into a 'Love Is...' comic style illustration. "
            "Style: Simple cartoon with clean black outlines, soft pastel colors, white background. "
            "Vintage 1990s bubble-gum wrapper aesthetic - minimal, cute, wholesome. "
            "Characters: Convert the person(s) into cartoon characters with chibi-like rounded bodies. "
            "Preserve their hairstyle, hair color, face shape, glasses if any. Gentle happy expressions. "
            "Composition: Centered, full body visible, white background only. "
            "Add 'Love is...' text at bottom in handwritten style with a sweet phrase about the scene. "
            "NOT realistic. NOT detailed. Keep it minimal and cute like classic Love Is comics."
        ),
        "category": "trend",
    },
    "cat_phone": {
        "label": "🐱 Котик вместо телефона",
        "description": "Заменю телефон в руках на милого котика",
        "prompt": (
            "Replace the phone in the person's hand with a small fluffy kitten. "
            "The kitten must be in the exact position and size where the phone was. "
            "The hand should naturally hold/cradle the kitten with fingers wrapped around it. "
            "Match the kitten's fur lighting and shadows to the original scene. "
            "The kitten should look calm and relaxed, possibly looking at the camera. "
            "Keep everything else exactly the same: person, face, pose, background, framing, colors, camera angle. "
            "Remove the phone completely - no trace of it. "
            "Photorealistic result. No style changes. No enhancements. No extra objects."
        ),
        "category": "trend",
    },
    "afro": {
        "label": "🦱 Афро",
        "description": "Добавлю пышную афро-причёску",
        "prompt": (
            "Change the person's haircut to a big voluminous afro hairstyle. "
            "Keep the face and everything else the same."
        ),
        "category": "style",
    },
    "mullet": {
        "label": "🥸 Маллет и усы",
        "description": "Добавлю причёску маллет и усы",
        "prompt": (
            "Give the person a mullet haircut and a mustache. "
            "Keep everything else the same."
        ),
        "category": "style",
    },
}

# ── Pricing (RUB, in kopecks for Telegram) ───────────────────────────────────

PACKAGES = {
    # Note: YooKassa test mode may require min 100₽. Prices in kopecks.
    "pkg_5": {"credits": 5, "price": 5900, "label": "5 фото — 59 ₽"},
    "pkg_10": {"credits": 10, "price": 9900, "label": "10 фото — 99 ₽"},
    "pkg_25": {"credits": 25, "price": 22900, "label": "25 фото — 229 ₽"},
    "pkg_50": {"credits": 50, "price": 39900, "label": "50 фото — 399 ₽"},
    "pkg_100": {"credits": 100, "price": 69900, "label": "100 фото — 699 ₽"},
}

PROMO_AMOUNTS = [10, 25, 50, 100]

# ── Conversation states ──────────────────────────────────────────────────────

(
    MAIN_MENU,
    CHOOSING_CATEGORY,
    CHOOSING_TREND,
    CHOOSING_STYLE,
    WAITING_PHOTO,
    STORE,
    WAITING_PAYMENT,
    PROMO_INPUT,
    REFERRAL,
    ADMIN_MENU,
    ADMIN_STATS,
    ADMIN_PROMO,
) = range(12)

# ── Gemini client ────────────────────────────────────────────────────────────

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ── Helper functions ─────────────────────────────────────────────────────────


def get_effects_by_category(category: str) -> dict:
    """Get all effects in a category."""
    return {k: v for k, v in TRANSFORMATIONS.items() if v.get("category") == category}


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build main menu keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Создать магию", callback_data="menu_create")],
        [InlineKeyboardButton("💳 Пополнить запасы", callback_data="menu_store")],
        [InlineKeyboardButton("🎁 Промокод", callback_data="menu_promo")],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data="menu_referral")],
    ])


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with just 'В начало' button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 В начало", callback_data="back_to_main")],
    ])


# ── Main Menu ────────────────────────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command. Check for referral link."""
    user = update.effective_user
    args = context.args

    # Parse referral link: /start ref_123456
    referred_by = None
    if args and args[0].startswith("ref_"):
        try:
            referred_by = int(args[0][4:])
            if referred_by == user.id:
                referred_by = None  # Can't refer yourself
        except ValueError:
            pass

    # Get or create user
    db_user, is_new = db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        referred_by=referred_by,
    )

    credits = db_user["credits"]
    name = user.first_name or "друг"

    await update.message.reply_text(
        f"Привет, {name}!\n💰 Баланс: {credits} фото",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show main menu (from callback)."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0
    name = user.first_name or "друг"

    text = f"Привет, {name}!\n💰 Баланс: {credits} фото"

    # Check if message has photo (can't edit photo messages to text)
    if query.message.photo:
        await query.message.delete()
        await context.bot.send_message(
            chat_id=user.id,
            text=text,
            reply_markup=main_menu_keyboard(),
        )
    else:
        await query.edit_message_text(
            text,
            reply_markup=main_menu_keyboard(),
        )
    return MAIN_MENU


# ── Create Magic Flow ────────────────────────────────────────────────────────


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show effect categories."""
    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Тренды", callback_data="cat_trend")],
        [InlineKeyboardButton("💇 Меняем стиль", callback_data="cat_style")],
        [InlineKeyboardButton("⬅️ В начало", callback_data="back_to_main")],
    ])

    await query.edit_message_text(
        "Выбери категорию:",
        reply_markup=keyboard,
    )
    return CHOOSING_CATEGORY


async def show_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show trend effects."""
    query = update.callback_query
    await query.answer()

    effects = get_effects_by_category("trend")
    buttons = [
        [InlineKeyboardButton(v["label"], callback_data=f"effect_{k}")]
        for k, v in effects.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ В начало", callback_data="back_to_main")])

    await query.edit_message_text(
        "🔥 Тренды",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return CHOOSING_TREND


async def show_styles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show style effects."""
    query = update.callback_query
    await query.answer()

    effects = get_effects_by_category("style")
    buttons = [
        [InlineKeyboardButton(v["label"], callback_data=f"effect_{k}")]
        for k, v in effects.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ В начало", callback_data="back_to_main")])

    await query.edit_message_text(
        "💇 Меняем стиль",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return CHOOSING_STYLE


async def select_effect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User selected an effect. Check credits and show description."""
    query = update.callback_query
    await query.answer()

    effect_id = query.data.replace("effect_", "")
    if effect_id not in TRANSFORMATIONS:
        await query.edit_message_text("Неизвестный эффект.", reply_markup=back_to_main_keyboard())
        return MAIN_MENU

    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0

    # Check credits
    if credits < 1:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Пополнить запасы", callback_data="menu_store")],
            [InlineKeyboardButton("👥 Пригласить друга", callback_data="menu_referral")],
            [InlineKeyboardButton("🏠 В начало", callback_data="back_to_main")],
        ])
        await query.edit_message_text(
            "❌ У тебя закончились фото",
            reply_markup=keyboard,
        )
        return MAIN_MENU

    # Store selected effect
    context.user_data["effect_id"] = effect_id

    effect = TRANSFORMATIONS[effect_id]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="back_to_main")],
    ])

    await query.edit_message_text(
        f"{effect['label']}\n\n{effect['description']}\n\nОтправь мне фото для обработки.",
        reply_markup=keyboard,
    )
    return WAITING_PHOTO


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive photo and process it."""
    effect_id = context.user_data.get("effect_id")
    if not effect_id or effect_id not in TRANSFORMATIONS:
        await update.message.reply_text(
            "Что-то пошло не так. Используй /start",
            reply_markup=back_to_main_keyboard(),
        )
        return MAIN_MENU

    user = update.effective_user

    # Deduct credit
    if not db.deduct_credit(user.id):
        await update.message.reply_text(
            "❌ У тебя закончились фото",
            reply_markup=back_to_main_keyboard(),
        )
        return MAIN_MENU

    # Download photo
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    effect = TRANSFORMATIONS[effect_id]
    status_msg = await update.message.reply_text("⏳ Создаю магию...")

    try:
        input_image = Image.open(io.BytesIO(bytes(photo_bytes)))

        # Call Gemini
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[effect["prompt"], input_image],
            config=types.GenerateContentConfig(
                response_modalities=["Text", "Image"],
            ),
        )

        # Extract result image
        result_image = None
        result_text = None
        for part in response.parts:
            if part.inline_data is not None:
                # Convert Gemini response to PIL Image
                image_data = part.inline_data.data
                result_image = Image.open(io.BytesIO(image_data))
            elif part.text is not None:
                result_text = part.text

        if result_image is None:
            # Refund credit
            new_balance = db.refund_credit(user.id)
            msg = f"❌ Что-то пошло не так\n\nКредит возвращён на баланс."
            if result_text:
                msg += f"\n\nОтвет модели: {result_text[:200]}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"effect_{effect_id}")],
                [InlineKeyboardButton("🏠 В начало", callback_data="back_to_main")],
            ])
            await status_msg.edit_text(msg, reply_markup=keyboard)
            return MAIN_MENU

        # Record generation for statistics
        db.record_generation(user.id, effect_id)

        # Check if we should credit referrer (first generation)
        referrer_id = db.mark_referral_credited(user.id)
        if referrer_id:
            db.add_credits(referrer_id, 3)
            logger.info(f"Credited referrer {referrer_id} with 3 credits for user {user.id}")

        # Get updated balance
        db_user = db.get_user(user.id)
        remaining = db_user["credits"] if db_user else 0

        # Send result
        output_buffer = io.BytesIO()
        result_image.save(output_buffer, format="PNG")
        output_buffer.seek(0)

        await status_msg.delete()
        await update.message.reply_photo(
            photo=output_buffer,
            caption=f"✅ {effect['label']}\n💰 Осталось: {remaining} фото",
            reply_markup=back_to_main_keyboard(),
        )

    except Exception as e:
        logger.error("Error during transformation: %s", e, exc_info=True)
        # Refund credit
        new_balance = db.refund_credit(user.id)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"effect_{effect_id}")],
            [InlineKeyboardButton("🏠 В начало", callback_data="back_to_main")],
        ])
        await status_msg.edit_text(
            f"❌ Что-то пошло не так\n\nКредит возвращён на баланс.\n\nОшибка: {str(e)[:100]}",
            reply_markup=keyboard,
        )
    finally:
        context.user_data.pop("effect_id", None)

    return MAIN_MENU


async def photo_expected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle non-photo message when photo is expected."""
    await update.message.reply_text(
        "Пожалуйста, отправь фото.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отмена", callback_data="back_to_main")],
        ]),
    )
    return WAITING_PHOTO


# ── Store Flow ───────────────────────────────────────────────────────────────


async def show_store(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show package store."""
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton(pkg["label"], callback_data=f"buy_{key}")]
        for key, pkg in PACKAGES.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ В начало", callback_data="back_to_main")])

    await query.edit_message_text(
        "Выбери пакет:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return STORE


async def buy_package(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send payment invoice for selected package."""
    query = update.callback_query
    await query.answer()

    package_id = query.data.replace("buy_", "")
    if package_id not in PACKAGES:
        await query.edit_message_text("Неизвестный пакет.", reply_markup=back_to_main_keyboard())
        return MAIN_MENU

    package = PACKAGES[package_id]
    context.user_data["pending_package"] = package_id

    try:
        # Delete the menu message
        await query.delete_message()

        # Send invoice
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=f"Пакет {package['credits']} фото",
            description=f"Пополнение баланса на {package['credits']} фото",
            payload=f"package_{package_id}_{update.effective_user.id}",
            currency="RUB",
            prices=[LabeledPrice(f"{package['credits']} фото", package["price"])],
            provider_token=YOOMONEY_PROVIDER_TOKEN,
        )

        # Send cancel button separately (invoices can't have inline buttons)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Нажми кнопку ниже, чтобы отменить покупку:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment")]
            ]),
        )
        return WAITING_PAYMENT
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Ошибка платежа: {e}\n\nПопробуйте позже.",
            reply_markup=back_to_main_keyboard(),
        )
        return MAIN_MENU


async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel payment and return to main menu."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("pending_package", None)
    await query.edit_message_text("Покупка отменена.")
    return await show_main_menu_fresh(update, context)


async def show_main_menu_fresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a fresh main menu message (not edit)."""
    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0
    name = user.first_name or "друг"
    await context.bot.send_message(
        chat_id=user.id,
        text=f"Привет, {name}!\n💰 Баланс: {credits} фото",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve the payment."""
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle successful payment."""
    user = update.effective_user
    package_id = context.user_data.pop("pending_package", None)

    if package_id and package_id in PACKAGES:
        package = PACKAGES[package_id]
        credits = package["credits"]
        price_rub = package["price"] // 100  # Convert kopecks to rubles

        # Add credits and record purchase
        new_balance = db.add_credits(user.id, credits)
        db.record_purchase(user.id, credits, price_rub)

        await update.message.reply_text(
            f"✅ Оплата прошла!\n+{credits} фото добавлено\n\n💰 Баланс: {new_balance} фото",
            reply_markup=back_to_main_keyboard(),
        )
    else:
        await update.message.reply_text(
            "Оплата получена, но произошла ошибка. Свяжитесь с поддержкой.",
            reply_markup=back_to_main_keyboard(),
        )

    return MAIN_MENU


# ── Promo Code Flow ──────────────────────────────────────────────────────────


async def show_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for promo code."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Введи промокод:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В начало", callback_data="back_to_main")],
        ]),
    )
    return PROMO_INPUT


async def handle_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle promo code input."""
    user = update.effective_user
    code = update.message.text.strip()

    success, message, credits = db.redeem_promo_code(user.id, code)

    if success:
        db_user = db.get_user(user.id)
        new_balance = db_user["credits"] if db_user else 0
        await update.message.reply_text(
            f"✅ Промокод активирован!\n+{credits} фото добавлено\n\n💰 Баланс: {new_balance} фото",
            reply_markup=back_to_main_keyboard(),
        )
    else:
        await update.message.reply_text(
            f"❌ {message}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать другой", callback_data="menu_promo")],
                [InlineKeyboardButton("🏠 В начало", callback_data="back_to_main")],
            ]),
        )

    return MAIN_MENU


# ── Referral Flow ────────────────────────────────────────────────────────────


async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show referral info and link."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"

    # TODO: Telegram share button requires inline mode, showing link as text for now
    await query.edit_message_text(
        f"Приглашай друзей и получай\n+3 фото за каждого!\n\nТвоя ссылка:\n{ref_link}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В начало", callback_data="back_to_main")],
        ]),
    )
    return REFERRAL


# ── Admin Menu ───────────────────────────────────────────────────────────────


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /admin command."""
    user = update.effective_user

    logger.info(f"Admin attempt: user.id={user.id}, ADMIN_ID={ADMIN_ID}")

    if user.id != ADMIN_ID:
        await update.message.reply_text(f"Доступ запрещён. (Your ID: {user.id})")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔐 Админ-панель",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🎁 Создать промокод", callback_data="admin_promo")],
            [InlineKeyboardButton("🏠 Выход", callback_data="back_to_main")],
        ]),
    )
    return ADMIN_MENU


async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show bot statistics."""
    query = update.callback_query
    await query.answer()

    stats = db.get_stats()

    # Build effect stats text
    effect_lines = []
    for effect_id, effect in TRANSFORMATIONS.items():
        count = stats["effect_stats"].get(effect_id, 0)
        # Get emoji from label
        emoji = effect["label"].split()[0]
        name = " ".join(effect["label"].split()[1:])
        effect_lines.append(f"{emoji} {name}: {count}")

    effects_text = "\n".join(effect_lines)

    text = (
        f"📊 Статистика бота\n\n"
        f"Пользователей: {stats['total_users']}\n"
        f"Всего генераций: {stats['total_generations']}\n"
        f"Куплено пакетов: {stats['total_purchases']}\n"
        f"Доход: {stats['total_revenue']} ₽\n\n"
        f"── По эффектам ──\n{effects_text}"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")],
        ]),
    )
    return ADMIN_STATS


async def show_admin_promo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show promo code creation menu."""
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton(f"{amount} фото", callback_data=f"create_promo_{amount}")]
        for amount in PROMO_AMOUNTS
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")])

    await query.edit_message_text(
        "🎁 Создать промокод\n\nСколько фото даёт промокод?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ADMIN_PROMO


async def create_promo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create a promo code."""
    query = update.callback_query
    await query.answer()

    amount = int(query.data.replace("create_promo_", ""))
    code = db.create_promo_code(credits=amount, max_uses=1)

    await query.edit_message_text(
        f"✅ Промокод создан!\n\nКод: {code}\nДаёт: +{amount} фото",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Создать ещё", callback_data="admin_promo")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")],
        ]),
    )
    return ADMIN_MENU


async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back to admin menu."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔐 Админ-панель",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🎁 Создать промокод", callback_data="admin_promo")],
            [InlineKeyboardButton("🏠 Выход", callback_data="back_to_main")],
        ]),
    )
    return ADMIN_MENU


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Start the bot."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Main conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("admin", admin_command),
        ],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(show_categories, pattern="^menu_create$"),
                CallbackQueryHandler(show_store, pattern="^menu_store$"),
                CallbackQueryHandler(show_promo_input, pattern="^menu_promo$"),
                CallbackQueryHandler(show_referral, pattern="^menu_referral$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
                # Effect retry
                CallbackQueryHandler(select_effect, pattern="^effect_"),
            ],
            CHOOSING_CATEGORY: [
                CallbackQueryHandler(show_trends, pattern="^cat_trend$"),
                CallbackQueryHandler(show_styles, pattern="^cat_style$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            CHOOSING_TREND: [
                CallbackQueryHandler(select_effect, pattern="^effect_"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            CHOOSING_STYLE: [
                CallbackQueryHandler(select_effect, pattern="^effect_"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            WAITING_PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo),
                MessageHandler(~filters.PHOTO & ~filters.COMMAND, photo_expected),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            STORE: [
                CallbackQueryHandler(buy_package, pattern="^buy_"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            WAITING_PAYMENT: [
                MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment),
                CallbackQueryHandler(cancel_payment, pattern="^cancel_payment$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            PROMO_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_promo_code),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            REFERRAL: [
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            ADMIN_MENU: [
                CallbackQueryHandler(show_admin_stats, pattern="^admin_stats$"),
                CallbackQueryHandler(show_admin_promo, pattern="^admin_promo$"),
                CallbackQueryHandler(admin_back, pattern="^admin_back$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            ADMIN_STATS: [
                CallbackQueryHandler(admin_back, pattern="^admin_back$"),
            ],
            ADMIN_PROMO: [
                CallbackQueryHandler(create_promo, pattern="^create_promo_"),
                CallbackQueryHandler(admin_back, pattern="^admin_back$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("admin", admin_command),
        ],
    )

    app.add_handler(conv_handler)

    # PreCheckoutQueryHandler must be at app level
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))

    logger.info("Photo bot started. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
