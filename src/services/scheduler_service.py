"""
Scheduler service for handling reminders and background tasks
"""
import os
import atexit
import json
import time
from datetime import datetime, timedelta
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

    def __init__(self, redis_client=None, whatsapp_service=None, calendar_sync_service=None):
        self.redis_client = redis_client
        self.whatsapp_service = whatsapp_service
        self.calendar_sync_service = calendar_sync_service  # Phase 2: Calendar sync service
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

            # Job 2: Cleanup old completed/cancelled tasks (weekly)
            self.scheduler.add_job(
                func=self._cleanup_old_tasks,
                trigger="cron",
                day_of_week='sun',
                hour=2,
                id="cleanup_tasks",
                name="Weekly cleanup of old completed tasks",
                kwargs={'app': app}
            )
            print("Added weekly cleanup job (Sundays at 2 AM)")

            # Job 3: Send daily summary (every morning)
            self.scheduler.add_job(
                func=self._send_daily_summary,
                trigger="cron",
                hour=9,
                minute=0,
                id="daily_summary",
                name="Daily task summary",
                timezone=self.israel_tz,
                kwargs={'app': app}
            )
            print("Added daily summary job (9 AM Israel time)")

            # Job 4: Daily task reminders - 3 times a day
            # Morning reminder (11 AM)
            self.scheduler.add_job(
                func=self._send_daily_task_reminder,
                trigger="cron",
                hour=11,
                minute=0,
                id="daily_reminder_morning",
                name="Daily task reminder - Morning (11 AM)",
                timezone=self.israel_tz,
                kwargs={'app': app}
            )
            print("Added daily reminder job (11 AM Israel time)")

            # Afternoon reminder (3 PM)
            self.scheduler.add_job(
                func=self._send_daily_task_reminder,
                trigger="cron",
                hour=15,
                minute=0,
                id="daily_reminder_afternoon",
                name="Daily task reminder - Afternoon (3 PM)",
                timezone=self.israel_tz,
                kwargs={'app': app}
            )
            print("Added daily reminder job (3 PM Israel time)")

            # Evening reminder (7 PM)
            self.scheduler.add_job(
                func=self._send_daily_task_reminder,
                trigger="cron",
                hour=19,
                minute=0,
                id="daily_reminder_evening",
                name="Daily task reminder - Evening (7 PM)",
                timezone=self.israel_tz,
                kwargs={'app': app}
            )
            print("Added daily reminder job (7 PM Israel time)")

            # Job 5: Generate recurring task instances at midnight
            self.scheduler.add_job(
                func=self._generate_recurring_instances_midnight,
                trigger="cron",
                hour=0,
                minute=0,
                id="generate_recurring_instances",
                name="Generate recurring task instances at midnight",
                timezone=self.israel_tz,
                kwargs={'app': app}
            )
            print("Added midnight recurring task generation job")
            
            # Job 6: Sync Google Calendar (Phase 2) - every 1 minutes
            if self.calendar_sync_service:
                self.scheduler.add_job(
                    func=self._sync_all_calendars,
                    trigger="interval",
                    minutes=1,
                    id="sync_calendars",
                    name="Sync Google Calendar for all users",
                    kwargs={'app': app}
                )
                print("Added calendar sync job (every 10 minutes)")
            else:
                print("Calendar sync service not available - skipping calendar sync job")

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
                from ..services.task_service import TaskService
                task_service = TaskService()
                
                # Get tasks that will be due in the next 30 minutes
                # Note: get_due_tasks_for_reminders already filters out recurring patterns
                due_tasks = task_service.get_due_tasks_for_reminders(time_window_minutes=30)

                if len(due_tasks) == 0:
                    # print("No tasks due for reminders.") # Optional: Reduce log noise
                    return

                print(f"Found {len(due_tasks)} tasks due for reminders in next 30 minutes")

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

    def _cleanup_old_tasks(self, app):
        """Delete completed and cancelled tasks older than 30 days"""
        try:
            with app.app_context():
                from ..models.database import Task, db
                
                # Calculate cutoff date (30 days ago)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                # Find old completed and cancelled tasks
                old_tasks = Task.query.filter(
                    Task.status.in_(['completed', 'cancelled']),
                    Task.updated_at < cutoff_date
                ).all()
                
                if len(old_tasks) == 0:
                    print("No old tasks to clean up")
                    return
                
                print(f"Found {len(old_tasks)} old tasks to delete")
                
                # Delete tasks
                for task in old_tasks:
                    db.session.delete(task)
                
                db.session.commit()
                print(f"✅ Cleaned up {len(old_tasks)} old tasks")
                
        except Exception as e:
            print(f"❌ Error in cleanup job: {e}")
            import traceback
            traceback.print_exc()
            try:
                if db.session.is_active:
                    db.session.rollback()
            except:
                pass

    def _send_daily_summary(self, app):
        """Send daily summary to all active users"""
        if not self.whatsapp_service:
            print("WhatsApp service not available for daily summary.")
            return
        
        try:
            with app.app_context():
                from ..models.database import Task, User, db
                
                # Get all users who have been active
                active_users = User.query.filter(
                    User.last_active.isnot(None)
                ).all()
                
                if len(active_users) == 0:
                    print("No active users for daily summary")
                    return
                
                print(f"Sending daily summary to {len(active_users)} users")
                now = datetime.utcnow()
                
                for user in active_users:
                    time.sleep(0.2)
                    try:
                        # Get tasks due today
                        now_israel = datetime.now(self.israel_tz)
                        today_start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
                        today_end_israel = today_start_israel + timedelta(days=1)
                        
                        today_start = today_start_israel.astimezone(pytz.UTC).replace(tzinfo=None)
                        today_end = today_end_israel.astimezone(pytz.UTC).replace(tzinfo=None)
                        
                        tasks_due_today = Task.query.filter(
                            Task.user_id == user.id,
                            Task.status == 'pending',
                            Task.is_recurring == False,  # Only show instances, not patterns
                            Task.due_date >= today_start,
                            Task.due_date < today_end
                        ).order_by(Task.due_date.asc()).all()
                        
                        # Get overdue tasks
                        overdue_tasks = Task.query.filter(
                            Task.user_id == user.id,
                            Task.status == 'pending',
                            Task.is_recurring == False,  # Only show instances, not patterns
                            Task.due_date < now,
                            Task.due_date.isnot(None)
                        ).order_by(Task.due_date.asc()).all()
                        
                        # Skip users with no tasks
                        if len(tasks_due_today) == 0 and len(overdue_tasks) == 0:
                            continue
                        
                        # Build summary message
                        summary_parts = ["📋 סיכום משימות יומי\n"]
                        
                        if overdue_tasks:
                            summary_parts.append(f"⚠️ באיחור ({len(overdue_tasks)}):")
                            for task in overdue_tasks[:5]:
                                due_local = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                                summary_parts.append(f"  • {task.description[:50]} ({due_local.strftime('%d/%m %H:%M')})")
                            if len(overdue_tasks) > 5:
                                summary_parts.append(f"  ... ועוד {len(overdue_tasks) - 5}")
                            summary_parts.append("")
                        
                        if tasks_due_today:
                            summary_parts.append(f"📅 משימות להיום ({len(tasks_due_today)}):")
                            for task in tasks_due_today[:5]:
                                due_local = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                                summary_parts.append(f"  • {task.description[:50]} ({due_local.strftime('%H:%M')})")
                            if len(tasks_due_today) > 5:
                                summary_parts.append(f"  ... ועוד {len(tasks_due_today) - 5}")
                            summary_parts.append("")
                        
                        # Phase 2: Add calendar events to daily summary
                        if user.google_calendar_enabled and self.calendar_sync_service:
                            try:
                                from ..services.calendar_service import CalendarService
                                calendar_service = CalendarService()
                                
                                # Fetch calendar events for today
                                calendar_events = calendar_service.fetch_events(user, today_start, today_end, fetch_all=True)
                                
                                # Filter out events that are already tasks (deduplication)
                                # Query ALL tasks with calendar_event_id (including completed, templates, etc.)
                                all_user_tasks_with_cal_id = Task.query.filter(
                                    Task.user_id == user.id,
                                    Task.calendar_event_id.isnot(None)
                                ).all()
                                task_event_ids = {t.calendar_event_id for t in all_user_tasks_with_cal_id}
                                
                                # Filter out:
                                # 1. Events that are already bot tasks (deduplication)
                                # 2. Cancelled events (status == 'cancelled')
                                # 3. Completed events (colorId == '8' or has ✅ in title)
                                display_events = [
                                    e for e in calendar_events 
                                    if e['id'] not in task_event_ids
                                    and e.get('status') != 'cancelled'
                                    and e.get('colorId') != '8'  # Gray = completed
                                    and not e.get('title', '').startswith('✅')  # Completed marker in title
                                ]
                                
                                if display_events:
                                    summary_parts.append(f"📆 אירועים ביומן ({len(display_events)}):")
                                    for event in display_events[:5]:
                                        start_local = event['start'].astimezone(self.israel_tz)
                                        end_local = event['end'].astimezone(self.israel_tz)
                                        summary_parts.append(f"  • {event['title'][:50]} ({start_local.strftime('%H:%M')}-{end_local.strftime('%H:%M')})")
                                    if len(display_events) > 5:
                                        summary_parts.append(f"  ... ועוד {len(display_events) - 5}")
                                    summary_parts.append("")
                            except Exception as calendar_error:
                                print(f"⚠️ Failed to fetch calendar events for daily summary: {calendar_error}")
                        
                        summary_parts.append("💪 בהצלחה היום!")
                        
                        summary_text = "\n".join(summary_parts)
                        
                        # Send WhatsApp message
                        result = self.whatsapp_service.send_message(user.phone_number, summary_text)
                        
                        if result.get("success"):
                            print(f"✅ Sent daily summary to user {user.id}")
                        else:
                            print(f"❌ Failed to send summary to user {user.id}: {result.get('error')}")
                        
                    except Exception as user_error:
                        print(f"❌ Error sending summary to user {user.id}: {user_error}")
                        continue
                
                print(f"✅ Daily summary job completed")
                
        except Exception as e:
            print(f"❌ Error in daily summary job: {e}")
            import traceback
            traceback.print_exc()

    def _send_daily_task_reminder(self, app):
        """Send friendly reminders 3 times a day about today's pending tasks"""
        if not self.whatsapp_service:
            print("WhatsApp service not available for daily reminders.")
            return
        
        try:
            with app.app_context():
                from ..models.database import Task, User, db
                
                # Get all active users
                active_users = User.query.filter(
                    User.last_active.isnot(None)
                ).all()
                
                if len(active_users) == 0:
                    print("No active users for daily reminder")
                    return
                
                print(f"Sending daily reminder to {len(active_users)} users")
                
                for user in active_users:
                    time.sleep(0.2)
                    try:
                        # Calculate TODAY's range in Israel timezone
                        now_israel = datetime.now(self.israel_tz)
                        today_start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
                        today_end_israel = today_start_israel + timedelta(days=1)
                        
                        today_start = today_start_israel.astimezone(pytz.UTC).replace(tzinfo=None)
                        today_end = today_end_israel.astimezone(pytz.UTC).replace(tzinfo=None)
                        
                        # Get ONLY tasks due today (not overdue, not future)
                        tasks_due_today = Task.query.filter(
                            Task.user_id == user.id,
                            Task.status == 'pending',
                            Task.is_recurring == False,  # Only show instances, not patterns
                            Task.due_date >= today_start,
                            Task.due_date < today_end
                        ).order_by(Task.due_date.asc()).all()
                        
                        # Build message based on whether there are tasks
                        if len(tasks_due_today) > 0:
                            # User has pending tasks today
                            message_parts = ["היי מה קורה? 👋\nיש לך עדיין משימות פתוחות להיום:\n"]
                            
                            for task in tasks_due_today[:10]:  # Show up to 10 tasks
                                if task.due_date:
                                    due_local = task.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                                    time_str = due_local.strftime('%H:%M')
                                    message_parts.append(f"🔸 {task.description[:60]} ({time_str})")
                                else:
                                    message_parts.append(f"🔸 {task.description[:60]}")
                            
                            if len(tasks_due_today) > 10:
                                message_parts.append(f"\n... ועוד {len(tasks_due_today) - 10} משימות נוספות")
                            
                            message_parts.append("\n💪 בואו נסיים אותן!")
                            reminder_text = "\n".join(message_parts)
                        else:
                            # No tasks for today - congratulate the user!
                            reminder_text = "כול הכבוד! 🎉\nאין לך משימות פתוחות כרגע.\n\nתיהנה מהיום! 😊"
                        
                        # Send WhatsApp message
                        result = self.whatsapp_service.send_message(user.phone_number, reminder_text)
                        
                        if result.get("success"):
                            print(f"✅ Sent daily reminder to user {user.id} ({len(tasks_due_today)} tasks)")
                        else:
                            print(f"❌ Failed to send reminder to user {user.id}: {result.get('error')}")
                        
                    except Exception as user_error:
                        print(f"❌ Error sending reminder to user {user.id}: {user_error}")
                        continue
                
                print(f"✅ Daily reminder job completed")
                
        except Exception as e:
            print(f"❌ Error in daily reminder job: {e}")
            import traceback
            traceback.print_exc()

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
                
                # Check if task is still pending (may have been completed/cancelled)
                if current_task.status != 'pending':
                    print(f"Task {task.id} is not pending (status: {current_task.status}) - skipping reminder.")
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

    def _generate_recurring_instances_midnight(self, app):
        """Generate recurring task instances at midnight"""
        try:
            with app.app_context():
                from ..models.database import Task, db
                from ..services.task_service import TaskService
                from ..services.calendar_service import CalendarService
                
                # Use TaskService with calendar_service for calendar sync
                calendar_service = CalendarService()
                task_service = TaskService(calendar_service=calendar_service)
                
                # Get all active recurring patterns
                recurring_patterns = Task.query.filter(
                    Task.is_recurring == True,
                    Task.status == 'pending'
                ).all()
                
                if len(recurring_patterns) == 0:
                    print("No active recurring patterns to process")
                    return
                
                print(f"Processing {len(recurring_patterns)} recurring patterns")
                generated_count = 0
                
                for pattern in recurring_patterns:
                    try:
                        now_israel = datetime.now(self.israel_tz)
                        today_date = now_israel.date()
                        today_weekday = now_israel.weekday()  # 0=Monday, 6=Sunday
                        today_day_of_month = today_date.day
                        
                        should_generate = False
                        
                        # Backward compatibility: normalize old patterns on-the-fly if needed
                        normalized_days_for_check = None
                        if not pattern.recurrence_days_of_week and pattern.recurrence_pattern != 'monthly':
                            # Try to normalize based on pattern type
                            if pattern.recurrence_pattern == 'daily':
                                # Daily: all days of week
                                normalized_days_for_check = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
                            elif pattern.recurrence_pattern == 'weekly' and pattern.due_date:
                                # Weekly: extract weekday from due_date
                                if pattern.due_date.tzinfo:
                                    pattern_due_israel = pattern.due_date.astimezone(self.israel_tz)
                                else:
                                    pattern_due_israel = pattern.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                                weekday_num = pattern_due_israel.weekday()  # 0=Monday, 6=Sunday
                                weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                                normalized_days_for_check = [weekday_names[weekday_num]]
                            elif pattern.recurrence_pattern == 'interval':
                                # Interval: all days
                                normalized_days_for_check = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
                        
                        # Check monthly patterns first
                        if pattern.recurrence_pattern == 'monthly':
                            if pattern.recurrence_day_of_month:
                                # Handle edge case: if day doesn't exist (e.g., Feb 31), use last day
                                if today_day_of_month == pattern.recurrence_day_of_month:
                                    should_generate = True
                                elif today_day_of_month > pattern.recurrence_day_of_month:
                                    # Check if today is last day of month and pattern day is after
                                    from calendar import monthrange
                                    last_day = monthrange(today_date.year, today_date.month)[1]
                                    if today_day_of_month == last_day and pattern.recurrence_day_of_month > last_day:
                                        should_generate = True
                        
                        # Check weekday-based patterns
                        elif pattern.recurrence_days_of_week or normalized_days_for_check:
                            import json
                            # Use normalized days if available (backward compatibility), otherwise use stored days
                            days_list = normalized_days_for_check if normalized_days_for_check else json.loads(pattern.recurrence_days_of_week)
                            day_mapping = {
                                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                                'friday': 4, 'saturday': 5, 'sunday': 6
                            }
                            target_weekdays = [day_mapping[d.lower()] for d in days_list if d.lower() in day_mapping]
                            
                            if today_weekday in target_weekdays:
                                # For interval patterns, also check if enough days passed
                                if pattern.recurrence_pattern == 'interval':
                                    # Find last instance
                                    last_instance = Task.query.filter(
                                        Task.parent_recurring_id == pattern.id,
                                        Task.status == 'pending'
                                    ).order_by(Task.due_date.desc()).first()
                                    
                                    if last_instance:
                                        if last_instance.due_date.tzinfo:
                                            last_due_israel = last_instance.due_date.astimezone(self.israel_tz)
                                        else:
                                            last_due_israel = last_instance.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                                        
                                        days_since_last = (today_date - last_due_israel.date()).days
                                        if days_since_last >= (pattern.recurrence_interval or 1):
                                            should_generate = True
                                    else:
                                        # No instances yet, check against pattern creation or due_date
                                        if pattern.due_date:
                                            if pattern.due_date.tzinfo:
                                                pattern_due_israel = pattern.due_date.astimezone(self.israel_tz)
                                            else:
                                                pattern_due_israel = pattern.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                                            
                                            days_since_pattern = (today_date - pattern_due_israel.date()).days
                                            if days_since_pattern >= 0 and days_since_pattern % (pattern.recurrence_interval or 1) == 0:
                                                should_generate = True
                                else:
                                    # Daily, weekly, specific_days: weekday match is enough
                                    should_generate = True
                        
                        if should_generate:
                            # Check for duplicate instance today
                            day_start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
                            day_end_israel = day_start_israel + timedelta(days=1)
                            day_start_utc = day_start_israel.astimezone(pytz.UTC).replace(tzinfo=None)
                            day_end_utc = day_end_israel.astimezone(pytz.UTC).replace(tzinfo=None)
                            
                            existing_instance = Task.query.filter(
                                Task.parent_recurring_id == pattern.id,
                                Task.due_date >= day_start_utc,
                                Task.due_date < day_end_utc
                            ).first()
                            
                            if existing_instance:
                                print(f"⚠️ Instance already exists for pattern {pattern.id} on {today_date}")
                                continue
                            
                            # Create instance for today with pattern's time
                            if pattern.due_date:
                                if pattern.due_date.tzinfo:
                                    pattern_due_israel = pattern.due_date.astimezone(self.israel_tz)
                                else:
                                    pattern_due_israel = pattern.due_date.replace(tzinfo=pytz.UTC).astimezone(self.israel_tz)
                                
                                instance_due_date = now_israel.replace(
                                    hour=pattern_due_israel.hour,
                                    minute=pattern_due_israel.minute,
                                    second=0,
                                    microsecond=0
                                )
                                instance_due_utc = instance_due_date.astimezone(pytz.UTC).replace(tzinfo=None)
                                
                                # Temporarily set pattern.due_date to today for instance generation
                                original_due_date = pattern.due_date
                                pattern.due_date = instance_due_utc
                                
                                instance = task_service.generate_next_instance(pattern)
                                
                                if not instance:
                                    pattern.due_date = original_due_date
                                    db.session.rollback()
                                else:
                                    generated_count += 1
                                    print(f"✅ Generated instance for pattern {pattern.id}: {pattern.description[:50]}")
                            else:
                                print(f"⚠️ Pattern {pattern.id} has no due_date, cannot generate instance")
                    
                    except Exception as pattern_error:
                        print(f"❌ Error generating instance for pattern {pattern.id}: {pattern_error}")
                        import traceback
                        traceback.print_exc()
                        try:
                            if db.session.is_active:
                                db.session.rollback()
                        except:
                            pass
                        continue
                
                print(f"✅ Midnight generation completed: {generated_count} instances created")
                
        except Exception as e:
            print(f"❌ Error in midnight recurring generation: {e}")
            import traceback
            traceback.print_exc()
            try:
                if db.session.is_active:
                    db.session.rollback()
            except:
                pass
    
    def _sync_all_calendars(self, app):
        """
        Sync Google Calendar for all users with calendar enabled (Phase 2).
        Called every 10 minutes by the scheduler.
        """
        if not self.calendar_sync_service:
            print("⚠️ Calendar sync service not available")
            return
        
        try:
            with app.app_context():
                from ..models.database import User
                
                # Get all users with calendar enabled
                users = User.query.filter_by(google_calendar_enabled=True).all()
                
                if not users:
                    print("📅 No users with calendar enabled")
                    return
                
                print(f"📅 Starting calendar sync for {len(users)} users")
                
                total_created = 0
                total_updated = 0
                total_deleted = 0
                
                for user in users:
                    try:
                        created, updated, deleted = self.calendar_sync_service.sync_user_calendar(user)
                        total_created += created
                        total_updated += updated
                        total_deleted += deleted
                    except Exception as user_error:
                        print(f"❌ Calendar sync failed for user {user.id}: {user_error}")
                        continue
                
                print(f"✅ Calendar sync completed: +{total_created} ↻{total_updated} -{total_deleted}")
                
        except Exception as e:
            print(f"❌ Error in calendar sync job: {e}")
            import traceback
            traceback.print_exc()
    
    def is_running(self):
        """Check if scheduler is running"""
        return self.scheduler and hasattr(self.scheduler, 'running') and self.scheduler.running
