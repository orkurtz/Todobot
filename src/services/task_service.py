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
    
    def get_user_tasks(self, user_id: int, status: str = 'pending', limit: int = 50) -> List[Task]:
        """Get user's tasks by status"""
        try:
            tasks = Task.query.filter_by(
                user_id=user_id,
                status=status
            ).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).limit(limit).all()
            
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
            
            # Tasks due today
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            due_today = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
                Task.due_date >= today_start,
                Task.due_date < today_end
            ).count()
            
            # Overdue tasks
            overdue = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
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
        
        # Try parsing explicit dates
        try:
            parsed_date = parser.parse(text, default=now)
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
                
                if not description:
                    continue
                
                if action == 'complete':
                    # Handle task completion
                    success, message = self._handle_task_completion(user_id, description, original_message)
                    if success:
                        completed_tasks.append(message)
                    else:
                        failed_tasks.append(f"Failed to complete: {message}")
                
                elif action == 'delete':
                    # Handle task deletion
                    success, message = self._handle_task_deletion(user_id, description)
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
                    
                    task = self.create_task(user_id, description, due_date)
                    created_tasks.append(task)
                
                elif action == 'update':
                    # Handle task update
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
                
            except Exception as e:
                print(f"❌ Failed to process task: {e}")
                failed_tasks.append(task_data.get('description', 'Unknown task'))
        
        # Build response message
        response_parts = []
        
        if created_tasks:
            task_summaries = []
            for task in created_tasks:
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
            task_id_str = task_data.get('task_id') or task_data.get('description')
            new_due_date_str = task_data.get('due_date')
            
            if not task_id_str:
                return False, "❌ אנא ציין איזו משימה לדחות (למשל: 'דחה משימה 2')"
            
            if not new_due_date_str:
                return False, "❌ אנא ציין מתי לדחות (למשל: 'למחר', 'ליום שלישי', 'בעוד שבוע')"
            
            # Parse task ID (same logic as update)
            if task_id_str.isdigit():
                task_id = int(task_id_str)
                
                task = Task.query.filter_by(id=task_id, user_id=user_id, status='pending').first()
                
                if not task:
                    tasks = self.get_user_tasks(user_id, status='pending', limit=100)
                    if task_id < 1 or task_id > len(tasks):
                        return False, f"❌ משימה #{task_id} לא נמצאה"
                    task = tasks[task_id - 1]
                    task_id = task.id
            else:
                return False, "❌ אנא ציין מספר משימה"
            
            # Parse new due date - USE NATURAL LANGUAGE PARSER!
            new_due_date = self.parse_date_from_text(new_due_date_str)
            
            # If natural language fails, try standard formats
            if not new_due_date:
                try:
                    new_due_date = datetime.strptime(new_due_date_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        new_due_date = datetime.strptime(new_due_date_str, "%Y-%m-%d")
                        new_due_date = new_due_date.replace(hour=9, minute=0)
                    except ValueError:
                        return False, f"❌ לא הצלחתי להבין מתי לדחות. נסה 'מחר', 'יום רביעי ב-15:00', או תאריך מדויק."
            
            # Update only the due date
            success, message = self.update_task(task_id, user_id, None, new_due_date)
            return success, message
            
        except Exception as e:
            print(f"❌ Error handling task reschedule: {e}")
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
