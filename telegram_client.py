from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

from config import API_ID, API_HASH, STRING_SESSION


client = None


async def start_user_client():

    global client

    if not STRING_SESSION:

        raise RuntimeError(
            "STRING_SESSION topilmadi. "
            "Railway Variables ga STRING_SESSION qo'ying."
        )

    client = TelegramClient(
        StringSession(STRING_SESSION),
        API_ID,
        API_HASH
    )

    await client.connect()

    if not await client.is_user_authorized():

        raise RuntimeError(
            "STRING_SESSION yaroqsiz yoki "
            "Telegram avtorizatsiyasi tugagan."
        )

    me = await client.get_me()

    print(
        "MTProto user connected:",
        getattr(me, "username", None),
        me.id
    )

    return client


async def resolve_query(value):

    value = value.strip()

    if value.startswith("https://t.me/"):

        value = value.rstrip("/")
        value = value.split("/")[-1]

    if value.startswith("t.me/"):

        value = value.rstrip("/")
        value = value.split("/")[-1]

    if value.startswith("@"):

        value = value[1:]

    try:

        if value.isdigit():

            entity = await client.get_entity(
                int(value)
            )

        else:

            entity = await client.get_entity(
                value
            )

        return entity, None

    except RPCError as e:

        return None, (
            f"Telegram API xatosi: "
            f"{type(e).__name__}"
        )

    except Exception as e:

        return None, str(e)


async def profile_photo(entity):

    try:

        photos = await client.get_profile_photos(
            entity,
            limit=1
        )

        if not photos:
            return None

        return await client.download_media(
            photos[0],
            file=bytes
        )

    except Exception:

        return None
