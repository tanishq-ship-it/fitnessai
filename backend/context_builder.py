from __future__ import annotations

import json
from typing import Any


def limit_messages_for_context(messages: list[dict], max_messages: int) -> list[dict]:
    if max_messages <= 0 or len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


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
            lines.append("Key points:\n" + "\n".join(f"- {point}" for point in key_points[:5]))

        if summary.get("next_steps"):
            lines.append(f"Next steps: {summary['next_steps']}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def format_profile_context(profile: dict[str, Any] | None) -> str:
    if not profile:
        return ""

    profile_data = profile.get("profile_json") or {}
    if not isinstance(profile_data, dict):
        return ""

    lines: list[str] = []
    for key in (
        "goal",
        "diet_type",
        "country",
        "height_cm",
        "weight_kg",
        "age",
        "sex",
        "experience_level",
        "activity_level",
        "workout_days_per_week",
        "preferred_workout_time",
        "sleep_hours_target",
    ):
        value = profile_data.get(key)
        if value not in (None, "", []):
            lines.append(f"- {key}: {value}")

    for key in ("equipment_access", "injuries", "limitations", "notes"):
        values = profile_data.get(key)
        if isinstance(values, list) and values:
            lines.append(f"- {key}: {', '.join(str(item) for item in values[:6])}")

    return "\n".join(lines)


def format_events_context(events: list[dict]) -> str:
    if not events:
        return ""

    lines: list[str] = []
    for event in events:
        event_type = event.get("event_type") or "event"
        summary = event.get("summary") or ""
        details = event.get("details_json") or {}

        line = f"- {event_type}: {summary}".strip()
        compact_details = _compact_json(details)
        if compact_details:
            line += f" | details: {compact_details}"
        lines.append(line)

    return "\n".join(lines)


def format_follow_up_state_context(state: dict[str, Any] | None) -> str:
    if not state:
        return ""

    missing_fields = state.get("missing_fields_json") or []
    if not isinstance(missing_fields, list):
        missing_fields = []

    lines: list[str] = []
    if state.get("pending_question"):
        lines.append(f"- pending_question: {state['pending_question']}")
    if missing_fields:
        lines.append(f"- missing_fields: {', '.join(str(item) for item in missing_fields)}")
    if state.get("last_asked_at"):
        lines.append(f"- last_asked_at: {state['last_asked_at']}")

    return "\n".join(lines)


def format_memory_context(results: dict[str, Any] | None) -> tuple[str, str]:
    if not results:
        return "", ""

    memories = results.get("results", [])
    relations = results.get("relations", [])

    memory_lines = [
        f"- {item['memory']}"
        for item in memories
        if isinstance(item, dict) and item.get("memory")
    ]
    relation_lines = []
    for relation in relations:
        if not isinstance(relation, dict):
            continue
        source = _stringify_relation_endpoint(
            relation.get("source") or relation.get("source_node") or relation.get("from")
        )
        edge = _stringify_relation_endpoint(
            relation.get("relationship")
            or relation.get("relation")
            or relation.get("type")
            or relation.get("edge")
        )
        target = _stringify_relation_endpoint(
            relation.get("destination") or relation.get("destination_node") or relation.get("to")
        )
        if source and edge and target:
            relation_lines.append(f"- {source} {edge} {target}")

    return "\n".join(memory_lines), "\n".join(relation_lines)


def _stringify_relation_endpoint(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("name", "id", "label", "type"):
            if value.get(key):
                return str(value[key])
        return ""
    return str(value).strip() if value is not None else ""


def _compact_json(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    try:
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    except TypeError:
        return str(value)
