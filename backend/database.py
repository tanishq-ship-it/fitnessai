import uuid
from datetime import datetime

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


# ── User operations ──

async def create_user(pool: asyncpg.Pool, email: str, password_hash: str) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO users (email, password_hash)
        VALUES ($1, $2)
        RETURNING id, email, created_at
        """,
        email,
        password_hash,
    )
    return dict(row)


async def get_user_by_email(pool: asyncpg.Pool, email: str) -> dict | None:
    row = await pool.fetchrow(
        "SELECT id, email, password_hash FROM users WHERE email = $1",
        email,
    )
    return dict(row) if row else None


# ── Session operations ──

async def create_session(
    pool: asyncpg.Pool,
    user_id: str,
    refresh_token_hash: str,
    expires_at: datetime,
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO sessions (user_id, refresh_token_hash, expires_at)
        VALUES ($1, $2, $3)
        RETURNING id, user_id, expires_at, created_at
        """,
        uuid.UUID(user_id),
        refresh_token_hash,
        expires_at,
    )
    return dict(row)


async def get_session_by_token_hash(pool: asyncpg.Pool, token_hash: str) -> dict | None:
    row = await pool.fetchrow(
        "SELECT id, user_id, expires_at FROM sessions WHERE refresh_token_hash = $1",
        token_hash,
    )
    return dict(row) if row else None


async def delete_session(pool: asyncpg.Pool, session_id: str) -> None:
    await pool.execute("DELETE FROM sessions WHERE id = $1", uuid.UUID(session_id))


async def delete_user_session_by_token(
    pool: asyncpg.Pool, user_id: str, token_hash: str
) -> None:
    await pool.execute(
        "DELETE FROM sessions WHERE user_id = $1 AND refresh_token_hash = $2",
        uuid.UUID(user_id),
        token_hash,
    )


# ── Conversation operations ──

async def create_conversation(
    pool: asyncpg.Pool, user_id: str, title: str = "New Chat"
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO conversations (user_id, title)
        VALUES ($1, $2)
        RETURNING id, user_id, title, created_at, updated_at
        """,
        uuid.UUID(user_id),
        title,
    )
    return dict(row)


async def update_conversation_title(
    pool: asyncpg.Pool, conversation_id: str, title: str
) -> None:
    await pool.execute(
        "UPDATE conversations SET title = $1, updated_at = now() WHERE id = $2",
        title,
        uuid.UUID(conversation_id),
    )


async def get_user_conversations(pool: asyncpg.Pool, user_id: str) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = $1
        ORDER BY updated_at DESC
        """,
        uuid.UUID(user_id),
    )
    return [dict(r) for r in rows]


async def verify_conversation_ownership(
    pool: asyncpg.Pool, conversation_id: str, user_id: str
) -> bool:
    row = await pool.fetchrow(
        "SELECT 1 FROM conversations WHERE id = $1 AND user_id = $2",
        uuid.UUID(conversation_id),
        uuid.UUID(user_id),
    )
    return row is not None


# ── Message operations ──

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
