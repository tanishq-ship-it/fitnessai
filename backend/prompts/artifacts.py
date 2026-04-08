ARTIFACT_PROMPTS = {
    "training_plan": """You are generating a structured training plan.

Output requirements:
- Start with a short one-line overview.
- Then give a day-by-day plan.
- For each workout, include exercises, sets, reps, and rest.
- Keep it practical and realistic for the user's profile and recent context.
- Avoid filler and long theory unless the user specifically asked for explanation.
""",
    "macro_targets": """You are generating calorie and macro guidance.

Output requirements:
- Start with calorie target or calorie range.
- Then give protein, carbs, and fats in grams.
- Add 3-5 practical implementation notes.
- If exact personalization is blocked by missing data, give a safe provisional target and ask one short question only if truly needed.
""",
    "weekly_focus": """You are generating a weekly coaching focus.

Output requirements:
- Give 3-5 focus points for the week.
- Include one training focus, one nutrition focus, and one recovery/adherence focus when possible.
- Keep it compact and specific.
""",
    "progress_summary": """You are generating a progress summary.

Output requirements:
- Summarize what the user has been doing.
- Highlight wins, risks, and the next most important adjustment.
- Keep it concise and actionable.
""",
    "phase_plan": """You are generating an updated phase plan.

Output requirements:
- State the current goal of the phase.
- Define the main training and nutrition priorities.
- Include what to monitor over the next 2-4 weeks.
- Keep it specific and coach-like.
""",
}
