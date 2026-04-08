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

        CREATE TABLE IF NOT EXISTS user_coaching_profiles (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS coaching_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            event_time TIMESTAMPTZ NULL,
            details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_coaching_events_user_created_at
            ON coaching_events(user_id, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_coaching_events_user_type_created_at
            ON coaching_events(user_id, event_type, created_at DESC);

        CREATE TABLE IF NOT EXISTS coaching_artifacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
            artifact_type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            content_markdown TEXT NOT NULL DEFAULT '',
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_coaching_artifacts_user_created_at
            ON coaching_artifacts(user_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS follow_up_states (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            pending_question TEXT NOT NULL DEFAULT '',
            missing_fields_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            last_asked_at TIMESTAMPTZ NULL,
            last_answered_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS proactive_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            due_at TIMESTAMPTZ NULL,
            summary TEXT NOT NULL DEFAULT '',
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_proactive_tasks_user_status_due_at
            ON proactive_tasks(user_id, status, due_at ASC);

        CREATE TABLE IF NOT EXISTS coaching_metrics (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
            metric_type TEXT NOT NULL,
            model_name TEXT NOT NULL DEFAULT '',
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_coaching_metrics_user_created_at
            ON coaching_metrics(user_id, created_at DESC);
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


async def get_user_coaching_profile(pool: asyncpg.Pool, user_id: str) -> dict | None:
    row = await pool.fetchrow(
        """
        SELECT user_id, profile_json, created_at, updated_at
        FROM user_coaching_profiles
        WHERE user_id = $1
        """,
        uuid.UUID(user_id),
    )
    return dict(row) if row else None


async def upsert_user_coaching_profile(
    pool: asyncpg.Pool,
    user_id: str,
    profile_json: dict[str, Any],
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO user_coaching_profiles (user_id, profile_json)
        VALUES ($1, $2::jsonb)
        ON CONFLICT (user_id)
        DO UPDATE SET
            profile_json = EXCLUDED.profile_json,
            updated_at = now()
        RETURNING user_id, profile_json, created_at, updated_at
        """,
        uuid.UUID(user_id),
        json.dumps(profile_json),
    )
    return dict(row)


async def get_recent_coaching_events(
    pool: asyncpg.Pool,
    user_id: str,
    *,
    event_types: list[str] | None = None,
    limit: int = 6,
) -> list[dict]:
    if event_types:
        rows = await pool.fetch(
            """
            SELECT id, user_id, conversation_id, event_type, summary, event_time, details_json, created_at
            FROM coaching_events
            WHERE user_id = $1 AND event_type = ANY($2::text[])
            ORDER BY COALESCE(event_time, created_at) DESC
            LIMIT $3
            """,
            uuid.UUID(user_id),
            event_types,
            limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT id, user_id, conversation_id, event_type, summary, event_time, details_json, created_at
            FROM coaching_events
            WHERE user_id = $1
            ORDER BY COALESCE(event_time, created_at) DESC
            LIMIT $2
            """,
            uuid.UUID(user_id),
            limit,
        )
    return [dict(r) for r in rows]


async def insert_coaching_events(
    pool: asyncpg.Pool,
    user_id: str,
    conversation_id: str,
    events: list[dict[str, Any]],
) -> list[dict]:
    inserted: list[dict] = []
    for event in events:
        row = await pool.fetchrow(
            """
            INSERT INTO coaching_events (
                user_id,
                conversation_id,
                event_type,
                summary,
                event_time,
                details_json
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            RETURNING id, user_id, conversation_id, event_type, summary, event_time, details_json, created_at
            """,
            uuid.UUID(user_id),
            uuid.UUID(conversation_id),
            event.get("event_type") or "check_in",
            event.get("summary") or "",
            event.get("event_time"),
            json.dumps(event.get("details") or {}),
        )
        inserted.append(dict(row))
    return inserted


async def create_coaching_artifact(
    pool: asyncpg.Pool,
    user_id: str,
    conversation_id: str,
    artifact_type: str,
    title: str,
    content_markdown: str,
    metadata: dict[str, Any] | None = None,
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO coaching_artifacts (
            user_id,
            conversation_id,
            artifact_type,
            title,
            content_markdown,
            metadata_json
        )
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING id, user_id, conversation_id, artifact_type, title, content_markdown, metadata_json, created_at, updated_at
        """,
        uuid.UUID(user_id),
        uuid.UUID(conversation_id),
        artifact_type,
        title,
        content_markdown,
        json.dumps(metadata or {}),
    )
    return dict(row)


async def get_follow_up_state(pool: asyncpg.Pool, user_id: str) -> dict | None:
    row = await pool.fetchrow(
        """
        SELECT user_id, pending_question, missing_fields_json, last_asked_at, last_answered_at, created_at, updated_at
        FROM follow_up_states
        WHERE user_id = $1
        """,
        uuid.UUID(user_id),
    )
    return dict(row) if row else None


async def upsert_follow_up_state(
    pool: asyncpg.Pool,
    user_id: str,
    pending_question: str,
    missing_fields: list[str],
    *,
    last_asked_at: datetime | None = None,
    last_answered_at: datetime | None = None,
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO follow_up_states (
            user_id,
            pending_question,
            missing_fields_json,
            last_asked_at,
            last_answered_at
        )
        VALUES ($1, $2, $3::jsonb, $4, $5)
        ON CONFLICT (user_id)
        DO UPDATE SET
            pending_question = EXCLUDED.pending_question,
            missing_fields_json = EXCLUDED.missing_fields_json,
            last_asked_at = EXCLUDED.last_asked_at,
            last_answered_at = EXCLUDED.last_answered_at,
            updated_at = now()
        RETURNING user_id, pending_question, missing_fields_json, last_asked_at, last_answered_at, created_at, updated_at
        """,
        uuid.UUID(user_id),
        pending_question,
        json.dumps(missing_fields),
        last_asked_at,
        last_answered_at,
    )
    return dict(row)


async def clear_follow_up_state(pool: asyncpg.Pool, user_id: str, *, answered_at: datetime | None = None) -> None:
    await pool.execute(
        """
        INSERT INTO follow_up_states (
            user_id,
            pending_question,
            missing_fields_json,
            last_asked_at,
            last_answered_at
        )
        VALUES ($1, '', '[]'::jsonb, NULL, $2)
        ON CONFLICT (user_id)
        DO UPDATE SET
            pending_question = '',
            missing_fields_json = '[]'::jsonb,
            last_answered_at = $2,
            updated_at = now()
        """,
        uuid.UUID(user_id),
        answered_at,
    )


async def create_proactive_tasks(
    pool: asyncpg.Pool,
    user_id: str,
    conversation_id: str,
    tasks: list[dict[str, Any]],
) -> list[dict]:
    created: list[dict] = []
    for task in tasks:
        row = await pool.fetchrow(
            """
            INSERT INTO proactive_tasks (
                user_id,
                conversation_id,
                task_type,
                status,
                due_at,
                summary,
                payload_json
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
            RETURNING id, user_id, conversation_id, task_type, status, due_at, summary, payload_json, created_at, updated_at
            """,
            uuid.UUID(user_id),
            uuid.UUID(conversation_id),
            task.get("task_type") or "checkin",
            task.get("status") or "open",
            task.get("due_at"),
            task.get("summary") or "",
            json.dumps(task.get("payload") or {}),
        )
        created.append(dict(row))
    return created


async def get_open_proactive_tasks(
    pool: asyncpg.Pool,
    user_id: str,
    *,
    limit: int = 5,
) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT id, user_id, conversation_id, task_type, status, due_at, summary, payload_json, created_at, updated_at
        FROM proactive_tasks
        WHERE user_id = $1 AND status = 'open'
        ORDER BY COALESCE(due_at, created_at) ASC
        LIMIT $2
        """,
        uuid.UUID(user_id),
        limit,
    )
    return [dict(r) for r in rows]


async def create_coaching_metric(
    pool: asyncpg.Pool,
    user_id: str,
    conversation_id: str,
    metric_type: str,
    model_name: str,
    payload: dict[str, Any],
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO coaching_metrics (
            user_id,
            conversation_id,
            metric_type,
            model_name,
            payload_json
        )
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING id, user_id, conversation_id, metric_type, model_name, payload_json, created_at
        """,
        uuid.UUID(user_id),
        uuid.UUID(conversation_id),
        metric_type,
        model_name,
        json.dumps(payload),
    )
    return dict(row)


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
