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

        async with self.pool.acquire() as conn:

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    bio TEXT,
                    phone TEXT,
                    is_bot BOOLEAN DEFAULT FALSE,
                    verified BOOLEAN DEFAULT FALSE,
                    premium BOOLEAN DEFAULT FALSE,
                    scam BOOLEAN DEFAULT FALSE,
                    fake BOOLEAN DEFAULT FALSE,
                    first_seen TIMESTAMP DEFAULT NOW(),
                    last_seen TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username
                ON users(username);
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE,
                    username TEXT,
                    title TEXT,
                    source_type TEXT,
                    added_at TIMESTAMP DEFAULT NOW(),
                    last_indexed TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_message_id BIGINT,
                    telegram_user_id BIGINT,
                    source_id INTEGER REFERENCES sources(id)
                        ON DELETE CASCADE,
                    message_text TEXT,
                    message_date TIMESTAMP,
                    public_url TEXT,
                    indexed_at TIMESTAMP DEFAULT NOW(),

                    UNIQUE(
                        telegram_message_id,
                        source_id
                    )
                );
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user
                ON messages(telegram_user_id);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_date
                ON messages(message_date);
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    id BIGSERIAL PRIMARY KEY,
                    source_user_id BIGINT,
                    target_user_id BIGINT,
                    connection_type TEXT,
                    source_id INTEGER REFERENCES sources(id)
                        ON DELETE CASCADE,
                    message_id BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS searches (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_user_id BIGINT,
                    query TEXT,
                    result_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

    async def save_user(self, user):

        bio = getattr(user, "about", None)

        async with self.pool.acquire() as conn:

            await conn.execute("""
                INSERT INTO users (
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    bio,
                    phone,
                    is_bot,
                    verified,
                    premium,
                    scam,
                    fake,
                    last_seen
                )
                VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,NOW()
                )
                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    bio = EXCLUDED.bio,
                    is_bot = EXCLUDED.is_bot,
                    verified = EXCLUDED.verified,
                    premium = EXCLUDED.premium,
                    scam = EXCLUDED.scam,
                    fake = EXCLUDED.fake,
                    last_seen = NOW()
            """,
                user.id,
                getattr(user, "username", None),
                getattr(user, "first_name", None),
                getattr(user, "last_name", None),
                bio,
                None,
                bool(getattr(user, "bot", False)),
                bool(getattr(user, "verified", False)),
                bool(getattr(user, "premium", False)),
                bool(getattr(user, "scam", False)),
                bool(getattr(user, "fake", False)),
            )

    async def add_source(
        self,
        telegram_id,
        username,
        title,
        source_type
    ):

        async with self.pool.acquire() as conn:

            return await conn.fetchrow("""
                INSERT INTO sources (
                    telegram_id,
                    username,
                    title,
                    source_type
                )
                VALUES ($1,$2,$3,$4)
                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type
                RETURNING id
            """,
                telegram_id,
                username,
                title,
                source_type
            )

    async def get_source(self, source_id):

        async with self.pool.acquire() as conn:

            return await conn.fetchrow("""
                SELECT *
                FROM sources
                WHERE id=$1
            """, source_id)

    async def save_message(
        self,
        message_id,
        user_id,
        source_id,
        text,
        message_date,
        public_url
    ):

        async with self.pool.acquire() as conn:

            await conn.execute("""
                INSERT INTO messages (
                    telegram_message_id,
                    telegram_user_id,
                    source_id,
                    message_text,
                    message_date,
                    public_url
                )
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (
                    telegram_message_id,
                    source_id
                )
                DO UPDATE SET
                    message_text = EXCLUDED.message_text,
                    message_date = EXCLUDED.message_date,
                    public_url = EXCLUDED.public_url
            """,
                message_id,
                user_id,
                source_id,
                text,
                message_date,
                public_url
            )

    async def update_source_indexed(self, source_id):

        async with self.pool.acquire() as conn:

            await conn.execute("""
                UPDATE sources
                SET last_indexed=NOW()
                WHERE id=$1
            """, source_id)

    async def search_messages_by_user(
        self,
        telegram_user_id,
        limit=30
    ):

        async with self.pool.acquire() as conn:

            return await conn.fetch("""
                SELECT
                    m.*,
                    s.title,
                    s.username AS source_username
                FROM messages m
                LEFT JOIN sources s
                    ON s.id=m.source_id
                WHERE m.telegram_user_id=$1
                ORDER BY m.message_date DESC
                LIMIT $2
            """,
                telegram_user_id,
                limit
            )

    async def search_messages_text(
        self,
        text,
        limit=30
    ):

        async with self.pool.acquire() as conn:

            return await conn.fetch("""
                SELECT
                    m.*,
                    s.title,
                    s.username AS source_username
                FROM messages m
                LEFT JOIN sources s
                    ON s.id=m.source_id
                WHERE m.message_text ILIKE $1
                ORDER BY m.message_date DESC
                LIMIT $2
            """,
                f"%{text}%",
                limit
            )

    async def save_search(
        self,
        telegram_user_id,
        query,
        result_count
    ):

        async with self.pool.acquire() as conn:

            await conn.execute("""
                INSERT INTO searches (
                    telegram_user_id,
                    query,
                    result_count
                )
                VALUES ($1,$2,$3)
            """,
                telegram_user_id,
                query,
                result_count
            )

    async def stats(self):

        async with self.pool.acquire() as conn:

            users = await conn.fetchval(
                "SELECT COUNT(*) FROM users"
            )

            sources = await conn.fetchval(
                "SELECT COUNT(*) FROM sources"
            )

            messages = await conn.fetchval(
                "SELECT COUNT(*) FROM messages"
            )

            searches = await conn.fetchval(
                "SELECT COUNT(*) FROM searches"
            )

            return {
                "users": users,
                "sources": sources,
                "messages": messages,
                "searches": searches
            }
