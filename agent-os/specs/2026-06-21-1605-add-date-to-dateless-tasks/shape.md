# Add Date to Dateless Tasks Command — Shaping Notes

## Scope

We are building a new command "הוסף תאריך למשימות" (and English/slash equivalents) to update all pending tasks without a due date to the next full hour in Israel.

## Decisions

- **Command behavior:** Only affects pending, non-recurring tasks where `due_date IS NULL`.
- **Target Time:** Moves tasks to the next full hour in Israel (using `Asia/Jerusalem` timezone converted to UTC).
- **Responses:**
  - Success message listing the number of tasks updated and the new due date.
  - Informative message if no dateless tasks are present: `"📋 אין משימות ללא תאריך יעד."`

## Context

- **Visuals:** None
- **References:** `delay_all_overdue_to_next_hour` in `src/services/task_service.py`
- **Product alignment:** N/A

## Standards Applied

- `global/minimalist-code` — Ponytail rule to keep implementation simple, reusing `update_task` and the existing timezone logic.
- `api/whatsapp` — Normalizing Hebrew command strings.
