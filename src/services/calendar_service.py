"""
Google Calendar integration service
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import pytz

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..models.database import db, User, Task
from ..config.settings import Config

class CalendarService:
    """Handle Google Calendar integration"""
    
    def __init__(self):
        self.client_id = Config.GOOGLE_CLIENT_ID
        self.client_secret = Config.GOOGLE_CLIENT_SECRET
        self.redirect_uri = Config.GOOGLE_REDIRECT_URI
        self.scopes = Config.GOOGLE_CALENDAR_SCOPES
        self.israel_tz = pytz.timezone('Asia/Jerusalem')
        self.default_duration_minutes = Config.CALENDAR_DEFAULT_EVENT_DURATION_MINUTES
        
        # Validate configuration
        if not self.client_id or not self.client_secret:
            print("⚠️ Warning: Google Calendar credentials not configured. Calendar integration will not work.")

    def _is_token_error(self, error: Exception) -> bool:
        """Check if error is related to invalid/revoked token"""
        error_str = str(error).lower()
        token_errors = ['invalid_grant', 'invalid_token', 'token_expired', 'invalid_request', 'unauthorized']
        return any(err in error_str for err in token_errors)
    
    def get_authorization_url(self, user_id: int) -> str:
        """Generate OAuth authorization URL for user to connect their calendar"""
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise ValueError("Google Calendar OAuth not properly configured. Missing CLIENT_ID, CLIENT_SECRET, or REDIRECT_URI.")
        
        try:
            from google_auth_oauthlib.flow import Flow
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uris": [self.redirect_uri],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                state=str(user_id)  # Pass user_id in state
            )
            
            return authorization_url
            
        except Exception as e:
            print(f"❌ Failed to generate authorization URL: {e}")
            raise e
    
    def handle_oauth_callback(self, code: str, user_id: int) -> Tuple[bool, str]:
        """Handle OAuth callback and store tokens"""
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            return False, "Google Calendar OAuth not properly configured"
        
        try:
            from google_auth_oauthlib.flow import Flow
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uris": [self.redirect_uri],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Store encrypted tokens
            user.google_access_token = credentials.token
            user.google_refresh_token = credentials.refresh_token
            user.google_token_expiry = credentials.expiry
            user.google_calendar_enabled = True
            
            # Get primary calendar ID
            service = build('calendar', 'v3', credentials=credentials)
            calendar = service.calendars().get(calendarId='primary').execute()
            user.google_calendar_id = calendar.get('id', 'primary')
            
            db.session.commit()
            
            print(f"✅ Calendar connected for user {user_id}")
            
            # Retry failed syncs immediately
            retry_count = self._retry_failed_syncs(user_id)
            
            message = "Calendar connected successfully!"
            if retry_count > 0:
                message += f"\nSynced {retry_count} missing tasks."
                
            return True, message
            
        except Exception as e:
            print(f"❌ OAuth callback error: {e}")
            db.session.rollback()
            return False, f"Failed to connect calendar: {str(e)}"
    
    def _retry_failed_syncs(self, user_id: int) -> int:
        """
        Retry syncing tasks that failed during downtime.
        
        Finds:
        1. Tasks with due_date but no calendar_event_id (never synced)
        2. Tasks with calendar_sync_error (failed update/creation)
        
        Returns:
            Number of successfully synced tasks
        """
        synced_count = 0
        try:
            user = User.query.get(user_id)
            if not user or not user.google_calendar_enabled:
                return 0
            
            # 1. Find tasks with due date but no calendar event (creation failed)
            # Removed status='pending' filter to catch completed tasks that were never synced
            unsynced_tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.due_date.isnot(None),
                Task.calendar_event_id.is_(None),
                Task.created_from_calendar == False
            ).all()
            
            # 2. Find tasks with sync errors (update failed)
            error_tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.calendar_sync_error.isnot(None)
            ).all()
            
            # Combine and deduplicate
            tasks_to_retry = list({t.id: t for t in (unsynced_tasks + error_tasks)}.values())
            
            print(f"🔄 Retrying sync for {len(tasks_to_retry)} tasks for user {user_id}")
            
            for task in tasks_to_retry:
                try:
                    success = False
                    if not task.calendar_event_id:
                        # Try create
                        success, _, _ = self.create_calendar_event(task)
                    else:
                        # Try update
                        success, _ = self.update_calendar_event(task)
                    
                    if success:
                        synced_count += 1
                        
                        # If task is already completed, ensure calendar reflects that
                        if task.status == 'completed':
                            print(f"   Checking off completed task {task.id} in calendar...")
                            self.mark_event_completed(task)
                except Exception as e:
                    print(f"⚠️ Failed to retry sync for task {task.id}: {e}")
            
            # 3. Integrity Check: Ensure recently completed tasks are marked on calendar
            # (Fixes retroactive cases where task was synced as pending but completion update failed)
            # We check the last 20 completed tasks to ensure they are visually completed on the calendar
            recent_completed = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'completed',
                Task.calendar_event_id.isnot(None)
            ).order_by(Task.completed_at.desc()).limit(100).all()
            
            if recent_completed:
                print(f"🔄 Verifying completion status for {len(recent_completed)} recent tasks")
                for task in recent_completed:
                    try:
                        # This is safe to call repeatedly (idempotent) - forces update to 'checked' state
                        self.mark_event_completed(task)
                    except Exception as e:
                        print(f"⚠️ Failed to verify completion for task {task.id}: {e}")
            
            if synced_count > 0:
                print(f"✅ Successfully recovered {synced_count} tasks for user {user_id}")
                
            return synced_count
            
        except Exception as e:
            print(f"❌ Error during sync recovery: {e}")
            return 0

    def get_credentials(self, user: User) -> Optional[Credentials]:
        """Get and refresh Google credentials for user"""
        if not user.google_calendar_enabled:
            return None
        
        if not user.google_access_token:
            return None
        
        try:
            credentials = Credentials(
                token=user.google_access_token,
                refresh_token=user.google_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes
            )
            
            # Proactive refresh: refresh if expired or expiring soon (within 5 minutes)
            now_utc = datetime.utcnow()
            needs_refresh = (
                credentials.expired or 
                (credentials.expiry and credentials.expiry <= now_utc + timedelta(minutes=5))
            )
            
            if needs_refresh:
                if not credentials.refresh_token:
                    # No refresh token available - disconnect
                    self._disable_calendar_for_user(user, "No refresh token available")
                    return None
                
                try:
                    credentials.refresh(Request())
                    
                    # Update stored tokens
                    user.google_access_token = credentials.token
                    user.google_token_expiry = credentials.expiry
                    db.session.commit()
                    
                    print(f"🔄 Refreshed calendar token for user {user.id}")
                except Exception as refresh_error:
                    # Check error type to determine if token is invalid
                    error_str = str(refresh_error).lower()
                    
                    # Token errors that require reconnection
                    token_errors = ['invalid_grant', 'invalid_token', 'token_expired', 'invalid_request', 'unauthorized']
                    is_token_error = any(err in error_str for err in token_errors)
                    
                    if is_token_error:
                        # Token is invalid/revoked - auto-disconnect
                        self._disable_calendar_for_user(user, f"Token invalid or revoked: {error_str[:100]}")
                        return None
                    else:
                        # Network or other temporary error - log but don't disconnect
                        print(f"⚠️ Failed to refresh token for user {user.id} (temporary error): {refresh_error}")
                        return None
            
            return credentials
            
        except Exception as e:
            print(f"❌ Failed to get credentials for user {user.id}: {e}")
            return None
    
    def create_calendar_event(self, task: Task) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a calendar event for a task
        Returns: (success, event_id, error_message)
        """
        try:
            user = User.query.get(task.user_id)
            if not user or not user.google_calendar_enabled:
                return False, None, "Calendar not enabled"
            
            if not task.due_date:
                return False, None, "Task has no due date"
            
            credentials = self.get_credentials(user)
            if not credentials:
                return False, None, "Failed to authenticate with Google Calendar"
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Convert due_date to Israel timezone
            due_date_utc = task.due_date.replace(tzinfo=pytz.UTC)
            due_date_israel = due_date_utc.astimezone(self.israel_tz)
            
            # Calculate end time (default 1 hour duration)
            end_time = due_date_israel + timedelta(minutes=self.default_duration_minutes)
            
            # Create event
            event = {
                'summary': task.description,
                'description': f'Created by TodoBot\nTask ID: {task.id}',
                'start': {
                    'dateTime': due_date_israel.isoformat(),
                    'timeZone': 'Asia/Jerusalem',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Jerusalem',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 15},
                    ],
                },
            }
            
            # Insert event
            created_event = service.events().insert(
                calendarId=user.google_calendar_id or 'primary',
                body=event
            ).execute()
            
            event_id = created_event['id']
            
            # Update task
            task.calendar_event_id = event_id
            task.calendar_synced = True
            task.calendar_sync_error = None
            db.session.commit()
            
            print(f"✅ Created calendar event {event_id} for task {task.id}")
            return True, event_id, None
            
        except HttpError as e:
            # Handle specific HTTP errors
            if e.resp.status == 401:
                # Unauthorized - token invalid, auto-disconnect
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, "Authentication failed (401)")
                error_msg = "Calendar authentication failed"
                task.calendar_sync_error = error_msg
                db.session.commit()
                return False, None, error_msg
            elif e.resp.status == 403:
                # Forbidden - permissions revoked, auto-disconnect
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, "Permissions revoked (403)")
                error_msg = "Calendar permissions revoked"
                task.calendar_sync_error = error_msg
                db.session.commit()
                return False, None, error_msg
            elif e.resp.status == 429:
                # Rate limited - log but don't disconnect
                error_msg = f"Google Calendar rate limit exceeded: {e}"
                print(f"⚠️ {error_msg}")
                task.calendar_sync_error = error_msg
                db.session.commit()
                return False, None, error_msg
            else:
                # Other HTTP errors
                error_msg = f"Google Calendar API error: {e}"
                print(f"❌ {error_msg}")
                task.calendar_sync_error = error_msg
                db.session.commit()
                return False, None, error_msg
            
        except Exception as e:
            # Check for token errors that weren't caught by HttpError
            if isinstance(e, RefreshError) or self._is_token_error(e):
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, f"Token invalid or revoked: {e}")
                error_msg = "Calendar token expired. Please reconnect."
                task.calendar_sync_error = error_msg
                db.session.commit()
                return False, None, error_msg
                
            error_msg = f"Failed to create calendar event: {str(e)}"
            print(f"❌ {error_msg}")
            task.calendar_sync_error = error_msg
            db.session.commit()
            return False, None, error_msg
    
    def update_calendar_event(self, task: Task) -> Tuple[bool, Optional[str]]:
        """Update an existing calendar event"""
        try:
            if not task.calendar_event_id:
                # No event to update, create new one
                return self.create_calendar_event(task)[:2]  # Return (success, event_id) without error
            
            user = User.query.get(task.user_id)
            if not user or not user.google_calendar_enabled:
                return False, "Calendar not enabled"
            
            credentials = self.get_credentials(user)
            if not credentials:
                return False, "Failed to authenticate"
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get existing event
            event = service.events().get(
                calendarId=user.google_calendar_id or 'primary',
                eventId=task.calendar_event_id
            ).execute()
            
            # Update event details
            if task.due_date:
                due_date_utc = task.due_date.replace(tzinfo=pytz.UTC)
                due_date_israel = due_date_utc.astimezone(self.israel_tz)
                end_time = due_date_israel + timedelta(minutes=self.default_duration_minutes)
                
                event['start'] = {
                    'dateTime': due_date_israel.isoformat(),
                    'timeZone': 'Asia/Jerusalem',
                }
                event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Jerusalem',
                }
            
            event['summary'] = task.description
            
            # Update the event
            updated_event = service.events().update(
                calendarId=user.google_calendar_id or 'primary',
                eventId=task.calendar_event_id,
                body=event
            ).execute()
            
            task.calendar_sync_error = None
            db.session.commit()
            
            print(f"✅ Updated calendar event {task.calendar_event_id} for task {task.id}")
            return True, None
            
        except HttpError as e:
            if e.resp.status == 401:
                # Unauthorized - token invalid, auto-disconnect
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, "Authentication failed (401)")
                return False, "Calendar authentication failed"
            elif e.resp.status == 403:
                # Forbidden - permissions revoked, auto-disconnect
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, "Permissions revoked (403)")
                return False, "Calendar permissions revoked"
            elif e.resp.status == 404:
                # Event was deleted from calendar, create new one
                print(f"⚠️ Event {task.calendar_event_id} not found, creating new one")
                task.calendar_event_id = None
                success, event_id, error = self.create_calendar_event(task)
                if success:
                    return True, None
                return False, error
            elif e.resp.status == 429:
                # Rate limited - log but don't disconnect
                error_msg = f"Google Calendar rate limit exceeded: {e}"
                print(f"⚠️ {error_msg}")
                return False, error_msg
            else:
                error_msg = f"Failed to update calendar event: {e}"
                print(f"❌ {error_msg}")
                return False, error_msg
            
        except Exception as e:
            # Check for token errors that weren't caught by HttpError
            if isinstance(e, RefreshError) or self._is_token_error(e):
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, f"Token invalid or revoked: {e}")
                return False, "Calendar token expired. Please reconnect."

            error_msg = f"Failed to update calendar event: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def delete_calendar_event(self, task: Task) -> Tuple[bool, Optional[str]]:
        """Delete a calendar event (when task is completed or deleted)"""
        try:
            if not task.calendar_event_id:
                return True, None  # Nothing to delete
            
            user = User.query.get(task.user_id)
            if not user or not user.google_calendar_enabled:
                return True, None  # Calendar not enabled, nothing to do
            
            credentials = self.get_credentials(user)
            if not credentials:
                return False, "Failed to authenticate"
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Delete the event
            service.events().delete(
                calendarId=user.google_calendar_id or 'primary',
                eventId=task.calendar_event_id
            ).execute()
            
            print(f"✅ Deleted calendar event {task.calendar_event_id} for task {task.id}")
            
            task.calendar_event_id = None
            task.calendar_synced = False
            db.session.commit()
            
            return True, None
            
        except HttpError as e:
            if e.resp.status == 401:
                # Unauthorized - token invalid, auto-disconnect
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, "Authentication failed (401)")
                return False, "Calendar authentication failed"
            elif e.resp.status == 403:
                # Forbidden - permissions revoked, auto-disconnect
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, "Permissions revoked (403)")
                return False, "Calendar permissions revoked"
            elif e.resp.status == 404:
                # Event already deleted, that's OK
                print(f"⚠️ Event {task.calendar_event_id} already deleted")
                task.calendar_event_id = None
                task.calendar_synced = False
                db.session.commit()
                return True, None
            elif e.resp.status == 429:
                # Rate limited - log but don't disconnect
                error_msg = f"Google Calendar rate limit exceeded: {e}"
                print(f"⚠️ {error_msg}")
                return False, error_msg
            else:
                error_msg = f"Failed to delete calendar event: {e}"
                print(f"❌ {error_msg}")
                return False, error_msg
            
        except Exception as e:
            # Check for token errors that weren't caught by HttpError
            if isinstance(e, RefreshError) or self._is_token_error(e):
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, f"Token invalid or revoked: {e}")
                return False, "Calendar token expired. Please reconnect."

            error_msg = f"Failed to delete calendar event: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def mark_event_completed(self, task: Task) -> Tuple[bool, Optional[str]]:
        """Mark a calendar event as completed (change color or add [DONE] to title)"""
        try:
            if not task.calendar_event_id:
                return True, None
            
            user = User.query.get(task.user_id)
            if not user or not user.google_calendar_enabled:
                return True, None
            
            credentials = self.get_credentials(user)
            if not credentials:
                return False, "Failed to authenticate"
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get existing event
            event = service.events().get(
                calendarId=user.google_calendar_id or 'primary',
                eventId=task.calendar_event_id
            ).execute()
            
            # Mark as completed (add prefix or change color)
            event['summary'] = f"✅ {task.description}"
            event['colorId'] = '8'  # Gray color for completed
            
            # Update the event
            service.events().update(
                calendarId=user.google_calendar_id or 'primary',
                eventId=task.calendar_event_id,
                body=event
            ).execute()
            
            print(f"✅ Marked calendar event {task.calendar_event_id} as completed")
            return True, None
            
        except HttpError as e:
            if e.resp.status == 401:
                # Unauthorized - token invalid, auto-disconnect
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, "Authentication failed (401)")
                # Don't fail task completion if calendar update fails
                return True, None
            elif e.resp.status == 403:
                # Forbidden - permissions revoked, auto-disconnect
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, "Permissions revoked (403)")
                # Don't fail task completion if calendar update fails
                return True, None
            elif e.resp.status == 404:
                # Event not found - that's OK, don't fail task completion
                print(f"⚠️ Event {task.calendar_event_id} not found when marking as completed")
                return True, None
            elif e.resp.status == 429:
                # Rate limited - log but don't fail task completion
                print(f"⚠️ Google Calendar rate limit exceeded when marking event as completed: {e}")
                return True, None
            else:
                # Other HTTP errors - don't fail task completion
                print(f"⚠️ Failed to mark event as completed: {e}")
                return True, None
        except Exception as e:
            # Check for token errors that weren't caught by HttpError
            if isinstance(e, RefreshError) or self._is_token_error(e):
                user = User.query.get(task.user_id)
                if user:
                    self._disable_calendar_for_user(user, f"Token invalid or revoked: {e}")
                return True, None

            # Don't fail task completion if calendar update fails
            print(f"⚠️ Failed to mark event as completed: {e}")
            return True, None  # Return success anyway
    
    def _disable_calendar_for_user(self, user: User, reason: str):
        """Disable calendar for user and notify them"""
        try:
            user.google_calendar_enabled = False
            user.google_access_token = None
            user.google_refresh_token = None
            user.google_token_expiry = None
            
            db.session.commit()
            
            print(f"🔌 Disabled calendar for user {user.id}: {reason}")
            
            # Notify user via WhatsApp (if service available)
            try:
                from ..app import whatsapp_service
                if whatsapp_service:
                    message = (
                        "⚠️ החיבור ליומן Google נפסק\n\n"
                        "החיבור נפסק מסיבה טכנית. כדי לחדש את החיבור:\n"
                        "כתוב 'חבר יומן' כדי להתחבר מחדש."
                    )
                    whatsapp_service.send_message(user.phone_number, message)
                    print(f"📱 Sent calendar disconnect notification to user {user.id}")
            except Exception as notify_error:
                # Don't fail if notification fails
                print(f"⚠️ Failed to notify user {user.id} about calendar disconnect: {notify_error}")
        except Exception as e:
            print(f"❌ Error disabling calendar for user {user.id}: {e}")
            db.session.rollback()
    
    def disconnect_calendar(self, user_id: int) -> Tuple[bool, str]:
        """Disconnect user's calendar"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            user.google_calendar_enabled = False
            user.google_access_token = None
            user.google_refresh_token = None
            user.google_token_expiry = None
            user.google_calendar_id = None
            
            db.session.commit()
            
            print(f"✅ Disconnected calendar for user {user_id}")
            return True, "Calendar disconnected successfully"
            
        except Exception as e:
            print(f"❌ Failed to disconnect calendar: {e}")
            db.session.rollback()
            return False, str(e)
    
    # ========== PHASE 2: CALENDAR FETCHING & FILTERING ==========
    
    def fetch_events(self, user: User, start_date: datetime, end_date: datetime, fetch_all: bool = False) -> list:
        """
        Fetch events from Google Calendar between dates.
        
        Args:
            user: User object
            start_date: Start datetime (timezone-aware)
            end_date: End datetime (timezone-aware)
            fetch_all: If False, only return events matching task criteria
        
        Returns:
            List of event dicts: {id, title, start, end, colorId, updated, description}
        """
        try:
            if not user.google_calendar_enabled:
                return []
            
            credentials = self.get_credentials(user)
            if not credentials:
                return []
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Ensure dates are timezone-aware (Israel timezone)
            if start_date.tzinfo is None:
                start_date = pytz.UTC.localize(start_date).astimezone(self.israel_tz)
            else:
                start_date = start_date.astimezone(self.israel_tz)
            
            if end_date.tzinfo is None:
                end_date = pytz.UTC.localize(end_date).astimezone(self.israel_tz)
            else:
                end_date = end_date.astimezone(self.israel_tz)
            
            # Fetch events from Google Calendar
            events_result = service.events().list(
                calendarId=user.google_calendar_id or 'primary',
                timeMin=start_date.isoformat(),
                timeMax=end_date.isoformat(),
                singleEvents=True,  # Expand recurring events
                orderBy='startTime'
            ).execute()
            
            events_raw = events_result.get('items', [])
            
            # Parse events
            events = []
            for event in events_raw:
                # Parse start and end times
                start = event.get('start', {})
                end = event.get('end', {})
                
                # Handle all-day events vs timed events
                if 'dateTime' in start:
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                elif 'date' in start:
                    # All-day event
                    start_dt = datetime.fromisoformat(start['date'] + 'T00:00:00').replace(tzinfo=self.israel_tz)
                else:
                    continue  # Skip events without start time
                
                if 'dateTime' in end:
                    end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                elif 'date' in end:
                    end_dt = datetime.fromisoformat(end['date'] + 'T23:59:59').replace(tzinfo=self.israel_tz)
                else:
                    end_dt = start_dt + timedelta(hours=1)
                
                # Parse updated timestamp
                updated_str = event.get('updated')
                if updated_str:
                    updated_dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
                else:
                    updated_dt = None
                
                event_dict = {
                    'id': event['id'],
                    'title': event.get('summary', '(No title)'),
                    'start': start_dt,
                    'end': end_dt,
                    'colorId': event.get('colorId'),
                    'updated': updated_dt,
                    'description': event.get('description', ''),
                    'status': event.get('status', 'confirmed'),
                    'transparency': event.get('transparency', 'opaque')  # 'transparent' = free time
                }
                
                # Filter by task criteria if requested
                if fetch_all or self.is_task_event(event_dict, user):
                    events.append(event_dict)
            
            print(f"📅 Fetched {len(events)} events for user {user.id} (fetch_all={fetch_all})")
            return events
            
        except HttpError as e:
            if e.resp.status in [401, 403]:
                self._disable_calendar_for_user(user, f"Failed to fetch events: HTTP {e.resp.status}")
            print(f"❌ Failed to fetch calendar events for user {user.id}: {e}")
            return []
        except Exception as e:
            # Check for token errors
            if isinstance(e, RefreshError) or self._is_token_error(e):
                self._disable_calendar_for_user(user, f"Token invalid or revoked: {e}")
            
            print(f"❌ Failed to fetch calendar events for user {user.id}: {e}")
            return []
    
    def is_task_event(self, event: Dict[str, Any], user: User) -> bool:
        """
        Check if calendar event should be converted to task.
        
        Criteria:
        - Event color matches user.calendar_sync_color OR
        - Event title contains '#' (if user.calendar_sync_hashtag enabled)
        
        Args:
            event: Event dict from fetch_events()
            user: User object
        
        Returns:
            bool
        """
        # Check color match
        if user.calendar_sync_color and event.get('colorId') == user.calendar_sync_color:
            return True
        
        # Check hashtag
        if user.calendar_sync_hashtag and '#' in event.get('title', ''):
            return True
        
        return False
    
    def get_event_updated_time(self, event: Dict[str, Any]) -> Optional[datetime]:
        """
        Extract last modified timestamp from event.
        
        Args:
            event: Event dict from fetch_events()
        
        Returns:
            datetime or None
        """
        return event.get('updated')
    
    def get_recurring_instances(self, user: User, recurring_event_id: str, days_ahead: int = 30) -> list:
        """
        Fetch instances of a recurring event.
        
        Args:
            user: User object
            recurring_event_id: ID of the recurring event
            days_ahead: How many days ahead to fetch instances
        
        Returns:
            List of event instance dicts
        """
        try:
            if not user.google_calendar_enabled:
                return []
            
            credentials = self.get_credentials(user)
            if not credentials:
                return []
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Calculate time range
            now = datetime.now(self.israel_tz)
            end_date = now + timedelta(days=days_ahead)
            
            # Fetch instances
            events_result = service.events().instances(
                calendarId=user.google_calendar_id or 'primary',
                eventId=recurring_event_id,
                timeMin=now.isoformat(),
                timeMax=end_date.isoformat()
            ).execute()
            
            instances_raw = events_result.get('items', [])
            
            # Parse instances (same logic as fetch_events)
            instances = []
            for instance in instances_raw:
                start = instance.get('start', {})
                end = instance.get('end', {})
                
                if 'dateTime' in start:
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                elif 'date' in start:
                    start_dt = datetime.fromisoformat(start['date'] + 'T00:00:00').replace(tzinfo=self.israel_tz)
                else:
                    continue
                
                if 'dateTime' in end:
                    end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                elif 'date' in end:
                    end_dt = datetime.fromisoformat(end['date'] + 'T23:59:59').replace(tzinfo=self.israel_tz)
                else:
                    end_dt = start_dt + timedelta(hours=1)
                
                updated_str = instance.get('updated')
                updated_dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00')) if updated_str else None
                
                instance_dict = {
                    'id': instance['id'],
                    'title': instance.get('summary', '(No title)'),
                    'start': start_dt,
                    'end': end_dt,
                    'colorId': instance.get('colorId'),
                    'updated': updated_dt,
                    'description': instance.get('description', ''),
                    'status': instance.get('status', 'confirmed'),
                    'transparency': instance.get('transparency', 'opaque'),
                    'recurring_event_id': recurring_event_id
                }
                
                instances.append(instance_dict)
            
            print(f"📅 Fetched {len(instances)} instances of recurring event {recurring_event_id}")
            return instances
            
        except Exception as e:
            # Check for token errors
            if isinstance(e, RefreshError) or self._is_token_error(e):
                self._disable_calendar_for_user(user, f"Token invalid or revoked: {e}")
                
            print(f"❌ Failed to fetch recurring event instances: {e}")
            return []
    
    def fetch_event_by_id(self, user: User, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch single event details by ID.
        
        Args:
            user: User object
            event_id: Calendar event ID
        
        Returns:
            Event dict or None
        """
        try:
            if not user.google_calendar_enabled:
                return None
            
            credentials = self.get_credentials(user)
            if not credentials:
                return None
            
            service = build('calendar', 'v3', credentials=credentials)
            
            event = service.events().get(
                calendarId=user.google_calendar_id or 'primary',
                eventId=event_id
            ).execute()
            
            # Parse event
            start = event.get('start', {})
            end = event.get('end', {})
            
            if 'dateTime' in start:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            elif 'date' in start:
                start_dt = datetime.fromisoformat(start['date'] + 'T00:00:00').replace(tzinfo=self.israel_tz)
            else:
                return None
            
            if 'dateTime' in end:
                end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            elif 'date' in end:
                end_dt = datetime.fromisoformat(end['date'] + 'T23:59:59').replace(tzinfo=self.israel_tz)
            else:
                end_dt = start_dt + timedelta(hours=1)
            
            updated_str = event.get('updated')
            updated_dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00')) if updated_str else None
            
            return {
                'id': event['id'],
                'title': event.get('summary', '(No title)'),
                'start': start_dt,
                'end': end_dt,
                'colorId': event.get('colorId'),
                'updated': updated_dt,
                'description': event.get('description', ''),
                'status': event.get('status', 'confirmed'),
                'transparency': event.get('transparency', 'opaque')
            }
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"⚠️ Event {event_id} not found")
                return None
            print(f"❌ Failed to fetch event {event_id}: {e}")
            return None
        except Exception as e:
            # Check for token errors
            if isinstance(e, RefreshError) or self._is_token_error(e):
                self._disable_calendar_for_user(user, f"Token invalid or revoked: {e}")
                
            print(f"❌ Failed to fetch event {event_id}: {e}")
            return None

