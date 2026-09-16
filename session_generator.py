import asyncio
from telethon import TelegramClient

API_ID = 12345678
API_HASH = "BU_YERGA_API_HASH"

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
