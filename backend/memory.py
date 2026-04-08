import logging
from typing import Any

from mem0 import Memory

from config import settings

logger = logging.getLogger(__name__)

# Pre-import OpenAI resource modules to avoid Python 3.14 import deadlocks when
# Mem0 runs concurrent embedding and chat calls on the first memory search.
try:
    import openai.resources.chat  # noqa: F401
    import openai.resources.embeddings  # noqa: F401
except Exception:
    pass

GRAPH_MEMORY_PROMPT = """
Extract only stable user fitness facts and relationships that will improve future coaching.

Prioritize:
- goals and desired outcomes
- injuries, pain points, and movement limitations
- exercise, equipment, and training preferences
- schedule and availability
- nutrition preferences and dietary constraints
- measurable stats such as weight, calorie targets, and protein targets

Use only facts explicitly stated by the user. Ignore assistant-generated text, greetings, filler, encouragement, and conversational small talk.

Relationship types must be short, general, and Neo4j-safe:
- use UPPERCASE_SNAKE_CASE only
- ASCII letters, numbers, and underscores only
- never output full sentences, punctuation, or emoji as relationship names

Examples:
- USER_ID HAS_NAME TANISHQ
- USER_ID PREFERS_WORKOUT_TIME MORNING
- USER_ID PREFERS_EQUIPMENT DUMBBELLS
- USER_ID HAS_INJURY LEFT_KNEE_PAIN

Avoid one-off conversational details unless they describe an ongoing constraint, routine, or preference.
""".strip()

def _build_base_config() -> dict[str, Any]:
    return {
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
    }


def _build_graph_store_config() -> dict[str, Any] | None:
    if not (settings.NEO4J_URI and settings.NEO4J_USERNAME and settings.NEO4J_PASSWORD):
        return None

    graph_config: dict[str, Any] = {
        "provider": "neo4j",
        "custom_prompt": GRAPH_MEMORY_PROMPT,
        "threshold": 0.75,
        "config": {
            "url": settings.NEO4J_URI,
            "username": settings.NEO4J_USERNAME,
            "password": settings.NEO4J_PASSWORD,
        },
    }
    if settings.NEO4J_DATABASE:
        graph_config["config"]["database"] = settings.NEO4J_DATABASE

    return graph_config


def _create_memory_client() -> tuple[Memory, bool]:
    base_config = _build_base_config()
    graph_store_config = _build_graph_store_config()

    if graph_store_config:
        graph_config = {**base_config, "graph_store": graph_store_config}
        try:
            logger.info("Initializing Mem0 with Neo4j graph memory")
            return Memory.from_config(graph_config), True
        except Exception as e:
            logger.warning(
                "Mem0 graph memory initialization failed, falling back to vector-only memory: %s",
                e,
            )

    logger.info("Initializing Mem0 with vector-only memory")
    return Memory.from_config(base_config), False


def _stringify_relation_value(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("name", "id", "label", "type"):
            if value.get(key):
                return str(value[key])
        return str(value)
    return str(value)


def _format_relation(relation: dict[str, Any]) -> str | None:
    source = relation.get("source") or relation.get("source_node") or relation.get("from")
    destination = relation.get("destination") or relation.get("destination_node") or relation.get("to")
    relationship = (
        relation.get("relationship")
        or relation.get("relation")
        or relation.get("type")
        or relation.get("edge")
    )

    if not (source and destination and relationship):
        return None

    return (
        f"- {_stringify_relation_value(source)} "
        f"{_stringify_relation_value(relationship)} "
        f"{_stringify_relation_value(destination)}"
    )


memory, GRAPH_MEMORY_ENABLED = _create_memory_client()


def search_memories(query: str, user_id: str, limit: int = 5) -> str:
    """Search relevant memories and graph relations for prompt injection."""
    try:
        results = memory.search(query=query, user_id=user_id, limit=limit)
        memories = results.get("results", [])
        relations = results.get("relations", []) if GRAPH_MEMORY_ENABLED else []

        sections: list[str] = []
        if memories:
            sections.append(
                "Relevant memories:\n"
                + "\n".join(f"- {m['memory']}" for m in memories if m.get("memory"))
            )

        formatted_relations = [
            formatted
            for relation in relations
            if (formatted := _format_relation(relation)) is not None
        ]
        if formatted_relations:
            sections.append("Related facts:\n" + "\n".join(formatted_relations))

        return "\n\n".join(sections)
    except Exception as e:
        logger.warning("Memory search failed: %s", e)
        return ""


def store_memories(messages: list[dict], user_id: str) -> None:
    """Extract and store facts from a conversation exchange."""
    try:
        # Only persist user-authored facts. Passing assistant text into graph extraction
        # produced noisy relationship labels and invalid Neo4j relationship names.
        user_messages = [
            {"role": "user", "content": message["content"]}
            for message in messages
            if message.get("role") == "user" and message.get("content", "").strip()
        ]
        if not user_messages:
            return

        memory.add(user_messages, user_id=user_id)
    except Exception as e:
        logger.warning("Memory store failed: %s", e)


def store_image_memory_facts(facts: list[str], user_id: str) -> None:
    """Persist only durable image-derived user facts."""
    try:
        filtered_facts: list[dict[str, str]] = []
        blocked_phrases = (
            "maybe",
            "might",
            "possibly",
            "appears",
            "looks like",
            "seems",
            "unclear",
            "not sure",
        )

        for fact in facts:
            cleaned = str(fact).strip()
            if not cleaned:
                continue

            lowered = cleaned.lower()
            if any(phrase in lowered for phrase in blocked_phrases):
                continue

            filtered_facts.append({"role": "user", "content": cleaned})

        if not filtered_facts:
            return

        memory.add(filtered_facts, user_id=user_id)
    except Exception as e:
        logger.warning("Image memory store failed: %s", e)
