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

class TaskService:
    """Handle task-related operations"""
    
    def __init__(self):
        self.israel_tz = pytz.timezone('Asia/Jerusalem')
    
    def create_task(self, user_id: int, description: str, due_date: datetime = None) -> Task:
        """Create a new task for user"""
        try:
            task = Task(
                user_id=user_id,
                description=description.strip()[:500],  # Limit description length
                due_date=due_date,
                status='pending'
            )
            
            db.session.add(task)
            db.session.commit()
            
            print(f"✅ Created task for user {user_id}: {description[:50]}...")
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
                tasks = base_query.order_by(Task.updated_at.desc()).limit(limit).all()
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
            
            db.session.commit()
            
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
            
            tasks = Task.query.filter(
                Task.status == 'pending',
                Task.is_recurring == False,  # Only show instances, not patterns
                Task.due_date.isnot(None),
                Task.due_date >= now,
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
            db.session.commit()
            
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
                
                # Add urgency indicators
                now = datetime.utcnow()
                if task.due_date < now:
                    task_text += f" ⚠️ (באיחור - {formatted_date})"
                elif task.due_date < now + timedelta(hours=24):
                    task_text += f" 🔥 (יעד היום {formatted_date})"
                else:
                    task_text += f" 📅 (יעד {formatted_date})"
            
            formatted_tasks.append(task_text)
        
        return "\n".join(formatted_tasks)
    
    def execute_parsed_tasks(self, user_id: int, parsed_tasks: List[Dict], original_message: str = None) -> str:
        """Execute parsed tasks from AI and return summary"""
        if not parsed_tasks:
            return ""
        
        created_tasks = []
        completed_tasks = []
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
                        completed_tasks.append(message)
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
                            recurrence_end_date
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
                        completed_tasks.append(message)  # Use completed_tasks list for updates
                    else:
                        failed_tasks.append(message)
                
                elif action == 'reschedule':
                    # Handle task reschedule
                    success, message = self._handle_task_reschedule(user_id, task_data)
                    if success:
                        completed_tasks.append(message)
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
                            completed_tasks.append(message)
                        else:
                            failed_tasks.append(message)
                
                elif action == 'complete_series':
                    task_id_str = task_data.get('task_id') or task_data.get('description')
                    if task_id_str and task_id_str.isdigit():
                        task_id = int(task_id_str)
                        success, message = self.complete_recurring_series(task_id, user_id)
                        if success:
                            completed_tasks.append(message)
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
        
        if completed_tasks:
            task_word = "משימה" if len(completed_tasks) == 1 else "משימות"
            response_parts.append(f"✅ הושלמו {len(completed_tasks)} {task_word}:\n" + "\n".join(completed_tasks))
        
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
        """Complete task by matching description"""
        try:
            # Search for tasks with similar description
            tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
                Task.description.ilike(f"%{description}%")
            ).all()
            
            if not tasks:
                return False, f"❌ לא נמצאה משימה פתוחה התואמת '{description}'"
            
            if len(tasks) == 1:
                # Single task found
                success, message = self.complete_task(tasks[0].id, user_id)
                if success:
                    return True, f"{tasks[0].description[:50]}..."
                else:
                    return False, message
            else:
                # Multiple tasks found
                return False, f"❌ נמצאו מספר משימות התואמות '{description}'. אנא היה יותר ספציפי או השתמש במספר המשימה."
                
        except Exception as e:
            print(f"❌ Error completing task by description: {e}")
            return False, str(e)
    
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
        """Delete task by matching description"""
        try:
            # Search for tasks with similar description
            tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
                Task.description.ilike(f"%{description}%")
            ).all()
            
            if not tasks:
                return False, f"❌ לא נמצאה משימה פתוחה התואמת '{description}'"
            
            if len(tasks) == 1:
                # Single task found
                success, message = self.delete_task(tasks[0].id, user_id)
                if success:
                    return True, f"{tasks[0].description[:50]}..."
                else:
                    return False, message
            else:
                # Multiple tasks found
                return False, f"❌ נמצאו מספר משימות התואמות '{description}'. אנא היה יותר ספציפי או השתמש במספר המשימה."
                
        except Exception as e:
            print(f"❌ Error deleting task by description: {e}")
            return False, str(e)
    
    def _handle_task_update(self, user_id: int, task_data: Dict) -> Tuple[bool, str]:
        """Handle task update action with natural language date parsing"""
        try:
            task_id_str = task_data.get('task_id') or task_data.get('description')
            new_description = task_data.get('new_description')
            new_due_date_str = task_data.get('due_date')
            
            if not task_id_str:
                return False, "❌ אנא ציין איזו משימה לעדכן (למשל: 'עדכן משימה 2')"
            
            # Parse task ID
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
                return False, "❌ אנא ציין מספר משימה (למשל: 2, 3, 42)"
            
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
            
            # Parse task ID (same logic as update)
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
                return False, "❌ אנא ציין מספר משימה"
            
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
                
                # Search for task
                tasks = Task.query.filter(
                    Task.user_id == user_id,
                    Task.status == 'pending',
                    Task.description.ilike(f"%{search_terms}%")
                ).all()
                
                if not tasks:
                    return f"❓ לא מצאתי משימה התואמת '{search_terms}'"
                elif len(tasks) == 1:
                    task = tasks[0]
                    if task.due_date:
                        local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                        return f"📅 {task.description}\nתאריך יעד: {local_time.strftime('%d/%m/%Y בשעה %H:%M')}"
                    else:
                        return f"📋 {task.description}\n(אין תאריך יעד מוגדר)"
                else:
                    result = f"מצאתי {len(tasks)} משימות התואמות:\n"
                    for i, task in enumerate(tasks[:5], 1):
                        if task.due_date:
                            local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                            result += f"\n{i}. {task.description} - {local_time.strftime('%d/%m %H:%M')}"
                        else:
                            result += f"\n{i}. {task.description}"
                    return result
            
            # Status/statistics queries
            elif any(word in query_lower for word in ['מה המצב', 'status', 'statistics', 'סטטיסטיקה']):
                stats = self.get_user_stats(user_id)
                return f"📊 סטטיסטיקה:\n• משימות פתוחות: {stats['pending']}\n• הושלמו: {stats['completed']}\n• סה\"כ: {stats['total']}"
            
            # List queries - "what tasks", "מה המשימות"
            elif any(word in query_lower for word in ['מה', 'what', 'show', 'list', 'הצג', 'רשימה']):
                tasks = self.get_user_tasks(user_id, status='pending', limit=10)
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
                             recurrence_end_date: datetime = None) -> Task:
        """Create a recurring task pattern"""
        import json
        from sqlalchemy.exc import IntegrityError
        
        # Validate pattern
        valid_patterns = ['daily', 'weekly', 'specific_days', 'interval']
        if recurrence_pattern not in valid_patterns:
            raise ValueError(f"Invalid recurrence pattern: {recurrence_pattern}")
        
        # Create pattern task
        task = Task(
            user_id=user_id,
            description=description.strip()[:500],
            due_date=due_date,
            status='pending',
            is_recurring=True,
            recurrence_pattern=recurrence_pattern,
            recurrence_interval=recurrence_interval,
            recurrence_days_of_week=json.dumps(recurrence_days_of_week) if recurrence_days_of_week else None,
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
        import json
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
        
        # Calculate next due date
        next_due_date = self._calculate_next_due_date(pattern_task)
        if not next_due_date:
            return None
        
        # Check if instance already exists for this date
        existing = Task.query.filter(
            Task.parent_recurring_id == pattern_task.id,
            Task.due_date == next_due_date
        ).first()
        
        if existing:
            print(f"⚠️ Instance already exists for {next_due_date}")
            return existing
        
        # Delete old incomplete instances before creating new one
        # For daily: Delete all old pending instances
        # For non-daily: Delete all old pending instances (they stay until new one is created)
        old_pending_instances = Task.query.filter(
            Task.parent_recurring_id == pattern_task.id,
            Task.status == 'pending',
            Task.due_date < next_due_date
        ).all()
        
        deleted_count = 0
        if old_pending_instances:
            for old_instance in old_pending_instances:
                db.session.delete(old_instance)
                deleted_count += 1
            print(f"🗑️ Deleted {deleted_count} old incomplete instance(s) for pattern {pattern_task.id}")
        
        # Create new instance
        instance = Task(
            user_id=pattern_task.user_id,
            description=pattern_task.description,
            due_date=next_due_date,
            status='pending',
            is_recurring=False,
            parent_recurring_id=pattern_task.id
        )
        
        db.session.add(instance)
        
        # Update pattern
        # Adjust instance count: increment for new instance, decrement for deleted old instances
        pattern_task.recurring_instance_count = max(0, pattern_task.recurring_instance_count - deleted_count) + 1
        pattern_task.due_date = next_due_date  # Update pattern's due_date to next occurrence
        
        try:
            db.session.commit()
            if deleted_count > 0:
                print(f"✅ Deleted {deleted_count} old instance(s) and created new instance {instance.id} for pattern {pattern_task.id}")
            else:
                print(f"✅ Generated recurring instance {instance.id} from pattern {pattern_task.id}")
            return instance
        except IntegrityError:
            db.session.rollback()
            print(f"⚠️ Duplicate prevented for pattern {pattern_task.id} at {next_due_date}")
            existing = Task.query.filter(
                Task.parent_recurring_id == pattern_task.id,
                Task.due_date == next_due_date
            ).first()
            return existing
    
    def _calculate_next_due_date(self, pattern_task: Task) -> Optional[datetime]:
        """Calculate the next due date for a recurring pattern"""
        import json
        from datetime import timedelta
        
        if not pattern_task.due_date:
            return None
        
        current_due = pattern_task.due_date
        now_israel = datetime.now(self.israel_tz)
        
        if pattern_task.recurrence_pattern == 'daily':
            next_due = current_due + timedelta(days=pattern_task.recurrence_interval or 1)
        
        elif pattern_task.recurrence_pattern == 'weekly':
            next_due = current_due + timedelta(weeks=pattern_task.recurrence_interval or 1)
        
        elif pattern_task.recurrence_pattern == 'interval':
            next_due = current_due + timedelta(days=pattern_task.recurrence_interval or 1)
        
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
            
            # Find next matching weekday
            search_date = current_due + timedelta(days=1)
            for _ in range(7):  # Check up to 7 days ahead
                if search_date.weekday() in target_weekdays:
                    # Keep the same time
                    next_due = search_date.replace(
                        hour=current_due.hour,
                        minute=current_due.minute,
                        second=0,
                        microsecond=0
                    )
                    break
                search_date += timedelta(days=1)
            else:
                return None
        
        else:
            return None
        
        return next_due
    
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
                deleted_count = Task.query.filter(
                    Task.parent_recurring_id == pattern_task_id,
                    Task.status == 'pending'
                ).delete()
                
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
                Task.status == 'pending',
                Task.due_date >= datetime.utcnow()
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