import asyncio
from telethon import TelegramClient

API_ID = 5923818664
API_HASH = "8f6f39d739c367dea66fbe3a137aff0a"

async def main():
    client = TelegramClient(
        "qidirgich_session",
        API_ID,
        API_HASH
    )

    await client.start()

    me = await client.get_me()

    print()
    print("================================")
    print("SESSION MUVAFFAQIYATLI YARATILDI")
    print("================================")
    print("ID:", me.id)
    print("Username:", getattr(me, "username", None))
    print("Session fayli:")
    print("qidirgich_session.session")
    print()

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
