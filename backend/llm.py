import json
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
Here is what you remember about this user from previous messages:
{memories}

Use this context to personalize your response. Don't mention that you're recalling memories."""


def build_system_prompt(memories_context: str = "") -> str:
    if memories_context:
        return SYSTEM_PROMPT_BASE + MEMORIES_SECTION.format(memories=memories_context)
    return SYSTEM_PROMPT_BASE

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
) -> AsyncGenerator[str, None]:
    """Stream tokens from OpenRouter. Yields content strings as they arrive."""

    system_prompt = build_system_prompt(memories_context)

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
