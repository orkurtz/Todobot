""""
AI service for handling Gemini API interactions and task parsing
"""
import os
import google.generativeai as genai
import json
import time
import random
import re  # <-- *** ADD THIS IMPORT AT THE TOP ***
import pytz
from typing import Dict, Any, List, Optional


# Import rate limiter and circuit breaker
from ..utils.rate_limiter import APIRateLimiter
from ..utils.circuit_breaker import CircuitBreaker

class AIService:
    """Handle AI-related operations including Gemini API calls"""
    
    def __init__(self, redis_client=None, calendar_service=None):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        # You've already correctly updated this to flash!
        self.model = genai.GenerativeModel('gemini-2.5-flash') 
        
        # Rate limiting and circuit breaker
        self.rate_limiter = APIRateLimiter(
            service_name="gemini",
            requests_per_minute=30,
            requests_per_hour=1000,
            requests_per_day=10000,
            redis_client=redis_client
        )
        
        self.circuit_breaker = CircuitBreaker(
            service_name="gemini",
            failure_threshold=3,
            recovery_timeout=60
        )
        
        # Phase 2: Calendar service for fetching events
        self.calendar_service = calendar_service
        
        # Load prompts
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load AI prompts from configuration"""
        return {
            'system': """You are an intelligent personal assistant integrated with WhatsApp. Your primary role is to help users manage their tasks and answer their questions in a helpful, concise manner.

Core Functions:
1. Extract and create tasks from user messages
2. Provide helpful responses to questions and requests  
3. Offer proactive task management suggestions
4. Maintain a friendly, professional tone

Language Support:
- Respond in the same language the user writes in
- Support Hebrew, English, Arabic, and other languages naturally
- Be culturally aware and appropriate

Task Extraction Guidelines:
- Look for actionable items, requests, reminders, and commitments
- Include context like dates, times, locations when mentioned
- Don't create tasks for casual conversation or questions
- Focus on concrete, actionable items

Response Style:
- Be concise but helpful (1-3 sentences typically)
- Use natural, conversational language
- Provide actionable advice when appropriate
- Ask clarifying questions if needed

