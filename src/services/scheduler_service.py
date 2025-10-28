"""
Scheduler service for handling reminders and background tasks
"""
import os
import atexit
import json
from datetime import datetime
import pytz
import re # Ensure re is imported if you used the JSON cleaning fix elsewhere or might need it
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

# Make sure these imports are correct based on your project structure
from ..models.database import db, Task, User, Message
# from ..services.encryption import encryption_service # Assuming you might use this later

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
            print("WhatsApp service not available for scheduler.")
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
                    # print("No tasks due for reminders.") # Optional: Reduce log noise
                    return

                print(f"Found {len(due_tasks)} tasks due for reminders")

                # Send reminders
                for task in due_tasks:
                    try:
                        # Pass the original task object fetched here
                        self._send_task_reminder(task, app)
                    except Exception as task_error:
                        print(f"Error processing reminder loop for task {task.id}: {task_error}")
                        # Optionally rollback here if needed, though _send_task_reminder should handle its own
                        try:
                            if db.session.is_active:
                                db.session.rollback()
                        except Exception as rb_err:
                            print(f"Rollback error in main loop: {rb_err}")
                        continue # Continue to the next task

        except Exception as e:
            print(f"Error in check_and_send_due_reminders: {e}")
            # Ensure rollback if the main query fails
            try:
                if db.session.is_active:
                    db.session.rollback()
            except Exception as rb_err:
                print(f"Rollback error after main exception: {rb_err}")


    # --- THIS IS THE CORRECTED FUNCTION ---
    def _send_task_reminder(self, task, app):
        """Send reminder message for a task - CORRECTED VERSION"""
        lock_key = f"reminder_lock:{task.id}"
        lock_acquired = False # Flag to track lock status

        try:
            if self.redis_client:
                lock_acquired = self.redis_client.set(lock_key, "locked", nx=True, ex=30)
                if not lock_acquired:
                    print(f"Another process is handling reminder for task {task.id} - skipping")
                    return

            with app.app_context():
                # Re-fetch the task within this context to ensure it's session-bound
                current_task = Task.query.get(task.id)
                if not current_task:
                    print(f"Task {task.id} not found in DB - skipping reminder.")
                    return
                # Check reminder_sent status again within the lock
                if current_task.reminder_sent:
                    print(f"Task {task.id} was already reminded by another process - skipping.")
                    return

                user = User.query.get(current_task.user_id)
                if not user:
                    print(f"User not found for task {current_task.id}")
                    return

                # Create reminder message
                current_time = datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                reminder_text = f"🔔 תזכורת!\n\n📋 {current_task.description}\n\n"
                if current_task.due_date:
                    due_local = current_task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                    if due_local.date() == current_time.date():
                        reminder_text += f"⏰ משימה להיום בשעה {due_local.strftime('%H:%M')}\n\n"
                    else:
                        reminder_text += f"⏰ משימה ל{due_local.strftime('%d/%m/%Y')} בשעה {due_local.strftime('%H:%M')}\n\n"
                reminder_text += "כדי לסמן כהושלמה, כתב 'סיימתי' והתיאור של המשימה."

                # Send WhatsApp message
                result = self.whatsapp_service.send_message(user.phone_number, reminder_text)

                if result.get("success"):
                    print(f"Sent reminder for task '{current_task.description[:50]}...' to user {user.phone_number}")
                    whatsapp_msg_id = result.get("response", {}).get("messages", [{}])[0].get("id")

                    # --- Start single transaction ---
                    try:
                        message_to_save = None
                        if whatsapp_msg_id:
                            parsed_tasks = json.dumps({
                                "tasks": [{"task_id": current_task.id, "description": current_task.description}]
                            })
                            message_to_save = Message(
                                user_id=user.id,
                                message_type='reminder',
                                whatsapp_message_id=whatsapp_msg_id,
                                parsed_tasks=parsed_tasks,
                                content=reminder_text,
                                ai_response=reminder_text
                            )
                            db.session.add(message_to_save)
                            print(f"Prepared reminder message with ID {whatsapp_msg_id} for saving")

                        # Mark as reminder sent (using the attached current_task)
                        current_task.reminder_sent = True
                        db.session.add(current_task) # Ensure task is in session
                        print(f"Marked task {current_task.id} as reminder sent")

                        # **** Commit ONCE at the end ****
                        db.session.commit()
                        print(f"✅ Successfully committed changes for task {current_task.id}")

                        if message_to_save:
                            print(f"Saved reminder message ID {whatsapp_msg_id}")

                    except Exception as db_error:
                        db.session.rollback() # Rollback if commit fails
                        print(f"❌ Database error during commit for task {current_task.id}: {db_error}")
                        # Optionally re-raise the error if needed
                        raise db_error # Re-raise to be caught by outer try/except

                else:
                    print(f"Failed to send reminder for task {current_task.id}: {result.get('error')}")
                    # Decide if you want to rollback or not commit if sending fails

        except Exception as e:
            # Rollback on general errors too
            try:
                if db.session.is_active:
                     db.session.rollback()
            except Exception as rb_error:
                 print(f"Error during rollback in outer exception: {rb_error}")
            print(f"❌ Error sending reminder process for task {task.id}: {e}") # Use original task ID for logging context

        finally:
            # Release Redis lock only if it was acquired
            if self.redis_client and lock_acquired:
                try:
                    self.redis_client.delete(lock_key)
                except Exception:
                    pass # Ignore errors during lock release

    # --- MAKE SURE INDENTATION IS CORRECT FROM HERE ONWARDS ---
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
        # Import app locally or ensure it's passed correctly
        from .. import app # Adjust if needed

        try:
            with app.app_context():
                task = Task.query.get(task_id)
                if task and task.status == 'pending' and not task.reminder_sent: # Added check for reminder_sent
                    # Pass the fetched task object
                    self._send_task_reminder(task, app)
                elif task:
                    print(f"Single reminder for task {task_id} skipped (not pending or already reminded).")
                else:
                    print(f"Single reminder for task {task_id} skipped (task not found).")
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
            # It's okay if the job doesn't exist (e.g., already run or cancelled)
            # from apscheduler.jobstores.base import JobLookupError
            # if isinstance(e, JobLookupError):
            #     print(f"Reminder job for task {task_id} not found (already run or cancelled).")
            #     return True
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
