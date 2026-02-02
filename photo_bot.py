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

# ── Configuration ──────────────────────────────────────────────────────────────

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
YOOMONEY_PROVIDER_TOKEN = os.environ["YOOMONEY_PROVIDER_TOKEN"]
GEMINI_MODEL = "gemini-3-pro-image-preview"

# Price per transformation in smallest currency units (cents for USD)
TRANSFORM_PRICE = 100  # $1.00
TRANSFORM_CURRENCY = "USD"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Transformation menu ───────────────────────────────────────────────────────

TRANSFORMATIONS = {
    "cat_phone": {
        "label": "🐱 Replace phone with a cat",
        "prompt": (
            "Replace any phone or mobile device the person is holding "
            "with a cute cat. Keep everything else the same."
        ),
    },
    "big_afro": {
        "label": "🦱 Big afro haircut",
        "prompt": (
            "Change the person's haircut to a big voluminous afro hairstyle. "
            "Keep the face and everything else the same."
        ),
    },
}

# ── Conversation states ───────────────────────────────────────────────────────

CHOOSING, WAITING_PHOTO, WAITING_PAYMENT = range(3)

# ── Gemini client ─────────────────────────────────────────────────────────────

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ── Handlers ──────────────────────────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the transformation menu."""
    keyboard = [
        [InlineKeyboardButton(t["label"], callback_data=key)]
        for key, t in TRANSFORMATIONS.items()
    ]
    await update.message.reply_text(
        "Welcome! Pick a photo transformation:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING


async def choose_transformation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Store the chosen transformation and ask for a photo."""
    query = update.callback_query
    await query.answer()

    choice = query.data
    if choice not in TRANSFORMATIONS:
        await query.edit_message_text("Unknown option. Use /start to try again.")
        return ConversationHandler.END

    context.user_data["transformation"] = choice
    label = TRANSFORMATIONS[choice]["label"]
    await query.edit_message_text(
        f"Selected: {label}\n\nNow send me a photo to transform."
    )
    return WAITING_PHOTO


async def handle_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receive photo, store it, and send a payment invoice."""
    choice = context.user_data.get("transformation")
    if not choice or choice not in TRANSFORMATIONS:
        await update.message.reply_text(
            "Something went wrong. Use /start to begin again."
        )
        return ConversationHandler.END

    # Download and store the photo for later processing
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    context.user_data["photo_bytes"] = bytes(photo_bytes)

    label = TRANSFORMATIONS[choice]["label"]
    price_display = f"${TRANSFORM_PRICE / 100:.2f}"

    # Send payment invoice
    await update.message.reply_invoice(
        title="Photo Transformation",
        description=f"{label}\nPrice: {price_display}",
        payload=f"transform_{choice}_{update.effective_user.id}",
        currency=TRANSFORM_CURRENCY,
        prices=[LabeledPrice("Transformation", TRANSFORM_PRICE)],
        provider_token=YOOMONEY_PROVIDER_TOKEN,
    )
    return WAITING_PAYMENT


async def pre_checkout(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Approve the payment (must respond within 10 seconds)."""
    query = update.pre_checkout_query

    # Verify we still have the photo stored
    if not context.user_data.get("photo_bytes"):
        await query.answer(ok=False, error_message="Session expired. Use /start to begin again.")
        return

    await query.answer(ok=True)


async def successful_payment(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Payment succeeded — now process the photo with Gemini."""
    choice = context.user_data.get("transformation")
    photo_bytes = context.user_data.get("photo_bytes")

    if not choice or not photo_bytes:
        await update.message.reply_text(
            "Something went wrong. Use /start to begin again."
        )
        return ConversationHandler.END

    prompt = TRANSFORMATIONS[choice]["prompt"]
    status_msg = await update.message.reply_text(
        "Payment received! Transforming your photo… please wait."
    )

    try:
        input_image = Image.open(io.BytesIO(photo_bytes))

        # Call Gemini
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, input_image],
            config=types.GenerateContentConfig(
                response_modalities=["Text", "Image"],
            ),
        )

        # Extract result image
        result_image = None
        result_text = None
        for part in response.parts:
            if part.inline_data is not None:
                result_image = part.as_image()
            elif part.text is not None:
                result_text = part.text

        if result_image is None:
            msg = "Gemini did not return an image. Try a different photo or transformation."
            if result_text:
                msg += f"\nModel said: {result_text}"
            await status_msg.edit_text(msg)
            return ConversationHandler.END

        # Send result back
        output_buffer = io.BytesIO()
        result_image.save(output_buffer, format="PNG")
        output_buffer.seek(0)

        await status_msg.delete()
        await update.message.reply_photo(
            photo=output_buffer,
            caption=f"Effect: {TRANSFORMATIONS[choice]['label']}\n\nUse /start for another transformation.",
        )

    except Exception as e:
        logger.error("Error during transformation: %s", e, exc_info=True)
        await status_msg.edit_text(
            f"Sorry, something went wrong.\nError: {str(e)[:200]}\n\nUse /start to try again."
        )
    finally:
        # Clean up stored photo
        context.user_data.pop("photo_bytes", None)
        context.user_data.pop("transformation", None)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    context.user_data.pop("photo_bytes", None)
    context.user_data.pop("transformation", None)
    await update.message.reply_text("Cancelled. Use /start to begin again.")
    return ConversationHandler.END


async def unexpected_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle non-photo messages when a photo is expected."""
    await update.message.reply_text("Please send a photo, or /cancel to abort.")
    return WAITING_PHOTO


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Start the bot."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(choose_transformation)],
            WAITING_PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo),
                MessageHandler(
                    ~filters.PHOTO & ~filters.COMMAND, unexpected_message
                ),
            ],
            WAITING_PAYMENT: [
                MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    # PreCheckoutQueryHandler must be registered at app level (outside ConversationHandler)
    # because Telegram sends it as a separate update type that needs immediate response
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))

    logger.info("Photo bot started. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
