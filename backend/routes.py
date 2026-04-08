import asyncio
import json
import logging
import re
from collections.abc import Awaitable
from datetime import datetime, timedelta, timezone
from typing import Any

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
from context_builder import (
    format_events_context,
    format_follow_up_state_context,
    format_memory_context,
    format_profile_context,
    format_recent_summaries,
    limit_messages_for_context,
)
from database import (
    create_conversation,
    create_coaching_artifact,
    create_coaching_metric,
    create_proactive_tasks,
    create_session,
    create_user,
    delete_session,
    delete_user_session_by_token,
    get_conversation_summary,
    get_follow_up_state,
    get_messages,
    get_open_proactive_tasks,
    get_recent_conversation_summaries,
    get_recent_coaching_events,
    get_session_by_token_hash,
    get_user_coaching_profile,
    get_user_by_email,
    get_user_conversations,
    save_message,
    clear_follow_up_state,
    insert_coaching_events,
    upsert_follow_up_state,
    upsert_user_coaching_profile,
    upsert_conversation_summary,
    update_conversation_title,
    verify_conversation_ownership,
)
from llm import (
    analyze_image_input,
    build_artifact_prompt,
    build_chat_prompt,
    extract_coaching_state,
    format_vision_context,
    generate_conversation_summary,
    generate_title,
    plan_chat_turn,
    stream_chat_response,
)
from memory import search_memories, store_image_memory_facts, store_memories, store_memory_entries
from config import settings

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
    message: str = ""
    conversation_id: str | None = None
    image_data_url: str | None = None


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
    assistant_message: str,
    plan: dict[str, Any],
    usage: dict[str, Any] | None,
    image_analysis: dict | None = None,
) -> None:
    history: list[dict] = []
    profile_row = await get_user_coaching_profile(pool, user_id)
    profile_context = format_profile_context(profile_row)
    vision_context = format_vision_context(image_analysis)

    try:
        history = await get_messages(pool, conversation_id)
        recent_history = limit_messages_for_context(history, settings.CHAT_HISTORY_WINDOW)
        extraction = await extract_coaching_state(
            recent_messages=recent_history,
            assistant_message=assistant_message,
            profile_context=profile_context,
            vision_context=vision_context,
        )
    except Exception as e:
        logger.warning("Coaching extraction failed: %s", e)
        extraction = {
            "profile_updates": {},
            "events": [],
            "memory_entries": [],
            "proactive_signals": [],
        }

    try:
        current_profile = profile_row.get("profile_json", {}) if profile_row else {}
        merged_profile = _merge_profile_data(current_profile, extraction.get("profile_updates", {}))
        if merged_profile != current_profile:
            await upsert_user_coaching_profile(pool, user_id, merged_profile)
    except Exception as e:
        logger.warning("Profile persistence failed: %s", e)

    events = _normalize_events(extraction.get("events", []))
    if events:
        try:
            await insert_coaching_events(pool, user_id, conversation_id, events)
        except Exception as e:
            logger.warning("Coaching event persistence failed: %s", e)

    memory_entries = extraction.get("memory_entries", [])
    try:
        if memory_entries:
            await asyncio.to_thread(store_memory_entries, memory_entries, user_id)
        else:
            await asyncio.to_thread(store_memories, exchange_messages, user_id)
    except Exception as e:
        logger.warning("Mem0 persistence failed: %s", e)

    if image_analysis:
        memory_candidates = image_analysis.get("memory_candidates", [])
        if memory_candidates:
            try:
                await asyncio.to_thread(store_image_memory_facts, memory_candidates, user_id)
            except Exception as e:
                logger.warning("Image memory persistence failed: %s", e)

    if plan.get("artifact_type") and plan.get("artifact_type") != "none":
        try:
            await create_coaching_artifact(
                pool,
                user_id,
                conversation_id,
                plan["artifact_type"],
                _artifact_title(plan["artifact_type"]),
                assistant_message,
                {
                    "intent": plan.get("intent"),
                    "response_mode": plan.get("response_mode"),
                },
            )
        except Exception as e:
            logger.warning("Artifact persistence failed: %s", e)

    try:
        if plan.get("should_ask_followup") and plan.get("followup_question"):
            await upsert_follow_up_state(
                pool,
                user_id,
                plan["followup_question"],
                plan.get("missing_fields", []),
                last_asked_at=datetime.now(timezone.utc),
            )
        elif extraction.get("profile_updates") or extraction.get("events") or extraction.get("memory_entries"):
            await clear_follow_up_state(pool, user_id, answered_at=datetime.now(timezone.utc))
    except Exception as e:
        logger.warning("Follow-up state persistence failed: %s", e)

    proactive_tasks = _build_proactive_tasks(extraction.get("proactive_signals", []))
    if proactive_tasks:
        try:
            await create_proactive_tasks(pool, user_id, conversation_id, proactive_tasks)
        except Exception as e:
            logger.warning("Proactive task persistence failed: %s", e)

    try:
        if not history:
            history = await get_messages(pool, conversation_id)
        summary_history = history.copy()
        image_summary = _format_image_summary_for_summary(image_analysis)
        if image_summary:
            insert_at = len(summary_history)
            if summary_history and summary_history[-1].get("role") == "assistant":
                insert_at -= 1
            summary_history.insert(insert_at, {"role": "user", "content": image_summary})
        existing_summary = await get_conversation_summary(pool, conversation_id)
        summary_payload = await generate_conversation_summary(
            summary_history,
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

    try:
        await create_coaching_metric(
            pool,
            user_id,
            conversation_id,
            "chat_turn",
            str((usage or {}).get("model", settings.OPENROUTER_MODEL)),
            {
                "plan": plan,
                "usage": usage or {},
                "event_count": len(events),
                "memory_entry_count": len(memory_entries),
            },
        )
    except Exception as e:
        logger.warning("Metric persistence failed: %s", e)


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
    title_seed: str,
    assistant_message: str,
    is_new_conversation: bool,
    plan: dict[str, Any],
    usage: dict[str, Any] | None,
    image_analysis: dict | None = None,
) -> None:
    if is_new_conversation:
        try:
            title = await generate_title(title_seed)
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
        assistant_message,
        plan,
        usage,
        image_analysis,
    )


