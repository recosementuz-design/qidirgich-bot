import logging
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.constants import ParseMode

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import BOT_TOKEN

from database import Database

from telegram_client import (
    client,
    start_client,
    resolve_username,
    resolve_id,
    download_profile_photo
)

from search_engine import (
    search_query,
    build_report
)

from indexer import index_source


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(
    "qidirgich"
)


db = Database()


# ============================================================
# ADMIN
# ============================================================

ADMIN_IDS = set()

admin_env = None

try:

    import os

    admin_env = os.getenv(
        "ADMIN_TELEGRAM_ID"
    )

    if admin_env:
        ADMIN_IDS.add(
            int(admin_env)
        )

except Exception:

    pass


def is_admin(user_id):

    return user_id in ADMIN_IDS


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [
        [
            InlineKeyboardButton(
                "🔎 Qidirish",
                callback_data="search"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Yordam",
                callback_data="help"
            )
        ]
    ]

    if is_admin(
        update.effective_user.id
    ):

        keyboard.append(
            [
                InlineKeyboardButton(
                    "👑 Admin",
                    callback_data="admin"
                )
            ]
        )

    text = (
        "🔎 <b>QIDIRGICH</b>\n\n"
        "Telegramdagi ochiq va botga "
        "ruxsat etilgan ma'lumotlarni "
        "qidirish tizimi.\n\n"
        "Username yuboring:\n"
        "<code>@username</code>\n\n"
        "Yoki Telegram ID:\n"
        "<code>123456789</code>"
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ============================================================
# HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        "ℹ️ <b>QIDIRGICH YORDAM</b>\n\n"
        "🔎 Username yoki Telegram ID yuboring.\n\n"
        "Misol:\n"
        "<code>@telegram</code>\n"
        "<code>123456789</code>\n\n"
        "Bot mavjud bo'lgan public va "
        "indekslangan Telegram ma'lumotlarini "
        "ko'rsatadi.\n\n"
        "🔐 Private chatlar va boshqa "
        "foydalanuvchilarning kontaktlari "
        "olinmaydi."
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# SEARCH
# ============================================================

async def handle_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = (
        update.message.text or ""
    ).strip()

    if not query:
        return

    status = await update.message.reply_text(
        "🔎 <b>QIDIRILMOQDA...</b>\n\n"
        f"<code>{query}</code>",
        parse_mode=ParseMode.HTML
    )

    user, error = await search_query(
        query
    )

    if error:

        await status.edit_text(
            f"❌ {error}"
        )

        return

    try:

        await db.save_user(
            user
        )

        report = await build_report(
            user,
            db
        )

        await db.save_search(
            update.effective_user.id,
            query,
            1
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🖼 Profil rasmi",
                    callback_data=f"photo:{user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "💬 Xabarlar",
                    callback_data=f"messages:{user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔎 Yangi qidiruv",
                    callback_data="search"
                )
            ]
        ]

        await status.edit_text(
            report,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    except Exception as e:

        logger.exception(e)

        await status.edit_text(
            "❌ Natijani tayyorlashda xatolik."
        )


# ============================================================
# CALLBACK
# ============================================================

async def callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data or ""

    if data == "search":

        await query.message.reply_text(
            "🔎 Username yoki Telegram ID yuboring."
        )

        return

    if data == "help":

        await query.message.reply_text(
            "🔎 Username yoki ID yuboring.\n\n"
            "Masalan:\n"
            "@username\n"
            "123456789"
        )

        return

    if data == "admin":

        if not is_admin(
            query.from_user.id
        ):

            await query.answer(
                "Ruxsat yo'q.",
                show_alert=True
            )

            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "➕ Manba qo'shish",
                    callback_data="admin_add_source"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Statistika",
                    callback_data="admin_stats"
                )
            ]
        ]

        await query.message.reply_text(
            "👑 <b>ADMIN PANEL</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return

    if data == "admin_stats":

        if not is_admin(
            query.from_user.id
        ):
            return

        stats = await db.stats()

        text = (
            "📊 <b>QIDIRGICH STATISTIKA</b>\n\n"
            f"👤 Users: {stats['users']}\n"
            f"📚 Sources: {stats['sources']}\n"
            f"💬 Messages: {stats['messages']}\n"
            f"🔎 Searches: {stats['searches']}"
        )

        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML
        )

        return

    if data == "admin_add_source":

        if not is_admin(
            query.from_user.id
        ):
            return

        context.user_data[
            "waiting_source"
        ] = True

        await query.message.reply_text(
            "➕ Public guruh yoki kanal username'ini yuboring.\n\n"
            "Masalan:\n"
            "<code>@examplegroup</code>",
            parse_mode=ParseMode.HTML
        )

        return

    if data.startswith("photo:"):

        try:

            user_id = int(
                data.split(":")[1]
            )

        except Exception:

            return

        user, error = await resolve_id(
            user_id
        )

        if error:

            await query.message.reply_text(
                "❌ Profilni qayta olishning imkoni bo'lmadi."
            )

            return

        photo = await download_profile_photo(
            user
        )

        if not photo:

            await query.message.reply_text(
                "🖼 Profil rasmi mavjud emas yoki "
                "uni olishga imkon yo'q."
            )

            return

        await query.message.reply_photo(
            photo=photo,
            caption=(
                f"👤 {getattr(user, 'first_name', '')}\n"
                f"🔗 @{getattr(user, 'username', '')}\n"
                f"🆔 {user.id}"
            )
        )

        return

    if data.startswith("messages:"):

        try:

            user_id = int(
                data.split(":")[1]
            )

        except Exception:

            return

        messages = await db.search_messages_by_user(
            user_id,
            20
        )

        if not messages:

            await query.message.reply_text(
                "💬 Bu user bo'yicha "
                "indekslangan xabar topilmadi."
            )

            return

        text = (
            "💬 <b>TOPILGAN OCHIQ XABARLAR</b>\n\n"
        )

        for message in messages:

            source = (
                message["title"]
                or message["source_username"]
                or "Noma'lum"
            )

            msg_text = (
                message["message_text"]
                or ""
            )

            msg_text = msg_text.replace(
                "\n",
                " "
            )

            if len(msg_text) > 300:

                msg_text = (
                    msg_text[:300]
                    + "..."
                )

            text += (
                f"👥 <b>{source}</b>\n"
                f"💬 {msg_text}\n"
            )

            if message["public_url"]:

                text += (
                    f"🔗 {message['public_url']}\n"
                )

            text += "\n"

        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML
        )


