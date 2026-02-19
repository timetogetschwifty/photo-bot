"""
Photo Bot — AI Photo Transformations with Credit System

A Telegram bot that applies AI-powered photo transformations using Google Gemini.
Features: credit system, promo codes, referrals, package purchases via YooMoney.
"""

import os
import io
import json
import logging
import yaml

from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    ReplyKeyboardMarkup,
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
import notifications as notif

# ── Configuration ──────────────────────────────────────────────────────────────

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
YOOMONEY_PROVIDER_TOKEN = os.environ.get("YOOMONEY_PROVIDER_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "your_bot")
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "")  # Support account for "О проекте"

GEMINI_MODEL = "gemini-3-pro-image-preview"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Load effects and categories from YAML ─────────────────────────────────────

BASE_DIR = os.path.dirname(__file__)

LOGO_PATH = None
for _ext in ("jpg", "png", "webp"):
    _p = os.path.join(BASE_DIR, "images", f"logo.{_ext}")
    if os.path.exists(_p):
        LOGO_PATH = _p
        break


def load_yaml_config() -> tuple[dict, dict]:
    """Load effects and categories from effects.yaml.

    Auto-resolves:
      - prompts/{effect_id}.txt  → effect["prompt"]
      - images/{effect_id}.jpg   → effect["example_image"]
    Categories support parent field for nesting.
    """
    yaml_path = os.path.join(BASE_DIR, "effects.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Load categories (filter enabled, sort by order)
    categories = {}
    for cat_id, cat in data.get("categories", {}).items():
        if cat.get("enabled", True):
            categories[cat_id] = cat
    # Auto-resolve category images from images/{cat_id}.{ext}
    for cat_id, cat in categories.items():
        if "image" not in cat:
            for ext in ("jpg", "png", "webp"):
                img_path = os.path.join(BASE_DIR, "images", f"{cat_id}.{ext}")
                if os.path.exists(img_path):
                    cat["image"] = img_path
                    break
    categories = dict(sorted(categories.items(), key=lambda x: x[1].get("order", 999)))

    # Load effects (filter enabled, auto-resolve files, sort by order)
    effects = {}
    for effect_id, effect in data.get("effects", {}).items():
        if effect.get("enabled", True):
            # Auto-resolve prompt from prompts/{effect_id}.txt
            if "prompt" not in effect:
                prompt_path = os.path.join(BASE_DIR, "prompts", f"{effect_id}.txt")
                if os.path.exists(prompt_path):
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        effect["prompt"] = f.read().strip()
                else:
                    logger.error(f"Prompt file not found, skipping effect: {prompt_path}")
                    continue
            # Auto-resolve example image from images/{effect_id}.jpg
            if "example_image" not in effect:
                for ext in ("jpg", "png", "webp"):
                    img_path = os.path.join(BASE_DIR, "images", f"{effect_id}.{ext}")
                    if os.path.exists(img_path):
                        effect["example_image"] = img_path
                        break
            effects[effect_id] = effect
    effects = dict(sorted(effects.items(), key=lambda x: x[1].get("order", 999)))

    return categories, effects


def get_subcategories(parent_id: str | None) -> dict:
    """Get child categories of a parent (None = top-level)."""
    return {
        k: v for k, v in CATEGORIES.items()
        if v.get("parent") == parent_id
    }


def get_effects_for(category_id: str | None) -> dict:
    """Get effects directly in a category (None = top-level / no category)."""
    return {
        k: v for k, v in TRANSFORMATIONS.items()
        if v.get("category") == category_id
    }


CATEGORIES, TRANSFORMATIONS = load_yaml_config()
logger.info(f"Loaded categories: {list(CATEGORIES.keys())}")
logger.info(f"Loaded effects: {list(TRANSFORMATIONS.keys())}")

# ── Pricing (RUB, in kopecks for Telegram) ───────────────────────────────────

PACKAGES = {
    # Note: YooKassa test mode may require min 100₽. Prices in kopecks.
    "pkg_10": {"credits": 10, "price": 9900, "label": "10 зарядов — 99 ₽"},
    "pkg_25": {"credits": 25, "price": 22900, "label": "25 зарядов — 229 ₽"},
    "pkg_50": {"credits": 50, "price": 39900, "label": "50 зарядов — 399 ₽"},
    "pkg_100": {"credits": 100, "price": 69900, "label": "100 зарядов — 699 ₽"},
}

PROMO_AMOUNTS = [10, 25, 50, 100]

# ── Conversation states ──────────────────────────────────────────────────────

(
    MAIN_MENU,
    BROWSING,
    WAITING_PHOTO,
    STORE,
    WAITING_PAYMENT,
    PROMO_INPUT,
    REFERRAL,
    ABOUT,
    ADMIN_MENU,
    ADMIN_STATS,
    ADMIN_PROMO,
) = range(11)

# ── Gemini client ────────────────────────────────────────────────────────────

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ── Helper functions ─────────────────────────────────────────────────────────


def reply_keyboard() -> ReplyKeyboardMarkup:
    """Build persistent reply keyboard (below input field)."""
    return ReplyKeyboardMarkup(
        [
            ["✨ Создать магию"],
            ["💳 Пополнить запасы", "🎁 Промокод"],
            ["👥 Пригласить друга", "ℹ️ О проекте"],
        ],
        resize_keyboard=True,
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build main menu inline keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Создать магию", callback_data="menu_create")],
        [InlineKeyboardButton("💳 Пополнить запасы", callback_data="menu_store")],
        [InlineKeyboardButton("🎁 Промокод", callback_data="menu_promo")],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data="menu_referral")],
        [InlineKeyboardButton("ℹ️ О проекте", callback_data="menu_about")],
    ])


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with just 'Назад' button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
    ])


