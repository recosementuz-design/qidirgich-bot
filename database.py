import asyncpg
from config import DATABASE_URL


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=5
        )
        await self.create_tables()

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        async with self.pool.acquire() as c:

            await c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    bio TEXT,
                    is_bot BOOLEAN DEFAULT FALSE,
                    verified BOOLEAN DEFAULT FALSE,
                    premium BOOLEAN DEFAULT FALSE,
                    scam BOOLEAN DEFAULT FALSE,
                    fake BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await c.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username
                ON users (LOWER(username))
            """)

            await c.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    title TEXT,
                    source_type TEXT NOT NULL,
                    last_indexed TIMESTAMPTZ,
                    message_count BIGINT DEFAULT 0
                )
            """)

            await c.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_message_id BIGINT NOT NULL,
                    source_id INTEGER NOT NULL
                        REFERENCES sources(id)
                        ON DELETE CASCADE,
                    telegram_user_id BIGINT,
                    message_text TEXT,
                    message_date TIMESTAMPTZ,
                    public_url TEXT,

                    UNIQUE(source_id, telegram_message_id)
                )
            """)

            await c.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user
                ON messages (telegram_user_id)
            """)

            await c.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_source
                ON messages (source_id)
            """)

            await c.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_date
                ON messages (message_date DESC)
            """)

            await c.execute("""
                CREATE TABLE IF NOT EXISTS searches (
                    id BIGSERIAL PRIMARY KEY,
                    requester_id BIGINT,
                    query TEXT,
                    result_count INTEGER,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

    async def save_user(self, user):
        if not user or not getattr(user, "id", None):
            return

        async with self.pool.acquire() as c:
            await c.execute("""
                INSERT INTO users (
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    bio,
                    is_bot,
                    verified,
                    premium,
                    scam,
                    fake,
                    updated_at
                )
                VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW()
                )

                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    username=EXCLUDED.username,
                    first_name=EXCLUDED.first_name,
                    last_name=EXCLUDED.last_name,
                    bio=EXCLUDED.bio,
                    is_bot=EXCLUDED.is_bot,
                    verified=EXCLUDED.verified,
                    premium=EXCLUDED.premium,
                    scam=EXCLUDED.scam,
                    fake=EXCLUDED.fake,
                    updated_at=NOW()
            """,
            user.id,
            getattr(user, "username", None),
            getattr(user, "first_name", None),
            getattr(user, "last_name", None),
            getattr(user, "about", None),
            bool(getattr(user, "bot", False)),
            bool(getattr(user, "verified", False)),
            bool(getattr(user, "premium", False)),
            bool(getattr(user, "scam", False)),
            bool(getattr(user, "fake", False))
            )

    async def upsert_source(self, entity):

        title = (
            getattr(entity, "title", None)
            or getattr(entity, "first_name", None)
            or str(entity.id)
        )

        if getattr(entity, "broadcast", False):
            source_type = "channel"
        else:
            source_type = "group"

        async with self.pool.acquire() as c:

            return await c.fetchrow("""
                INSERT INTO sources (
                    telegram_id,
                    username,
                    title,
                    source_type
                )
                VALUES ($1,$2,$3,$4)

                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    username=EXCLUDED.username,
                    title=EXCLUDED.title,
                    source_type=EXCLUDED.source_type

                RETURNING
                    id,
                    title,
                    username,
                    source_type
            """,
            entity.id,
            getattr(entity, "username", None),
            title,
            source_type
            )

    async def save_message(self, source_id, message):

        sender_id = getattr(message, "sender_id", None)
        text = getattr(message, "message", None)

        if not text:
            return False

        public_url = None

        try:
            public_url = getattr(
                message,
                "message_link",
                None
            )
        except Exception:
            pass

        async with self.pool.acquire() as c:

            result = await c.execute("""
                INSERT INTO messages (
                    telegram_message_id,
                    source_id,
                    telegram_user_id,
                    message_text,
                    message_date,
                    public_url
                )
                VALUES ($1,$2,$3,$4,$5,$6)

                ON CONFLICT (
                    source_id,
                    telegram_message_id
                )

                DO UPDATE SET
                    telegram_user_id=EXCLUDED.telegram_user_id,
                    message_text=EXCLUDED.message_text,
                    message_date=EXCLUDED.message_date,
                    public_url=EXCLUDED.public_url
            """,
            message.id,
            source_id,
            sender_id,
            text,
            message.date,
            public_url
            )

            return True

    async def finish_source(self, source_id):

        async with self.pool.acquire() as c:

            await c.execute("""
                UPDATE sources

                SET
                    last_indexed=NOW(),
                    message_count=(
                        SELECT COUNT(*)
                        FROM messages
                        WHERE source_id=$1
                    )

                WHERE id=$1
            """, source_id)

    async def user_messages(
        self,
        user_id,
        limit=20
    ):

        async with self.pool.acquire() as c:

            return await c.fetch("""
                SELECT
                    m.*,
                    s.title,
                    s.username AS source_username

                FROM messages m

                JOIN sources s
                    ON s.id=m.source_id

                WHERE m.telegram_user_id=$1

                ORDER BY
                    m.message_date DESC NULLS LAST

                LIMIT $2
            """,
            user_id,
            limit
            )

    async def search_text(
        self,
        text,
        limit=20
    ):

        async with self.pool.acquire() as c:

            return await c.fetch("""
                SELECT
                    m.*,
                    s.title,
                    s.username AS source_username

                FROM messages m

                JOIN sources s
                    ON s.id=m.source_id

                WHERE
                    m.message_text ILIKE $1

                ORDER BY
                    m.message_date DESC NULLS LAST

                LIMIT $2
            """,
            f"%{text}%",
            limit
            )

    async def stats(self):

        async with self.pool.acquire() as c:

            return {
                "users": await c.fetchval(
                    "SELECT COUNT(*) FROM users"
                ),

                "sources": await c.fetchval(
                    "SELECT COUNT(*) FROM sources"
                ),

                "messages": await c.fetchval(
                    "SELECT COUNT(*) FROM messages"
                ),

                "searches": await c.fetchval(
                    "SELECT COUNT(*) FROM searches"
                )
            }

    async def save_search(
        self,
        requester_id,
        query,
        count
    ):

        async with self.pool.acquire() as c:

            await c.execute("""
                INSERT INTO searches (
                    requester_id,
                    query,
                    result_count
                )
                VALUES ($1,$2,$3)
            """,
            requester_id,
            query,
            count
            )