# ============================================================
# ADMIN SOURCE HANDLER
# ============================================================

async def handle_admin_source(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):

        return

    if not context.user_data.get(
        "waiting_source"
    ):

        return

    context.user_data[
        "waiting_source"
    ] = False

    source_username = (
        update.message.text or ""
    ).strip()

    if source_username.startswith("@"):

        source_username = (
            source_username[1:]
        )

    status = await update.message.reply_text(
        "🔎 Manba tekshirilmoqda..."
    )

    try:

        entity = await client.get_entity(
            source_username
        )

        title = getattr(
            entity,
            "title",
            None
        ) or getattr(
            entity,
            "first_name",
            None
        ) or source_username

        source_type = (
            "channel"
            if getattr(
                entity,
                "broadcast",
                False
            )
            else "group"
        )

        source = await db.add_source(
            telegram_id=entity.id,
            username=source_username,
            title=title,
            source_type=source_type
        )

        source_id = source["id"]

        await status.edit_text(
            "📥 <b>INDekSLASH BOSHLANDI</b>\n\n"
            f"Manba: <b>{title}</b>\n"
            "Bu jarayon biroz vaqt olishi mumkin...",
            parse_mode=ParseMode.HTML
        )

        count = await index_source(
            db=db,
            source_entity=entity,
            source_id=source_id,
            limit=1000
        )

        await update.message.reply_text(
            "✅ <b>INDEX TAYYOR</b>\n\n"
            f"Manba: {title}\n"
            f"Saqlangan xabarlar: {count}",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        logger.exception(e)

        await status.edit_text(
            f"❌ Manbani indekslashda xatolik:\n{e}"
        )


# ============================================================
# STARTUP
# ============================================================

async def main():

    await db.connect()

    await start_client(
        BOT_TOKEN
    )

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callbacks
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_admin_source
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_search
        )
    )

    logger.info(
        "QIDIRGICH ISHGA TUSHDI"
    )

    await application.initialize()

    await application.start()

    await application.updater.start_polling()

    try:

        while True:

            await asyncio.sleep(
                3600
            )

    finally:

        await application.updater.stop()

        await application.stop()

        await application.shutdown()

        await client.disconnect()

        await db.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
