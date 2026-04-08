import json
import re
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from config import settings
from prompts.artifacts import ARTIFACT_PROMPTS
from prompts.extraction import COACHING_EXTRACTION_PROMPT
from prompts.planner import PLANNER_PROMPT
from prompts.summary import SUMMARY_PROMPT
from prompts.system import build_chat_system_prompt

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

VISION_ANALYSIS_PROMPT = """You are analyzing a single user image for a fitness coaching assistant.

First, identify the image type as one of:
- meal
- progress
- form_check
- unclear

Return valid JSON only with this exact shape:
{
  "category": "meal|progress|form_check|unclear",
  "summary": "short plain-text summary",
  "observations": ["string"],
  "uncertainties": ["string"],
  "memory_candidates": ["string"]
}

Rules:
- Focus only on what is visibly supported by the image.
- If the user also provided text, use it only to guide the analysis.
- For meals, describe likely foods and visible portion clues. Do not guess exact calories unless clearly approximate.
- For progress photos, describe visible posture or physique observations carefully. Never guess exact body-fat percentage.
- For form checks, identify the likely movement and visible mechanics or safety cues.
- Keep memory_candidates extremely strict. Include only stable, durable user facts worth remembering long-term. If unsure, return [].
- Do not include markdown fences or extra commentary."""


async def generate_title(user_message: str) -> str:
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Generate a short title (1-3 words max) for a chat conversation based on the "
                    "user's message. Reply with ONLY the title, nothing else. No quotes, no punctuation."
                ),
            },
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "max_tokens": 15,
        "temperature": 0.2,
    }
    try:
        content = await _fetch_text_completion(payload, timeout=15.0)
        title = content.strip().strip('"\'').strip()
        words = title.split()
        return " ".join(words[:3]) if words else "New Chat"
    except Exception:
        return "New Chat"