def back_to_browse_keyboard() -> InlineKeyboardMarkup:
    """Keyboard that returns user to previous browse level."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_browse")],
    ])


async def edit_message(query, text: str, reply_markup, parse_mode=None):
    """Edit message in place, preserving photo if present (for photo-bearing screens like main menu)."""
    try:
        if query.message.photo:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise


async def edit_text_screen(query, context, chat_id: int, text: str, reply_markup, parse_mode=None):
    """For text-only screens: removes stale photo if present, then edits or sends text."""
    try:
        if query.message.photo:
            await query.message.delete()
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise


async def edit_main_menu_screen(query, context, chat_id: int, text: str, reply_markup):
    """Show main menu with correct logo regardless of the current message type.

    photo + logo     → edit_message_media to logo (no jump, correct image)
    photo + no logo  → edit_message_caption (no jump)
    text  + logo     → delete + send_photo (one unavoidable jump)
    text  + no logo  → edit_message_text (no jump)
    """
    try:
        if LOGO_PATH:
            if query.message.photo:
                with open(LOGO_PATH, "rb") as img:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=img, caption=text),
                        reply_markup=reply_markup,
                    )
            else:
                await query.message.delete()
                with open(LOGO_PATH, "rb") as img:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=img,
                        caption=text,
                        reply_markup=reply_markup,
                    )
        else:
            if query.message.photo:
                await query.edit_message_caption(caption=text, reply_markup=reply_markup)
            else:
                await query.edit_message_text(text, reply_markup=reply_markup)
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise


# ── Main Menu ────────────────────────────────────────────────────────────────


async def send_main_menu(bot, chat_id, text, reply_markup):
    """Send main menu with logo if available, otherwise text-only."""
    if LOGO_PATH:
        with open(LOGO_PATH, "rb") as img:
            await bot.send_photo(chat_id=chat_id, photo=img, caption=text, reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command. Check for referral link or deep link."""
    user = update.effective_user
    args = context.args

    # Parse deep link parameters
    referred_by = None
    auto_browse = False

    if args:
        param = args[0]
        # Referral link: /start ref_123456
        if param.startswith("ref_"):
            try:
                referred_by = int(param[4:])
                if referred_by == user.id:
                    referred_by = None  # Can't refer yourself
            except ValueError:
                pass
        # Browse deep link: /start browse
        elif param == "browse":
            auto_browse = True

    # Get or create user
    db_user, is_new = db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        referred_by=referred_by,
    )

    credits = db_user["credits"]
    name = user.first_name or "друг"

    # If auto_browse is set, go straight to effects menu (single message)
    if auto_browse:
        context.user_data["current_category"] = None
        title, keyboard = build_browse_keyboard(None, credits)
        await update.message.reply_text(
            title,
            reply_markup=keyboard,
        )
        return BROWSING
    else:
        # Normal start - show main menu with logo
        text = f"Привет, {name}!\n⚡ Доступно зарядов: {credits}\nВыбери действие 👇"
        await send_main_menu(context.bot, update.effective_chat.id, text, reply_keyboard())
        return MAIN_MENU


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show main menu (from callback) using reply keyboard mode."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0
    name = user.first_name or "друг"

    text = f"Привет, {name}!\n⚡ Доступно зарядов: {credits}\nВыбери действие 👇"

    # Keep generated result photos, but remove other callback-origin messages
    # so main menu stays visually consistent as a fresh reply-keyboard screen.
    is_result_photo = bool(query.message.caption and query.message.caption.startswith("✅"))
    if not is_result_photo:
        try:
            await query.message.delete()
        except Exception:
            pass

    await send_main_menu(context.bot, update.effective_chat.id, text, reply_keyboard())
    return MAIN_MENU


