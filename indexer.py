import logging

from telegram_client import client


logger = logging.getLogger(__name__)


async def index_source(
    db,
    source_entity,
    source_id,
    limit=1000
):

    count = 0

    try:

        async for message in client.iter_messages(
            source_entity,
            limit=limit
        ):

            if not message:
                continue

            text = getattr(
                message,
                "message",
                None
            )

            if not text:
                continue

            sender_id = None

            try:

                sender = await message.get_sender()

                if sender:
                    sender_id = getattr(
                        sender,
                        "id",
                        None
                    )

                    if sender_id:
                        await db.save_user(
                            sender
                        )

            except Exception:

                pass

            public_url = None

            try:

                public_url = message.message_link

            except Exception:

                pass

            await db.save_message(
                message_id=message.id,
                user_id=sender_id,
                source_id=source_id,
                text=text,
                message_date=message.date,
                public_url=public_url
            )

            count += 1

        await db.update_source_indexed(
            source_id
        )

        return count

    except Exception as e:

        logger.exception(
            "Indexing error"
        )

        raise e
