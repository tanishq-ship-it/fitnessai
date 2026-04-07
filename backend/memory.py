import logging

from mem0 import Memory

from config import settings

logger = logging.getLogger(__name__)

memory = Memory.from_config({
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "connection_string": settings.DIRECT_URL,
            "collection_name": "memories",
            "embedding_model_dims": 1536,
            "hnsw": True,
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4.1-nano-2025-04-14",
            "api_key": settings.OPENAI_API_KEY,
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": settings.OPENAI_API_KEY,
        },
    },
})


def search_memories(query: str, user_id: str, limit: int = 5) -> str:
    """Search relevant memories and return formatted string for prompt injection."""
    try:
        results = memory.search(query=query, user_id=user_id, limit=limit)
        memories = results.get("results", [])
        if not memories:
            return ""
        return "\n".join(f"- {m['memory']}" for m in memories)
    except Exception as e:
        logger.warning("Memory search failed: %s", e)
        return ""


def store_memories(messages: list[dict], user_id: str) -> None:
    """Extract and store facts from a conversation exchange."""
    try:
        memory.add(messages, user_id=user_id)
    except Exception as e:
        logger.warning("Memory store failed: %s", e)
