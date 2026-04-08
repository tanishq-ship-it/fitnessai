import json
import re
from typing import Any
from collections.abc import AsyncGenerator

import httpx

from config import settings

SYSTEM_PROMPT_BASE = """You are FitnessAI, an expert fitness coach and nutritionist. You give clear, actionable advice about workouts, nutrition, recovery, and general health.

Guidelines:
- Be concise but thorough. Use bullet points and bold text for structure.
- Ask clarifying questions when the user's goal or situation is unclear.
- Always prioritize safety — recommend consulting a doctor for injuries or medical conditions.
- Be motivating and supportive, never judgmental.
- When giving workout plans, specify sets, reps, and rest periods.
- When giving nutrition advice, include specific amounts (grams of protein, calories, etc.)."""

MEMORIES_SECTION = """
Here is what you remember about this user from previous messages and linked facts:
{memories}

Use this context to personalize your response. Treat linked facts as stable context when they are relevant. Don't mention that you're recalling memories."""

SUMMARIES_SECTION = """
Here are concise summaries of recent earlier conversations with this user:
{summaries}

Use these summaries when the user asks what was discussed previously, what plan they were following, how they were progressing, or what to do next. Prefer the most recent relevant summary. Don't mention that you're reading stored summaries."""

VISION_SECTION = """
The user attached an image. Here is a compact analysis of what is visible:
{vision_context}

Use this to answer naturally. Treat uncertain observations as uncertain. Don't mention internal analysis, prompts, or model steps."""


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


def build_system_prompt(
    memories_context: str = "",
    summaries_context: str = "",
    vision_context: str = "",
) -> str:
    prompt = SYSTEM_PROMPT_BASE
    if vision_context:
        prompt += VISION_SECTION.format(vision_context=vision_context)
    if summaries_context:
        prompt += SUMMARIES_SECTION.format(summaries=summaries_context)
    if memories_context:
        prompt += MEMORIES_SECTION.format(memories=memories_context)
    return prompt

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def generate_title(user_message: str) -> str:
    """Generate a 1-3 word conversation title from the user's first message."""
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Generate a short title (1-3 words max) for a chat conversation based on the user's message. Reply with ONLY the title, nothing else. No quotes, no punctuation, no explanation.",
            },
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "max_tokens": 15,
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            title = data["choices"][0]["message"]["content"].strip()
            # Clean up: remove quotes, limit length
            title = title.strip('"\'').strip()
            # Cap at 3 words
            words = title.split()
            return " ".join(words[:3]) if words else "New Chat"
    except Exception:
        return "New Chat"


async def stream_chat_response(
    messages: list[dict],
    memories_context: str = "",
    summaries_context: str = "",
    vision_context: str = "",
) -> AsyncGenerator[str, None]:
    """Stream tokens from OpenRouter. Yields content strings as they arrive."""

    system_prompt = build_system_prompt(memories_context, summaries_context, vision_context)

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": True,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", OPENROUTER_URL, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    token = chunk["choices"][0]["delta"].get("content", "")
                    if token:
                        yield token
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


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
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
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


def format_recent_summaries(summaries: list[dict]) -> str:
    if not summaries:
        return ""

    blocks: list[str] = []
    for idx, summary in enumerate(summaries, start=1):
        lines = [f"Conversation {idx}: {summary.get('title') or 'Untitled chat'}"]
        if summary.get("summary"):
            lines.append(f"Summary: {summary['summary']}")

        key_points = [point for point in summary.get("key_points", []) if point]
        if key_points:
            lines.append("Key points:\n" + "\n".join(f"- {point}" for point in key_points))

        if summary.get("next_steps"):
            lines.append(f"Next steps: {summary['next_steps']}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


async def generate_conversation_summary(
    messages: list[dict],
    previous_summary: str = "",
) -> dict:
    """Generate a durable summary for cross-conversation recall."""

    transcript = "\n".join(
        f"{message['role'].upper()}: {message['content']}"
        for message in messages[-40:]
    )

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You create durable conversation summaries for a long-term fitness coach memory system. "
                    "Return strict JSON with keys: summary (string), key_points (array of strings), next_steps (string). "
                    "Preserve what the user asked, the constraints/preferences/injuries/goals that matter, "
                    "what advice or plan was given, and what the user should do next. Keep it concise but useful."
                ),
            },
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
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"summary": content, "key_points": [], "next_steps": ""}

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