def _format_user_message_for_storage(message: str, has_image: bool) -> str:
    text = message.strip()
    if has_image and text:
        return f"{text}\n\n[Image attached]"
    if has_image:
        return "[Image attached]"
    return text


def _build_memory_query(message: str, image_analysis: dict | None) -> str:
    text = message.strip()
    if text:
        return text
    if not image_analysis:
        return ""
    summary = str(image_analysis.get("summary", "")).strip()
    if summary:
        return summary
    observations = image_analysis.get("observations", [])
    return observations[0] if observations else ""


def _build_title_seed(message: str, image_analysis: dict | None) -> str:
    text = message.strip()
    if text:
        return text
    if not image_analysis:
        return "Image chat"
    category = str(image_analysis.get("category", "")).replace("_", " ").strip()
    return f"{category.title()} Check" if category else "Image chat"


def _format_image_summary_for_summary(image_analysis: dict | None) -> str:
    if not image_analysis:
        return ""

    parts = []
    category = str(image_analysis.get("category", "")).replace("_", " ").strip()
    if category:
        parts.append(f"Attached image type: {category}.")

    summary = str(image_analysis.get("summary", "")).strip()
    if summary:
        parts.append(f"Image summary: {summary}")

    observations = image_analysis.get("observations", [])
    if observations:
        parts.append("Image observations: " + "; ".join(observations[:3]))

    return " ".join(parts).strip()