async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle restart button (callback version of /start) in reply keyboard mode."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0
    name = user.first_name or "друг"

    # Clear any stale user data
    context.user_data.clear()

    text = f"Привет, {name}!\n⚡ Доступно зарядов: {credits}\nВыбери действие 👇"

    is_result_photo = bool(query.message.caption and query.message.caption.startswith("✅"))
    if not is_result_photo:
        try:
            await query.message.delete()
        except Exception:
            pass

    await send_main_menu(context.bot, update.effective_chat.id, text, reply_keyboard())
    return MAIN_MENU


async def back_to_browse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to previous browse category, editing the result photo in place."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0

    category_id = context.user_data.get("previous_category")
    context.user_data["current_category"] = category_id

    title, keyboard = build_browse_keyboard(category_id, credits)

    # Prefer category image, fall back to logo — keeps a photo message alive
    # so subsequent category/effect taps can use edit_message_media (no jump).
    cat_image = CATEGORIES.get(category_id or "", {}).get("image") if category_id else None
    image_path = (cat_image if cat_image and os.path.exists(cat_image) else None) or LOGO_PATH

    # Never edit or delete a generated result photo (caption always starts with ✅).
    is_result_photo = bool(query.message.caption and query.message.caption.startswith("✅"))

    if is_result_photo:
        # Result photo must stay — send browse screen as a new message below it.
        if image_path:
            with open(image_path, "rb") as img:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=img,
                    caption=title,
                    reply_markup=keyboard,
                )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=title,
                reply_markup=keyboard,
            )
    elif image_path:
        if query.message.photo:
            try:
                with open(image_path, "rb") as img:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=img, caption=title),
                        reply_markup=keyboard,
                    )
            except Exception as e:
                if "message is not modified" not in str(e).lower():
                    # Fallback: delete nav message + resend as photo
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    with open(image_path, "rb") as img:
                        await context.bot.send_photo(
                            chat_id=user.id,
                            photo=img,
                            caption=title,
                            reply_markup=keyboard,
                        )
        else:
            # Text message (e.g. nav message after result photo) — delete and send photo
            try:
                await query.message.delete()
            except Exception:
                pass
            with open(image_path, "rb") as img:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=img,
                    caption=title,
                    reply_markup=keyboard,
                )
    else:
        await edit_text_screen(query, context, user.id, title, keyboard)
    return BROWSING


# ── Reply Keyboard Handlers ─────────────────────────────────────────────────


def build_browse_keyboard(category_id: str | None, credits: int) -> tuple[str, InlineKeyboardMarkup]:
    """Build keyboard showing subcategories + effects for a category.

    category_id=None → top-level (the "Create" screen).
    Returns (title_text, keyboard).
    """
    buttons = []

    # Effects at this level
    for eff_id, eff in get_effects_for(category_id).items():
        buttons.append([InlineKeyboardButton(eff["label"], callback_data=f"effect_{eff_id}")])

    # Subcategories
    for cat_id, cat in get_subcategories(category_id).items():
        buttons.append([InlineKeyboardButton(cat["label"], callback_data=f"cat_{cat_id}")])

    # Back button
    if category_id is None:
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
        title = f"⚡ Доступно зарядов: {credits}\nВыбери категорию:"
    else:
        parent = CATEGORIES.get(category_id, {}).get("parent")
        back_data = f"cat_{parent}" if parent else "browse_root"
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=back_data)])
        category_label = CATEGORIES.get(category_id, {}).get("label", "Выбери:")
        title = f"⚡ Доступно зарядов: {credits}\n{category_label}"

    return title, InlineKeyboardMarkup(buttons)


