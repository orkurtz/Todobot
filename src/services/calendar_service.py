"""
Google Calendar integration service
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import pytz

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
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
            return True, "Calendar connected successfully!"
            
        except Exception as e:
            print(f"❌ OAuth callback error: {e}")
            db.session.rollback()
            return False, f"Failed to connect calendar: {str(e)}"
    
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
            
            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
                # Update stored tokens
                user.google_access_token = credentials.token
                user.google_token_expiry = credentials.expiry
                db.session.commit()
                
                print(f"🔄 Refreshed calendar token for user {user.id}")
            
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
            error_msg = f"Google Calendar API error: {e}"
            print(f"❌ {error_msg}")
            task.calendar_sync_error = error_msg
            db.session.commit()
            return False, None, error_msg
            
        except Exception as e:
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
            if e.resp.status == 404:
                # Event was deleted from calendar, create new one
                print(f"⚠️ Event {task.calendar_event_id} not found, creating new one")
                task.calendar_event_id = None
                success, event_id, error = self.create_calendar_event(task)
                if success:
                    return True, None
                return False, error
            
            error_msg = f"Failed to update calendar event: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
            
        except Exception as e:
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
            if e.resp.status == 404:
                # Event already deleted, that's OK
                print(f"⚠️ Event {task.calendar_event_id} already deleted")
                task.calendar_event_id = None
                task.calendar_synced = False
                db.session.commit()
                return True, None
            
            error_msg = f"Failed to delete calendar event: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
            
        except Exception as e:
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
            
        except Exception as e:
            # Don't fail task completion if calendar update fails
            print(f"⚠️ Failed to mark event as completed: {e}")
            return True, None  # Return success anyway
    
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

