COACHING_EXTRACTION_PROMPT = """You extract structured coaching state from a single chat exchange for a fitness coaching app.

Return valid JSON only with this exact shape:
{
  "profile_updates": {
    "goal": "",
    "diet_type": "",
    "country": "",
    "height_cm": null,
    "weight_kg": null,
    "age": null,
    "sex": "",
    "experience_level": "",
    "activity_level": "",
    "equipment_access": ["string"],
    "injuries": ["string"],
    "limitations": ["string"],
    "workout_days_per_week": null,
    "preferred_workout_time": "",
    "sleep_hours_target": null,
    "notes": ["string"]
  },
  "events": [
    {
      "event_type": "workout|meal|recovery|adherence|progress_note|check_in",
      "summary": "string",
      "event_time": "",
      "details": {}
    }
  ],
  "memory_entries": [
    {
      "text": "string",
      "category": "profile|goal|preference|injury|schedule|nutrition|training|progress|location|habit|artifact",
      "enable_graph": true
    }
  ],
  "proactive_signals": [
    {
      "signal_type": "missed_workout|low_adherence|needs_checkin|plateau_hint|positive_momentum",
      "summary": "string",
      "score": 0.0
    }
  ]
}

Rules:
- Use only information explicitly stated by the user or strongly supported by the provided image analysis.
- Do not invent missing facts.
- Profile updates should contain only durable facts or preferences worth keeping.
- Temporary one-off facts belong in `events`, not `profile_updates`.
- `memory_entries` should contain only durable, reusable coaching facts.
- Keep memory text short and factual.
- If a field is unknown, leave it empty, null, or [].
- `event_time` may be empty if unknown.
- `details` should be compact and structured.
"""
