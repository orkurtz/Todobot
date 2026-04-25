"""
Build the daily task/calendar summary text (9 AM push and on-demand command).
Must not depend on SchedulerService or WhatsApp — safe to import from the web process.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Literal, Optional

import pytz

from ..models.database import Task, User

SummarySource = Literal["cron", "on_demand"]


class DailySummaryService:
    def __init__(self):
        self.israel_tz = pytz.timezone("Asia/Jerusalem")

    def build(self, user: User, *, source: SummarySource) -> Optional[str]:
        """
        Returns None for cron when user has no overdue/today tasks (no push).
        On-demand always returns a non-empty str (summary or empty-state message).
        """
        now_utc = datetime.utcnow()
        now_israel = datetime.now(self.israel_tz)
        today_start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_israel = today_start_israel + timedelta(days=1)

        today_start = today_start_israel.astimezone(pytz.UTC).replace(tzinfo=None)
        today_end = today_end_israel.astimezone(pytz.UTC).replace(tzinfo=None)

        tasks_due_today = (
            Task.query.filter(
                Task.user_id == user.id,
                Task.status == "pending",
                Task.is_recurring == False,
                Task.due_date >= today_start,
                Task.due_date < today_end,
            )
            .order_by(Task.due_date.asc())
            .all()
        )

        overdue_tasks = (
            Task.query.filter(
                Task.user_id == user.id,
                Task.status == "pending",
                Task.is_recurring == False,
                Task.due_date < now_utc,
                Task.due_date.isnot(None),
            )
            .order_by(Task.due_date.asc())
            .all()
        )

        has_tasks = bool(tasks_due_today or overdue_tasks)

        if source == "cron" and not has_tasks:
            return None

        summary_parts: List[str] = ["📋 סיכום משימות יומי\n"]
        has_body = False

        if overdue_tasks:
            has_body = True
            summary_parts.append(f"⚠️ באיחור ({len(overdue_tasks)}):")
            for task in overdue_tasks[:5]:
                due_local = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                desc = (task.description or "")[:50]
                summary_parts.append(f"  • {desc} ({due_local.strftime('%d/%m %H:%M')})")
            if len(overdue_tasks) > 5:
                summary_parts.append(f"  ... ועוד {len(overdue_tasks) - 5}")
            summary_parts.append("")

        if tasks_due_today:
            has_body = True
            summary_parts.append(f"📅 משימות להיום ({len(tasks_due_today)}):")
            for task in tasks_due_today[:5]:
                due_local = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                desc = (task.description or "")[:50]
                summary_parts.append(f"  • {desc} ({due_local.strftime('%H:%M')})")
            if len(tasks_due_today) > 5:
                summary_parts.append(f"  ... ועוד {len(tasks_due_today) - 5}")
            summary_parts.append("")

        include_calendar = user.google_calendar_enabled and (
            has_tasks or source == "on_demand"
        )

        if include_calendar:
            try:
                from ..services.calendar_service import CalendarService

                calendar_service = CalendarService()
                calendar_events = calendar_service.fetch_events(
                    user, today_start, today_end, fetch_all=True
                )

                all_user_tasks_with_cal_id = Task.query.filter(
                    Task.user_id == user.id,
                    Task.calendar_event_id.isnot(None),
                ).all()
                task_event_ids = {t.calendar_event_id for t in all_user_tasks_with_cal_id}

                display_events = [
                    e
                    for e in calendar_events
                    if e["id"] not in task_event_ids
                    and e.get("status") != "cancelled"
                    and e.get("colorId") != "8"
                    and not (e.get("title") or "").startswith("✅")
                ]

                if display_events:
                    has_body = True
                    summary_parts.append(f"📆 אירועים ביומן ({len(display_events)}):")
                    for event in display_events[:5]:
                        start_local = event["start"].astimezone(self.israel_tz)
                        end_local = event["end"].astimezone(self.israel_tz)
                        title = (event.get("title") or "")[:50]
                        summary_parts.append(
                            f"  • {title} ({start_local.strftime('%H:%M')}-{end_local.strftime('%H:%M')})"
                        )
                    if len(display_events) > 5:
                        summary_parts.append(f"  ... ועוד {len(display_events) - 5}")
                    summary_parts.append("")
            except Exception as calendar_error:
                print(f"⚠️ Failed to fetch calendar events for daily summary: {calendar_error}")

        if source == "on_demand" and not has_body:
            return self._empty_on_demand_message(user)

        summary_parts.append("💪 בהצלחה היום!")
        return "\n".join(summary_parts)

    def _empty_on_demand_message(self, user: User) -> str:
        lines = [
            "📋 סיכום משימות יומי",
            "",
            "אין כרגע משימות באיחור או עם יעד להיום.",
        ]
        if user.google_calendar_enabled:
            lines.append("לא נמצאו אירועים ביומן להצגה להיום (למעט אירועים שכבר משויכים למשימות בבוט).")
        lines.append("יום נעים!")
        return "\n".join(lines)
