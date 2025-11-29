"""
Task management service for handling todo operations
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import re
import json
from dateutil import parser
import pytz

from ..models.database import db, Task, User
from ..utils.fuzzy_matcher import FuzzyTaskMatcher

class TaskService:
    """Handle task-related operations"""
    
    def __init__(self, calendar_service=None, ai_service=None):
        self.israel_tz = pytz.timezone('Asia/Jerusalem')
        self.calendar_service = calendar_service  # Optional calendar service for sync
        self.ai_service = ai_service  # Phase 2: For fetching full schedule with calendar events
        self.fuzzy_matcher = FuzzyTaskMatcher(self.israel_tz)  # Hybrid matching: fuzzy + semantic
    
    def create_task(self, user_id: int, description: str, due_date: datetime = None) -> Task:
        """Create a new task for user"""
        try:
            task = Task(
                user_id=user_id,
                description=description.strip()[:500],  # Limit description length
                due_date=due_date,
                status='pending',
                last_modified_at=datetime.utcnow()  # Track modification for Phase 2 sync
            )
            
            db.session.add(task)
            db.session.commit()
            
            print(f"✅ Created task for user {user_id}: {description[:50]}...")
            
            # Sync to calendar if enabled and has due date
            if self.calendar_service and due_date:
                try:
                    success, event_id, error = self.calendar_service.create_calendar_event(task)
                    if success:
                        print(f"📅 Synced task {task.id} to calendar: {event_id}")
                    elif error:
                        print(f"⚠️ Failed to sync to calendar: {error}")
                except Exception as e:
                    print(f"⚠️ Calendar sync error (non-fatal): {e}")
            
            return task
            
        except Exception as e:
            print(f"❌ Failed to create task: {e}")
            db.session.rollback()
            raise e
    
    def get_user_tasks(self, user_id: int, status: str = 'pending', limit: int = 50,
                       include_patterns_when_completed: bool = False) -> List[Task]:
        """Get user's tasks by status (exclude recurring patterns unless requested for completed)."""
        try:
            base_query = Task.query.filter(
                Task.user_id == user_id,
                Task.status == status
            )
            if status == 'completed' and include_patterns_when_completed:
                tasks = base_query.order_by(Task.completed_at.desc()).limit(limit).all()
            else:
                tasks = base_query.filter(Task.is_recurring == False).order_by(
                    Task.due_date.asc().nullslast(), Task.created_at.desc()
                ).limit(limit).all()
            return tasks
        
        except Exception as e:
            print(f"❌ Failed to get user tasks: {e}")
            return []
    
    def complete_task(self, task_id: int, user_id: int) -> Tuple[bool, str]:
        """Mark a task as completed"""
        try:
            task = Task.query.filter_by(id=task_id, user_id=user_id).first()
            
            if not task:
                return False, "❌ המשימה לא נמצאה או שאינה שייכת לך"
            
            # Prevent completing recurring patterns directly
            if task.is_recurring:
                return False, "❌ לא ניתן להשלים תבנית חוזרת ישירות. השתמש ב'השלם סדרה [מספר]' כדי להשלים את כל הסדרה."
            
            if task.status == 'completed':
                return False, "❌ המשימה כבר הושלמה"
            
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            task.last_modified_at = datetime.utcnow()  # Track modification for Phase 2 sync
            
            db.session.commit()
            
            # Mark calendar event as completed if exists
            if self.calendar_service and task.calendar_event_id:
                try:
                    success, error = self.calendar_service.mark_event_completed(task)
                    if not success:
                        print(f"⚠️ Failed to update calendar: {error}")
                except Exception as e:
                    print(f"⚠️ Calendar sync error (non-fatal): {e}")
            
            print(f"✅ Task {task_id} completed by user {user_id}")
            return True, f"Task completed: {task.description[:50]}..."
            
        except Exception as e:
            print(f"❌ Failed to complete task: {e}")
            db.session.rollback()
            return False, f"Failed to complete task: {str(e)}"
    
    def delete_task(self, task_id: int, user_id: int) -> Tuple[bool, str]:
        """Delete a task"""
        try:
            task = Task.query.filter_by(id=task_id, user_id=user_id).first()
            
            if not task:
                return False, "❌ המשימה לא נמצאה או שאינה שייכת לך"
            
            # Prevent deleting recurring patterns directly
            if task.is_recurring:
                return False, "❌ לא ניתן למחוק תבנית חוזרת ישירות. השתמש ב'עצור סדרה [מספר]' כדי לעצור את הסדרה."
            
            task_desc = task.description[:50]
            
            # Delete calendar event first if exists
            if self.calendar_service and task.calendar_event_id:
                try:
                    success, error = self.calendar_service.delete_calendar_event(task)
                    if not success:
                        print(f"⚠️ Failed to delete calendar event: {error}")
                except Exception as e:
                    print(f"⚠️ Calendar sync error (non-fatal): {e}")
            
            db.session.delete(task)
            db.session.commit()
            
            print(f"🗑️ Task {task_id} deleted by user {user_id}")
            return True, f"Task deleted: {task_desc}..."
            
        except Exception as e:
            print(f"❌ Failed to delete task: {e}")
            db.session.rollback()
            return False, f"Failed to delete task: {str(e)}"
    
    def get_task_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's task statistics"""
        try:
            total_tasks = Task.query.filter_by(user_id=user_id).count()
            pending_tasks = Task.query.filter_by(user_id=user_id, status='pending').count()
            completed_tasks = Task.query.filter_by(user_id=user_id, status='completed').count()
            
            # Tasks due today - IN ISRAEL TIME
            now_israel = datetime.now(self.israel_tz)  # Current time in Israel
            today_start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)  # Midnight Israel
            today_end_israel = today_start_israel + timedelta(days=1)  # Next midnight Israel
            
            # Convert to UTC for database comparison (Task.due_date is stored in UTC)
            today_start = today_start_israel.astimezone(pytz.UTC).replace(tzinfo=None)
            today_end = today_end_israel.astimezone(pytz.UTC).replace(tzinfo=None)
            
            due_today = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
                Task.is_recurring == False,  # Only show instances, not patterns
                Task.due_date >= today_start,
                Task.due_date < today_end
            ).count()
            
            # Overdue tasks
            overdue = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
                Task.is_recurring == False,  # Only show instances, not patterns
                Task.due_date < datetime.utcnow()
            ).count()
            
            return {
                'total': total_tasks,
                'pending': pending_tasks,
                'completed': completed_tasks,
                'due_today': due_today,
                'overdue': overdue,
                'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
            }
            
        except Exception as e:
            print(f"❌ Failed to get task stats: {e}")
            return {
                'total': 0,
                'pending': 0,
                'completed': 0,
                'due_today': 0,
                'overdue': 0,
                'completion_rate': 0
            }
    
    def parse_date_from_text(self, text: str, user_timezone: str = 'Asia/Jerusalem') -> Optional[datetime]:
        """Parse date/time from natural language text with support for relative time expressions"""
        if not text:
            return None
        
        text = text.lower().strip()
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)
        
        # Handle relative time expressions in Hebrew
        # Pattern: "בעוד X דקות/שעות/ימים" or "עוד X דקות/שעות/ימים"
        hebrew_relative_patterns = [
            (r'(?:בעוד|עוד)\s+(\d+)\s*(?:דקות?|דקה)', 'minutes'),
            (r'(?:בעוד|עוד)\s+חצי\s+שעה', 'half_hour'),
            (r'(?:בעוד|עוד)\s+(\d+)\s*(?:שעות?|שעה)', 'hours'),
            (r'(?:בעוד|עוד)\s+(\d+)\s*(?:ימים?|יום)', 'days'),
            (r'(?:בעוד|עוד)\s+(?:שבוע|שבועיים)', 'week'),
            (r'(?:בעוד|עוד)\s+חודש', 'month'),
        ]
        
        for pattern, unit in hebrew_relative_patterns:
            match = re.search(pattern, text)
            if match:
                if unit == 'minutes':
                    minutes = int(match.group(1))
                    target_date = now + timedelta(minutes=minutes)
                elif unit == 'half_hour':
                    target_date = now + timedelta(minutes=30)
                elif unit == 'hours':
                    hours = int(match.group(1))
                    target_date = now + timedelta(hours=hours)
                elif unit == 'days':
                    days = int(match.group(1))
                    target_date = now + timedelta(days=days)
                elif unit == 'week':
                    if 'שבועיים' in text:
                        target_date = now + timedelta(weeks=2)
                    else:
                        target_date = now + timedelta(weeks=1)
                elif unit == 'month':
                    target_date = now + timedelta(days=30)
                
                return target_date.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Handle relative time expressions in English
        # Pattern: "in X minutes/hours/days"
        english_relative_patterns = [
            (r'in\s+(\d+)\s*(?:minutes?|mins?)', 'minutes'),
            (r'in\s+(?:a\s+)?half\s+(?:an\s+)?hour', 'half_hour'),
            (r'in\s+(\d+)\s*(?:hours?|hrs?)', 'hours'),
            (r'in\s+(\d+)\s*(?:days?)', 'days'),
            (r'in\s+(?:a\s+)?week', 'week'),
            (r'in\s+(\d+)\s*(?:weeks?)', 'weeks'),
            (r'in\s+(?:a\s+)?month', 'month'),
        ]
        
        for pattern, unit in english_relative_patterns:
            match = re.search(pattern, text)
            if match:
                if unit == 'minutes':
                    minutes = int(match.group(1))
                    target_date = now + timedelta(minutes=minutes)
                elif unit == 'half_hour':
                    target_date = now + timedelta(minutes=30)
                elif unit == 'hours':
                    hours = int(match.group(1))
                    target_date = now + timedelta(hours=hours)
                elif unit == 'days':
                    days = int(match.group(1))
                    target_date = now + timedelta(days=days)
                elif unit == 'week':
                    target_date = now + timedelta(weeks=1)
                elif unit == 'weeks':
                    weeks = int(match.group(1))
                    target_date = now + timedelta(weeks=weeks)
                elif unit == 'month':
                    target_date = now + timedelta(days=30)
                
                return target_date.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Handle Hebrew date expressions
        hebrew_mappings = {
            'היום': 0,
            'מחר': 1,
            'מחרתיים': 2,
            'שלשום': -3,
            'אתמול': -1,
            'ראשון': 6,  # Sunday
            'שני': 0,    # Monday  
            'שלישי': 1,  # Tuesday
            'רביעי': 2,  # Wednesday
            'חמישי': 3,  # Thursday
            'שישי': 4,   # Friday
            'שבת': 5     # Saturday
        }
        
        # Handle English relative dates
        english_mappings = {
            'today': 0,
            'tomorrow': 1,
            'yesterday': -1,
            'next week': 7,
            'next month': 30
        }
        
        # Check Hebrew expressions
        for hebrew, days in hebrew_mappings.items():
            if hebrew in text:
                if hebrew in ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']:
                    # Calculate next occurrence of this weekday
                    current_weekday = now.weekday()
                    days_ahead = (days - current_weekday) % 7
                    if days_ahead == 0:  # If it's the same weekday, assume next week
                        days_ahead = 7
                    target_date = now + timedelta(days=days_ahead)
                else:
                    target_date = now + timedelta(days=days)
                
                # Try to extract time if present
                time_match = re.search(r'(\d{1,2}):(\d{2})', text)
                if time_match:
                    hour, minute = int(time_match.group(1)), int(time_match.group(2))
                    target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                
                return target_date.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Check English expressions
        for english, days in english_mappings.items():
            if english in text:
                target_date = now + timedelta(days=days)
                
                # Try to extract time if present (same as Hebrew handling)
                time_match = re.search(r'(\d{1,2}):(\d{2})', text)
                if time_match:
                    hour, minute = int(time_match.group(1)), int(time_match.group(2))
                    target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                
                return target_date.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Handle DD/MM and DD/MM/YYYY formats (Israeli/European format)
        # This MUST come before parser.parse() to avoid American MM/DD interpretation
        date_formats_to_try = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
            r'(\d{1,2})/(\d{1,2})',           # DD/MM
        ]
        
        for pattern in date_formats_to_try:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.groups()) == 3:  # DD/MM/YYYY
                        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        target_date = tz.localize(datetime(year, month, day, 9, 0))
                    else:  # DD/MM (assume current year)
                        day, month = int(match.group(1)), int(match.group(2))
                        year = now.year
                        target_date = tz.localize(datetime(year, month, day, 9, 0))
                        
                        # If date is in the past, assume next year
                        if target_date < now:
                            target_date = tz.localize(datetime(year + 1, month, day, 9, 0))
                    
                    # Extract time if present (HH:MM format)
                    time_match = re.search(r'(?:בשעה|ב-|at)?\s*(\d{1,2}):(\d{2})', text)
                    if time_match:
                        hour, minute = int(time_match.group(1)), int(time_match.group(2))
                        target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    print(f"✅ Parsed DD/MM date: {text} → {target_date}")
                    return target_date.astimezone(pytz.UTC).replace(tzinfo=None)
                    
                except ValueError as e:
                    print(f"⚠️ Invalid date format in '{text}': {e}")
                    continue  # Try next pattern
        
        # Try parsing explicit dates with dayfirst=True for other formats
        try:
            parsed_date = parser.parse(text, dayfirst=True, default=now)
            if parsed_date.tzinfo is None:
                parsed_date = tz.localize(parsed_date)
            return parsed_date.astimezone(pytz.UTC).replace(tzinfo=None)
        except:
            pass
        
        return None
    
    def get_due_tasks_for_reminders(self, time_window_minutes: int = 15) -> List[Task]:
        """Get tasks that are due for reminders"""
        try:
            now = datetime.utcnow()
            window_end = now + timedelta(minutes=time_window_minutes)
            # Look back 24 hours to catch anything missed during downtime
            lookback_start = now - timedelta(hours=24)
            
            tasks = Task.query.filter(
                Task.status == 'pending',
                Task.is_recurring == False,  # Only show instances, not patterns
                Task.due_date.isnot(None),
                Task.due_date >= lookback_start,
                Task.due_date <= window_end,
                Task.reminder_sent.is_(False)
            ).all()
            
            return tasks
            
        except Exception as e:
            print(f"❌ Failed to get due tasks for reminders: {e}")
            return []
    
    def mark_reminder_sent(self, task_id: int) -> bool:
        """Mark that a reminder was sent for this task"""
        try:
            task = Task.query.get(task_id)
            if task:
                task.reminder_sent = True
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"❌ Failed to mark reminder sent: {e}")
            db.session.rollback()
            return False
    
    def update_task(self, task_id: int, user_id: int, new_description: str = None, new_due_date: datetime = None) -> Tuple[bool, str]:
        """Update an existing task with friendly Hebrew messages"""
        try:
            task = Task.query.filter_by(id=task_id, user_id=user_id).first()
            
            if not task:
                return False, "❌ לא מצאתי את המשימה הזו. אולי כבר נמחקה?"
            
            # Prevent updating recurring patterns directly (should use update_recurring_pattern instead)
            if task.is_recurring:
                return False, "❌ לא ניתן לעדכן תבנית חוזרת דרך עדכון רגיל. השתמש בפקודת עדכון תבנית או עדכן מופעים ספציפיים."
            
            if task.status == 'completed':
                return False, "❌ לא ניתן לעדכן משימה שכבר הושלמה. תמחק אותה ותיצור משימה חדשה במקום."
            
            # Store old values for confirmation message
            old_description = task.description
            old_due_date = task.due_date
            
            # Update fields if provided
            if new_description:
                task.description = new_description.strip()[:500]
            
            if new_due_date is not None:  # Allow None to clear due date
                task.due_date = new_due_date
                task.reminder_sent = False  # Reset reminder if date changed
            
            task.updated_at = datetime.utcnow()
            task.last_modified_at = datetime.utcnow()  # Track modification for Phase 2 sync
            db.session.commit()
            
            # Update calendar event if exists
            if self.calendar_service:
                if task.calendar_event_id:
                    try:
                        success, error = self.calendar_service.update_calendar_event(task)
                        if not success:
                            print(f"⚠️ Failed to update calendar: {error}")
                    except Exception as e:
                        print(f"⚠️ Calendar sync error (non-fatal): {e}")
                
                # If we DON'T have an event ID but have a due date, try to create one (Recovery)
                elif task.due_date:
                    try:
                        success, event_id, error = self.calendar_service.create_calendar_event(task)
                        if success:
                            print(f"📅 Created missing calendar event for updated task")
                        elif error:
                            print(f"⚠️ Failed to create calendar event: {error}")
                    except Exception as e:
                        print(f"⚠️ Calendar sync error (non-fatal): {e}")
            
            # Build confirmation message in Hebrew
            changes = []
            if new_description and new_description != old_description:
                changes.append(f"תיאור: '{old_description[:30]}...' → '{task.description[:30]}...'")
            if new_due_date != old_due_date:
                if new_due_date:
                    local_time = new_due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                    changes.append(f"תאריך יעד → {local_time.strftime('%d/%m/%Y בשעה %H:%M')}")
                else:
                    changes.append("תאריך יעד הוסר")
            
            print(f"✅ Updated task {task_id} for user {user_id}: {', '.join(changes)}")
            return True, f"✅ משימה #{task_id} עודכנה:\n{chr(10).join('• ' + c for c in changes)}"
            
        except Exception as e:
            print(f"❌ Failed to update task: {e}")
            db.session.rollback()
            return False, f"❌ שגיאה בעדכון המשימה. נסה שוב."
    
    def format_task_list(self, tasks: List[Task], show_due_date: bool = True) -> str:
        """Format task list for display"""
        if not tasks:
            return "📋 לא נמצאו משימות."
        
        formatted_tasks = []
        for i, task in enumerate(tasks, 1):
            # Add recurring indicator
            if task.parent_recurring_id:
                pattern = task.get_recurring_pattern()
                if pattern:
                    pattern_desc = self._format_recurrence_pattern(pattern)
                    task_text = f"{i}. 🔄 {task.description} [#{task.id}] ({pattern_desc})"
                else:
                    task_text = f"{i}. 🔄 {task.description} [#{task.id}]"
            else:
                task_text = f"{i}. {task.description} [#{task.id}]"
            
            if show_due_date and task.due_date:
                # Convert UTC to Israel timezone for display
                local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                formatted_date = local_time.strftime("%d/%m %H:%M")
                
                # Get current date in Israel timezone for comparison
                now_israel = datetime.now(self.israel_tz)
                today_israel = now_israel.date()
                tomorrow_israel = today_israel + timedelta(days=1)
                task_date_israel = local_time.date()
                
                # Compare dates to determine label
                if task.due_date < datetime.utcnow():  # Overdue check (UTC comparison)
                    task_text += f" ⚠️ (באיחור - {formatted_date})"
                elif task_date_israel == today_israel:
                    task_text += f" 🔥 (יעד היום {formatted_date})"
                elif task_date_israel == tomorrow_israel:
                    task_text += f" 🔥 (יעד מחר {formatted_date})"
                else:
                    task_text += f" 📅 (יעד {formatted_date})"
            
            formatted_tasks.append(task_text)
        
        return "\n".join(formatted_tasks)
    
    def execute_parsed_tasks(self, user_id: int, parsed_tasks: List[Dict], original_message: str = None) -> str:
        """Execute parsed tasks from AI and return summary"""
        if not parsed_tasks:
            return ""
        
        created_tasks = []
        actions_performed = {
            'complete': [],
            'update': [],
            'reschedule': [],
            'stop_series': [],
            'complete_series': []
        }
        deleted_tasks = []
        failed_tasks = []
        query_results = []
        
        for task_data in parsed_tasks:
            try:
                action = task_data.get('action', 'add')
                description = task_data.get('description', '').strip()
                
                # Only require description for 'add' action
                # For other actions (reschedule, update, complete, delete, query), task_id is used instead
                if action == 'add' and not description:
                    continue
                
                if action == 'complete':
                    # Handle task completion - use task_id if available, fallback to description
                    task_identifier = task_data.get('task_id') or description
                    success, message = self._handle_task_completion(user_id, task_identifier, original_message)
                    if success:
                        actions_performed['complete'].append(message)
                    else:
                        failed_tasks.append(f"Failed to complete: {message}")
                
                elif action == 'delete':
                    # Handle task deletion - use task_id if available, fallback to description
                    task_identifier = task_data.get('task_id') or description
                    success, message = self._handle_task_deletion(user_id, task_identifier)
                    if success:
                        deleted_tasks.append(message)
                    else:
                        failed_tasks.append(f"Failed to delete: {message}")
                
                elif action == 'add':
                    # Create new task
                    due_date = None
                    due_date_str = task_data.get('due_date')
                    if due_date_str:
                        # Try natural language parsing FIRST (supports Hebrew!)
                        due_date = self.parse_date_from_text(due_date_str)
                        
                        # If natural language parsing fails, try standard formats as fallback
                        if not due_date:
                            try:
                                due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M")
                            except ValueError:
                                try:
                                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                                    due_date = due_date.replace(hour=9, minute=0)  # Default to 9 AM
                                except ValueError:
                                    print(f"⚠️ Could not parse due date: '{due_date_str}'")
                    
                    # NEW: Check for recurrence
                    recurrence_pattern = task_data.get('recurrence_pattern')
                    
                    if recurrence_pattern:
                        recurrence_interval = task_data.get('recurrence_interval', 1)
                        recurrence_days_of_week = task_data.get('recurrence_days_of_week')
                        recurrence_day_of_month = task_data.get('recurrence_day_of_month')
                        recurrence_end_date_str = task_data.get('recurrence_end_date')
                        
                        # Parse end date if provided
                        recurrence_end_date = None
                        if recurrence_end_date_str:
                            recurrence_end_date = self.parse_date_from_text(recurrence_end_date_str)
                        
                        task = self.create_recurring_task(
                            user_id,
                            description,
                            due_date,
                            recurrence_pattern,
                            recurrence_interval,
                            recurrence_days_of_week,
                            recurrence_end_date,
                            recurrence_day_of_month
                        )
                    else:
                        # Existing non-recurring creation
                        task = self.create_task(user_id, description, due_date)
                    
                    created_tasks.append(task)
                
                elif action == 'update':
                    # Handle task update - support recurring pattern updates
                    task_id_str = task_data.get('task_id') or task_data.get('description')
                    if task_id_str and task_id_str.isdigit():
                        target_task = Task.query.filter_by(id=int(task_id_str), user_id=user_id).first()
                        if target_task and target_task.is_recurring:
                            success, message = self.update_recurring_pattern(int(task_id_str), user_id, task_data)
                        else:
                            success, message = self._handle_task_update(user_id, task_data)
                    else:
                        success, message = self._handle_task_update(user_id, task_data)
                    if success:
                        actions_performed['update'].append(message)
                    else:
                        failed_tasks.append(message)
                
                elif action == 'reschedule':
                    # Handle task reschedule
                    success, message = self._handle_task_reschedule(user_id, task_data)
                    if success:
                        actions_performed['reschedule'].append(message)
                    else:
                        failed_tasks.append(message)
                
                elif action == 'query':
                    # Query action - actually query the database!
                    print(f"📋 Query action detected for: {description}")
                    query_result = self._handle_query_action(user_id, description, task_data)
                    if query_result:
                        query_results.append(query_result)
                
                elif action == 'stop_series':
                    task_id_str = task_data.get('task_id') or task_data.get('description')
                    if task_id_str and task_id_str.isdigit():
                        task_id = int(task_id_str)
                        # Check if message contains delete indicators
                        delete_instances = ('מחק' in (original_message or '').lower() or 
                                          'delete' in (original_message or '').lower())
                        success, message = self.stop_recurring_series(task_id, user_id, delete_instances)
                        if success:
                            actions_performed['stop_series'].append(message)
                        else:
                            failed_tasks.append(message)
                
                elif action == 'complete_series':
                    task_id_str = task_data.get('task_id') or task_data.get('description')
                    if task_id_str and task_id_str.isdigit():
                        task_id = int(task_id_str)
                        success, message = self.complete_recurring_series(task_id, user_id)
                        if success:
                            actions_performed['complete_series'].append(message)
                        else:
                            failed_tasks.append(message)
                
            except Exception as e:
                print(f"❌ Failed to process task: {e}")
                failed_tasks.append(task_data.get('description', 'Unknown task'))
        
        # Build response message
        response_parts = []
        
        if created_tasks:
            task_summaries = []
            for task in created_tasks:
                if task.is_recurring:
                    pattern_text = self._format_recurrence_pattern(task)
                    summary = f"✅ {task.description} 🔄 ({pattern_text})"
                else:
                    summary = f"✅ {task.description}"
                
                if task.due_date:
                    local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                    summary += f" (יעד: {local_time.strftime('%d/%m %H:%M')})"
                task_summaries.append(summary)
            
            task_word = "משימה" if len(created_tasks) == 1 else "משימות"
            response_parts.append(f"נוצרו {len(created_tasks)} {task_word}:\n" + "\n".join(task_summaries))
        
        if actions_performed['complete']:
            task_word = "משימה" if len(actions_performed['complete']) == 1 else "משימות"
            response_parts.append(f"✅ הושלמו {len(actions_performed['complete'])} {task_word}:\n" + "\n".join(actions_performed['complete']))
        
        if actions_performed['update']:
            task_word = "משימה" if len(actions_performed['update']) == 1 else "משימות"
            response_parts.append(f"✏️ עודכנו {len(actions_performed['update'])} {task_word}:\n" + "\n".join(actions_performed['update']))
        
        if actions_performed['reschedule']:
            task_word = "משימה" if len(actions_performed['reschedule']) == 1 else "משימות"
            response_parts.append(f"📅 נדחו {len(actions_performed['reschedule'])} {task_word}:\n" + "\n".join(actions_performed['reschedule']))
        
        if actions_performed['stop_series']:
            task_word = "סדרה" if len(actions_performed['stop_series']) == 1 else "סדרות"
            response_parts.append(f"🛑 נעצרו {len(actions_performed['stop_series'])} {task_word}:\n" + "\n".join(actions_performed['stop_series']))
        
        if actions_performed['complete_series']:
            task_word = "סדרה" if len(actions_performed['complete_series']) == 1 else "סדרות"
            response_parts.append(f"✅ הושלמו {len(actions_performed['complete_series'])} {task_word}:\n" + "\n".join(actions_performed['complete_series']))
        
        if deleted_tasks:
            task_word = "משימה" if len(deleted_tasks) == 1 else "משימות"
            response_parts.append(f"🗑️ נמחקו {len(deleted_tasks)} {task_word}:\n" + "\n".join(deleted_tasks))
        
        if query_results:
            response_parts.append("\n".join(query_results))
        
        if failed_tasks:
            task_word = "משימה" if len(failed_tasks) == 1 else "משימות"
            response_parts.append(f"⚠️ נכשל בעיבוד {len(failed_tasks)} {task_word}:\n" + "\n".join(failed_tasks))
        
        return "\n\n".join(response_parts) if response_parts else ""
    
    def _handle_task_completion(self, user_id: int, description: str, original_message: str = None) -> Tuple[bool, str]:
        """Handle task completion based on description or number"""
        try:
            # Check if description is a digit
            if description.isdigit():
                task_id = int(description)
                
                # Try as task ID first (check if task with that ID exists for user)
                success, message = self._complete_task_by_id(user_id, task_id)
                if success:
                    return success, message
                
                # If not found by ID, try as position number
                return self._complete_task_by_number(user_id, task_id)
            
            # Otherwise, try to complete by description match
            return self._complete_task_by_description(user_id, description)
            
        except Exception as e:
            print(f"❌ Error handling task completion: {e}")
            return False, str(e)
    
    def _complete_task_by_id(self, user_id: int, task_id: int) -> Tuple[bool, str]:
        """Complete task by its database ID"""
        try:
            task = Task.query.filter_by(id=task_id, user_id=user_id, status='pending').first()
            
            if not task:
                return False, f"❌ משימה #{task_id} לא נמצאה או כבר הושלמה"
            
            success, message = self.complete_task(task.id, user_id)
            if success:
                return True, f"#{task_id}: {task.description[:50]}..."
            else:
                return False, message
        except Exception as e:
            print(f"❌ Error completing task by ID: {e}")
            return False, str(e)
    
    def _complete_task_by_number(self, user_id: int, task_number: int) -> Tuple[bool, str]:
        """Complete task by its number in the list"""
        try:
            # Get pending tasks
            tasks = self.get_user_tasks(user_id, status='pending', limit=100)
            
            if not tasks:
                return False, "❌ לא נמצאו משימות פתוחות"
            
            if task_number < 1 or task_number > len(tasks):
                return False, f"❌ משימה מספר {task_number} לא נמצאה. יש לך {len(tasks)} משימות פתוחות."
            
            # Select the task by number (1-indexed)
            task_to_complete = tasks[task_number - 1]
            
            # Mark as completed
            success, message = self.complete_task(task_to_complete.id, user_id)
            if success:
                return True, f"משימה {task_number}: {task_to_complete.description[:50]}..."
            else:
                return False, message
                
        except Exception as e:
            print(f"❌ Error completing task by number: {e}")
            return False, str(e)
    
    def _complete_task_by_description(self, user_id: int, description: str) -> Tuple[bool, str]:
        """Complete task by matching description using hybrid fuzzy + AI semantic matching"""
        try:
            # Get all pending tasks for user
            tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending'
            ).all()
            
            if not tasks:
                return False, "❌ אין לך משימות פתוחות"
            
            print(f"🔍 Hybrid matching: '{description}' against {len(tasks)} tasks")
            
            # LAYER 1: Fuzzy matching (fast, free, handles 95% of cases)
            match_result = self.fuzzy_matcher.find_single_best_match(description, tasks)
            
            if match_result:
                task, score = match_result
                print(f"   ✅ Fuzzy match: '{task.description}' (score: {score:.1f})")
                
                # High confidence (>= 65%) - execute immediately
                if score >= 65:
                    success, message = self.complete_task(task.id, user_id)
                    if success:
                        # Add confidence indicator for medium scores
                        if score < 85:
                            confidence_note = f" (התאמה: {int(score)}%)"
                        else:
                            confidence_note = ""
                        return True, f"{task.description[:50]}...{confidence_note}"
                    else:
                        return False, message
            
            # LAYER 2: Fallback to ILIKE substring matching
            # Note: AI semantic matching was considered but deemed unnecessary
            # Fuzzy matching already handles 95%+ of real-world cases (typos, partial matches)
            print(f"   ⚠️ Fuzzy match score too low, trying ILIKE fallback...")
            fallback_tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
                Task.description.ilike(f"%{description}%")
            ).all()
            
            if fallback_tasks:
                print(f"   ✅ ILIKE fallback found {len(fallback_tasks)} matches")
                best_task = self.fuzzy_matcher._select_by_due_date(fallback_tasks)
                if best_task:
                    success, message = self.complete_task(best_task.id, user_id)
                    if success:
                        return True, f"{best_task.description[:50]}..."
                    return False, message
            
            return False, f"❌ לא נמצאה משימה פתוחה התואמת '{description}'"
                
        except Exception as e:
            print(f"❌ Error completing task by description: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    def _select_best_recurring_instance(self, tasks: List[Task]) -> Optional[Task]:
        """Select the best recurring instance from multiple matches.
        
        Prioritizes:
        1. Tasks due today or overdue (most overdue first)
        2. Earliest upcoming task if none overdue
        
        Returns None if no recurring instances found.
        """
        # Filter to recurring instances only
        recurring_instances = [t for t in tasks if t.parent_recurring_id is not None]
        
        if not recurring_instances:
            return None
        
        # Calculate today start in Israel timezone, then convert to UTC
        now_israel = datetime.now(self.israel_tz)
        today_start = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_utc = today_start.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Find overdue or due today instances
        due_today_or_overdue = [
            t for t in recurring_instances 
            if t.due_date and t.due_date <= today_start_utc
        ]
        
        if due_today_or_overdue:
            # Complete the most overdue one (earliest due_date)
            return min(due_today_or_overdue, 
                      key=lambda t: t.due_date if t.due_date else datetime.max)
        else:
            # If none are overdue, pick the earliest upcoming one
            return min(recurring_instances,
                      key=lambda t: t.due_date if t.due_date else datetime.max)
    
    def _handle_task_deletion(self, user_id: int, description: str) -> Tuple[bool, str]:
        """Handle task deletion based on description or number"""
        try:
            # Check if description is a digit
            if description.isdigit():
                task_id = int(description)
                
                # Try as task ID first (check if task with that ID exists for user)
                success, message = self._delete_task_by_id(user_id, task_id)
                if success:
                    return success, message
                
                # If not found by ID, try as position number
                return self._delete_task_by_number(user_id, task_id)
            
            # Otherwise, try to delete by description match
            return self._delete_task_by_description(user_id, description)
            
        except Exception as e:
            print(f"❌ Error handling task deletion: {e}")
            return False, str(e)
    
    def _delete_task_by_id(self, user_id: int, task_id: int) -> Tuple[bool, str]:
        """Delete task by its database ID"""
        try:
            task = Task.query.filter_by(id=task_id, user_id=user_id, status='pending').first()
            
            if not task:
                return False, f"❌ משימה #{task_id} לא נמצאה"
            
            success, message = self.delete_task(task.id, user_id)
            if success:
                return True, f"#{task_id}: {task.description[:50]}..."
            else:
                return False, message
        except Exception as e:
            print(f"❌ Error deleting task by ID: {e}")
            return False, str(e)
    
    def _delete_task_by_number(self, user_id: int, task_number: int) -> Tuple[bool, str]:
        """Delete task by its number in the list"""
        try:
            # Get pending tasks
            tasks = self.get_user_tasks(user_id, status='pending', limit=100)
            
            if not tasks:
                return False, "❌ לא נמצאו משימות פתוחות"
            
            if task_number < 1 or task_number > len(tasks):
                return False, f"❌ משימה מספר {task_number} לא נמצאה. יש לך {len(tasks)} משימות פתוחות."
            
            # Select the task by number (1-indexed)
            task_to_delete = tasks[task_number - 1]
            
            # Delete the task
            success, message = self.delete_task(task_to_delete.id, user_id)
            if success:
                return True, f"משימה {task_number}: {task_to_delete.description[:50]}..."
            else:
                return False, message
                
        except Exception as e:
            print(f"❌ Error deleting task by number: {e}")
            return False, str(e)
    
    def _delete_task_by_description(self, user_id: int, description: str) -> Tuple[bool, str]:
        """Delete task by matching description using hybrid fuzzy + AI semantic matching"""
        try:
            # Get all pending tasks for user
            tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending'
            ).all()
            
            if not tasks:
                return False, "❌ אין לך משימות פתוחות"
            
            print(f"🔍 Hybrid matching: '{description}' against {len(tasks)} tasks")
            
            # LAYER 1: Fuzzy matching (fast, free, handles 95% of cases)
            match_result = self.fuzzy_matcher.find_single_best_match(description, tasks)
            
            if match_result:
                task, score = match_result
                print(f"   ✅ Fuzzy match: '{task.description}' (score: {score:.1f})")
                
                # High confidence (>= 65%) - execute immediately
                if score >= 65:
                    success, message = self.delete_task(task.id, user_id)
                    if success:
                        # Add confidence indicator for medium scores
                        if score < 85:
                            confidence_note = f" (התאמה: {int(score)}%)"
                        else:
                            confidence_note = ""
                        return True, f"{task.description[:50]}...{confidence_note}"
                    else:
                        return False, message
            
            # LAYER 2: Fallback to ILIKE substring matching
            # Note: AI semantic matching was considered but deemed unnecessary
            # Fuzzy matching already handles 95%+ of real-world cases (typos, partial matches)
            print(f"   ⚠️ Fuzzy match score too low, trying ILIKE fallback...")
            fallback_tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
                Task.description.ilike(f"%{description}%")
            ).all()
            
            if fallback_tasks:
                print(f"   ✅ ILIKE fallback found {len(fallback_tasks)} matches")
                best_task = self.fuzzy_matcher._select_by_due_date(fallback_tasks)
                if best_task:
                    success, message = self.delete_task(best_task.id, user_id)
                    if success:
                        return True, f"{best_task.description[:50]}..."
                    return False, message
            
            return False, f"❌ לא נמצאה משימה פתוחה התואמת '{description}'"
                
        except Exception as e:
            print(f"❌ Error deleting task by description: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    def _handle_task_update(self, user_id: int, task_data: Dict) -> Tuple[bool, str]:
        """Handle task update action with natural language date parsing"""
        try:
            task_id_str = task_data.get('task_id') or task_data.get('description')
            new_description = task_data.get('new_description')
            new_due_date_str = task_data.get('due_date')
            
            if not task_id_str:
                return False, "❌ אנא ציין איזו משימה לעדכן (למשל: 'עדכן משימה 2')"
            
            # Parse task ID or description
            if task_id_str.isdigit():
                task_id = int(task_id_str)
                
                # Try as database ID first
                task = Task.query.filter_by(id=task_id, user_id=user_id, status='pending').first()
                
                if not task:
                    # Try as position number
                    tasks = self.get_user_tasks(user_id, status='pending', limit=100)
                    if task_id < 1 or task_id > len(tasks):
                        return False, f"❌ משימה #{task_id} לא נמצאה. יש לך {len(tasks)} משימות פתוחות."
                    task = tasks[task_id - 1]
                    task_id = task.id
            else:
                # Try to match by description
                tasks = Task.query.filter(
                    Task.user_id == user_id,
                    Task.status == 'pending',
                    Task.description.ilike(f"%{task_id_str}%")
                ).all()
                
                if not tasks:
                    return False, f"❌ לא נמצאה משימה פתוחה התואמת '{task_id_str}'"
                
                if len(tasks) == 1:
                    # Single task found - ensure it's an instance, not a pattern
                    if tasks[0].is_recurring:
                        return False, "❌ לא ניתן לעדכן תבנית חוזרת ישירות. השתמש במספר המשימה לעדכון הסדרה."
                    task_id = tasks[0].id
                else:
                    # Multiple tasks found - prioritize recurring instances
                    best_task = self._select_best_recurring_instance(tasks)
                    
                    if best_task:
                        # Found a recurring instance to update
                        task_id = best_task.id
                    else:
                        # No recurring instances, return error asking for more specificity
                        return False, f"❌ נמצאו מספר משימות התואמות '{task_id_str}'. אנא היה יותר ספציפי או השתמש במספר המשימה."
            
            # Parse new due date if provided - USE NATURAL LANGUAGE PARSER!
            new_due_date = None
            if new_due_date_str:
                # Try natural language parsing first
                new_due_date = self.parse_date_from_text(new_due_date_str)
                
                # If that fails, try standard formats
                if not new_due_date:
                    try:
                        new_due_date = datetime.strptime(new_due_date_str, "%Y-%m-%d %H:%M")
                    except ValueError:
                        try:
                            new_due_date = datetime.strptime(new_due_date_str, "%Y-%m-%d")
                            new_due_date = new_due_date.replace(hour=9, minute=0)
                        except ValueError:
                            return False, f"❌ לא הצלחתי להבין את התאריך '{new_due_date_str}'. נסה 'מחר', 'יום שלישי', או תאריך מדויק."
            
            # Update the task
            success, message = self.update_task(task_id, user_id, new_description, new_due_date)
            return success, message
            
        except Exception as e:
            print(f"❌ Error handling task update: {e}")
            return False, "❌ שגיאה בעדכון המשימה. נסה שוב."
    
    def _handle_task_reschedule(self, user_id: int, task_data: Dict) -> Tuple[bool, str]:
        """Handle task reschedule action (change only due date) with natural language"""
        try:
            print(f"🔥 DEBUG - _handle_task_reschedule called")
            print(f"   task_data: {task_data}")
            
            task_id_str = task_data.get('task_id') or task_data.get('description')
            new_due_date_str = task_data.get('due_date')
            
            print(f"   task_id_str: '{task_id_str}', new_due_date_str: '{new_due_date_str}'")
            
            if not task_id_str:
                return False, "❌ אנא ציין איזו משימה לדחות (למשל: 'דחה משימה 2')"
            
            if not new_due_date_str:
                return False, "❌ אנא ציין מתי לדחות (למשל: 'למחר', 'ליום שלישי', 'בעוד שבוע')"
            
            # Parse task ID or description (same logic as update)
            if task_id_str.isdigit():
                task_id = int(task_id_str)
                print(f"   Searching for task with ID={task_id}")
                
                task = Task.query.filter_by(id=task_id, user_id=user_id, status='pending').first()
                
                if not task:
                    print(f"   ⚠️ Task ID={task_id} not found in DB (or not pending)")
                    tasks = self.get_user_tasks(user_id, status='pending', limit=100)
                    print(f"   Trying position-based: user has {len(tasks)} pending tasks")
                    if task_id < 1 or task_id > len(tasks):
                        print(f"   ❌ Position {task_id} out of range (1-{len(tasks)})")
                        return False, f"❌ משימה #{task_id} לא נמצאה. יש לך {len(tasks)} משימות פתוחות."
                    task = tasks[task_id - 1]
                    task_id = task.id
                    print(f"   ✅ Found task by position: position {task_id_str} → DB ID {task_id}")
                else:
                    print(f"   ✅ Found task by DB ID: {task_id}")
            else:
                # Try to match by description
                print(f"   Searching for task by description: '{task_id_str}'")
                tasks = Task.query.filter(
                    Task.user_id == user_id,
                    Task.status == 'pending',
                    Task.description.ilike(f"%{task_id_str}%")
                ).all()
                
                if not tasks:
                    print(f"   ❌ No tasks found matching '{task_id_str}'")
                    return False, f"❌ לא נמצאה משימה פתוחה התואמת '{task_id_str}'"
                
                if len(tasks) == 1:
                    # Single task found - ensure it's an instance, not a pattern
                    if tasks[0].is_recurring:
                        print(f"   ❌ Task is a recurring pattern, not an instance")
                        return False, "❌ לא ניתן לדחות תבנית חוזרת ישירות. השתמש במספר המשימה לדחיית הסדרה."
                    task_id = tasks[0].id
                    print(f"   ✅ Found task by description: '{task_id_str}' → DB ID {task_id}")
                else:
                    # Multiple tasks found - prioritize recurring instances
                    print(f"   ⚠️ Multiple tasks found ({len(tasks)}), selecting best recurring instance")
                    best_task = self._select_best_recurring_instance(tasks)
                    
                    if best_task:
                        # Found a recurring instance to reschedule
                        task_id = best_task.id
                        print(f"   ✅ Selected recurring instance: DB ID {task_id}")
                    else:
                        # No recurring instances, return error asking for more specificity
                        print(f"   ❌ No recurring instances found among {len(tasks)} matches")
                        return False, f"❌ נמצאו מספר משימות התואמות '{task_id_str}'. אנא היה יותר ספציפי או השתמש במספר המשימה."
            
            # Parse new due date - USE NATURAL LANGUAGE PARSER!
            new_due_date = self.parse_date_from_text(new_due_date_str)
            print(f"   Parsed due_date from '{new_due_date_str}' → {new_due_date}")
            
            # If natural language fails, try standard formats
            if not new_due_date:
                print(f"   ⚠️ Natural language parsing failed, trying standard formats")
                try:
                    new_due_date = datetime.strptime(new_due_date_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        new_due_date = datetime.strptime(new_due_date_str, "%Y-%m-%d")
                        new_due_date = new_due_date.replace(hour=9, minute=0)
                    except ValueError:
                        print(f"   ❌ All date parsing methods failed!")
                        return False, f"❌ לא הצלחתי להבין מתי לדחות. נסה 'מחר', 'יום רביעי ב-15:00', או תאריך מדויק."
            
            # Update only the due date
            print(f"   Calling update_task(task_id={task_id}, user_id={user_id}, new_due_date={new_due_date})")
            success, message = self.update_task(task_id, user_id, None, new_due_date)
            print(f"   update_task returned: success={success}, message='{message}'")
            return success, message
            
        except Exception as e:
            print(f"❌ Error handling task reschedule: {e}")
            import traceback
            traceback.print_exc()
            return False, "❌ שגיאה בדחיית המשימה. נסה שוב."
    
    def _handle_query_action(self, user_id: int, description: str, task_data: Dict) -> Optional[str]:
        """Handle query action by actually querying the database"""
        try:
            query_lower = description.lower()
            
            # NEW: Date-specific queries - "what tasks for tomorrow", "מה המשימות למחר"
            # Check for date keywords in Hebrew and English
            date_keywords = {
                'tomorrow': ['tomorrow', 'מחר', 'למחר', 'tomorrow\'s', 'for tomorrow'],
                'today': ['today', 'היום', 'להיום', 'today\'s', 'for today'],
                'yesterday': ['yesterday', 'אתמול', 'for yesterday', 'what did i do'],
                'this week': ['this week', 'השבוע', 'השבוע הזה', 'for this week'],
                'next week': ['next week', 'שבוע הבא', 'for next week']
            }
            
            # Check if query contains date keywords
            for key, keywords in date_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    # Calculate date range based on keyword
                    now_israel = datetime.now(self.israel_tz)
                    
                    if key == 'tomorrow':
                        target_date = now_israel + timedelta(days=1)
                        target_date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        target_date_end = target_date_start + timedelta(days=1)
                        date_display = 'מחר'
                    elif key == 'today':
                        target_date_start = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
                        target_date_end = target_date_start + timedelta(days=1)
                        date_display = 'היום'
                    elif key == 'yesterday':
                        target_date_start = now_israel.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
                        target_date_end = target_date_start + timedelta(days=1)
                        date_display = 'אתמול'
                    elif key == 'this week':
                        # Start of week (Sunday in Israel)
                        days_since_sunday = (now_israel.weekday() + 1) % 7
                        week_start = now_israel - timedelta(days=days_since_sunday)
                        target_date_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                        target_date_end = target_date_start + timedelta(days=7)
                        date_display = 'השבוע'
                    elif key == 'next week':
                        # Start of next week
                        days_since_sunday = (now_israel.weekday() + 1) % 7
                        week_start = now_israel - timedelta(days=days_since_sunday)
                        target_date_start = week_start + timedelta(days=7)
                        target_date_end = target_date_start + timedelta(days=7)
                        date_display = 'שבוע הבא'
                    else:
                        continue
                    
                    # Convert to UTC for database query
                    target_date_start_utc = target_date_start.astimezone(pytz.UTC).replace(tzinfo=None)
                    target_date_end_utc = target_date_end.astimezone(pytz.UTC).replace(tzinfo=None)
                    
                    # Query tasks for that date range
                    # If querying past (yesterday), include completed tasks
                    query = Task.query.filter(
                        Task.user_id == user_id,
                        Task.is_recurring == False,
                        Task.due_date >= target_date_start_utc,
                        Task.due_date < target_date_end_utc
                    )
                    
                    # Only filter by 'pending' if looking at future/today
                    # For past (yesterday), we want to see what was done too
                    if key not in ['yesterday']:
                         query = query.filter(Task.status == 'pending')
                    
                    tasks = query.order_by(Task.due_date.asc()).all()
                    
                    # Phase 2: Use get_full_schedule for today/tomorrow to include calendar events
                    if self.ai_service and key in ['today', 'tomorrow', 'this week'] and key != 'yesterday':
                        try:
                            user = User.query.get(user_id)
                            if user and user.google_calendar_enabled:
                                # Use AI service to get full schedule (tasks + events)
                                date_filter_map = {'today': 'today', 'tomorrow': 'tomorrow', 'this week': 'week'}
                                schedule = self.ai_service.get_full_schedule(user, date_filter_map[key])
                                return self.ai_service.format_schedule_response(schedule)
                        except Exception as e:
                            print(f"⚠️ Failed to get full schedule: {e}")
                            # Fall through to tasks-only display
                    
                    # Fallback: tasks only (or if calendar not enabled)
                    if not tasks:
                        return f"📋 אין לך משימות ל{date_display}"
                    
                    result = f"📋 המשימות שלך ל{date_display} ({len(tasks)}):\n\n"
                    result += self.format_task_list(tasks)
                    return result
            
            # Also check for due_date in task_data (from AI parsing) - handles natural language dates
            if task_data.get('due_date'):
                due_date_str = task_data['due_date']
                # Parse the date using the existing parse_date_from_text method
                parsed_date = self.parse_date_from_text(due_date_str)
                if parsed_date:
                    # Get tasks for that specific date
                    # Ensure parsed_date is timezone-aware
                    if parsed_date.tzinfo is None:
                        parsed_date = pytz.UTC.localize(parsed_date)
                    
                    date_start = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    date_end = date_start + timedelta(days=1)
                    
                    # Convert to UTC for database query
                    date_start_utc = date_start.astimezone(pytz.UTC).replace(tzinfo=None)
                    date_end_utc = date_end.astimezone(pytz.UTC).replace(tzinfo=None)
                    
                    # Check if query is for today
                    now_israel = datetime.now(self.israel_tz)
                    today_start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end_israel = today_start_israel + timedelta(days=1)
                    is_today_query = (date_start >= today_start_israel and date_start < today_end_israel)
                    
                    if is_today_query:
                        tasks = Task.query.filter(
                            Task.user_id == user_id,
                            Task.status == 'pending',
                            Task.is_recurring == False,
                            Task.due_date >= date_start_utc,
                            Task.due_date < date_end_utc
                        ).order_by(Task.due_date.asc()).all()
                    else:
                        tasks = Task.query.filter(
                            Task.user_id == user_id,
                            Task.status == 'pending',
                            Task.is_recurring == False,
                            Task.due_date >= date_start_utc,
                            Task.due_date < date_end_utc
                        ).order_by(Task.due_date.asc()).all()
                    
                    if not tasks:
                        # Format date for display
                        local_date = parsed_date.astimezone(self.israel_tz)
                        date_display = local_date.strftime('%d/%m/%Y')
                        return f"📋 אין לך משימות ל{date_display}"
                    
                    # Format date for display
                    local_date = parsed_date.astimezone(self.israel_tz)
                    date_display = local_date.strftime('%d/%m/%Y')
                    result = f"📋 המשימות שלך ל{date_display} ({len(tasks)}):\n\n"
                    result += self.format_task_list(tasks)
                    return result
            
            # Count queries - "how many tasks", "כמה משימות"
            if any(word in query_lower for word in ['כמה', 'how many', 'count']):
                pending_tasks = self.get_user_tasks(user_id, status='pending')
                if len(pending_tasks) == 0:
                    return "📋 אין לך משימות פתוחות כרגע!"
                elif len(pending_tasks) == 1:
                    return "📋 יש לך משימה פתוחה אחת"
                else:
                    return f"📋 יש לך {len(pending_tasks)} משימות פתוחות"
            
            # When queries - "when is", "מתי"
            elif any(word in query_lower for word in ['מתי', 'when']):
                # Extract keywords from query (remove question words)
                search_terms = query_lower
                for stop_word in ['מתי', 'when', 'is', 'the', 'my', 'ה', 'את', 'של']:
                    search_terms = search_terms.replace(stop_word, '')
                search_terms = search_terms.strip()
                
                if not search_terms:
                    return "❓ לא הבנתי איזו משימה אתה מחפש. נסה להיות יותר ספציפי."
                
                # Get all pending tasks
                all_tasks = Task.query.filter(
                    Task.user_id == user_id,
                    Task.status == 'pending'
                ).all()
                
                if not all_tasks:
                    return "📋 אין לך משימות פתוחות כרגע!"
                
                # Use fuzzy matching to find best matches
                matches = self.fuzzy_matcher.find_best_matches(search_terms, all_tasks, top_n=5)
                
                if not matches:
                    return f"❓ לא מצאתי משימה התואמת '{search_terms}'"
                elif len(matches) == 1:
                    task, score = matches[0]
                    if task.due_date:
                        local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                        return f"📅 {task.description}\nתאריך יעד: {local_time.strftime('%d/%m/%Y בשעה %H:%M')}"
                    else:
                        return f"📋 {task.description}\n(אין תאריך יעד מוגדר)"
                else:
                    result = f"מצאתי {len(matches)} משימות התואמות:\n"
                    for i, (task, score) in enumerate(matches, 1):
                        if task.due_date:
                            local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                            result += f"\n{i}. {task.description} - {local_time.strftime('%d/%m %H:%M')}"
                        else:
                            result += f"\n{i}. {task.description}"
                    return result
            
            # Status/statistics queries
            elif any(word in query_lower for word in ['מה המצב', 'status', 'statistics', 'סטטיסטיקה']):
                stats = self.get_task_stats(user_id)
                return f"📊 סטטיסטיקה:\n• משימות פתוחות: {stats['pending']}\n• הושלמו: {stats['completed']}\n• סה\"כ: {stats['total']}"
            
            # List queries - "what tasks", "מה המשימות"
            elif any(word in query_lower for word in ['מה', 'what', 'show', 'list', 'הצג', 'רשימה']):
                tasks = self.get_user_tasks(user_id, status='pending', limit=10)
                if not tasks:
                    return "📋 אין לך משימות פתוחות כרגע!"
                
                result = f"📋 המשימות שלך ({len(tasks)}):\n\n"
                result += self.format_task_list(tasks)
                return result
            
            # FALLBACK: General task listing for queries that don't match specific patterns
            # Catches natural language variations like "can you show me what I need to do?"
            task_related_keywords = [
                'task', 'tasks', 'todo', 'todos', 'things to do', 'need to do', 'have to do',
                'what to do', 'what do', 'show me', 'tell me',
                'משימה', 'משימות', 'לעשות', 'צריך', 'יש לי', 'מה יש', 'מה צריך', 'תראה',
                'מה לעשות', 'מה עלי', 'איזה משימות'
            ]
            
            if any(keyword in query_lower for keyword in task_related_keywords):
                # General listing request - show all pending tasks
                tasks = self.get_user_tasks(user_id, status='pending', limit=20)
                if not tasks:
                    return "📋 אין לך משימות פתוחות כרגע!"
                
                result = f"📋 המשימות שלך ({len(tasks)}):\n\n"
                result += self.format_task_list(tasks)
                return result
            
            # Default - return None to let AI response handle it
            return None
            
        except Exception as e:
            print(f"❌ Error handling query: {e}")
            return None
    
    # ========== RECURRING TASK METHODS ==========
    
    def create_recurring_task(self, user_id: int, description: str, due_date: datetime,
                             recurrence_pattern: str, recurrence_interval: int = 1,
                             recurrence_days_of_week: List[str] = None,
                             recurrence_end_date: datetime = None,
                             recurrence_day_of_month: int = None) -> Task:
        """Create a recurring task pattern"""
        import json
        from sqlalchemy.exc import IntegrityError
        
        # Validate pattern
        valid_patterns = ['daily', 'weekly', 'specific_days', 'interval', 'monthly']
        if recurrence_pattern not in valid_patterns:
            raise ValueError(f"Invalid recurrence pattern: {recurrence_pattern}")
        
        # Normalize patterns to always populate recurrence_days_of_week
        normalized_days_of_week = None
        
        if recurrence_pattern == 'daily':
            # Daily: all days of week
            normalized_days_of_week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
            
        elif recurrence_pattern == 'weekly':
            # Weekly: extract weekday from due_date
            if due_date:
                if due_date.tzinfo:
                    due_israel = due_date.astimezone(self.israel_tz)
                else:
                    due_israel = due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                weekday_num = due_israel.weekday()  # 0=Monday, 6=Sunday
                weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                normalized_days_of_week = [weekday_names[weekday_num]]
            else:
                # No due_date, cannot determine weekday
                normalized_days_of_week = None
                
        elif recurrence_pattern == 'specific_days':
            # Specific_days: use provided list (already normalized)
            normalized_days_of_week = recurrence_days_of_week
            
        elif recurrence_pattern == 'interval':
            # Interval: all days (but will check interval separately in scheduler)
            normalized_days_of_week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
            
        elif recurrence_pattern == 'monthly':
            # Monthly: no days_of_week, uses recurrence_day_of_month instead
            normalized_days_of_week = None
        
        # Create pattern task
        task = Task(
            user_id=user_id,
            description=description.strip()[:500],
            due_date=due_date,
            status='pending',
            is_recurring=True,
            recurrence_pattern=recurrence_pattern,
            recurrence_interval=recurrence_interval,
            recurrence_days_of_week=json.dumps(normalized_days_of_week) if normalized_days_of_week else None,
            recurrence_day_of_month=recurrence_day_of_month,
            recurrence_end_date=recurrence_end_date,
            recurring_instance_count=0,
            recurring_max_instances=100
        )
        
        db.session.add(task)
        db.session.flush()  # Get task.id before commit
        
        # Check if we should generate first instance immediately
        if due_date:
            now_israel = datetime.now(self.israel_tz)
            # Convert due_date to Israel timezone for comparison
            if due_date.tzinfo:
                due_israel = due_date.astimezone(self.israel_tz)
            else:
                # Assume UTC if no timezone
                due_israel = due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
            
            # If due_date is today or in the past, create first instance immediately
            if due_israel.date() <= now_israel.date():
                # Check if instance already exists for this date/time
                existing = Task.query.filter(
                    Task.parent_recurring_id == task.id,
                    Task.due_date == due_date
                ).first()
                
                if not existing:
                    # Create instance with the current due_date (first occurrence)
                    instance = Task(
                        user_id=user_id,
                        description=task.description,
                        due_date=due_date,
                        status='pending',
                        is_recurring=False,
                        parent_recurring_id=task.id
                    )
                    db.session.add(instance)
                    task.recurring_instance_count += 1
                    
                    # Calculate and update pattern's due_date to NEXT occurrence
                    next_due_date = self._calculate_next_due_date(task)
                    if next_due_date:
                        task.due_date = next_due_date
                        print(f"✅ Generated first instance immediately for pattern {task.id}, next due: {next_due_date}")
                    else:
                        print(f"⚠️ Could not calculate next due date for pattern {task.id}")
                    
                    # Sync first instance to calendar if enabled and has due_date
                    if self.calendar_service and due_date:
                        try:
                            # Flush to get instance.id before committing
                            db.session.flush()
                            success, event_id, error = self.calendar_service.create_calendar_event(instance)
                            if success:
                                print(f"📅 Synced first recurring instance {instance.id} to calendar: {event_id}")
                            elif error:
                                print(f"⚠️ Failed to sync first instance to calendar: {error}")
                        except Exception as e:
                            print(f"⚠️ Calendar sync error for first instance (non-fatal): {e}")
                else:
                    print(f"⚠️ Instance already exists for pattern {task.id} at {due_date}")
        
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            print(f"❌ Integrity error creating recurring task: {e}")
            raise
        
        print(f"✅ Created recurring task pattern for user {user_id}: {description[:50]}...")
        return task
    
    def generate_next_instance(self, pattern_task: Task) -> Optional[Task]:
        """Generate the next instance of a recurring task"""
        from sqlalchemy.exc import IntegrityError
        
        if not pattern_task.is_recurring or pattern_task.status != 'pending':
            return None
        
        # Check instance limit
        if pattern_task.recurring_instance_count >= pattern_task.recurring_max_instances:
            print(f"⚠️ Max instances ({pattern_task.recurring_max_instances}) reached for pattern {pattern_task.id}")
            return None
        
        # Check end date
        if pattern_task.recurrence_end_date and datetime.utcnow() > pattern_task.recurrence_end_date:
            print(f"⚠️ Recurrence end date reached for pattern {pattern_task.id}")
            return None
        
        instance_due_date = pattern_task.due_date
        if not instance_due_date:
            print(f"⚠️ Pattern {pattern_task.id} has no due_date set, skipping generation")
            return None
        
        # Normalise to UTC naive for comparisons/storage
        if instance_due_date.tzinfo:
            instance_due_date_utc = instance_due_date.astimezone(pytz.UTC)
        else:
            instance_due_date_utc = instance_due_date.replace(tzinfo=pytz.UTC)
        instance_due_date_naive = instance_due_date_utc.replace(tzinfo=None)
        
        # If an instance already exists for this occurrence, advance the pattern and return it
        existing_current = Task.query.filter(
            Task.parent_recurring_id == pattern_task.id,
            Task.due_date == instance_due_date_naive
        ).first()
        if existing_current:
            print(f"⚠️ Instance already exists for pattern {pattern_task.id} at {instance_due_date_naive}")
            next_due_date = self._calculate_next_due_date(pattern_task)
            if next_due_date and next_due_date != pattern_task.due_date:
                pattern_task.due_date = next_due_date
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    print(f"⚠️ Failed to advance due date for pattern {pattern_task.id} after detecting existing instance")
            return existing_current
        
        # Calculate next occurrence (after this one)
        next_due_date = self._calculate_next_due_date(pattern_task)
        if not next_due_date:
            return None
        
        # Delete old incomplete instances before creating new one
        old_pending_instances = Task.query.filter(
            Task.parent_recurring_id == pattern_task.id,
            Task.status == 'pending',
            Task.due_date < instance_due_date_naive
        ).all()
        
        deleted_count = 0
        if old_pending_instances:
            for old_instance in old_pending_instances:
                # Delete calendar event for old instance if exists
                if self.calendar_service and old_instance.calendar_event_id:
                    try:
                        success, error = self.calendar_service.delete_calendar_event(old_instance)
                        if success:
                            print(f"🗑️ Deleted calendar event for old instance {old_instance.id}")
                        else:
                            # Log but don't block - orphaned events are better than stuck tasks
                            print(f"⚠️ Failed to delete calendar event for old instance {old_instance.id}: {error}")
                    except Exception as e:
                        print(f"⚠️ Calendar sync error deleting old instance event (non-fatal): {e}")
                
                db.session.delete(old_instance)
                deleted_count += 1
            print(f"🗑️ Deleted {deleted_count} old incomplete instance(s) for pattern {pattern_task.id}")
        
        # Create new instance for the current due date
        instance = Task(
            user_id=pattern_task.user_id,
            description=pattern_task.description,
            due_date=instance_due_date_naive,
            status='pending',
            is_recurring=False,
            parent_recurring_id=pattern_task.id
        )
        
        db.session.add(instance)
        
        # Update pattern
        pattern_task.recurring_instance_count = max(0, pattern_task.recurring_instance_count - deleted_count) + 1
        pattern_task.due_date = next_due_date  # Move pattern to the next occurrence
        
        # Sync instance to calendar if enabled and has due_date
        # Do this before commit but after flush to get instance.id
        if self.calendar_service and instance_due_date_naive:
            try:
                db.session.flush()  # Get instance.id before committing
                success, event_id, error = self.calendar_service.create_calendar_event(instance)
                if success:
                    print(f"📅 Synced recurring instance {instance.id} to calendar: {event_id}")
                elif error:
                    print(f"⚠️ Failed to sync instance to calendar: {error}")
            except Exception as e:
                print(f"⚠️ Calendar sync error for instance (non-fatal): {e}")
        
        try:
            db.session.commit()
            if deleted_count > 0:
                print(f"✅ Deleted {deleted_count} old instance(s) and created new instance {instance.id} for pattern {pattern_task.id}")
            else:
                print(f"✅ Generated recurring instance {instance.id} from pattern {pattern_task.id}")
            return instance
        except IntegrityError:
            db.session.rollback()
            print(f"⚠️ Duplicate prevented for pattern {pattern_task.id} at {instance_due_date_naive}")
            existing = Task.query.filter(
                Task.parent_recurring_id == pattern_task.id,
                Task.due_date == instance_due_date_naive
            ).first()
            return existing
    
    def _calculate_next_due_date(self, pattern_task: Task) -> Optional[datetime]:
        """Calculate the next due date for a recurring pattern"""
        import json
        from datetime import timedelta
        
        if not pattern_task.due_date:
            return None
        
        # Normalize current due date to Israel timezone for calculations
        current_due = pattern_task.due_date
        if current_due.tzinfo:
            current_due_utc = current_due.astimezone(pytz.UTC)
        else:
            current_due_utc = current_due.replace(tzinfo=pytz.UTC)
        current_due_israel = current_due_utc.astimezone(self.israel_tz)
        
        if pattern_task.recurrence_pattern == 'daily':
            next_due_israel = current_due_israel + timedelta(days=pattern_task.recurrence_interval or 1)
        
        elif pattern_task.recurrence_pattern == 'weekly':
            next_due_israel = current_due_israel + timedelta(weeks=pattern_task.recurrence_interval or 1)
        
        elif pattern_task.recurrence_pattern == 'interval':
            next_due_israel = current_due_israel + timedelta(days=pattern_task.recurrence_interval or 1)
        
        elif pattern_task.recurrence_pattern == 'specific_days':
            # Parse days of week
            if not pattern_task.recurrence_days_of_week:
                return None
            
            days_list = json.loads(pattern_task.recurrence_days_of_week)
            day_mapping = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            target_weekdays = [day_mapping[d.lower()] for d in days_list if d.lower() in day_mapping]
            
            if not target_weekdays:
                return None
            
            # Find next matching weekday (strictly after current occurrence)
            search_date = current_due_israel + timedelta(days=1)
            for _ in range(7):  # Check up to 7 days ahead
                if search_date.weekday() in target_weekdays:
                    next_due_israel = search_date.replace(
                        hour=current_due_israel.hour,
                        minute=current_due_israel.minute,
                        second=current_due_israel.second,
                        microsecond=current_due_israel.microsecond
                    )
                    break
                search_date += timedelta(days=1)
            else:
                return None
        
        elif pattern_task.recurrence_pattern == 'monthly':
            if not pattern_task.recurrence_day_of_month:
                return None
            
            # Get next month
            next_month = current_due_israel.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)  # First day of next month
            
            # Try to set to recurrence_day_of_month
            try:
                next_due_israel = next_month.replace(day=pattern_task.recurrence_day_of_month)
            except ValueError:
                # Day doesn't exist in that month (e.g., Feb 31), use last day of month
                from calendar import monthrange
                last_day = monthrange(next_month.year, next_month.month)[1]
                next_due_israel = next_month.replace(day=last_day)
            
            # Preserve time from current_due
            next_due_israel = next_due_israel.replace(
                hour=current_due_israel.hour,
                minute=current_due_israel.minute,
                second=current_due_israel.second,
                microsecond=current_due_israel.microsecond
            )
        
        else:
            return None
        
        # Convert back to UTC naive for storage
        next_due_utc = next_due_israel.astimezone(pytz.UTC)
        return next_due_utc.replace(tzinfo=None)
    
    def stop_recurring_series(self, pattern_task_id: int, user_id: int, delete_instances: bool = False) -> Tuple[bool, str]:
        """Stop a recurring series (deletes future instances)"""
        try:
            pattern = Task.query.filter_by(id=pattern_task_id, user_id=user_id, is_recurring=True).first()
            
            if not pattern:
                return False, f"❌ לא נמצאה סדרה חוזרת #{pattern_task_id}"
            
            # Mark pattern as cancelled
            pattern.status = 'cancelled'
            
            # Delete all future pending instances
            if delete_instances:
                # Get instances first to delete their calendar events
                future_instances = Task.query.filter(
                    Task.parent_recurring_id == pattern_task_id,
                    Task.status == 'pending'
                ).all()
                
                # Delete calendar events for instances with proper error tracking
                deleted_cal_events = 0
                failed_cal_deletes = 0
                if self.calendar_service:
                    for instance in future_instances:
                        if instance.calendar_event_id:
                            try:
                                success, error = self.calendar_service.delete_calendar_event(instance)
                                if success:
                                    deleted_cal_events += 1
                                    print(f"🗑️ Deleted calendar event for stopped instance {instance.id}")
                                else:
                                    failed_cal_deletes += 1
                                    print(f"⚠️ Failed to delete calendar event for instance {instance.id}: {error}")
                            except Exception as e:
                                failed_cal_deletes += 1
                                print(f"⚠️ Calendar sync error deleting instance event (non-fatal): {e}")
                
                if failed_cal_deletes > 0:
                    print(f"⚠️ {failed_cal_deletes} calendar events may be orphaned (check Google Calendar manually)")
                
                # Now bulk delete the instances
                deleted_count = Task.query.filter(
                    Task.parent_recurring_id == pattern_task_id,
                    Task.status == 'pending'
                ).delete(synchronize_session=False)
                
                db.session.commit()
                
                return True, f"✅ הסדרה החוזרת נעצרה ו-{deleted_count} משימות עתידיות נמחקו"
            else:
                db.session.commit()
                return True, f"✅ הסדרה החוזרת נעצרה (משימות קיימות נשמרו)"
            
        except Exception as e:
            print(f"❌ Error stopping series: {e}")
            db.session.rollback()
            return False, "❌ שגיאה בעצירת הסדרה"
    
    def complete_recurring_series(self, pattern_task_id: int, user_id: int) -> Tuple[bool, str]:
        """Complete a recurring series (keeps all instances)"""
        try:
            pattern = Task.query.filter_by(id=pattern_task_id, user_id=user_id, is_recurring=True).first()
            
            if not pattern:
                return False, f"❌ לא נמצאה סדרה חוזרת #{pattern_task_id}"
            
            # Mark pattern as completed
            pattern.status = 'completed'
            pattern.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return True, f"✅ הסדרה החוזרת הושלמה (כל המשימות הקיימות נשמרו)"
            
        except Exception as e:
            print(f"❌ Error completing series: {e}")
            db.session.rollback()
            return False, "❌ שגיאה בהשלמת הסדרה"
    
    def get_recurring_patterns(self, user_id: int, active_only: bool = True) -> List[Task]:
        """Get all recurring patterns for a user"""
        try:
            query = Task.query.filter_by(user_id=user_id, is_recurring=True)
            
            if active_only:
                query = query.filter_by(status='pending')
            
            patterns = query.order_by(Task.created_at.desc()).all()
            return patterns
            
        except Exception as e:
            print(f"❌ Error getting recurring patterns: {e}")
            return []
    
    def _format_recurrence_pattern(self, task: Task) -> str:
        """Format recurrence pattern as Hebrew text"""
        import json
        
        if not task.is_recurring:
            return ""
        
        pattern = task.recurrence_pattern
        interval = task.recurrence_interval or 1
        
        if pattern == 'daily':
            if interval == 1:
                return "כל יום"
            else:
                return f"כל {interval} ימים"
        
        elif pattern == 'weekly':
            if interval == 1:
                return "כל שבוע"
            else:
                return f"כל {interval} שבועות"
        
        elif pattern == 'specific_days':
            if task.recurrence_days_of_week:
                days = json.loads(task.recurrence_days_of_week)
                day_names_heb = {
                    'monday': 'שני', 'tuesday': 'שלישי', 'wednesday': 'רביעי',
                    'thursday': 'חמישי', 'friday': 'שישי', 'saturday': 'שבת', 'sunday': 'ראשון'
                }
                hebrew_days = [day_names_heb.get(d.lower(), d) for d in days]
                return f"כל יום {' ו'.join(hebrew_days)}"
            return "ימים ספציפיים"
        
        elif pattern == 'interval':
            return f"כל {interval} ימים"
        
        elif pattern == 'monthly':
            if task.recurrence_day_of_month:
                return f"כל חודש ב-{task.recurrence_day_of_month}"
            return "כל חודש"
        
        return "חוזר"

    def update_recurring_pattern(self, pattern_id: int, user_id: int, task_data: Dict) -> Tuple[bool, str]:
        """Update a recurring pattern and propagate changes to future pending instances."""
        try:
            pattern = Task.query.filter_by(id=pattern_id, user_id=user_id, is_recurring=True).first()
            if not pattern:
                return False, f"❌ לא נמצאה סדרה חוזרת #{pattern_id}"

            old_description = pattern.description
            old_due = pattern.due_date
            # Safely extract time tuple, handling None case
            old_time_tuple = None
            if old_due:
                try:
                    old_time_tuple = (old_due.hour, old_due.minute)
                except AttributeError:
                    old_time_tuple = None

            # Extract fields
            new_description = task_data.get('new_description')
            new_due_str = task_data.get('due_date')
            new_pattern = task_data.get('recurrence_pattern')
            new_interval = task_data.get('recurrence_interval')
            new_days = task_data.get('recurrence_days_of_week')
            new_end_date_str = task_data.get('recurrence_end_date')

            # Parse dates
            new_due = None
            if new_due_str:
                new_due = self.parse_date_from_text(new_due_str)
            new_end = None
            if new_end_date_str:
                new_end = self.parse_date_from_text(new_end_date_str)

            # Apply updates to pattern
            if new_description:
                pattern.description = new_description.strip()[:500]
            if new_pattern:
                pattern.recurrence_pattern = new_pattern
            if new_interval is not None:
                pattern.recurrence_interval = int(new_interval) if str(new_interval).isdigit() else pattern.recurrence_interval
            if new_days is not None:
                try:
                    # Accept list or comma-separated string
                    if isinstance(new_days, str):
                        import json as _json
                        maybe_list = None
                        try:
                            maybe_list = _json.loads(new_days)
                        except Exception:
                            maybe_list = [d.strip() for d in new_days.split(',') if d.strip()]
                        new_days_list = maybe_list
                    else:
                        new_days_list = new_days
                    import json as _json
                    pattern.recurrence_days_of_week = _json.dumps(new_days_list) if new_days_list else None
                except Exception:
                    pass
            if new_end is not None:
                pattern.recurrence_end_date = new_end
            if new_due is not None:
                pattern.due_date = new_due

            db.session.commit()

            # Determine if time-of-day changed
            # Safely extract time tuple, handling None case
            new_time_tuple = None
            if pattern.due_date:
                try:
                    new_time_tuple = (pattern.due_date.hour, pattern.due_date.minute)
                except AttributeError:
                    new_time_tuple = None
            time_changed = old_time_tuple != new_time_tuple

            # Propagate to future pending instances
            future_instances = Task.query.filter(
                Task.parent_recurring_id == pattern_id,
                Task.status == 'pending'
                # Removed due_date filter to ensure we catch the single live instance even if it's overdue
            ).all()

            updated = 0
            for inst in future_instances:
                # update description
                if new_description:
                    inst.description = pattern.description
                # align time-of-day while keeping the instance date
                if time_changed and inst.due_date and pattern.due_date:
                    inst.due_date = inst.due_date.replace(
                        hour=pattern.due_date.hour,
                        minute=pattern.due_date.minute,
                        second=0,
                        microsecond=0
                    )
                
                # --- FIX: Sync Recurring Instance Updates to Calendar ---
                if self.calendar_service:
                    try:
                        if inst.calendar_event_id:
                            self.calendar_service.update_calendar_event(inst)
                        elif inst.due_date:
                            self.calendar_service.create_calendar_event(inst)
                    except Exception as e:
                        print(f"⚠️ Calendar sync warning for instance {inst.id}: {e}")
                # --------------------------------------------------------
                
                updated += 1

            if updated:
                db.session.commit()

            changes = []
            if new_description and new_description != old_description:
                changes.append("תיאור התבנית עודכן")
            if new_due is not None and new_due != old_due:
                changes.append("שעת/תאריך היעד של התבנית עודכן")
            if new_pattern or new_interval is not None or new_days is not None:
                changes.append("דפוס החזרתיות עודכן")
            if updated:
                changes.append(f"עודכנו {updated} מופעים עתידיים")

            message = "✅ התבנית החוזרת עודכנה" + (": " + ", ".join(changes) if changes else "")
            return True, message

        except Exception as e:
            print(f"❌ Error updating recurring pattern: {e}")
            db.session.rollback()
            return False, "❌ שגיאה בעדכון התבנית החוזרת"