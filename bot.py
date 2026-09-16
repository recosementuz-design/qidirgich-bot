import os
import logging
import asyncio
from io import BytesIO

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from telethon import TelegramClient
from telethon.errors import (
    UsernameInvalidError,
    UsernameNotOccupiedError,
    FloodWaitError,
    RPCError,
)
from telethon.tl.types import User


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

if not API_ID:
    raise RuntimeError("API_ID topilmadi")

if not API_HASH:
    raise RuntimeError("API_HASH topilmadi")

try:
    API_ID = int(API_ID)
except ValueError:
    raise RuntimeError("API_ID raqam bo'lishi kerak")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("qidirgich")


# ============================================================
# TELETHON CLIENT
# ============================================================

# Railway persistent disk ishlatilsa session saqlanadi.
# Birinchi versiyada bot account orqali ishlaymiz.
telegram_client = TelegramClient(
    "qidirgich_bot_session",
    API_ID,
    API_HASH,
)


# ============================================================
# USER SEARCH CACHE
# ============================================================

user_cache = {}


# ============================================================
# HELPERS
# ============================================================

def clean_username(text: str) -> str:
    text = text.strip()

    if text.startswith("https://t.me/"):
        text = text.replace("https://t.me/", "", 1)

    if text.startswith("http://t.me/"):
        text = text.replace("http://t.me/", "", 1)

    if text.startswith("t.me/"):
        text = text.replace("t.me/", "", 1)

    if text.startswith("@"):
        text = text[1:]

    return text.strip()


def profile_name(user) -> str:
    first = getattr(user, "first_name", None) or ""
    last = getattr(user, "last_name", None) or ""

    name = f"{first} {last}".strip()

    return name if name else "Noma'lum"


def username_text(user) -> str:
    username = getattr(user, "username", None)

    if username:
        return f"@{username}"

    return "Username mavjud emas"


def bool_text(value: bool) -> str:
    return "✅ Ha" if value else "❌ Yo'q"


# ============================================================
# TELEGRAM PROFILE LOOKUP
# ============================================================

async def lookup_user(username: str):
    username = clean_username(username)

    if not username:
        return None, "Username bo'sh."

    try:
        entity = await telegram_client.get_entity(username)

        if not isinstance(entity, User):
            return None, "Bu username Telegram foydalanuvchisi emas."

        user_cache[entity.id] = entity

        return entity, None

    except UsernameInvalidError:
        return None, "Username noto'g'ri formatda."

    except UsernameNotOccupiedError:
        return None, "Bunday username topilmadi."

    except FloodWaitError as e:
        return None, f"Telegram vaqtinchalik cheklov berdi. {e.seconds} soniya kuting."

    except RPCError as e:
        logger.exception("Telegram RPC error")
        return None, f"Telegram API xatosi: {str(e)}"

    except Exception as e:
        logger.exception("Lookup error")
        return None, f"Qidirishda xatolik: {str(e)}"


# ============================================================
# PROFILE REPORT
# ============================================================

async def make_profile_report(user):
    user_id = getattr(user, "id", None)

    username = username_text(user)
    name = profile_name(user)

    bot = getattr(user, "bot", False)
    verified = getattr(user, "verified", False)
    premium = getattr(user, "premium", False)
    scam = getattr(user, "scam", False)
    fake = getattr(user, "fake", False)
    restricted = getattr(user, "restricted", False)

    report = (
        "🔎 <b>QIDIRGICH</b>\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>TELEGRAM PROFIL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 Ism: <b>{name}</b>\n"
        f"🔗 Username: <b>{username}</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🤖 Bot: {bool_text(bot)}\n"
        f"☑️ Verified: {bool_text(verified)}\n"
        f"⭐ Premium: {bool_text(premium)}\n"
        f"⚠️ Scam belgisi: {bool_text(scam)}\n"
        f"⚠️ Fake belgisi: {bool_text(fake)}\n"
        f"🔒 Restricted: {bool_text(restricted)}\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>KEYINGI QIDIRUV</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Quyidagi tugmalardan foydalaning."
    )

    return report


# ============================================================
# PROFILE PHOTO
# ============================================================

async def get_profile_photo(user):
    try:
        photos = await telegram_client.get_profile_photos(
            user,
            limit=1,
        )

        if not photos:
            return None

        image_bytes = await telegram_client.download_media(
            photos[0],
            file=bytes,
        )

        if not image_bytes:
            return None

        return BytesIO(image_bytes)

    except Exception:
        logger.exception("Profile photo error")
        return None


# ============================================================
# PUBLIC GROUP / CHANNEL SEARCH
# ============================================================