async def handle_reply_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle '✨ Создать магию' from reply keyboard."""
    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0

    # Track current browsing category (None = top level)
    context.user_data['current_category'] = None

    title, keyboard = build_browse_keyboard(None, credits)
    await update.message.reply_text(title, reply_markup=keyboard)
    return BROWSING


async def handle_reply_store(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle '💳 Пополнить запасы' from reply keyboard."""
    buttons = [
        [InlineKeyboardButton(pkg["label"], callback_data=f"buy_{key}")]
        for key, pkg in PACKAGES.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    await update.message.reply_text("Выбери пакет:", reply_markup=InlineKeyboardMarkup(buttons))
    return STORE


async def handle_reply_promo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle '🎁 Промокод' from reply keyboard."""
    await update.message.reply_text(
        "Введи промокод:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
        ]),
    )
    return PROMO_INPUT


async def handle_reply_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle '👥 Пригласить друга' from reply keyboard."""
    user = update.effective_user
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    await update.message.reply_text(
        f"Приглашай друзей и получай\n+3 заряда за каждого!\n\nТвоя ссылка:\n{ref_link}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
        ]),
    )
    return REFERRAL


# ── Create Magic Flow ────────────────────────────────────────────────────────


async def show_browse_root(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show top-level browse screen (from inline menu)."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0

    # Track current browsing category (None = top level)
    context.user_data['current_category'] = None

    title, keyboard = build_browse_keyboard(None, credits)

    await edit_main_menu_screen(query, context, update.effective_chat.id, title, keyboard)
    return BROWSING


async def browse_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate into a category/subcategory — generic handler for any depth."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0

    category_id = query.data.replace("cat_", "")

    # Validate category exists
    if category_id and category_id not in CATEGORIES:
        error_text = "❌ Категория не найдена\n\nНажми кнопку ниже, чтобы начать заново:"
        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Начать заново", callback_data="restart")],
        ])
        await edit_text_screen(query, context, update.effective_chat.id, error_text, error_keyboard)
        return MAIN_MENU

    # Track current browsing category
    context.user_data['current_category'] = category_id

    title, keyboard = build_browse_keyboard(category_id, credits)

    cat_image = CATEGORIES.get(category_id, {}).get("image")

    if cat_image and os.path.exists(cat_image):
        if query.message.photo:
            try:
                with open(cat_image, "rb") as img:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=img, caption=title),
                        reply_markup=keyboard,
                    )
            except Exception as e:
                if "message is not modified" not in str(e).lower():
                    # Fallback: delete stale photo + resend
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    with open(cat_image, "rb") as img:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=img,
                            caption=title,
                            reply_markup=keyboard,
                        )
        else:
            # Text message — delete it before sending photo so it doesn't linger above
            try:
                await query.message.delete()
            except Exception:
                pass
            with open(cat_image, "rb") as img:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=img,
                    caption=title,
                    reply_markup=keyboard,
                )
    else:
        await edit_text_screen(query, context, update.effective_chat.id, title, keyboard)
    return BROWSING


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
        # Store category before showing error
        current_category = context.user_data.get('current_category')
        back_callback = f"cat_{current_category}" if current_category else "browse_root"

        # Credits exhausted message (upsell to buy or refer)
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"

        message = (
            "😢 <b>Заряды закончились!</b>\n\n"
            "Но не переживай — продолжить легко:\n\n"
            "🎁 <b>Специальное предложение:</b>\n"
            "10 зарядов всего за 99 ₽\n\n"
            "Или пригласи друга и получи <b>+3 заряда бесплатно</b>! 👥\n\n"
            f"Твоя ссылка:\n<code>{ref_link}</code>"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Купить заряды", callback_data="menu_store")],
            [InlineKeyboardButton("👥 Пригласить друга", callback_data="menu_referral")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=back_callback)],
        ])

        await edit_text_screen(query, context, update.effective_chat.id, message, keyboard, parse_mode="HTML")

        return BROWSING

    # Store selected effect and remember which category we came from
    context.user_data["effect_id"] = effect_id
    context.user_data["previous_category"] = context.user_data.get('current_category')

    effect = TRANSFORMATIONS[effect_id]

    # Build back button that returns to the category we came from
    previous_category = context.user_data.get("previous_category")
    back_callback = f"cat_{previous_category}" if previous_category else "browse_root"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data=back_callback)],
    ])

    tips = (effect.get('tips') or '').strip()
    best_input = (effect.get('best_input') or '').strip()
    parts = []
    if tips:
        parts.append(tips)
    if best_input:
        parts.append(f"📷 Лучше всего подойдёт: {best_input}")
    parts.append("Отправь мне фото для обработки 👇")
    message = "\n\n".join(parts)

    example_image = effect.get("example_image")
    if example_image and os.path.exists(example_image):
        if query.message.photo:
            try:
                with open(example_image, "rb") as img:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=img, caption=message),
                        reply_markup=keyboard,
                    )
            except Exception as e:
                if "message is not modified" not in str(e).lower():
                    # Fallback: delete stale photo + resend
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    with open(example_image, "rb") as img:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=img,
                            caption=message,
                            reply_markup=keyboard,
                        )
        else:
            # Text message — delete it before sending photo so it doesn't linger above
            try:
                await query.message.delete()
            except Exception:
                pass
            with open(example_image, "rb") as img:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=img,
                    caption=message,
                    reply_markup=keyboard,
                )
    else:
        await edit_text_screen(query, context, update.effective_chat.id, message, keyboard)
    return WAITING_PHOTO


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive photo and process it."""
    effect_id = context.user_data.get("effect_id")
    if not effect_id or effect_id not in TRANSFORMATIONS:
        # Session lost - offer restart
        await update.message.reply_text(
            "❌ Сессия истекла\n\nНажми кнопку ниже, чтобы начать заново:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Начать заново", callback_data="restart")],
            ]),
        )
        return MAIN_MENU

    user = update.effective_user

    # Deduct credit
    if not db.deduct_credit(user.id):
        # Credits exhausted message (upsell to buy or refer)
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"

        message = (
            "😢 <b>Заряды закончились!</b>\n\n"
            "Но не переживай — продолжить легко:\n\n"
            "🎁 <b>Специальное предложение:</b>\n"
            "10 зарядов всего за 99 ₽\n\n"
            "Или пригласи друга и получи <b>+3 заряда бесплатно</b>! 👥\n\n"
            f"Твоя ссылка:\n<code>{ref_link}</code>"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Купить заряды", callback_data="menu_store")],
            [InlineKeyboardButton("👥 Пригласить друга", callback_data="menu_referral")],
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="back_to_main")],
        ])

        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode="HTML",
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
        logger.info(f"Calling Gemini model: {GEMINI_MODEL}")
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[effect["prompt"], input_image],
            config=types.GenerateContentConfig(
                response_modalities=["Text", "Image"],
            ),
        )
        # Log model info from response if available
        if hasattr(response, 'model_version'):
            logger.info(f"Gemini response model_version: {response.model_version}")
        logger.info(f"Gemini response candidates: {len(response.candidates) if response.candidates else 0}")

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
            msg = f"❌ Что-то пошло не так\n\nКредит возвращён на баланс.\n⚡ Доступно зарядов: {new_balance}"
            if result_text:
                msg += f"\n\nОтвет модели: {result_text[:200]}"

            # Build back button that returns to the category we came from
            previous_category = context.user_data.get("previous_category")
            back_callback = f"cat_{previous_category}" if previous_category else "browse_root"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"effect_{effect_id}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=back_callback)],
            ])
            await status_msg.edit_text(msg, reply_markup=keyboard)
            return BROWSING

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
            caption=f"✅ {effect['label']}\n⚡ Осталось зарядов: {remaining}",
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Выбери следующий эффект:",
            reply_markup=back_to_browse_keyboard(),
        )

    except Exception as e:
        logger.error("Error during transformation: %s", e, exc_info=True)
        # Refund credit
        new_balance = db.refund_credit(user.id)

        # Build back button that returns to the category we came from
        previous_category = context.user_data.get("previous_category")
        back_callback = f"cat_{previous_category}" if previous_category else "browse_root"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"effect_{effect_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=back_callback)],
        ])
        await status_msg.edit_text(
            f"❌ Что-то пошло не так\n\nКредит возвращён на баланс.\n⚡ Доступно зарядов: {new_balance}\n\nОшибка: {str(e)[:100]}",
            reply_markup=keyboard,
        )
        return BROWSING
    finally:
        context.user_data.pop("effect_id", None)

    return MAIN_MENU


async def photo_expected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle non-photo message when photo is expected."""
    # Build back button that returns to the category we came from
    previous_category = context.user_data.get("previous_category")
    back_callback = f"cat_{previous_category}" if previous_category else "browse_root"

    await update.message.reply_text(
        "Пожалуйста, отправь фото.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data=back_callback)],
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
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])

    text = "Выбери пакет:"
    keyboard = InlineKeyboardMarkup(buttons)

    await edit_text_screen(query, context, update.effective_chat.id, text, keyboard)
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

        # Prepare fiscal receipt data (required by YooKassa for Russian tax law)
        # NOTE: Invoice price is in kopecks, but receipt amount must be in RUBLES
        price_rubles = package["price"] / 100

        receipt_data = {
            "receipt": {
                "items": [
                    {
                        "description": f"{package['credits']} зарядов",
                        "quantity": 1,
                        "amount": {
                            "value": price_rubles,
                            "currency": "RUB"
                        },
                        "vat_code": 1,  # No VAT
                        "payment_mode": "full_payment",
                        "payment_subject": "service"
                    }
                ]
            }
        }

        # Send invoice with fiscal data
        # Email will be collected on payment form (required for receipt delivery)
        invoice_msg = await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=f"Пакет {package['credits']} зарядов",
            description=f"Пополнение баланса на {package['credits']} зарядов",
            payload=f"package_{package_id}_{update.effective_user.id}",
            currency="RUB",
            prices=[LabeledPrice(f"{package['credits']} зарядов", package["price"])],
            provider_token=YOOMONEY_PROVIDER_TOKEN,
            provider_data=json.dumps(receipt_data),
            need_email=True,
            send_email_to_provider=True,
        )
        context.user_data["pending_invoice_message_id"] = invoice_msg.message_id

        # Send cancel button separately (invoices can't have inline buttons)
        cancel_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Нажми кнопку ниже, чтобы отменить покупку:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="cancel_payment")]
            ]),
        )
        context.user_data["pending_cancel_message_id"] = cancel_msg.message_id
        return WAITING_PAYMENT
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Ошибка платежа: {e}\n\nПопробуйте позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К выбору пакетов", callback_data="menu_store")],
            ]),
        )
        return STORE


