import asyncio
import os

from telethon import TelegramClient
from telethon.sessions import StringSession


API_ID = int(
    os.environ.get(
        "API_ID"
    )
    or input("API_ID: ").strip()
)

API_HASH = (
    os.environ.get(
        "API_HASH"
    )
    or input("API_HASH: ").strip()
)


async def main():

    client = TelegramClient(
        StringSession(),
        API_ID,
        API_HASH
    )

    await client.start()

    session = client.session.save()

    print()
    print(
        "================================"
    )
    print(
        "STRING_SESSION"
    )
    print(
        "================================"
    )
    print(session)
    print(
        "================================"
    )
    print(
        "END"
    )
    print(
        "================================"
    )

    await client.disconnect()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
