"""
Calendar Sync Service - Two-way synchronization between Google Calendar and Bot Tasks
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import pytz

from ..models.database import db, User, Task
from .calendar_service import CalendarService
from .task_service import TaskService


class CalendarSyncService:
    """Handle bidirectional sync between Google Calendar and Bot Tasks"""
    
    def __init__(self, calendar_service: CalendarService, task_service: TaskService):
        self.calendar_service = calendar_service
        self.task_service = task_service
        self.israel_tz = pytz.timezone('Asia/Jerusalem')
    
    def sync_user_calendar(self, user: User) -> Tuple[int, int, int]:
        """
        Main sync function called every 10 minutes by worker.
        
        Process:
        1. Fetch events since last_calendar_sync
        2. For each task-event (color or '#'):
           - Find existing task by calendar_event_id
           - Compare timestamps: resolve_conflict()
           - Create new task if not exists
        3. Detect deleted events: handle_event_deletion()
        4. Check event completion status: auto-complete tasks
        5. Update user.last_calendar_sync
        
        Returns:
            (created_count, updated_count, deleted_count)
        """
        created_count = 0
        updated_count = 0
        deleted_count = 0
        
        try:
            if not user.google_calendar_enabled:
                return (0, 0, 0)
            
            # Determine sync window
            if user.last_calendar_sync:
                start_date = user.last_calendar_sync - timedelta(hours=1)  # 1 hour overlap for safety
            else:
                # First sync: look back 7 days
                start_date = datetime.now(pytz.UTC) - timedelta(days=7)
            
            end_date = datetime.now(pytz.UTC) + timedelta(days=30)  # Look ahead 30 days
            
            # Fetch all events (including non-task events for deletion detection)
            all_events = self.calendar_service.fetch_events(user, start_date, end_date, fetch_all=True)
            
            if not all_events and not user.last_calendar_sync:
                # First sync with no events - just mark as synced
                user.last_calendar_sync = datetime.now(pytz.UTC)
                db.session.commit()
                print(f"✅ First calendar sync for user {user.id}: No events found")
                return (0, 0, 0)
            
            # Separate task-events from regular events
            task_events = [e for e in all_events if self.calendar_service.is_task_event(e, user)]
            
            print(f"📊 Sync user {user.id}: {len(all_events)} total events, {len(task_events)} task-events")
            
            # Track processed event IDs
            processed_event_ids = set()
            
            # Process task-events
            for event in task_events:
                processed_event_ids.add(event['id'])
                
                # Check if task already exists
                existing_task = Task.query.filter_by(
                    user_id=user.id,
                    calendar_event_id=event['id']
                ).first()
                
                if existing_task:
                    # Existing task - check for updates
                    if self._resolve_conflict(existing_task, event):
                        updated_count += 1
                else:
                    # New event - create task
                    new_task = self.create_task_from_event(user, event)
                    if new_task:
                        created_count += 1
            
            # Check for deleted events (tasks with calendar_event_id that no longer exist)
            deleted_count += self._handle_event_deletions(user, all_events)
            
            # Verify bot-completed tasks are marked in calendar (Bot → Calendar)
            # Only look at the most recent completions within a recent time window
            # to avoid repeatedly touching very old tasks and reduce API calls.
            recent_cutoff = datetime.utcnow() - timedelta(minutes=60)
            recent_completed = Task.query.filter(
                Task.user_id == user.id,
                Task.status == 'completed',
                Task.calendar_event_id.isnot(None),
                Task.completed_at.isnot(None),
                Task.completed_at >= recent_cutoff
            ).order_by(Task.completed_at.desc()).limit(10).all()
            
            if recent_completed:
                print(f"🔄 Verifying {len(recent_completed)} completed tasks in calendar")
                for task in recent_completed:
                    try:
                        # Idempotent - safe to call repeatedly
                        self.calendar_service.mark_event_completed(task)
                    except Exception as e:
                        print(f"⚠️ Failed to mark task {task.id} as completed: {e}")
            
            # Update last sync timestamp
            user.last_calendar_sync = datetime.now(pytz.UTC)
            db.session.commit()
            
            print(f"✅ Synced calendar for user {user.id}: +{created_count} ↻{updated_count} -{deleted_count}")
            return (created_count, updated_count, deleted_count)
            
        except Exception as e:
            print(f"❌ Calendar sync failed for user {user.id}: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return (created_count, updated_count, deleted_count)
    
    def _resolve_conflict(self, task: Task, calendar_event: Dict[str, Any]) -> bool:
        """
        Compare timestamps and update accordingly (last write wins).
        
        Logic:
        - If task.last_modified_at > calendar_event.updated: Update calendar from task
        - If calendar_event.updated > task.last_modified_at: Update task from calendar
        - Store calendar_last_modified after sync
        
        Returns:
            True if task was updated, False otherwise
        """
        try:
            event_updated = calendar_event.get('updated')
            if not event_updated:
                return False
            
            # Ensure timezone awareness
            if event_updated.tzinfo is None:
                event_updated = pytz.UTC.localize(event_updated)
            else:
                event_updated = event_updated.astimezone(pytz.UTC)
            
            # Check if we already synced this version
            if task.calendar_last_modified:
                # Make calendar_last_modified timezone-aware for comparison
                cal_last_modified = task.calendar_last_modified
                if cal_last_modified.tzinfo is None:
                    cal_last_modified = pytz.UTC.localize(cal_last_modified)
                
                if cal_last_modified >= event_updated:
                    # Already up to date
                    return False
            
            # Check if task was modified more recently than calendar event
            if task.last_modified_at:
                task_modified = task.last_modified_at
                if task_modified.tzinfo is None:
                    task_modified = pytz.UTC.localize(task_modified)
                else:
                    task_modified = task_modified.astimezone(pytz.UTC)
                
                if task_modified > event_updated:
                    # Task is newer - update calendar from task
                    print(f"📤 Task {task.id} newer than calendar, updating calendar")
                    self.calendar_service.update_calendar_event(task)
                    task.calendar_last_modified = event_updated.replace(tzinfo=None)  # Store as naive UTC
                    db.session.commit()
                    return False  # Task not updated (calendar was updated)
            
            # Calendar event is newer - update task from calendar
            print(f"📥 Calendar event {calendar_event['id']} newer than task {task.id}, updating task")
            
            # Parse event start time to due_date
            event_start = calendar_event['start']
            if event_start.tzinfo is None:
                event_start = self.israel_tz.localize(event_start)
            
            # Convert to UTC for storage
            due_date_utc = event_start.astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Update task fields
            task.description = calendar_event['title']
            task.due_date = due_date_utc
            task.calendar_last_modified = event_updated.replace(tzinfo=None)
            
            # Check if event is completed (status or transparency)
            if calendar_event.get('status') == 'cancelled' or calendar_event.get('transparency') == 'transparent':
                if task.status == 'pending':
                    task.status = 'completed'
                    task.completed_at = datetime.utcnow()
                    print(f"✅ Auto-completed task {task.id} from calendar")
            
            # Don't update last_modified_at because this is a calendar sync, not a bot change
            db.session.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to resolve conflict for task {task.id}: {e}")
            db.session.rollback()
            return False
    
    def create_task_from_event(self, user: User, event: Dict[str, Any]) -> Optional[Task]:
        """
        Convert calendar event to bot task.
        
        Args:
            user: User object
            event: Event dict from calendar_service.fetch_events()
        
        Returns:
            Created Task or None
        """
        try:
            # Parse event start time
            event_start = event['start']
            if event_start.tzinfo is None:
                event_start = self.israel_tz.localize(event_start)
            
            # Convert to UTC for storage
            due_date_utc = event_start.astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Check if event is already completed
            is_completed = (
                event.get('status') == 'cancelled' or 
                event.get('transparency') == 'transparent'
            )
            
            # Create task
            task = Task(
                user_id=user.id,
                description=event['title'],
                due_date=due_date_utc,
                status='completed' if is_completed else 'pending',
                completed_at=datetime.utcnow() if is_completed else None,
                calendar_event_id=event['id'],
                calendar_synced=True,
                created_from_calendar=True,  # Mark as originated from calendar
                last_modified_at=datetime.utcnow(),
                calendar_last_modified=event.get('updated').replace(tzinfo=None) if event.get('updated') else None
            )
            
            db.session.add(task)
            db.session.commit()
            
            print(f"✅ Created task {task.id} from calendar event {event['id']}")
            return task
            
        except Exception as e:
            print(f"❌ Failed to create task from event {event.get('id')}: {e}")
            db.session.rollback()
            return None
    
    def _handle_event_deletions(self, user: User, current_events: List[Dict[str, Any]]) -> int:
        """
        Delete tasks if their calendar events were deleted.
        Only deletes tasks where created_from_calendar=True.
        
        Args:
            user: User object
            current_events: List of all current events from calendar
        
        Returns:
            Number of tasks deleted
        """
        deleted_count = 0
        
        try:
            # Get all event IDs from current events
            current_event_ids = {e['id'] for e in current_events}
            
            # Find tasks with calendar_event_id that are missing from current events
            tasks_with_calendar_events = Task.query.filter(
                Task.user_id == user.id,
                Task.calendar_event_id.isnot(None),
                Task.created_from_calendar == True,  # Only delete calendar-originated tasks
                Task.status == 'pending'  # Don't delete completed tasks
            ).all()
            
            for task in tasks_with_calendar_events:
                if task.calendar_event_id not in current_event_ids:
                    # Event was deleted from calendar
                    print(f"🗑️ Deleting task {task.id} (calendar event {task.calendar_event_id} deleted)")
                    db.session.delete(task)
                    deleted_count += 1
            
            if deleted_count > 0:
                db.session.commit()
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ Failed to handle event deletions: {e}")
            db.session.rollback()
            return deleted_count
    
    def sync_recurring_event(self, user: User, recurring_event_id: str) -> Tuple[int, int]:
        """
        Handle recurring event instances.
        Fetches instances for next 30 days and creates/updates tasks.
        
        Args:
            user: User object
            recurring_event_id: ID of recurring event
        
        Returns:
            (created_count, updated_count)
        """
        created_count = 0
        updated_count = 0
        
        try:
            instances = self.calendar_service.get_recurring_instances(user, recurring_event_id, days_ahead=30)
            
            for instance in instances:
                # Check if task exists for this instance
                existing_task = Task.query.filter_by(
                    user_id=user.id,
                    calendar_event_id=instance['id']
                ).first()
                
                if existing_task:
                    # Update existing task
                    if self._resolve_conflict(existing_task, instance):
                        updated_count += 1
                else:
                    # Create new task for instance
                    # Only create if event is a task-event
                    if self.calendar_service.is_task_event(instance, user):
                        new_task = self.create_task_from_event(user, instance)
                        if new_task:
                            created_count += 1
            
            print(f"✅ Synced recurring event {recurring_event_id}: +{created_count} ↻{updated_count}")
            return (created_count, updated_count)
            
        except Exception as e:
            print(f"❌ Failed to sync recurring event {recurring_event_id}: {e}")
            return (created_count, updated_count)