async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel payment and return to store."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("pending_package", None)

    # Remove cancel prompt message
    try:
        await query.message.delete()
    except Exception:
        pass

    # Remove invoice message so chat doesn't keep stale payment UI
    invoice_message_id = context.user_data.pop("pending_invoice_message_id", None)
    if invoice_message_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=invoice_message_id,
            )
        except Exception:
            pass

    context.user_data.pop("pending_cancel_message_id", None)

    buttons = [
        [InlineKeyboardButton(pkg["label"], callback_data=f"buy_{key}")]
        for key, pkg in PACKAGES.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выбери пакет:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return STORE


async def show_main_menu_fresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a fresh main menu message (not edit)."""
    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0
    name = user.first_name or "друг"
    text = f"Привет, {name}!\n⚡ Доступно зарядов: {credits}\nВыбери действие 👇"
    await send_main_menu(context.bot, user.id, text, main_menu_keyboard())
    return MAIN_MENU


async def recover_stale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Recover from stale inline callbacks after deploy/restart.
    Triggered only when callback was not handled by ConversationHandler.
    """
    query = update.callback_query
    if not query:
        return

    # Acknowledge click quickly so user doesn't see a hanging spinner.
    await query.answer("Бот обновился, открываю меню...")

    user = update.effective_user
    db_user = db.get_user(user.id)
    credits = db_user["credits"] if db_user else 0
    name = user.first_name or "друг"
    text = f"Привет, {name}!\n⚡ Доступно зарядов: {credits}\nВыбери действие 👇"

    # Never delete a generated result photo (caption always starts with ✅).
    is_result_photo = bool(query.message.caption and query.message.caption.startswith("✅"))
    if not is_result_photo:
        try:
            await query.message.delete()
        except Exception:
            pass

    await send_main_menu(context.bot, user.id, text, reply_keyboard())


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
            f"✅ Оплата прошла!\n+{credits} зарядов добавлено\n\n⚡ Доступно зарядов: {new_balance}",
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

    text = "Введи промокод:"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
    ])

    await edit_text_screen(query, context, update.effective_chat.id, text, keyboard)
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
            f"✅ Промокод активирован!\n+{credits} зарядов добавлено\n\n⚡ Доступно зарядов: {new_balance}",
            reply_markup=back_to_main_keyboard(),
        )
    else:
        await update.message.reply_text(
            f"❌ {message}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать другой", callback_data="menu_promo")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
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

    text = f"Приглашай друзей и получай\n+3 заряда за каждого!\n\nТвоя ссылка:\n{ref_link}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
    ])

    await edit_text_screen(query, context, update.effective_chat.id, text, keyboard)
    return REFERRAL