async def stream_chat_response(
    *,
    messages: list[dict],
    system_prompt: str,
    max_tokens: int,
    model: str | None = None,
    temperature: float = 0.4,
) -> AsyncGenerator[dict[str, Any], None]:
    payload = {
        "model": model or settings.OPENROUTER_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": True,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        async with client.stream("POST", OPENROUTER_URL, json=payload, headers=_headers()) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                usage = chunk.get("usage")
                if usage:
                    yield {
                        "type": "usage",
                        "usage": usage,
                        "model": chunk.get("model", payload["model"]),
                    }

                choices = chunk.get("choices") or []
                if not choices:
                    continue

                delta = choices[0].get("delta") or {}
                token = delta.get("content", "")
                if token:
                    yield {"type": "token", "token": token}


async def plan_chat_turn(
    *,
    latest_user_message: str,
    recent_messages: list[dict],
    profile_context: str = "",
    memories_context: str = "",
    relations_context: str = "",
    summaries_context: str = "",
    follow_up_state_context: str = "",
    vision_context: str = "",
) -> dict[str, Any]:
    transcript = _format_transcript(recent_messages)
    user_prompt = (
        f"Latest user message:\n{latest_user_message or '[Empty message]'}\n\n"
        f"Recent conversation:\n{transcript or 'None'}\n\n"
        f"Known profile:\n{profile_context or 'None'}\n\n"
        f"Relevant memories:\n{memories_context or 'None'}\n\n"
        f"Relevant relations:\n{relations_context or 'None'}\n\n"
        f"Earlier summaries:\n{summaries_context or 'None'}\n\n"
        f"Clarification state:\n{follow_up_state_context or 'None'}\n\n"
        f"Image context:\n{vision_context or 'None'}"
    )

    payload = {
        "model": _planner_model(),
        "messages": [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "max_tokens": settings.CHAT_PLANNER_MAX_TOKENS,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        content = await _fetch_text_completion(payload, timeout=25.0)
        parsed = _extract_json_object(content)
        return _normalize_plan(parsed, latest_user_message)
    except Exception:
        return _default_plan(latest_user_message)


async def extract_coaching_state(
    *,
    recent_messages: list[dict],
    assistant_message: str,
    profile_context: str = "",
    vision_context: str = "",
) -> dict[str, Any]:
    transcript = _format_transcript(recent_messages)
    payload = {
        "model": _extraction_model(),
        "messages": [
            {"role": "system", "content": COACHING_EXTRACTION_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current profile:\n{profile_context or 'None'}\n\n"
                    f"Recent conversation:\n{transcript or 'None'}\n\n"
                    f"Assistant reply:\n{assistant_message}\n\n"
                    f"Image context:\n{vision_context or 'None'}"
                ),
            },
        ],
        "stream": False,
        "max_tokens": settings.CHAT_EXTRACTION_MAX_TOKENS,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        content = await _fetch_text_completion(payload, timeout=30.0)
        parsed = _extract_json_object(content)
        return _normalize_extraction(parsed)
    except Exception:
        return _default_extraction()


def build_chat_prompt(
    *,
    plan: dict[str, Any],
    profile_context: str = "",
    events_context: str = "",
    follow_up_state_context: str = "",
    memories_context: str = "",
    relations_context: str = "",
    summaries_context: str = "",
    vision_context: str = "",
) -> str:
    return build_chat_system_prompt(
        response_mode=plan.get("response_mode", "brief_answer"),
        intent=plan.get("intent", "other"),
        should_ask_followup=bool(plan.get("should_ask_followup")),
        followup_question=plan.get("followup_question", ""),
        missing_fields=plan.get("missing_fields", []),
        profile_context=profile_context,
        events_context=events_context,
        follow_up_state_context=follow_up_state_context,
        memories_context=memories_context,
        relations_context=relations_context,
        summaries_context=summaries_context,
        vision_context=vision_context,
    )


def build_artifact_prompt(
    artifact_type: str,
    *,
    plan: dict[str, Any],
    profile_context: str = "",
    events_context: str = "",
    follow_up_state_context: str = "",
    memories_context: str = "",
    relations_context: str = "",
    summaries_context: str = "",
    vision_context: str = "",
) -> str:
    base_prompt = build_chat_prompt(
        plan={**plan, "response_mode": "artifact"},
        profile_context=profile_context,
        events_context=events_context,
        follow_up_state_context=follow_up_state_context,
        memories_context=memories_context,
        relations_context=relations_context,
        summaries_context=summaries_context,
        vision_context=vision_context,
    )
    extra = ARTIFACT_PROMPTS.get(artifact_type, "")
    return f"{base_prompt}\n\n{extra}".strip()


async def generate_conversation_summary(
    messages: list[dict],
    previous_summary: str = "",
) -> dict[str, Any]:
    transcript = _format_transcript(messages[-40:])
    payload = {
        "model": _planner_model(),
        "messages": [
            {"role": "system", "content": SUMMARY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Previous summary:\n{previous_summary or 'None'}\n\n"
                    f"Conversation transcript:\n{transcript}\n\n"
                    'Return only valid JSON like {"summary":"...","key_points":["..."],"next_steps":"..."}'
                ),
            },
        ],
        "stream": False,
        "max_tokens": 400,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    try:
        content = await _fetch_text_completion(payload, timeout=20.0)
        parsed = _extract_json_object(content)
    except Exception:
        parsed = {"summary": "", "key_points": [], "next_steps": ""}

    summary = str(parsed.get("summary", "")).strip()
    key_points_raw = parsed.get("key_points", [])
    if not isinstance(key_points_raw, list):
        key_points_raw = []
    key_points = [str(point).strip() for point in key_points_raw if str(point).strip()]
    next_steps = str(parsed.get("next_steps", "")).strip()

    return {
        "summary": summary,
        "key_points": key_points,
        "next_steps": next_steps,
    }


async def analyze_image_input(image_data_url: str, user_message: str = "") -> dict[str, Any]:
    guidance = user_message.strip() or "Analyze this image for a fitness coaching chat."

    payload = {
        "model": settings.OPENROUTER_VISION_MODEL,
        "messages": [
            {"role": "system", "content": VISION_ANALYSIS_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": guidance},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
        "stream": False,
        "max_tokens": 500,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(OPENROUTER_URL, json=payload, headers=_headers())
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

    parsed = _extract_json_object(content)
    category = str(parsed.get("category", "unclear")).strip().lower()
    if category not in {"meal", "progress", "form_check", "unclear"}:
        category = "unclear"

    return {
        "category": category,
        "summary": str(parsed.get("summary", "")).strip(),
        "observations": _coerce_string_list(parsed.get("observations")),
        "uncertainties": _coerce_string_list(parsed.get("uncertainties")),
        "memory_candidates": _coerce_string_list(parsed.get("memory_candidates")),
    }


def format_vision_context(analysis: dict[str, Any] | None) -> str:
    if not analysis:
        return ""

    lines = [f"Image type: {analysis.get('category', 'unclear')}"]

    summary = str(analysis.get("summary", "")).strip()
    if summary:
        lines.append(f"Summary: {summary}")

    observations = _coerce_string_list(analysis.get("observations"))
    if observations:
        lines.append("Observations:\n" + "\n".join(f"- {item}" for item in observations))

    uncertainties = _coerce_string_list(analysis.get("uncertainties"))
    if uncertainties:
        lines.append("Uncertainties:\n" + "\n".join(f"- {item}" for item in uncertainties))

    return "\n".join(lines)


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _normalize_plan(parsed: dict[str, Any], latest_user_message: str) -> dict[str, Any]:
    plan = _default_plan(latest_user_message)

    intent = str(parsed.get("intent", "")).strip()
    if intent:
        plan["intent"] = intent

    response_mode = str(parsed.get("response_mode", "")).strip()
    if response_mode in {"brief_answer", "brief_answer_plus_one_question", "question_only", "artifact"}:
        plan["response_mode"] = response_mode

    plan["should_ask_followup"] = bool(parsed.get("should_ask_followup"))
    plan["followup_question"] = str(parsed.get("followup_question", "")).strip()
    plan["missing_fields"] = _coerce_string_list(parsed.get("missing_fields"))
    plan["memory_query"] = str(parsed.get("memory_query", "")).strip() or latest_user_message.strip()
    plan["memory_categories"] = _coerce_string_list(parsed.get("memory_categories"))

    artifact_type = str(parsed.get("artifact_type", "none")).strip()
    if artifact_type in {"none", "training_plan", "macro_targets", "weekly_focus", "progress_summary", "phase_plan"}:
        plan["artifact_type"] = artifact_type
    plan["reason"] = str(parsed.get("reason", "")).strip()

    if plan["response_mode"] == "artifact" and plan["artifact_type"] == "none":
        plan["artifact_type"] = "training_plan"

    if not plan["should_ask_followup"]:
        plan["followup_question"] = ""
        plan["missing_fields"] = []

    return plan


def _default_plan(latest_user_message: str) -> dict[str, Any]:
    message = latest_user_message.lower()
    artifact_type = "none"
    response_mode = "brief_answer"
    if any(term in message for term in ("plan", "split", "macro", "calories", "summary", "phase")):
        response_mode = "artifact"
        if "macro" in message or "calorie" in message:
            artifact_type = "macro_targets"
        elif "weekly" in message:
            artifact_type = "weekly_focus"
        elif "summary" in message or "progress" in message:
            artifact_type = "progress_summary"
        elif "phase" in message:
            artifact_type = "phase_plan"
        else:
            artifact_type = "training_plan"

    return {
        "intent": "other",
        "response_mode": response_mode,
        "should_ask_followup": False,
        "followup_question": "",
        "missing_fields": [],
        "memory_query": latest_user_message.strip(),
        "memory_categories": [],
        "artifact_type": artifact_type,
        "reason": "",
    }


def _normalize_extraction(parsed: dict[str, Any]) -> dict[str, Any]:
    normalized = _default_extraction()

    profile_updates = parsed.get("profile_updates", {})
    if isinstance(profile_updates, dict):
        normalized["profile_updates"] = profile_updates

    events = parsed.get("events", [])
    if isinstance(events, list):
        normalized["events"] = [
            {
                "event_type": str(event.get("event_type", "")).strip(),
                "summary": str(event.get("summary", "")).strip(),
                "event_time": _coerce_datetime_string(event.get("event_time")),
                "details": event.get("details", {}) if isinstance(event.get("details", {}), dict) else {},
            }
            for event in events
            if isinstance(event, dict) and str(event.get("event_type", "")).strip()
        ]

    memory_entries = parsed.get("memory_entries", [])
    if isinstance(memory_entries, list):
        normalized["memory_entries"] = [
            {
                "text": str(entry.get("text", "")).strip(),
                "category": str(entry.get("category", "")).strip(),
                "enable_graph": bool(entry.get("enable_graph", True)),
            }
            for entry in memory_entries
            if isinstance(entry, dict) and str(entry.get("text", "")).strip()
        ]

    proactive_signals = parsed.get("proactive_signals", [])
    if isinstance(proactive_signals, list):
        normalized["proactive_signals"] = [
            {
                "signal_type": str(signal.get("signal_type", "")).strip(),
                "summary": str(signal.get("summary", "")).strip(),
                "score": _coerce_float(signal.get("score")),
            }
            for signal in proactive_signals
            if isinstance(signal, dict) and str(signal.get("signal_type", "")).strip()
        ]

    return normalized


def _default_extraction() -> dict[str, Any]:
    return {
        "profile_updates": {},
        "events": [],
        "memory_entries": [],
        "proactive_signals": [],
    }


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_datetime_string(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }


async def _fetch_text_completion(payload: dict[str, Any], *, timeout: float) -> str:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(OPENROUTER_URL, json=payload, headers=_headers())
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


def _planner_model() -> str:
    return settings.OPENROUTER_PLANNER_MODEL or settings.OPENROUTER_MODEL


def _extraction_model() -> str:
    return settings.OPENROUTER_EXTRACTION_MODEL or settings.OPENROUTER_PLANNER_MODEL or settings.OPENROUTER_MODEL


def _format_transcript(messages: list[dict]) -> str:
    return "\n".join(
        f"{str(message.get('role', 'user')).upper()}: {message.get('content', '')}"
        for message in messages
        if str(message.get("content", "")).strip()
    )
