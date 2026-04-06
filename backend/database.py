import uuid
import asyncpg

from config import settings


async def create_pool() -> asyncpg.Pool:
    # statement_cache_size=0 is required for Supabase PgBouncer pooler
    return await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=2,
        max_size=10,
        statement_cache_size=0,
    )


async def save_message(
    pool: asyncpg.Pool,
    conversation_id: str,
    role: str,
    content: str,
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO messages (conversation_id, role, content)
        VALUES ($1, $2, $3)
        RETURNING id, conversation_id, role, content, created_at
        """,
        uuid.UUID(conversation_id),
        role,
        content,
    )
    return dict(row)


async def get_messages(pool: asyncpg.Pool, conversation_id: str) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        """,
        uuid.UUID(conversation_id),
    )
    return [dict(r) for r in rows]