Remember: You're helping busy people stay organized while maintaining natural conversation.""",
            
            'task_parsing': """Act as an expert personal assistant. Your goal is to accurately understand the user's intent and extract structured task data into JSON.

CONTEXT:
- Current Date/Time: {current_date}
- User Timezone: Asia/Jerusalem (Israel)
- Language: Hebrew and English (can be mixed)

CORE INSTRUCTIONS:
1. **Analyze Intent:** Determine if the user wants to 'add', 'complete', 'delete', 'update' (content), 'reschedule' (time), 'query' (view), or manage a 'recurring series'.
2. **Reasoning over Matching:** Do not just look for keywords. Understand the meaning. If a user says "I'm done with the meeting", that is a 'complete' action.
3. **Formatting:** Return ONLY raw JSON. Do NOT use Markdown formatting (no ```json wrappers).

LOGIC RULES:
- **Dates & Times:**
  - "Tomorrow" = Current Date + 1 day.
  - "Next week" = Start of the upcoming week.
  - "In X hours/minutes" = Calculate based on {current_date}.
  - If a time isn't specified, default to null.
- **Identification:**
  - If a **number** is mentioned (e.g., "task 5", "#2", "5"), extract it as `task_id`.
  - If **text** is used (e.g., "buy milk"), extract it as `description` for matching.
- **Recurring:**
  - Detect patterns like "every day", "every Monday", "once a month", "every X days".
  - Map to `recurrence_pattern`: 'daily', 'weekly', 'monthly', 'interval' (every X days), or 'specific_days'.
- **Update vs Reschedule (CRITICAL):**
  - If user wants to change the **content/description**: use `update` with `new_description`.
  - If user wants to change the **date/time**: use `reschedule` with `due_date`.
  - Keywords for reschedule: "defer", "postpone", "move to", "change date", "דחה", "העבר".
- **Multiple Tasks:**
  - If user mentions multiple items with "and" or commas, create separate task objects.

RESPONSE STRUCTURE (JSON):
{{
    "tasks": [
        {{
            "action": "add" | "complete" | "delete" | "update" | "reschedule" | "query" | "stop_series" | "complete_series",
            "description": "The task text OR the text identifier used to find the task",
            "task_id": "The numeric identifier (if mentioned, e.g., '5')",
            "due_date": "YYYY-MM-DD HH:MM" (preferred) OR "natural language",
            "new_description": "The new text (for 'update' action only)",
            "recurrence_pattern": "daily" | "weekly" | "monthly" | "interval" | "specific_days" | null,
            "recurrence_interval": number (default 1) | null,
            "recurrence_days_of_week": ["monday", "wednesday"] | null,
            "recurrence_day_of_month": number (1-31) | null
        }}
    ]
}}

FEW-SHOT EXAMPLES (Guidelines covering all scenarios):

User: "תזכיר לי מחר ב-9 בבוקר לשלוח מייל"
JSON: {{"tasks": [{{"action": "add", "description": "לשלוח מייל", "due_date": "tomorrow at 09:00"}}]}}

User: "Buy milk and call mom" (Multiple tasks)
JSON: {{"tasks": [{{"action": "add", "description": "Buy milk"}}, {{"action": "add", "description": "call mom"}}]}}

User: "סיימתי משימה 3" (Finished task 3)
JSON: {{"tasks": [{{"action": "complete", "task_id": "3", "description": "3"}}]}}

User: "מחק את המשימה לקנות חלב" (Delete by text description)
JSON: {{"tasks": [{{"action": "delete", "description": "לקנות חלב"}}]}}

User: "דחה את 5 לעוד שעתיים" (Reschedule - time change)
JSON: {{"tasks": [{{"action": "reschedule", "task_id": "5", "due_date": "in 2 hours"}}]}}

User: "Move task 1 to tomorrow" (Reschedule - time change)
JSON: {{"tasks": [{{"action": "reschedule", "task_id": "1", "due_date": "tomorrow"}}]}}

User: "שנה את משימה 2 ל-ללכת לרופא" (Update - content change)
JSON: {{"tasks": [{{"action": "update", "task_id": "2", "new_description": "ללכת לרופא"}}]}}

User: "Change milk to bread" (Update - content change)
JSON: {{"tasks": [{{"action": "update", "description": "milk", "new_description": "bread"}}]}}

User: "מה המשימות שלי למחר?" (Query)
JSON: {{"tasks": [{{"action": "query", "description": "tasks for tomorrow", "due_date": "tomorrow"}}]}}

User: "כל שני וחמישי ב-17:00 חוג ג'ודו" (Specific days recurrence)
JSON: {{"tasks": [{{"action": "add", "description": "חוג ג'ודו", "due_date": "next Monday at 17:00", "recurrence_pattern": "specific_days", "recurrence_days_of_week": ["monday", "thursday"]}}]}}

User: "כל 3 ימים לקחת תרופה" (Interval recurrence)
JSON: {{"tasks": [{{"action": "add", "description": "לקחת תרופה", "due_date": "{current_date}", "recurrence_pattern": "interval", "recurrence_interval": 3}}]}}

User: "Every day at 9am vitamins" (Daily recurrence)
JSON: {{"tasks": [{{"action": "add", "description": "vitamins", "due_date": "today at 09:00", "recurrence_pattern": "daily", "recurrence_interval": 1}}]}}

User: "עצור את סדרה 4" (Stop series)
JSON: {{"tasks": [{{"action": "stop_series", "task_id": "4"}}]}}

User: "השלם סדרה 2" (Complete series - mark done but keep instances)
JSON: {{"tasks": [{{"action": "complete_series", "task_id": "2"}}]}}

User Message to Analyze: {message}"""
        }
    
    def get_response(self, user_id: int, user_message: str, conversation_history: List = None, query_results: str = None) -> str:
        """Get AI response from Gemini
        
        Args:
            user_id: User ID
            user_message: User's message
            conversation_history: Previous conversation messages
            query_results: Optional database query results to provide context
        """
        # Check rate limiting
        allowed, error_msg = self.rate_limiter.is_allowed()
        if not allowed:
            return f"⚠️ שירות ה-AI אינו זמין זמנית: {error_msg}"
        
        # Check circuit breaker
        available, status_msg = self.circuit_breaker.is_available()
        if not available:
            return f"⚠️ שירות ה-AI אינו זמין זמנית: {status_msg}"
        
        try:
            # Build conversation context
            context_messages = []
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages for context
                    context_messages.append(f"User: {msg.content}")
                    if msg.ai_response:
                        context_messages.append(f"Assistant: {msg.ai_response}")
            
            # Build full prompt
            full_prompt = f"{self.prompts['system']}\n\n"
            if context_messages:
                full_prompt += "Recent conversation:\n" + "\n".join(context_messages) + "\n\n"
            
            # If query results provided, include them so AI knows what database returned
            if query_results:
                full_prompt += f"Database query results:\n{query_results}\n\n"
                full_prompt += f"User message: {user_message}\n\n"
                full_prompt += "Based on the database query results above, generate a natural, helpful response. "
                full_prompt += "Acknowledge the tasks found (or confirm if none found) in a friendly way. "
                full_prompt += "Keep it concise (1-2 sentences). The task list will be shown below your response.\n\n"
            else:
                full_prompt += f"User message: {user_message}\n\nPlease respond helpfully:"
            
            # Make API call with exponential backoff
            response = self._make_api_call_with_retry(full_prompt)
            
            # Record success
            self.circuit_breaker.record_success()
            
            return response.strip()
            
        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            self.circuit_breaker.record_failure(e)
            return "מצטער, אני מתקשה לעבד את הבקשה שלך כרגע. אנא נסה שוב בעוד רגע."
    
    # ======================================================================
    # === THIS IS THE UPDATED FUNCTION WITH THE SIMPLE, EFFECTIVE FIX ===
    # ======================================================================
    def parse_tasks(self, message_text: str) -> List[Dict[str, Any]]:
        """Parse tasks from user message using AI"""
        from datetime import datetime
        
        try:
            # Check rate limiting
            allowed, error_msg = self.rate_limiter.is_allowed()
            if not allowed:
                print(f"Rate limit exceeded for task parsing: {error_msg}")
                return []
            
            # Check circuit breaker
            available, status_msg = self.circuit_breaker.is_available()
            if not available:
                print(f"Circuit breaker open for task parsing: {status_msg}")
                return []
            
            israel_tz = pytz.timezone('Asia/Jerusalem')
            current_date = datetime.now(israel_tz).strftime("%Y-%m-%d %H:%M")
            prompt = self.prompts['task_parsing'].format(
                current_date=current_date,
                message=message_text
            )
            
            # Make API call
            response_text = self._make_api_call_with_retry(prompt)
            
            # === DEBUG: Show raw AI response ===
            print(f"🔥 DEBUG parse_tasks - Raw AI Response:")
            print(f"   Input message: '{message_text}'")
            print(f"   AI returned ({len(response_text)} chars):")
            print(f"   {response_text[:800]}")  # First 800 characters
            if len(response_text) > 800:
                print(f"   ... (truncated, total {len(response_text)} chars)")
            
            # ------------------------------------------------------------------
            # === SIMPLE & EFFECTIVE FIX START ===
            # This robustly finds and extracts the JSON from the raw response.
            # ------------------------------------------------------------------
            
            # Use regex to find the JSON block, ignoring the ```json ... ```
            # re.DOTALL makes '.' match newlines, which is crucial here.
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            
            if not match:
                print(f"❌ Failed to find any JSON in the AI response.")
                print(f"Raw response: {response_text}")
                return []

            # Extract the matched JSON string
            cleaned_response = match.group(0)
            print(f"✅ Found JSON block ({len(cleaned_response)} chars):")
            print(f"   {cleaned_response[:500]}")
            if len(cleaned_response) > 500:
                print(f"   ... (truncated)")
            
            # ------------------------------------------------------------------
            # === SIMPLE & EFFECTIVE FIX END ===
            # ------------------------------------------------------------------

            # Parse JSON response
            try:
                # Parse the *cleaned* text
                parsed_data = json.loads(cleaned_response) 
                tasks = parsed_data.get('tasks', [])
                
                print(f"✅ JSON parsed successfully, found {len(tasks)} task(s) in JSON")
                for idx, task in enumerate(tasks):
                    print(f"   Task {idx+1}: {task}")
                
                # Validate and clean tasks - INCLUDING action field
                valid_tasks = []
                for task in tasks:
                    action = task.get('action', 'add')
                    
                    # For these actions, description is optional (task_id is used instead)
                    if action in ['reschedule', 'complete', 'delete', 'update', 'query', 'stop_series', 'complete_series']:
                        valid_tasks.append({
                            'action': action,
                            'description': (task.get('description') or task.get('title', '')).strip(),  # Support both title and description
                            'due_date': task.get('due_date'),
                            'status': task.get('status', 'pending'),
                            'task_id': task.get('task_id'),
                            'new_description': task.get('new_description'),
                            # NEW: Recurring fields
                            'recurrence_pattern': task.get('recurrence_pattern'),
                            'recurrence_interval': task.get('recurrence_interval', 1),
                            'recurrence_days_of_week': task.get('recurrence_days_of_week'),
                            'recurrence_day_of_month': task.get('recurrence_day_of_month'),
                            'recurrence_end_date': task.get('recurrence_end_date')
                        })
                    # For 'add' action, description is required
                    elif action == 'add' and (task.get('description') or task.get('title')) and len((task.get('description') or task.get('title', '')).strip()) > 0:
                        valid_tasks.append({
                            'action': action,
                            'description': (task.get('description') or task.get('title', '')).strip(),
                            'due_date': task.get('due_date'),
                            'status': task.get('status', 'pending'),
                            'task_id': task.get('task_id'),
                            'new_description': task.get('new_description'),
                            # NEW: Recurring fields
                            'recurrence_pattern': task.get('recurrence_pattern'),
                            'recurrence_interval': task.get('recurrence_interval', 1),
                            'recurrence_days_of_week': task.get('recurrence_days_of_week'),
                            'recurrence_day_of_month': task.get('recurrence_day_of_month'),
                            'recurrence_end_date': task.get('recurrence_end_date')
                        })
                
                print(f"✅ Validated {len(valid_tasks)} task(s) after filtering")
                
                self.circuit_breaker.record_success()
                return valid_tasks
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse AI response as JSON: {e}")
                print(f"Raw response: {response_text}") # Log the original for debugging
                print(f"Cleaned response attempt: {cleaned_response}")
                return []
            
        except Exception as e:
            print(f"❌ Task parsing error: {e}")
            self.circuit_breaker.record_failure(e)
            return []
    
    def parse_tasks_from_audio(self, audio_data: bytes, mime_type: str = "audio/ogg") -> List[Dict[str, Any]]:
        """
        Parse tasks from audio using Gemini's multimodal capabilities
        Transcribes and extracts tasks in one API call
        """
        from datetime import datetime
        import tempfile
        import os
        
        try:
            # Check rate limiting
            allowed, error_msg = self.rate_limiter.is_allowed()
            if not allowed:
                print(f"Rate limit exceeded for audio task parsing: {error_msg}")
                return []
            
            # Check circuit breaker
            available, status_msg = self.circuit_breaker.is_available()
            if not available:
                print(f"Circuit breaker open for audio task parsing: {status_msg}")
                return []
            
            israel_tz = pytz.timezone('Asia/Jerusalem')
            current_date = datetime.now(israel_tz).strftime("%Y-%m-%d %H:%M")
            
            # Build prompt for audio transcription + task extraction
            audio_prompt = f"""You are an expert at understanding voice messages in Hebrew and English and extracting actionable tasks.

Listen to this audio message and:
1. Transcribe what the person is saying
2. Extract any tasks or to-do items mentioned
3. Identify due dates mentioned (in Hebrew or English)

Current date for reference: {current_date}
User timezone: Asia/Jerusalem (Israel)

Return JSON in this exact format (if a time is spoken, include due_date with HH:MM; support recurring fields when present):
{{
    "transcription": "the transcribed text here",
    "tasks": [
        {{
            "action": "add" | "complete" | "delete" | "update" | "reschedule" | "query",
            "description": "task description",
            "due_date": "natural language date like 'מחר', 'tomorrow', 'יום שלישי' (use HH:MM if time spoken)" or null,
            "task_id": task number if mentioned or null,
            "new_description": "new description for update action" or null,
            "recurrence_pattern": "daily" | "weekly" | "specific_days" | "interval" | "monthly" | null,
            "recurrence_interval": number or null,
            "recurrence_days_of_week": ["monday", "wednesday"] or null,
            "recurrence_day_of_month": number (1-31) or null,
            "recurrence_end_date": date string or null
        }}
    ]
}}

Examples:
Hebrew audio "תזכיר לי לקנות חלב מחר בשעה חמש" → 
{{
    "transcription": "תזכיר לי לקנות חלב מחר בשעה חמש",
    "tasks": [{{"action": "add", "description": "לקנות חלב", "due_date": "מחר בשעה 17:00"}}]
}}

English audio "remind me to call mom tomorrow at 3pm" →
{{
    "transcription": "remind me to call mom tomorrow at 3pm",
    "tasks": [{{"action": "add", "description": "call mom", "due_date": "tomorrow at 15:00"}}]
}}

Hebrew audio "תזכיר לי כל יום ב-9 לקחת ויטמינים" →
{{
    "transcription": "תזכיר לי כל יום ב-9 לקחת ויטמינים",
    "tasks": [{{"action": "add", "description": "לקחת ויטמינים", "due_date": "היום ב-09:00", "recurrence_pattern": "daily", "recurrence_interval": 1}}]
}}

Hebrew audio "סיימתי את משימה 2" →
{{
    "transcription": "סיימתי את משימה 2",
    "tasks": [{{"action": "complete", "description": "2", "task_id": "2"}}]
}}

If the audio is just conversation with no tasks, return empty tasks array.
Always include the transcription for transparency.
"""

            # Save audio to temporary file for Gemini upload
            print(f"📤 Preparing audio for Gemini ({len(audio_data)} bytes)...")
            
            # Determine file extension from mime_type
            extension = '.ogg'
            if 'opus' in mime_type.lower():
                extension = '.opus'
            elif 'mpeg' in mime_type.lower() or 'mp3' in mime_type.lower():
                extension = '.mp3'
            elif 'wav' in mime_type.lower():
                extension = '.wav'
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Upload audio file to Gemini
                print(f"📤 Uploading audio to Gemini...")
                audio_file = genai.upload_file(path=temp_path, mime_type=mime_type)
                print(f"✅ Audio uploaded to Gemini: {audio_file.name}")
                
                # Generate content with audio + prompt
                print("🤖 Processing audio with Gemini...")
                response = self.model.generate_content([audio_prompt, audio_file])
                
                if not response or not response.text:
                    print("⚠️ Empty response from Gemini for audio")
                    return []
                
                response_text = response.text
                print(f"📄 Gemini audio response: {response_text[:200]}...")
                
                # Parse JSON response
                match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if not match:
                    print(f"❌ No JSON found in Gemini audio response")
                    return []
                
                cleaned_response = match.group(0)
                
                try:
                    parsed_data = json.loads(cleaned_response)
                    transcription = parsed_data.get('transcription', '')
                    tasks = parsed_data.get('tasks', [])
                    
                    print(f"🎤 Transcription: {transcription}")
                    print(f"📋 Extracted {len(tasks)} tasks from audio")
                    
                    # Validate and clean tasks
                    valid_tasks = []
                    for task in tasks:
                        if (task.get('description') or task.get('title')) and len((task.get('description') or task.get('title', '')).strip()) > 0:
                            valid_tasks.append({
                                'action': task.get('action', 'add'),
                                'description': (task.get('description') or task.get('title', '')).strip(),
                                'due_date': task.get('due_date'),
                                'status': task.get('status', 'pending'),
                                'task_id': task.get('task_id'),
                                'new_description': task.get('new_description'),
                                'recurrence_pattern': task.get('recurrence_pattern'),
                                'recurrence_interval': task.get('recurrence_interval'),
                                'recurrence_days_of_week': task.get('recurrence_days_of_week'),
                                'recurrence_day_of_month': task.get('recurrence_day_of_month'),
                                'recurrence_end_date': task.get('recurrence_end_date'),
                                'transcription': transcription  # Include transcription
                            })
                    
                    self.circuit_breaker.record_success()
                    return valid_tasks
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse Gemini audio response as JSON: {e}")
                    print(f"Raw response: {response_text}")
                    return []
                    
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
            
        except Exception as e:
            print(f"❌ Audio task parsing error: {e}")
            import traceback
            traceback.print_exc()
            self.circuit_breaker.record_failure(e)
            return []
    
    def _make_api_call_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Make Gemini API call with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                
                if response.candidates and response.candidates[0].content:
                    return response.candidates[0].content.parts[0].text
                else:
                    # This might be where the empty response comes from
                    # (e.g., safety filters)
                    print("Warning: Gemini response was empty (possibly safety filters).")
                    return "" # Return empty string instead of raising exception
                
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Gemini API attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)
                else:
                    raise e
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        return self.rate_limiter.get_usage_stats()
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker (for admin use)"""
        from ..utils.circuit_breaker import CircuitState
        self.circuit_breaker.state = CircuitState.CLOSED
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.last_failure_time = None
        self.circuit_breaker.next_attempt_time = None
    
    # ========== PHASE 2: CALENDAR INTEGRATION ==========
    
    def get_full_schedule(self, user, date_filter='today'):
        """
        Get tasks + calendar events for display, filtering duplicates.
        
        Args:
            user: User object
            date_filter: 'today', 'tomorrow', 'week', etc.
        
        Returns:
            Dict with {'tasks': [...], 'events': [...]}
        """
        from ..models.database import Task
        import pytz
        from datetime import datetime, timedelta
        
        israel_tz = pytz.timezone('Asia/Jerusalem')
        
        # Calculate date range based on filter
        now_israel = datetime.now(israel_tz)
        
        if date_filter == 'today':
            start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
            end_israel = start_israel + timedelta(days=1)
        elif date_filter == 'tomorrow':
            start_israel = (now_israel + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_israel = start_israel + timedelta(days=1)
        elif date_filter == 'week':
            start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
            end_israel = start_israel + timedelta(days=7)
        else:
            # Default to today
            start_israel = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
            end_israel = start_israel + timedelta(days=1)
        
        # Convert to UTC for database query
        start_utc = start_israel.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = end_israel.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Get tasks for date range
        tasks = Task.query.filter(
            Task.user_id == user.id,
            Task.status == 'pending',
            Task.is_recurring == False,  # Only show instances, not patterns
            Task.due_date >= start_utc,
            Task.due_date < end_utc
        ).order_by(Task.due_date.asc()).all()
        
        # Fetch calendar events if enabled
        events = []
        if self.calendar_service and user.google_calendar_enabled:
            try:
                # Fetch ALL calendar events for the date range
                all_events = self.calendar_service.fetch_events(user, start_utc, end_utc, fetch_all=True)
                
                # CRITICAL: Filter out events that are already tasks (deduplication)
                # Query ALL tasks with calendar_event_id (including templates, completed, etc.) to prevent duplicates
                all_user_tasks_with_cal_id = Task.query.filter(
                    Task.user_id == user.id,
                    Task.calendar_event_id.isnot(None)
                ).all()
                task_event_ids = {t.calendar_event_id for t in all_user_tasks_with_cal_id}
                
                # Filter out:
                # 1. Events that are already bot tasks (deduplication)
                # 2. Cancelled events (status == 'cancelled')
                # 3. Completed events (colorId == '8' or has ✅ in title)
                events = [
                    e for e in all_events 
                    if e['id'] not in task_event_ids
                    and e.get('status') != 'cancelled'
                    and e.get('colorId') != '8'  # Gray = completed
                    and not e.get('title', '').startswith('✅')  # Completed marker in title
                ]
                
                print(f"📅 Schedule for user {user.id}: {len(tasks)} tasks, {len(events)} events (deduplicated from {len(all_events)} total)")
            except Exception as e:
                print(f"⚠️ Failed to fetch calendar events: {e}")
                events = []
        
        return {
            'tasks': tasks,
            'events': events
        }
    
    def format_schedule_response(self, schedule_data):
        """
        Format schedule with separate sections for tasks and events.
        
        Args:
            schedule_data: Dict from get_full_schedule()
        
        Returns:
            Formatted string for WhatsApp
        """
        import pytz
        
        israel_tz = pytz.timezone('Asia/Jerusalem')
        tasks = schedule_data.get('tasks', [])
        events = schedule_data.get('events', [])
        
        if not tasks and not events:
            return "📋 אין לך משימות או אירועים להיום!"
        
        parts = []
        
        # Section 1: Bot Tasks (using TaskService formatter for proper format with IDs)
        if tasks:
            parts.append(f"📋 המשימות שלך ({len(tasks)}):\n")
            
            # Import TaskService to use its format_task_list method
            from ..app import task_service
            formatted_tasks = task_service.format_task_list(tasks, show_due_date=True)
            parts.append(formatted_tasks)
            parts.append("")  # Empty line separator
        
        # Section 2: Calendar Events (non-task events)
        if events:
            parts.append(f"📅 אירועים ביומן ({len(events)}):")
            for event in events:
                start_time = event['start'].astimezone(israel_tz).strftime('%H:%M')
                end_time = event['end'].astimezone(israel_tz).strftime('%H:%M')
                # Changed icon from 🕐 to 🗓️ (better WhatsApp support)
                parts.append(f"🗓️ {start_time}-{end_time} {event['title'][:50]}")
        
        return "\n".join(parts)
