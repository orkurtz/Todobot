""""
AI service for handling Gemini API interactions and task parsing
"""
import os
import google.generativeai as genai
import json
import time
import random
import re  # <-- *** ADD THIS IMPORT AT THE TOP ***
from typing import Dict, Any, List, Optional


# Import rate limiter and circuit breaker
from ..utils.rate_limiter import APIRateLimiter
from ..utils.circuit_breaker import CircuitBreaker

class AIService:
    """Handle AI-related operations including Gemini API calls"""
    
    def __init__(self, redis_client=None):
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
            
            'task_parsing': """Analyze the user's message to identify task-related actions: adding new tasks, completing existing tasks, deleting existing tasks, or updating/rescheduling existing tasks.

Instructions:
1. Determine the user's primary intent: 'add', 'complete', 'delete', 'update', 'reschedule', or 'query'
2. For 'add': Extract the task description and due date/time
3. For 'complete' or 'delete': Extract task identifier (number or keywords) - ALWAYS set task_id field!
4. For 'update': Extract task identifier AND new description (and optionally new date) - ALWAYS set task_id field!
5. For 'reschedule': Extract task identifier AND new due date/time - ALWAYS set task_id field!
6. Support natural language dates in Hebrew and English, including relative times like "בעוד X דקות/שעות" and "in X minutes/hours"
7. Do not create tasks for casual conversation, questions without action, past completed actions, or vague statements.
8. CRITICAL: When user mentions a task number (like "משימה 2", "task 3", just "2", etc), ALWAYS include "task_id": "NUMBER" in the JSON!

Actions:
- 'add': Create new task
- 'complete': Mark task as done
- 'delete': Remove task
- 'update': Change task description (and optionally due date)
- 'reschedule': Change only the due date/time
- 'query': Ask about tasks
- 'stop_series': Stop a recurring series
- 'complete_series': Complete a recurring series

Recurring Task Support:
- "תזכיר לי כל יום..." → daily recurring
- "כל יום ב-9" / "every day at 9am" → daily at specific time
- "כל שבוע" / "every week" → weekly recurring
- "כל יום שני" / "every Monday" → weekly on specific day
- "כל יום שני ורביעי" / "every Monday and Wednesday" → specific multiple days
- "כל יומיים" / "every 2 days" → interval recurring
- "כל שני וחמישי ב-15:00" → specific days with time

Series Management:
- "עצור סדרה [מספר]" / "stop series [number]" → stop_series action
- "השלם סדרה [מספר]" / "complete series [number]" → complete_series action
- "מחק סדרה [מספר]" / "delete series [number]" → stop_series with delete

For recurring tasks, add these fields:
- "recurrence_pattern": "daily" | "weekly" | "specific_days" | "interval"
- "recurrence_interval": number (default 1)
- "recurrence_days_of_week": ["monday", "wednesday"] or null
- "recurrence_end_date": date string or null

Current date for reference: {current_date}
User timezone: Asia/Jerusalem

Respond with JSON only:
{{"tasks": [
    {{
        "action": "add" | "complete" | "delete" | "update" | "reschedule" | "query",
        "description": "task description OR identifier OR new description",
        "due_date": "natural language date" or "YYYY-MM-DD HH:MM" or null,
        "task_id": task number as string or null,
        "new_description": "new description for update action" or null
    }}
]}}

Examples:
Hebrew - Reschedule (דחייה/הקדמה):
- "העבר משימה 2 למחר" → {{"tasks": [{{"action": "reschedule", "task_id": "2", "due_date": "מחר"}}]}}
- "דחה משימה 1 ביומיים" → {{"tasks": [{{"action": "reschedule", "task_id": "1", "due_date": "מחרתיים"}}]}}
- "דחה משימה 3 בשעתיים" → {{"tasks": [{{"action": "reschedule", "task_id": "3", "due_date": "בעוד שעתיים"}}]}}
- "העבר משימה 5 בעוד 30 דקות" → {{"tasks": [{{"action": "reschedule", "task_id": "5", "due_date": "בעוד 30 דקות"}}]}}
- "דחה 2 בעוד שבוע" → {{"tasks": [{{"action": "reschedule", "task_id": "2", "due_date": "בעוד שבוע"}}]}}
- "דחה משימה 12 ל-31/10" → {{"tasks": [{{"action": "reschedule", "task_id": "12", "due_date": "31/10"}}]}}
- "דחה ל-31/10 את משימה 12" → {{"tasks": [{{"action": "reschedule", "task_id": "12", "due_date": "31/10"}}]}}
- "העבר משימה 5 לתאריך 15/12" → {{"tasks": [{{"action": "reschedule", "task_id": "5", "due_date": "15/12"}}]}}
- "העבר ל-15/12 משימה 5" → {{"tasks": [{{"action": "reschedule", "task_id": "5", "due_date": "15/12"}}]}}
- "דחה את 3 ל-5/11 בשעה 14:00" → {{"tasks": [{{"action": "reschedule", "task_id": "3", "due_date": "5/11 14:00"}}]}}
- "את משימה 7 דחה ל-20/11" → {{"tasks": [{{"action": "reschedule", "task_id": "7", "due_date": "20/11"}}]}}

Hebrew - Update (שינוי תיאור):
- "שנה משימה 3 להתקשר לרופא" → {{"tasks": [{{"action": "update", "task_id": "3", "new_description": "התקשר לרופא"}}]}}
- "עדכן משימה 5 קנה חלב מחר ב-10" → {{"tasks": [{{"action": "update", "task_id": "5", "new_description": "קנה חלב", "due_date": "מחר ב-10:00"}}]}}
- "שנה 1 ללקנות לחם" → {{"tasks": [{{"action": "update", "task_id": "1", "new_description": "לקנות לחם"}}]}}

Hebrew - Complete (השלמה):
- "סיימתי משימה 2" → {{"tasks": [{{"action": "complete", "description": "2", "task_id": "2"}}]}}
- "גמרתי את 3" → {{"tasks": [{{"action": "complete", "description": "3", "task_id": "3"}}]}}

Hebrew - Add (יצירה):
- "תזכיר לי לקנות חלב מחר בבוקר" → {{"tasks": [{{"action": "add", "description": "לקנות חלב", "due_date": "מחר בבוקר"}}]}}
- "להתקשר לאמא בעוד שעה" → {{"tasks": [{{"action": "add", "description": "להתקשר לאמא", "due_date": "בעוד שעה"}}]}}

English - Reschedule:
- "Move task 2 to tomorrow" → {{"tasks": [{{"action": "reschedule", "task_id": "2", "due_date": "tomorrow"}}]}}
- "Postpone task 1 by 2 days" → {{"tasks": [{{"action": "reschedule", "task_id": "1", "due_date": "in 2 days"}}]}}
- "Reschedule task 3 in 2 hours" → {{"tasks": [{{"action": "reschedule", "task_id": "3", "due_date": "in 2 hours"}}]}}
- "Delay 5 by 30 minutes" → {{"tasks": [{{"action": "reschedule", "task_id": "5", "due_date": "in 30 minutes"}}]}}

English - Update:
- "Change task 3 to call dentist" → {{"tasks": [{{"action": "update", "task_id": "3", "new_description": "call dentist"}}]}}
- "Update task 2 buy bread tomorrow" → {{"tasks": [{{"action": "update", "task_id": "2", "new_description": "buy bread", "due_date": "tomorrow"}}]}}

English - Complete:
- "Done with task 2" → {{"tasks": [{{"action": "complete", "description": "2", "task_id": "2"}}]}}
- "Finished 3" → {{"tasks": [{{"action": "complete", "description": "3", "task_id": "3"}}]}}

Recurring Tasks:
"תזכיר לי כל יום ב-9 לקחת ויטמינים" →
{{"tasks": [{{"action": "add", "description": "לקחת ויטמינים", "due_date": "היום ב-9:00", "recurrence_pattern": "daily", "recurrence_interval": 1}}]}}

"כל יום שני ורביעי ב-10 להתקשר" →
{{"tasks": [{{"action": "add", "description": "להתקשר", "due_date": "next Monday at 10am", "recurrence_pattern": "specific_days", "recurrence_days_of_week": ["monday", "wednesday"]}}]}}

"כל יומיים להשקות צמחים" →
{{"tasks": [{{"action": "add", "description": "להשקות צמחים", "due_date": "היום", "recurrence_pattern": "interval", "recurrence_interval": 2}}]}}

"every day at 9am take vitamins" →
{{"tasks": [{{"action": "add", "description": "take vitamins", "due_date": "today at 9am", "recurrence_pattern": "daily", "recurrence_interval": 1}}]}}

Series Management:
"עצור סדרה 5" →
{{"tasks": [{{"action": "stop_series", "task_id": "5"}}]}}

"השלם סדרה 3" →
{{"tasks": [{{"action": "complete_series", "task_id": "3"}}]}}

Important: Always include "task_id" field when user mentions a specific task number!

Message to analyze: {message}"""
        }
    
    def get_response(self, user_id: int, user_message: str, conversation_history: List = None) -> str:
        """Get AI response from Gemini"""
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
            
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
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
                            'description': task.get('description', '').strip(),  # Can be empty for these actions
                            'due_date': task.get('due_date'),
                            'status': task.get('status', 'pending'),
                            'task_id': task.get('task_id'),
                            'new_description': task.get('new_description'),
                            # NEW: Recurring fields
                            'recurrence_pattern': task.get('recurrence_pattern'),
                            'recurrence_interval': task.get('recurrence_interval', 1),
                            'recurrence_days_of_week': task.get('recurrence_days_of_week'),
                            'recurrence_end_date': task.get('recurrence_end_date')
                        })
                    # For 'add' action, description is required
                    elif action == 'add' and task.get('description') and len(task['description'].strip()) > 0:
                        valid_tasks.append({
                            'action': action,
                            'description': task['description'].strip(),
                            'due_date': task.get('due_date'),
                            'status': task.get('status', 'pending'),
                            'task_id': task.get('task_id'),
                            'new_description': task.get('new_description'),
                            # NEW: Recurring fields
                            'recurrence_pattern': task.get('recurrence_pattern'),
                            'recurrence_interval': task.get('recurrence_interval', 1),
                            'recurrence_days_of_week': task.get('recurrence_days_of_week'),
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
            
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Build prompt for audio transcription + task extraction
            audio_prompt = f"""You are an expert at understanding voice messages in Hebrew and English and extracting actionable tasks.

Listen to this audio message and:
1. Transcribe what the person is saying
2. Extract any tasks or to-do items mentioned
3. Identify due dates mentioned (in Hebrew or English)

Current date for reference: {current_date}
User timezone: Asia/Jerusalem (Israel)

Return JSON in this exact format:
{{
    "transcription": "the transcribed text here",
    "tasks": [
        {{
            "action": "add" | "complete" | "delete" | "update" | "reschedule" | "query",
            "description": "task description",
            "due_date": "natural language date like 'מחר', 'tomorrow', 'יום שלישי'" or null,
            "task_id": task number if mentioned or null,
            "new_description": "new description for update action" or null
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
                        if task.get('description') and len(task['description'].strip()) > 0:
                            valid_tasks.append({
                                'action': task.get('action', 'add'),
                                'description': task['description'].strip(),
                                'due_date': task.get('due_date'),
                                'status': task.get('status', 'pending'),
                                'task_id': task.get('task_id'),
                                'new_description': task.get('new_description'),
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
