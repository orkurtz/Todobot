"""
Scheduler service for handling reminders and background tasks
"""
import os
import atexit
import json
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from ..models.database import db, Task, User, Message
from ..services.encryption import encryption_service

class SchedulerService:
    """Handle scheduled tasks like reminders"""
    
    def __init__(self, redis_client=None, whatsapp_service=None):
        self.redis_client = redis_client
        self.whatsapp_service = whatsapp_service
        self.scheduler = None
        self.israel_tz = pytz.timezone('Asia/Jerusalem')
        
    def initialize_scheduler(self, app):
        """Initialize and start the scheduler"""
        if self.scheduler and hasattr(self.scheduler, 'running') and self.scheduler.running:
            print("Scheduler is already running - skipping initialization")
            return True
        
        try:
            # Configure job store
            if self.redis_client:
                jobstores = {
                    'default': RedisJobStore(
                        host=self.redis_client.connection_pool.connection_kwargs.get('host', 'localhost'),
                        port=self.redis_client.connection_pool.connection_kwargs.get('port', 6379),
                        db=1  # Use different DB for jobs
                    )
                }
                print("Using Redis job store for scheduler")
            else:
                jobstores = {'default': MemoryJobStore()}
                print("Using memory job store for scheduler")
            
            # Configure executors
            executors = {
                'default': ThreadPoolExecutor(20)
            }
            
            # Job defaults
            job_defaults = {
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 30
            }
            
            # Create scheduler
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults
            )
            
            print("Starting scheduler...")
            self.scheduler.start()
            print("Scheduler started successfully!")
            
            # Add recurring job to check for due reminders
            self.scheduler.add_job(
                func=self._check_and_send_due_reminders,
                trigger="interval",
                seconds=30,
                id="db_reminder_checker",
                name="Check database for due reminders",
                kwargs={'app': app}
            )
            print("Added recurring job to check database for due reminders every 30 seconds")
            
            # Shutdown scheduler on exit
            atexit.register(self._shutdown_scheduler)
            
            return True
            
        except Exception as e:
            print(f"Failed to start scheduler: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _shutdown_scheduler(self):
        """Shutdown scheduler gracefully"""
        if self.scheduler and hasattr(self.scheduler, 'running') and self.scheduler.running:
            print("Shutting down scheduler...")
            self.scheduler.shutdown(wait=False)
    
    def _check_and_send_due_reminders(self, app):
        """Database-based reminder system - checks for tasks due for reminders"""
        if not self.whatsapp_service:
            return
            
        try:
            with app.app_context():
                now = datetime.utcnow()
                
                # Find tasks that are due for reminders and haven't been sent yet
                due_tasks = Task.query.filter(
                    Task.due_date <= now,
                    (Task.reminder_sent == False) | (Task.reminder_sent.is_(None)),
                    Task.status == 'pending',
                    Task.due_date.isnot(None)
                ).all()
                
                if len(due_tasks) == 0:
                    return
                
                print(f"Found {len(due_tasks)} tasks due for reminders")
                
                # Send reminders
                for task in due_tasks:
                    try:
                        self._send_task_reminder(task, app)
                    except Exception as task_error:
                        print(f"Error processing reminder for task {task.id}: {task_error}")
                        continue
                        
        except Exception as e:
            print(f"Error in check_and_send_due_reminders: {e}")
    
    def _send_task_reminder(self, task, app):
        """Send reminder message for a task"""
        # Use Redis lock to prevent duplicate execution
        lock_key = f"reminder_lock:{task.id}"
        
        try:
            if self.redis_client:
                lock_acquired = self.redis_client.set(lock_key, "locked", nx=True, ex=30)
                if not lock_acquired:
                    print(f"Another process is handling reminder for task {task.id} - skipping")
                    return
            
            with app.app_context():
                # Get user information
                user = User.query.get(task.user_id)
                if not user:
                    print(f"User not found for task {task.id}")
                    return
                
                # Create reminder message
                current_time = datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                
                reminder_text = f"🔔 תזכורת!\n\n📋 {task.description}\n\n"
                
                if task.due_date:
                    due_local = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                    if due_local.date() == current_time.date():
                        reminder_text += f"⏰ משימה להיום בשעה {due_local.strftime('%H:%M')}\n\n"
                    else:
                        reminder_text += f"⏰ משימה ל{due_local.strftime('%d/%m/%Y')} בשעה {due_local.strftime('%H:%M')}\n\n"
                
                reminder_text += "כדי לסמן כהושלמה, כתב 'סיימתי' והתיאור של המשימה."
                
                # Send WhatsApp message
                result = self.whatsapp_service.send_message(user.phone_number, reminder_text)
                
                if result.get("success"):
                    print(f"Sent reminder for task '{task.description[:50]}...' to user {user.phone_number}")
                    
                    # Save the reminder message for reaction handling
                    whatsapp_msg_id = result.get("response", {}).get("messages", [{}])[0].get("id")
                    if whatsapp_msg_id:
                        parsed_tasks = json.dumps({
                            "tasks": [{"task_id": task.id, "description": task.description}]
                        })
                        
                        message = Message(
                            user_id=user.id,
                            message_type='reminder',
                            whatsapp_message_id=whatsapp_msg_id,
                            parsed_tasks=parsed_tasks
                        )
                        message.content = reminder_text
                        message.ai_response = reminder_text
                        
                        db.session.add(message)
                        db.session.commit()
                        
                        print(f"Saved reminder message with ID {whatsapp_msg_id} for reaction handling")
                    
                    # Mark as reminder sent
                    task.reminder_sent = True
                    db.session.commit()
                    print(f"Marked task {task.id} as reminder sent")
                    
                else:
                    print(f"Failed to send reminder for task {task.id}: {result.get('error')}")
                
        except Exception as e:
            print(f"Error sending reminder for task {task.id}: {e}")
        finally:
            # Release Redis lock
            if self.redis_client:
                try:
                    self.redis_client.delete(lock_key)
                except Exception:
                    pass
    
    def schedule_task_reminder(self, task_id, reminder_datetime):
        """Schedule a specific reminder for a task"""
        if not self.scheduler:
            return False
            
        try:
            self.scheduler.add_job(
                func=self._send_single_task_reminder,
                trigger='date',
                run_date=reminder_datetime,
                args=[task_id],
                id=f"reminder_{task_id}",
                name=f"Task {task_id} reminder",
                replace_existing=True
            )
            print(f"Scheduled reminder for task {task_id} at {reminder_datetime}")
            return True
        except Exception as e:
            print(f"Failed to schedule reminder for task {task_id}: {e}")
            return False
    
    def _send_single_task_reminder(self, task_id):
        """Send reminder for a single task (used by scheduled jobs)"""
        from .. import app  # Import here to avoid circular imports
        
        try:
            with app.app_context():
                task = Task.query.get(task_id)
                if task and task.status == 'pending':
                    self._send_task_reminder(task, app)
        except Exception as e:
            print(f"Error in single task reminder for {task_id}: {e}")
    
    def cancel_task_reminder(self, task_id):
        """Cancel a scheduled reminder for a task"""
        if not self.scheduler:
            return False
            
        try:
            self.scheduler.remove_job(f"reminder_{task_id}")
            print(f"Cancelled scheduled reminder for task {task_id}")
            return True
        except Exception as e:
            print(f"Failed to cancel reminder for task {task_id}: {e}")
            return False
    
    def get_scheduled_jobs(self):
        """Get list of scheduled jobs"""
        if not self.scheduler:
            return []
        
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            return jobs
        except Exception as e:
            print(f"Error getting scheduled jobs: {e}")
            return []
    
    def is_running(self):
        """Check if scheduler is running"""
        return self.scheduler and hasattr(self.scheduler, 'running') and self.scheduler.running