def _merge_profile_data(existing: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(existing, dict):
        existing = {}
    if not isinstance(updates, dict):
        return existing

    merged = dict(existing)
    for key, value in updates.items():
        if value in ("", None, []):
            continue
        if isinstance(value, list):
            current = merged.get(key)
            if not isinstance(current, list):
                current = []
            merged[key] = _dedupe_strings([*current, *value])
        else:
            merged[key] = value
    return merged


def _dedupe_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        output.append(cleaned)
    return output


def _normalize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("event_type", "")).strip()
        summary = str(event.get("summary", "")).strip()
        if not event_type or not summary:
            continue
        normalized.append(
            {
                "event_type": event_type,
                "summary": summary,
                "event_time": _parse_event_time(event.get("event_time")),
                "details": event.get("details", {}) if isinstance(event.get("details", {}), dict) else {},
            }
        )
    return normalized


def _parse_event_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _artifact_title(artifact_type: str) -> str:
    titles = {
        "training_plan": "Training Plan",
        "macro_targets": "Macro Targets",
        "weekly_focus": "Weekly Focus",
        "progress_summary": "Progress Summary",
        "phase_plan": "Phase Plan",
    }
    return titles.get(artifact_type, "Coaching Artifact")


def _build_proactive_tasks(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for signal in signals:
        signal_type = str(signal.get("signal_type", "")).strip()
        summary = str(signal.get("summary", "")).strip()
        if not signal_type or not summary:
            continue
        due_at = None
        if signal_type in {"missed_workout", "low_adherence", "needs_checkin"}:
            due_at = now + timedelta(days=1)
        tasks.append(
            {
                "task_type": signal_type,
                "status": "open",
                "due_at": due_at,
                "summary": summary,
                "payload": {"score": signal.get("score", 0.0)},
            }
        )
    return tasks


def _event_types_for_intent(intent: str) -> list[str] | None:
    mapping = {
        "workout_log": ["workout", "adherence", "progress_note"],
        "meal_log": ["meal", "adherence", "progress_note"],
        "recovery_update": ["recovery", "adherence", "progress_note"],
        "progress_update": ["progress_note", "adherence", "workout", "meal"],
        "plan_request": ["workout", "recovery", "adherence", "progress_note"],
        "macro_request": ["meal", "adherence", "progress_note"],
        "summary_request": ["workout", "meal", "recovery", "adherence", "progress_note"],
    }
    return mapping.get(intent)


def _apply_followup_policy(full_response: str, plan: dict[str, Any]) -> str:
    response = full_response.strip()
    followup_question = str(plan.get("followup_question", "")).strip()
    if not followup_question:
        return response

    response_mode = str(plan.get("response_mode", "brief_answer")).strip()
    if response_mode == "question_only":
        return followup_question

    if plan.get("should_ask_followup") and followup_question.lower() not in response.lower():
        if response:
            return f"{response}\n\n{followup_question}"
        return followup_question

    return response


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
    message_text = body.message.strip()
    has_image = bool(body.image_data_url)

    if not message_text and not has_image:
        raise HTTPException(400, "Message or image is required")
    if has_image and not body.image_data_url.startswith("data:image/"):
        raise HTTPException(400, "Only image uploads are supported")
    if has_image and len(body.image_data_url) > 8_000_000:
        raise HTTPException(400, "Image is too large")

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

    vision_analysis = None
    if has_image:
        try:
            vision_analysis = await analyze_image_input(body.image_data_url, message_text)
        except Exception:
            logger.exception("Failed to analyze image input")
            raise HTTPException(502, "Image analysis failed")

    stored_user_message = _format_user_message_for_storage(message_text, has_image)
    memory_query = _build_memory_query(message_text, vision_analysis)
    title_seed = _build_title_seed(message_text, vision_analysis)

    try:
        await save_message(pool, conversation_id, "user", stored_user_message)
        history = await get_messages(pool, conversation_id)
        profile_row = await get_user_coaching_profile(pool, user_id)
        follow_up_state = await get_follow_up_state(pool, user_id)
        recent_summaries = await get_recent_conversation_summaries(
            pool,
            user_id,
            exclude_conversation_id=conversation_id,
            limit=3,
        )
        open_proactive_tasks = await get_open_proactive_tasks(pool, user_id, limit=3)
    except Exception as e:
        logger.exception("Failed to process chat request")
        return {"error": str(e)}

    recent_history = limit_messages_for_context(history, settings.CHAT_HISTORY_WINDOW)
    profile_context = format_profile_context(profile_row)
    follow_up_state_context = format_follow_up_state_context(follow_up_state)
    summaries_context = format_recent_summaries(recent_summaries)
    vision_context = format_vision_context(vision_analysis)

    planner_seed_results = search_memories(
        memory_query or stored_user_message,
        user_id,
        limit=min(settings.CHAT_MEMORIES_LIMIT, 4),
        rerank=False,
    )
    planner_memories_context, planner_relations_context = format_memory_context(planner_seed_results)

    plan = await plan_chat_turn(
        latest_user_message=stored_user_message,
        recent_messages=recent_history,
        profile_context=profile_context,
        memories_context=planner_memories_context,
        relations_context=planner_relations_context,
        summaries_context=summaries_context,
        follow_up_state_context=follow_up_state_context,
        vision_context=vision_context,
    )

    event_types = _event_types_for_intent(plan.get("intent", ""))
    recent_events = await get_recent_coaching_events(
        pool,
        user_id,
        event_types=event_types,
        limit=settings.CHAT_EVENTS_LIMIT,
    )
    events_context = format_events_context(recent_events)
    if open_proactive_tasks:
        task_lines = [
            f"- proactive_task: {task['task_type']} | {task['summary']}"
            for task in open_proactive_tasks
            if task.get("task_type") and task.get("summary")
        ]
        if task_lines:
            events_context = "\n".join([events_context, *task_lines]).strip()

    memory_results = search_memories(
        plan.get("memory_query") or memory_query or stored_user_message,
        user_id,
        limit=settings.CHAT_MEMORIES_LIMIT,
        categories=plan.get("memory_categories"),
        rerank=settings.CHAT_ENABLE_MEMORY_RERANK,
    )
    memories_context, relations_context = format_memory_context(memory_results)

    if plan.get("response_mode") == "artifact" and plan.get("artifact_type") != "none":
        system_prompt = build_artifact_prompt(
            plan["artifact_type"],
            plan=plan,
            profile_context=profile_context,
            events_context=events_context,
            follow_up_state_context=follow_up_state_context,
            memories_context=memories_context,
            relations_context=relations_context,
            summaries_context=summaries_context,
            vision_context=vision_context,
        )
        max_tokens = settings.CHAT_ARTIFACT_MAX_TOKENS
    else:
        system_prompt = build_chat_prompt(
            plan=plan,
            profile_context=profile_context,
            events_context=events_context,
            follow_up_state_context=follow_up_state_context,
            memories_context=memories_context,
            relations_context=relations_context,
            summaries_context=summaries_context,
            vision_context=vision_context,
        )
        max_tokens = 90 if plan.get("response_mode") == "question_only" else settings.CHAT_RESPONSE_MAX_TOKENS

    async def event_stream():
        full_response = ""
        usage: dict[str, Any] | None = None
        try:
            async for event in stream_chat_response(
                messages=recent_history,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
            ):
                if event.get("type") == "usage":
                    usage = {"model": event.get("model", settings.OPENROUTER_MODEL), **(event.get("usage") or {})}
                    continue
                token = str(event.get("token", ""))
                if token:
                    full_response += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        full_response = _apply_followup_policy(full_response, plan)

        if full_response:
            saved = await save_message(pool, conversation_id, "assistant", full_response)
            yield f"data: {json.dumps({'done': True, 'message_id': str(saved['id']), 'conversation_id': conversation_id})}\n\n"
            _schedule_background_task(
                _finalize_chat_response(
                    pool,
                    user_id,
                    conversation_id,
                    stored_user_message,
                    title_seed,
                    full_response,
                    is_new_conversation,
                    plan,
                    usage,
                    vision_analysis,
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
