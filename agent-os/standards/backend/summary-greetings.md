# Predictable & Noise-Filtered Hebrew Summaries

Standardize the daily digest compilation, calendar filtering, and localized greetings.

## Rules

- **Deterministic Greeting Rotation**: Use the day-of-year (`tm_yday % len(greetings)`) to cycle between different greetings. Avoid random selection to keep outputs testable and consistent.
- **Workweek Localization**: Adjust greetings depending on the day of the week in Israel (e.g., special Friday Shabbat greetings, Sunday workweek start greetings).
- **Calendar Noise Filtering**: Filter out irrelevant events from summaries:
  - Exclude events marked with `colorId == 8` (gray color, used for low-priority or non-task calendar events).
  - Exclude events with titles starting with `✅` (completed items).
  - Exclude calendar event IDs that correspond to tasks already tracked in the bot's database.

## Code Example

```python
# Rotate greetings deterministically without random choice
day_of_year = now_israel.timetuple().tm_yday
idx = day_of_year % len(greetings)
greeting = greetings[idx]

# Exclude completed, muted color (gray), and duplicate task events
display_events = [
    event for event in calendar_events
    if event["id"] not in active_task_event_ids
    and event.get("colorId") != "8"
    and not (event.get("title") or "").startswith("✅")
]
```

## Rationale
- Deterministic greeting rotation provides a friendly, varied interface while remaining testable in CI pipelines.
- Filtering calendar color status prevents cluttering summaries with completed or secondary calendar entries.
