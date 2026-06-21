# Task Recurrence & Lifecycle Management

Structure and govern recurring schedule templates and their generated execution instances.

## Rules

- **Decoupled Template vs. Instance Model**:
  - Store the recurrence ruleset in a template row where `is_recurring = True` (represents the schedule, e.g., "Gym every Monday").
  - Create separate task rows for each scheduled occurrence where `parent_recurring_id = template_id` (represents the actionable task instance).
- **Strict Pattern Action Guards**: Block standard task completion (`complete_task`) or deletion (`delete_task`) logic when targeted at template rows. Users must use series-specific commands (e.g., "עצור סדרה", "השלם סדרה") to change templates.
- **Idempotent Midnight Instantiation**: Generate the next day's instance for active templates at midnight via scheduler cron. Ensure we check for duplicate instances on the target date before inserting a new row.
- **Israel-Time Recurrence Checking**: Analyze weekday lists or day-of-month recurrence rules within the `Asia/Jerusalem` timezone, converting the generated schedule to UTC prior to database write.

## Code Example

```python
# Guard against direct modifications of the series template
if task.is_recurring:
    return False, "Cannot complete or delete a recurring pattern directly."

# Create a single instance linked to pattern template
task_instance = Task(
    user_id=pattern.user_id,
    description=pattern.description,
    due_date=calculated_due_date_utc,
    status='pending',
    parent_recurring_id=pattern.id
)
db.session.add(task_instance)
```

## Rationale
- Separating templates from instances enables users to mutate individual task occurrences (complete, postpone, or delete) without corrupting future recurring schedules.
- Restricting standard mutation commands on pattern templates prevents accidental loss of recurring series.
