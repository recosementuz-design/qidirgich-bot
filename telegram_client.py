import logging

from telethon import TelegramClient
from telethon.errors import (
    UsernameInvalidError,
    UsernameNotOccupiedError,
    RPCError
)
from telethon.tl.types import User, Channel

from config import API_ID, API_HASH


logger = logging.getLogger(__name__)


client = TelegramClient(
    "qidirgich_session",
    API_ID,
    API_HASH
)


async def start_client(bot_token):

    await client.start(
        bot_token=bot_token
    )

    me = await client.get_me()

    logger.info(
        "Telegram client connected: @%s",
        getattr(me, "username", None)
    )


async def resolve_username(username):

    username = username.strip()

    if username.startswith("@"):
        username = username[1:]

    if username.startswith("https://t.me/"):
        username = username.replace(
            "https://t.me/",
            "",
            1
        )

    if username.startswith("t.me/"):
        username = username.replace(
            "t.me/",
            "",
            1
        )

    try:

        entity = await client.get_entity(
            username
        )

        return entity, None

    except UsernameInvalidError:

        return None, "Username noto'g'ri."

    except UsernameNotOccupiedError:

        return None, "Bunday username topilmadi."

    except RPCError as e:

        logger.exception(e)

        return None, "Telegram API xatosi."

    except Exception as e:

        logger.exception(e)

        return None, "Qidiruvda xatolik."


async def resolve_id(user_id):

    try:

        user_id = int(user_id)

        entity = await client.get_entity(
            user_id
        )

        return entity, None

    except Exception as e:

        logger.exception(e)

        return None, (
            "Bu ID bo'yicha Telegram entity "
            "mavjud emas yoki unga kirish imkoniyati yo'q."
        )


async def get_profile_photo(user):

    try:

        photos = await client.get_profile_photos(
            user,
            limit=10
        )

        return photos

    except Exception as e:

        logger.exception(e)

        return []


async def download_profile_photo(user):

    try:

        photos = await client.get_profile_photos(
            user,
            limit=1
        )

        if not photos:
            return None

        return await client.download_media(
            photos[0],
            file=bytes
        )

    except Exception as e:

        logger.exception(e)

        return None


def is_user(entity):

    return isinstance(entity, User)


def is_channel(entity):

    return isinstance(entity, Channel)
