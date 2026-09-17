import asyncio
import logging

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

from config import (
    BOT_TOKEN,
    ADMIN_TELEGRAM_ID
)

from database import Database

from telegram_client import (
    start_user_client,
    resolve_query,
    profile_photo
)

from indexer import index_source

from search_engine import search_user


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("qidirgich")


db = Database()


def is_admin(user_id):

    return user_id == ADMIN_TELEGRAM_ID


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

    await update.message.reply_text(

        "🔎 <b>QIDIRGICH</b>\n\n"

        "Telegram username yoki ID yuboring.\n\n"

        "Masalan:\n"
        "<code>@username</code>\n"
        "<code>123456789</code>\n\n"

        "Qidiruv faqat Telegram orqali "
        "ko'rish mumkin bo'lgan ma'lumotlar "
        "doirasida ishlaydi.",

        parse_mode=ParseMode.HTML,

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


async def help_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🔎 <b>QIDIRISH</b>\n\n"

        "Username yoki Telegram ID yuboring.\n\n"

        "Admin public guruh yoki kanalni "
        "indekslashi mumkin.\n\n"

        "Private chatlar, kontaktlar va "
        "ruxsatsiz yopiq ma'lumotlar olinmaydi.",

        parse_mode=ParseMode.HTML
    )


async def search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = (
        update.message.text or ""
    ).strip()

    if not query:
        return

    if context.user_data.get(
        "waiting_source"
    ):
        return

    status = await update.message.reply_text(
        "🔎 Qidirilmoqda..."
    )

    result = await search_user(
        db,
        query
    )

    if not result["ok"]:

        await status.edit_text(
            "❌ Topilmadi yoki Telegram "
            "ushbu ma'lumotga kirishga "
            "ruxsat bermadi.\n\n"
            + result["error"]
        )

        return

    entity = result["entity"]

    messages = result["messages"]

    first_name = (
        getattr(
            entity,
            "first_name",
            None
        )
        or ""
    )

    last_name = (
        getattr(
            entity,
            "last_name",
            None
        )
        or ""
    )

    name = (
        f"{first_name} {last_name}"
    ).strip()

    if not name:

        name = (
            getattr(
                entity,
                "title",
                None
            )
            or "Noma'lum"
        )

    username = getattr(
        entity,
        "username",
        None
    )

    text = (
        "🔎 <b>QIDIRGICH NATIJASI</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{name}</b>\n"
        f"🆔 <code>{entity.id}</code>\n"
    )

    if username:

        text += (
            f"🔗 @{username}\n"
        )

    bio = getattr(
        entity,
        "about",
        None
    )

    if bio:

        text += (
            f"📝 {bio[:500]}\n"
        )

    if getattr(
        entity,
        "verified",
        False
    ):

        text += (
            "☑️ Verified: ha\n"
        )

    if getattr(
        entity,
        "premium",
        False
    ):

        text += (
            "⭐ Premium: ha\n"
        )

    if getattr(
        entity,
        "bot",
        False
    ):

        text += (
            "🤖 Bot: ha\n"
        )

    text += (
        "\n💬 <b>Indekslangan xabarlar:</b> "
        f"{len(messages)}\n"
    )

    if messages:

        for row in messages[:10]:

            source = (
                row["title"]
                or row["source_username"]
                or "Noma'lum"
            )

            message_text = (
                row["message_text"]
                or ""
            ).replace(
                "\n",
                " "
            )

            text += (
                f"\n• <b>{source}</b>\n"
                f"  {message_text[:180]}\n"
            )

    else:

        text += (
            "\nℹ️ Ushbu foydalanuvchi bo'yicha "
            "indekslangan public xabar topilmadi."
        )

    keyboard = [

        [
            InlineKeyboardButton(
                "🖼 Profil rasmi",
                callback_data=(
                    f"photo:{entity.id}"
                )
            )
        ]

    ]

    await db.save_search(
        update.effective_user.id,
        query,
        len(messages)
    )

    await status.edit_text(

        text,

        parse_mode=ParseMode.HTML,

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


async def callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    if data == "search":

        await query.message.reply_text(
            "🔎 Username yoki Telegram ID yuboring."
        )

        return

    if data == "help":

        await query.message.reply_text(
            "Username yoki Telegram ID yuboring."
        )

        return

    if data == "admin":

        if not is_admin(
            query.from_user.id
        ):

            return

        keyboard = [

            [
                InlineKeyboardButton(
                    "➕ Public manba qo'shish",
                    callback_data="add_source"
                )
            ],

            [
                InlineKeyboardButton(
                    "📊 Statistika",
                    callback_data="stats"
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

    if data == "stats":

        if not is_admin(
            query.from_user.id
        ):

            return

        stats = await db.stats()

        await query.message.reply_text(

            "📊 <b>STATISTIKA</b>\n\n"

            f"👤 Users: {stats['users']}\n"
            f"📚 Sources: {stats['sources']}\n"
            f"💬 Messages: {stats['messages']}\n"
            f"🔎 Searches: {stats['searches']}",

            parse_mode=ParseMode.HTML
        )

        return

    if data == "add_source":

        if not is_admin(
            query.from_user.id
        ):

            return

        context.user_data[
            "waiting_source"
        ] = True

        await query.message.reply_text(

            "➕ Public guruh yoki kanal "
            "username'ini yuboring.\n\n"

            "Masalan:\n"
            "<code>@example</code>",

            parse_mode=ParseMode.HTML
        )

        return

    if data.startswith(
        "photo:"
    ):

        user_id = data.split(
            ":",
            1
        )[1]

        entity, error = await resolve_query(
            user_id
        )

        if error:

            await query.message.reply_text(
                "❌ Profil topilmadi."
            )

            return

        photo = await profile_photo(
            entity
        )

        if not photo:

            await query.message.reply_text(
                "🖼 Profil rasmi olinmadi."
            )

            return

        await query.message.reply_photo(
            photo=photo
        )


async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if (
        is_admin(
            update.effective_user.id
        )
        and context.user_data.get(
            "waiting_source"
        )
    ):

        context.user_data[
            "waiting_source"
        ] = False

        raw = (
            update.message.text or ""
        ).strip()

        entity, error = await resolve_query(
            raw
        )

        if error:

            await update.message.reply_text(
                "❌ Manba topilmadi.\n\n"
                + error
            )

            return

        if not getattr(
            entity,
            "title",
            None
        ):

            await update.message.reply_text(

                "❌ Public guruh yoki kanal "
                "username'ini yuboring."
            )

            return

        try:

            source = await db.upsert_source(
                entity
            )

            status = await update.message.reply_text(
                "📥 Indekslash boshlandi..."
            )

            count = await index_source(
                db,
                entity,
                source["id"],
                limit=1000
            )

            await status.edit_text(

                "✅ <b>INDEX TAYYOR</b>\n\n"

                f"📚 {source['title']}\n"
                f"💬 Xabarlar: {count}",

                parse_mode=ParseMode.HTML
            )

        except Exception as e:

            log.exception(
                "Index error"
            )

            await update.message.reply_text(

                "❌ Indekslashda xatolik:\n"
                f"{type(e).__name__}: {e}"
            )

        return

    await search(
        update,
        context
    )


async def main():

    print(
        "PostgreSQL ulanishi..."
    )

    await db.connect()

    print(
        "MTProto user session ulanishi..."
    )

    await start_user_client()

    print(
        "Bot ishga tushmoqda..."
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
            help_cmd
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
            message_handler
        )
    )

    await application.initialize()

    await application.start()

    await application.updater.start_polling()

    print(
        "================================"
    )

    print(
        "QIDIRGICH ISHGA TUSHDI"
    )

    print(
        "================================"
    )

    try:

        while True:

            await asyncio.sleep(
                3600
            )

    finally:

        await application.updater.stop()

        await application.stop()

        await application.shutdown()

        await db.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
