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
                return False, "Task not found or doesn't belong to you"
            
            if task.status == 'completed':
                return False, "Task is already completed"
            
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
                return False, "Task not found or doesn't belong to you"
            
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
        """Parse date/time from natural language text"""
        if not text:
            return None
        
        text = text.lower().strip()
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)
        
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
    
    def format_task_list(self, tasks: List[Task], show_due_date: bool = True) -> str:
        """Format task list for display"""
        if not tasks:
            return "📋 No tasks found."
        
        formatted_tasks = []
        for i, task in enumerate(tasks, 1):
            task_text = f"{i}. {task.description}"
            
            if show_due_date and task.due_date:
                # Convert UTC to Israel timezone for display
                local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                formatted_date = local_time.strftime("%m/%d %H:%M")
                
                # Add urgency indicators
                now = datetime.utcnow()
                if task.due_date < now:
                    task_text += f" ⚠️ (Overdue - {formatted_date})"
                elif task.due_date < now + timedelta(hours=24):
                    task_text += f" 🔥 (Due {formatted_date})"
                else:
                    task_text += f" 📅 (Due {formatted_date})"
            
            formatted_tasks.append(task_text)
        
        return "\n".join(formatted_tasks)
    
    def execute_parsed_tasks(self, user_id: int, parsed_tasks: List[Dict], original_message: str = None) -> str:
        """Execute parsed tasks from AI and return summary"""
        if not parsed_tasks:
            return ""
        
        created_tasks = []
        failed_tasks = []
        
        for task_data in parsed_tasks:
            try:
                description = task_data.get('description', '').strip()
                if not description:
                    continue
                
                # Parse due date if provided
                due_date = None
                due_date_str = task_data.get('due_date')
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M")
                    except ValueError:
                        # Try parsing as date only
                        try:
                            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                            due_date = due_date.replace(hour=9, minute=0)  # Default to 9 AM
                        except ValueError:
                            pass
                
                # Create the task
                task = self.create_task(user_id, description, due_date)
                created_tasks.append(task)
                
            except Exception as e:
                print(f"❌ Failed to create task from parsed data: {e}")
                failed_tasks.append(task_data.get('description', 'Unknown task'))
        
        # Build response message
        if created_tasks:
            task_summaries = []
            for task in created_tasks:
                summary = f"✅ {task.description}"
                if task.due_date:
                    local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                    summary += f" (Due: {local_time.strftime('%m/%d %H:%M')})"
                task_summaries.append(summary)
            
            response = f"Created {len(created_tasks)} task{'s' if len(created_tasks) != 1 else ''}:\n\n"
            response += "\n".join(task_summaries)
            
            if failed_tasks:
                response += f"\n\n⚠️ Failed to create {len(failed_tasks)} task(s)"
            
            return response
        
        return ""