from telegram_client import resolve_query


async def search_user(
    db,
    query
):

    entity, error = await resolve_query(
        query
    )

    if error:
        return {
            "ok": False,
            "error": error
        }

    try:
        await db.save_user(entity)
    except Exception:
        pass

    messages = await db.user_messages(
        entity.id,
        limit=20
    )

    return {
        "ok": True,
        "entity": entity,
        "messages": messages
    }
