import json
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


async def ensure_schema(pool: asyncpg.Pool) -> None:
    await pool.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            conversation_id UUID PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            summary TEXT NOT NULL DEFAULT '',
            key_points JSONB NOT NULL DEFAULT '[]'::jsonb,
            next_steps TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user_updated_at
            ON conversation_summaries(user_id, updated_at DESC);
        """
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


async def get_conversation_summary(pool: asyncpg.Pool, conversation_id: str) -> dict | None:
    row = await pool.fetchrow(
        """
        SELECT conversation_id, user_id, summary, key_points, next_steps, created_at, updated_at
        FROM conversation_summaries
        WHERE conversation_id = $1
        """,
        uuid.UUID(conversation_id),
    )
    return dict(row) if row else None


async def upsert_conversation_summary(
    pool: asyncpg.Pool,
    user_id: str,
    conversation_id: str,
    summary: str,
    key_points: list[str],
    next_steps: str,
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO conversation_summaries (
            conversation_id,
            user_id,
            summary,
            key_points,
            next_steps
        )
        VALUES ($1, $2, $3, $4::jsonb, $5)
        ON CONFLICT (conversation_id)
        DO UPDATE SET
            summary = EXCLUDED.summary,
            key_points = EXCLUDED.key_points,
            next_steps = EXCLUDED.next_steps,
            updated_at = now()
        RETURNING conversation_id, user_id, summary, key_points, next_steps, created_at, updated_at
        """,
        uuid.UUID(conversation_id),
        uuid.UUID(user_id),
        summary,
        json.dumps(key_points),
        next_steps,
    )
    return dict(row)


async def get_recent_conversation_summaries(
    pool: asyncpg.Pool,
    user_id: str,
    *,
    exclude_conversation_id: str | None = None,
    limit: int = 3,
) -> list[dict]:
    params: list[object] = [uuid.UUID(user_id)]
    where_clause = "WHERE cs.user_id = $1"

    if exclude_conversation_id:
        params.append(uuid.UUID(exclude_conversation_id))
        where_clause += f" AND cs.conversation_id != ${len(params)}"

    params.append(limit)
    rows = await pool.fetch(
        f"""
        SELECT
            cs.conversation_id,
            c.title,
            cs.summary,
            cs.key_points,
            cs.next_steps,
            cs.updated_at
        FROM conversation_summaries cs
        JOIN conversations c ON c.id = cs.conversation_id
        {where_clause}
        ORDER BY cs.updated_at DESC
        LIMIT ${len(params)}
        """,
        *params,
    )
    return [dict(r) for r in rows]


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
