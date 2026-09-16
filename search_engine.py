from telegram_client import (
    resolve_username,
    resolve_id,
    get_profile_photo
)


async def search_query(query):

    query = query.strip()

    if not query:
        return None, "Qidiruv so'rovi bo'sh."

    if query.isdigit():

        return await resolve_id(query)

    return await resolve_username(query)


async def build_report(user, db):

    await db.save_user(user)

    username = getattr(
        user,
        "username",
        None
    )

    first_name = getattr(
        user,
        "first_name",
        None
    ) or ""

    last_name = getattr(
        user,
        "last_name",
        None
    ) or ""

    full_name = (
        f"{first_name} {last_name}"
    ).strip()

    if not full_name:
        full_name = "Noma'lum"

    bio = getattr(
        user,
        "about",
        None
    )

    if not bio:
        bio = "Mavjud emas"

    messages = await db.search_messages_by_user(
        user.id,
        limit=30
    )

    photos = await get_profile_photo(user)

    report = []

    report.append(
        "🔎 <b>QIDIRGICH NATIJASI</b>"
    )

    report.append("━━━━━━━━━━━━━━━━━━")

    report.append(
        "👤 <b>PROFIL</b>"
    )

    report.append(
        f"Ism: <b>{full_name}</b>"
    )

    report.append(
        f"Username: <b>@{username}</b>"
        if username
        else "Username: mavjud emas"
    )

    report.append(
        f"ID: <code>{user.id}</code>"
    )

    report.append(
        f"Bio: {bio[:500]}"
    )

    if getattr(user, "verified", False):
        report.append("☑️ Verified: ha")

    if getattr(user, "premium", False):
        report.append("⭐ Premium: ha")

    report.append("")

    report.append(
        "🖼 <b>PROFIL RASMLARI</b>"
    )

    report.append(
        f"Topilgan: <b>{len(photos)}</b>"
    )

    report.append("")

    report.append(
        "💬 <b>INDEKSLANGAN XABARLAR</b>"
    )

    report.append(
        f"Topilgan: <b>{len(messages)}</b>"
    )

    report.append("")

    if messages:

        for index, message in enumerate(
            messages[:10],
            start=1
        ):

            source = (
                message["title"]
                or message["source_username"]
                or "Noma'lum manba"
            )

            text = (
                message["message_text"]
                or ""
            )

            text = text.replace(
                "\n",
                " "
            )

            if len(text) > 180:
                text = text[:180] + "..."

            report.append(
                f"<b>{index}.</b> {source}"
            )

            report.append(
                f"💬 {text}"
            )

            if message["public_url"]:

                report.append(
                    f"🔗 {message['public_url']}"
                )

            report.append("")

    report.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    report.append(
        "ℹ️ Faqat botga ochiq/ruxsat etilgan "
        "va indekslangan Telegram ma'lumotlari "
        "ko'rsatiladi."
    )

    return "\n".join(report)
