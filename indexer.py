from telegram_client import client


async def index_source(
    db,
    entity,
    source_id,
    limit=1000
):

    count = 0

    async for message in client.iter_messages(
        entity,
        limit=limit
    ):

        if not getattr(
            message,
            "message",
            None
        ):
            continue

        try:

            sender = await message.get_sender()

            if sender:

                await db.save_user(
                    sender
                )

        except Exception:
            pass

        await db.save_message(
            source_id,
            message
        )

        count += 1

    await db.finish_source(
        source_id
    )

    return count