# ── About Flow ──────────────────────────────────────────────────────────────


async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show about/disclaimer info."""
    query = update.callback_query
    await query.answer()

    text = (
        "ℹ️ О проекте\n\n"
        "Проект предназначен для людей достигших возраста 18+ "
        "и демонстрирует работу нейросетей.\n\n"
        "Все созданные изображения не могут быть использованы "
        "для рекламных или иных порочащих репутацию других граждан целей.\n\n"
        "Если вам кажется что ваши права нарушены или у вас возникли "
        "вопросы/предложения по работе проекта – пишите в нашу поддержку."
    )

    buttons = []
    if SUPPORT_USERNAME:
        buttons.append([InlineKeyboardButton("✉️ Написать в поддержку", url=f"https://t.me/{SUPPORT_USERNAME}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])

    keyboard = InlineKeyboardMarkup(buttons)

    await edit_text_screen(query, context, update.effective_chat.id, text, keyboard)
    return ABOUT


async def show_about_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show about/disclaimer info (from reply keyboard text)."""
    text = (
        "ℹ️ О проекте\n\n"
        "Проект предназначен для людей достигших возраста 18+ "
        "и демонстрирует работу нейросетей.\n\n"
        "Все созданные изображения не могут быть использованы "
        "для рекламных или иных порочащих репутацию других граждан целей.\n\n"
        "Если вам кажется что ваши права нарушены или у вас возникли "
        "вопросы/предложения по работе проекта – пишите в нашу поддержку."
    )

    buttons = []
    if SUPPORT_USERNAME:
        buttons.append([InlineKeyboardButton("✉️ Написать в поддержку", url=f"https://t.me/{SUPPORT_USERNAME}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ABOUT


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

    # Build package stats text
    package_lines = []
    package_stats = stats.get("package_stats", {})
    for pkg_id, pkg in PACKAGES.items():
        credits = pkg["credits"]
        pkg_data = package_stats.get(credits, {"count": 0, "revenue": 0})
        package_lines.append(f"{credits} зарядов: {pkg_data['count']} шт. ({pkg_data['revenue']} ₽)")

    packages_text = "\n".join(package_lines)

    text = (
        f"📊 Статистика бота\n\n"
        f"Пользователей: {stats['total_users']}\n"
        f"Всего генераций: {stats['total_generations']}\n"
        f"Куплено пакетов: {stats['total_purchases']}\n"
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


async def show_admin_promo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show promo code creation menu."""
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton(f"{amount} зарядов", callback_data=f"create_promo_{amount}")]
        for amount in PROMO_AMOUNTS
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")])

    await query.edit_message_text(
        "🎁 Создать промокод\n\nСколько зарядов даёт промокод?",
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
        f"✅ Промокод создан!\n\nКод: {code}\nДаёт: +{amount} зарядов",
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

    # Initialize notification system
    notif.init_notifications(app.bot)

    # Reply keyboard handlers — shared across all user-facing states
    reply_kb = [
        MessageHandler(filters.Regex("^✨ Создать магию$"), handle_reply_create),
        MessageHandler(filters.Regex("^💳 Пополнить запасы$"), handle_reply_store),
        MessageHandler(filters.Regex("^🎁 Промокод$"), handle_reply_promo),
        MessageHandler(filters.Regex("^👥 Пригласить друга$"), handle_reply_referral),
        MessageHandler(filters.Regex("^ℹ️ О проекте$"), show_about_from_text),
    ]

    # Main conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("admin", admin_command),
            # Allow old inline buttons to work even after bot restarts.
            CallbackQueryHandler(restart_bot, pattern="^restart$"),
            CallbackQueryHandler(back_to_browse, pattern="^back_to_browse$"),
            CallbackQueryHandler(show_browse_root, pattern="^(menu_create|browse_root)$"),
            CallbackQueryHandler(show_store, pattern="^menu_store$"),
            CallbackQueryHandler(show_promo_input, pattern="^menu_promo$"),
            CallbackQueryHandler(show_referral, pattern="^menu_referral$"),
            CallbackQueryHandler(show_about, pattern="^menu_about$"),
            CallbackQueryHandler(show_main_menu, pattern="^(back_to_main|main_menu)$"),
            CallbackQueryHandler(browse_category, pattern="^cat_"),
            CallbackQueryHandler(select_effect, pattern="^effect_"),
            CallbackQueryHandler(buy_package, pattern="^buy_"),
            CallbackQueryHandler(cancel_payment, pattern="^cancel_payment$"),
            # Allow reply keyboard text actions to recover after restart too.
            *reply_kb,
        ],
        states={
            MAIN_MENU: [
                # Inline keyboard handlers
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(back_to_browse, pattern="^back_to_browse$"),
                CallbackQueryHandler(show_browse_root, pattern="^menu_create$"),
                CallbackQueryHandler(show_store, pattern="^menu_store$"),
                CallbackQueryHandler(show_promo_input, pattern="^menu_promo$"),
                CallbackQueryHandler(show_referral, pattern="^menu_referral$"),
                CallbackQueryHandler(show_about, pattern="^menu_about$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
                # Effect retry
                CallbackQueryHandler(select_effect, pattern="^effect_"),
            ] + reply_kb,
            BROWSING: [
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(show_browse_root, pattern="^browse_root$"),
                CallbackQueryHandler(browse_category, pattern="^cat_"),
                CallbackQueryHandler(select_effect, pattern="^effect_"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ] + reply_kb,
            WAITING_PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo),
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(back_to_browse, pattern="^back_to_browse$"),
                CallbackQueryHandler(show_browse_root, pattern="^browse_root$"),
                CallbackQueryHandler(browse_category, pattern="^cat_"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ] + reply_kb + [
                MessageHandler(~filters.PHOTO & ~filters.COMMAND, photo_expected),
            ],
            STORE: [
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(show_store, pattern="^menu_store$"),
                CallbackQueryHandler(buy_package, pattern="^buy_"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ] + reply_kb,
            WAITING_PAYMENT: [
                MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment),
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(show_store, pattern="^menu_store$"),
                CallbackQueryHandler(cancel_payment, pattern="^cancel_payment$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ] + reply_kb,
            PROMO_INPUT: reply_kb + [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_promo_code),
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            REFERRAL: [
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ] + reply_kb,
            ABOUT: [
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ] + reply_kb,
            ADMIN_MENU: [
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(show_admin_stats, pattern="^admin_stats$"),
                CallbackQueryHandler(show_admin_promo, pattern="^admin_promo$"),
                CallbackQueryHandler(admin_back, pattern="^admin_back$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_main$"),
            ],
            ADMIN_STATS: [
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
                CallbackQueryHandler(admin_back, pattern="^admin_back$"),
            ],
            ADMIN_PROMO: [
                CallbackQueryHandler(restart_bot, pattern="^restart$"),
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
    # Fallback recovery for stale/unknown callback_data after deploys.
    app.add_handler(CallbackQueryHandler(recover_stale_callback))

    # PreCheckoutQueryHandler must be at app level
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))

    logger.info("Photo bot started. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
