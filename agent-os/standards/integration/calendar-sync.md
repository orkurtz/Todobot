# Two-Way Google Calendar Sync

Synchronize tasks bidirectionally between the bot's database and Google Calendar.

## Rules

- **Last-Write-Wins**: Resolve conflicts by comparing the task's `last_modified_at` with the calendar event's `updated` timestamp.
- **Selective Deletion**: Only delete database tasks if they originated from the calendar (`created_from_calendar == True`). Never delete bot-originated tasks if they are missing from the calendar.
- **Sync Window Overlap**: Retrieve calendar updates using a 1-hour overlap window (`last_calendar_sync - timedelta(hours=1)`) to catch late-arriving events or adjustments.
- **Idempotent Completion Sync**: Limit updates of completed tasks back to the calendar to those marked complete within a recent window (e.g., 60 minutes) to prevent redundant API calls.

## Code Example

```python
# Compare timestamps to resolve conflicts
if task.last_modified_at > event_updated:
    calendar_service.update_calendar_event(task)
else:
    task.description = calendar_event['title']
    task.due_date = due_date_utc
    task.calendar_last_modified = event_updated
```

## Rationale
- Preserving bot-only tasks allows users the flexibility to keep specific tasks out of their public Google Calendar.
- Minimizing checked tasks and fetching within fixed windows reduces CPU usage and API overhead, keeping costs low on platforms like Railway.
