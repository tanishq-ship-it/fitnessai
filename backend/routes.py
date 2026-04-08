import asyncio
import json
import logging
import re
from collections.abc import Awaitable
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import (
    create_access_token,
    generate_refresh_token,
    get_current_user,
    hash_password,
    hash_refresh_token,
    verify_password,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from database import (
    create_conversation,
    create_session,
    create_user,
    delete_session,
    delete_user_session_by_token,
    get_conversation_summary,
    get_messages,
    get_recent_conversation_summaries,
    get_session_by_token_hash,
    get_user_by_email,
    get_user_conversations,
    save_message,
    upsert_conversation_summary,
    update_conversation_title,
    verify_conversation_ownership,
)
from llm import (
    format_recent_summaries,
    generate_conversation_summary,
    generate_title,
    stream_chat_response,
)
from memory import search_memories, store_memories

logger = logging.getLogger(__name__)

router = APIRouter()
BACKGROUND_TASKS: set[asyncio.Task] = set()

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ── Request/Response Models ──

class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


# ── Helper ──

async def _create_token_pair(pool, user_id: str, email: str) -> dict:
    refresh_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    await create_session(pool, user_id, hash_refresh_token(refresh_token), expires_at)
    access_token = create_access_token(user_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user_id, "email": email},
    }


async def _persist_long_term_context(
    pool,
    user_id: str,
    conversation_id: str,
    exchange_messages: list[dict],
) -> None:
    try:
        await asyncio.to_thread(store_memories, exchange_messages, user_id)
    except Exception as e:
        logger.warning("Mem0 persistence failed: %s", e)

    try:
        history = await get_messages(pool, conversation_id)
        existing_summary = await get_conversation_summary(pool, conversation_id)
        summary_payload = await generate_conversation_summary(
            history,
            previous_summary=existing_summary["summary"] if existing_summary else "",
        )
        await upsert_conversation_summary(
            pool,
            user_id,
            conversation_id,
            summary_payload["summary"],
            summary_payload["key_points"],
            summary_payload["next_steps"],
        )
    except Exception as e:
        logger.warning("Conversation summary persistence failed: %s", e)


def _schedule_background_task(coro: Awaitable[None]) -> None:
    task = asyncio.create_task(coro)
    BACKGROUND_TASKS.add(task)

    def _on_done(completed: asyncio.Task) -> None:
        BACKGROUND_TASKS.discard(completed)
        try:
            completed.result()
        except Exception as e:
            logger.warning("Background task failed: %s", e)

    task.add_done_callback(_on_done)


async def _finalize_chat_response(
    pool,
    user_id: str,
    conversation_id: str,
    user_message: str,
    assistant_message: str,
    is_new_conversation: bool,
) -> None:
    if is_new_conversation:
        try:
            title = await generate_title(user_message)
            await update_conversation_title(pool, conversation_id, title)
        except Exception as e:
            logger.warning("Title generation failed: %s", e)

    await _persist_long_term_context(
        pool,
        user_id,
        conversation_id,
        [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ],
    )


# ── Health ──

@router.get("/health")
async def health():
    return {"status": "ok"}


# ── Auth Endpoints ──

@router.post("/auth/signup")
async def signup(body: SignupRequest, request: Request):
    pool = request.app.state.db_pool

    if not EMAIL_REGEX.match(body.email):
        raise HTTPException(400, "Invalid email format")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    existing = await get_user_by_email(pool, body.email.lower())
    if existing:
        raise HTTPException(409, "Email already registered")

    user = await create_user(pool, body.email.lower(), hash_password(body.password))
    return await _create_token_pair(pool, str(user["id"]), user["email"])


@router.post("/auth/login")
async def login(body: LoginRequest, request: Request):
    pool = request.app.state.db_pool

    user = await get_user_by_email(pool, body.email.lower())
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    return await _create_token_pair(pool, str(user["id"]), user["email"])


@router.post("/auth/refresh")
async def refresh(body: RefreshRequest, request: Request):
    pool = request.app.state.db_pool

    token_hash = hash_refresh_token(body.refresh_token)
    session = await get_session_by_token_hash(pool, token_hash)
    if not session:
        raise HTTPException(401, "Invalid refresh token")

    if session["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        await delete_session(pool, str(session["id"]))
        raise HTTPException(401, "Refresh token expired")

    # Token rotation: delete old session, create new one
    await delete_session(pool, str(session["id"]))

    user_id = str(session["user_id"])
    # Fetch user email for response
    user_row = await pool.fetchrow("SELECT email FROM users WHERE id = $1", session["user_id"])
    if not user_row:
        raise HTTPException(401, "User not found")

    return await _create_token_pair(pool, user_id, user_row["email"])


@router.post("/auth/logout")
async def logout(body: LogoutRequest, request: Request, user: dict = Depends(get_current_user)):
    pool = request.app.state.db_pool
    token_hash = hash_refresh_token(body.refresh_token)
    await delete_user_session_by_token(pool, user["user_id"], token_hash)
    return {"status": "ok"}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["user_id"], "email": user["email"]}


# ── Chat ──

@router.post("/chat")
async def chat(body: ChatRequest, request: Request, user: dict = Depends(get_current_user)):
    pool = request.app.state.db_pool
    user_id = user["user_id"]

    # Resolve or create conversation
    is_new_conversation = False
    if body.conversation_id:
        if not await verify_conversation_ownership(pool, body.conversation_id, user_id):
            raise HTTPException(403, "Not your conversation")
        conversation_id = body.conversation_id
    else:
        conv = await create_conversation(pool, user_id)
        conversation_id = str(conv["id"])
        is_new_conversation = True

    try:
        await save_message(pool, conversation_id, "user", body.message)
        history = await get_messages(pool, conversation_id)
        recent_summaries = await get_recent_conversation_summaries(
            pool,
            user_id,
            exclude_conversation_id=conversation_id,
            limit=3,
        )
    except Exception as e:
        logger.exception("Failed to process chat request")
        return {"error": str(e)}

    # Search memories scoped to user (not conversation)
    memories_context = search_memories(body.message, user_id)
    summaries_context = format_recent_summaries(recent_summaries)

    async def event_stream():
        full_response = ""
        try:
            async for token in stream_chat_response(history, memories_context, summaries_context):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        if full_response:
            saved = await save_message(pool, conversation_id, "assistant", full_response)
            yield f"data: {json.dumps({'done': True, 'message_id': str(saved['id']), 'conversation_id': conversation_id})}\n\n"
            _schedule_background_task(
                _finalize_chat_response(
                    pool,
                    user_id,
                    conversation_id,
                    body.message,
                    full_response,
                    is_new_conversation,
                )
            )
        else:
            yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Conversations ──

@router.get("/conversations")
async def list_conversations(request: Request, user: dict = Depends(get_current_user)):
    pool = request.app.state.db_pool
    conversations = await get_user_conversations(pool, user["user_id"])
    return {
        "conversations": [
            {
                "id": str(c["id"]),
                "title": c["title"],
                "created_at": c["created_at"].isoformat(),
                "updated_at": c["updated_at"].isoformat(),
            }
            for c in conversations
        ]
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str, request: Request, user: dict = Depends(get_current_user)
):
    pool = request.app.state.db_pool
    if not await verify_conversation_ownership(pool, conversation_id, user["user_id"]):
        raise HTTPException(403, "Not your conversation")

    messages = await get_messages(pool, conversation_id)
    return {"messages": messages}
