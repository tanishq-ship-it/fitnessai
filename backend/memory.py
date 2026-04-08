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


def search_memories(
    query: str,
    user_id: str,
    *,
    limit: int = 5,
    categories: list[str] | None = None,
    rerank: bool = False,
    enable_graph: bool | None = None,
) -> dict[str, Any]:
    """Search relevant memories and graph relations with optional filters."""
    if not query.strip():
        return {"results": [], "relations": []}

    search_kwargs: dict[str, Any] = {"query": query, "user_id": user_id, "limit": limit}
    if categories:
        normalized = [category for category in (_normalize_category(item) for item in categories) if category]
        if normalized:
            search_kwargs["filters"] = {"category": {"in": normalized}}
    if rerank:
        search_kwargs["rerank"] = True
    if enable_graph is None:
        enable_graph = GRAPH_MEMORY_ENABLED
    search_kwargs["enable_graph"] = enable_graph

    try:
        results = _run_memory_search(search_kwargs)
        memories = results.get("results", []) if isinstance(results, dict) else []
        relations = results.get("relations", []) if isinstance(results, dict) else []
        return {
            "results": memories if isinstance(memories, list) else [],
            "relations": relations if isinstance(relations, list) else [],
        }
    except Exception as e:
        logger.warning("Memory search failed: %s", e)
        return {"results": [], "relations": []}


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


def store_memory_entries(entries: list[dict[str, Any]], user_id: str) -> None:
    """Store curated durable memories with optional category metadata."""
    for entry in entries:
        text = str(entry.get("text", "")).strip()
        if not text:
            continue

        metadata = {}
        category = _normalize_category(entry.get("category"))
        if category:
            metadata["category"] = category

        payload = [{"role": "user", "content": text}]
        add_kwargs: dict[str, Any] = {"user_id": user_id}
        if metadata:
            add_kwargs["metadata"] = metadata
        if GRAPH_MEMORY_ENABLED:
            add_kwargs["enable_graph"] = bool(entry.get("enable_graph", True))

        try:
            memory.add(payload, **add_kwargs)
        except TypeError:
            add_kwargs.pop("metadata", None)
            add_kwargs.pop("enable_graph", None)
            try:
                memory.add(payload, **add_kwargs)
            except Exception as e:
                logger.warning("Curated memory store failed: %s", e)
        except Exception as e:
            logger.warning("Curated memory store failed: %s", e)


def store_image_memory_facts(facts: list[str], user_id: str) -> None:
    """Persist only durable image-derived user facts."""
    try:
        filtered_facts: list[dict[str, Any]] = []
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

            filtered_facts.append(
                {
                    "text": cleaned,
                    "category": "progress",
                    "enable_graph": True,
                }
            )

        if not filtered_facts:
            return

        store_memory_entries(filtered_facts, user_id)
    except Exception as e:
        logger.warning("Image memory store failed: %s", e)


def _normalize_category(value: Any) -> str:
    cleaned = str(value or "").strip().lower().replace(" ", "_")
    if not cleaned:
        return ""
    return "".join(char for char in cleaned if char.isalnum() or char == "_")


def _run_memory_search(search_kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        results = memory.search(**search_kwargs)
        return results if isinstance(results, dict) else {"results": [], "relations": []}
    except TypeError:
        fallback_kwargs = {
            key: value
            for key, value in search_kwargs.items()
            if key not in {"filters", "rerank", "enable_graph"}
        }
        results = memory.search(**fallback_kwargs)
        return results if isinstance(results, dict) else {"results": [], "relations": []}
    except Exception:
        if search_kwargs.get("rerank"):
            fallback_kwargs = dict(search_kwargs)
            fallback_kwargs.pop("rerank", None)
            results = memory.search(**fallback_kwargs)
            return results if isinstance(results, dict) else {"results": [], "relations": []}
        raise