async def search_public_source(username: str, source: str):
    """
    Bu funksiya berilgan public guruh/kanal ichida
    username bilan bog'liq ochiq xabarlarni tekshiradi.

    Eslatma:
    Telegram API boshqa odamning barcha guruh a'zoliklarini
    universal tarzda bermaydi.
    """

    try:
        source_entity = await telegram_client.get_entity(source)

    except Exception as e:
        logger.warning("Source topilmadi: %s | %s", source, e)
        return []

    results = []

    try:
        async for message in telegram_client.iter_messages(
            source_entity,
            search=username,
            limit=30,
        ):
            if not message:
                continue

            text = getattr(message, "message", None)

            if not text:
                continue

            results.append(
                {
                    "message_id": message.id,
                    "text": text[:500],
                    "date": str(message.date),
                }
            )

    except Exception as e:
        logger.warning(
            "Source search error %s: %s",
            source,
            e,
        )

    return results


# ============================================================
# TELEGRAM BOT COMMANDS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "🔎 Qidirish",
                callback_data="search",
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Yordam",
                callback_data="help",
            )
        ],
    ]

    text = (
        "🔎 <b>QIDIRGICH</b>\n"
        "\n"
        "Telegram ichidagi mavjud va ruxsat etilgan "
        "ma'lumotlarni qidirish tizimi.\n"
        "\n"
        "Username yuboring:\n"
        "<code>@username</code>\n"
        "\n"
        "Masalan:\n"
        "<code>@telegram</code>"
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ <b>QIDIRGICH YORDAM</b>\n"
        "\n"
        "Botga Telegram username yuboring.\n"
        "\n"
        "Misol:\n"
        "<code>@username</code>\n"
        "\n"
        "Bot mavjud bo'lgan Telegram ma'lumotlarini "
        "tekshiradi.\n"
        "\n"
        "🔐 Private chatlar, boshqa foydalanuvchilarning "
        "kontaktlari va yashirin ma'lumotlar olinmaydi."
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# SEARCH MESSAGE
# ============================================================

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    raw = update.message.text or ""
    username = clean_username(raw)

    if not username:
        await update.message.reply_text(
            "❌ Username yuboring.\n\nMasalan: @username"
        )
        return

    searching = await update.message.reply_text(
        "🔎 <b>QIDIRILMOQDA...</b>\n\n"
        f"Username: <code>@{username}</code>\n\n"
        "Telegram ma'lumotlari tekshirilmoqda...",
        parse_mode=ParseMode.HTML,
    )

    user, error = await lookup_user(username)

    if error:
        await searching.edit_text(
            f"❌ <b>Qidiruv natijasi</b>\n\n{error}",
            parse_mode=ParseMode.HTML,
        )
        return

    report = await make_profile_report(user)

    keyboard = [
        [
            InlineKeyboardButton(
                "🖼 Profil rasmi",
                callback_data=f"photo:{user.id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Qayta qidirish",
                callback_data="search",
            )
        ],
    ]

    await searching.edit_text(
        report,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ============================================================
# CALLBACKS
# ============================================================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    data = query.data or ""

    if data == "help":
        text = (
            "ℹ️ <b>QIDIRGICH</b>\n\n"
            "Username yuboring va Telegramdagi "
            "mavjud/ruxsat etilgan ma'lumotlarni tekshiring.\n\n"
            "Masalan:\n"
            "<code>@username</code>"
        )

        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "search":
        await query.edit_message_text(
            "🔎 <b>Username yuboring</b>\n\n"
            "Masalan:\n"
            "<code>@username</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith("photo:"):
        try:
            user_id = int(data.split(":", 1)[1])
        except ValueError:
            await query.message.reply_text(
                "❌ ID noto'g'ri."
            )
            return

        user = user_cache.get(user_id)

        if not user:
            await query.message.reply_text(
                "⚠️ Qidiruv ma'lumotlari topilmadi. "
                "Username'ni qayta yuboring."
            )
            return

        await query.message.reply_text(
            "🖼 Profil rasmi olinmoqda..."
        )

        photo = await get_profile_photo(user)

        if not photo:
            await query.message.reply_text(
                "🖼 Profil rasmi mavjud emas yoki "
                "uni olishga ruxsat berilmagan."
            )
            return

        await query.message.reply_photo(
            photo=photo,
            caption=(
                f"👤 {profile_name(user)}\n"
                f"🔗 {username_text(user)}\n"
                f"🆔 <code>{user.id}</code>"
            ),
            parse_mode=ParseMode.HTML,
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception(
        "Unhandled exception:",
        exc_info=context.error,
    )


# ============================================================
# START TELEGRAM CLIENT
# ============================================================

async def start_telegram_client():
    logger.info("Telegram client ishga tushmoqda...")

    await telegram_client.start(
        bot_token=BOT_TOKEN
    )

    me = await telegram_client.get_me()

    logger.info(
        "Telegram client connected: %s",
        getattr(me, "username", None),
    )


# ============================================================
# MAIN
# ============================================================

async def main():
    await start_telegram_client()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callbacks,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_search,
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info("Qidirgich bot ishga tushdi.")

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        while True:
            await asyncio.sleep(3600)

    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

        await telegram_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")

    except Exception:
        logger.exception(
            "Bot ishga tushishida xatolik."
        )
