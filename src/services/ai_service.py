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
3. For 'complete' or 'delete': Extract task identifier (number or keywords)
4. For 'update': Extract task identifier AND new description (and optionally new date)
5. For 'reschedule': Extract task identifier AND new due date/time
6. Support natural language dates in Hebrew and English
7. Do not create tasks for casual conversation, questions without action, past completed actions, or vague statements.

Actions:
- 'add': Create new task
- 'complete': Mark task as done
- 'delete': Remove task
- 'update': Change task description (and optionally due date)
- 'reschedule': Change only the due date/time
- 'query': Ask about tasks

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
Hebrew:
- "העבר משימה 2 למחר" → {{"tasks": [{{"action": "reschedule", "task_id": "2", "due_date": "מחר"}}]}}
- "שנה משימה 3 להתקשר לרופא" → {{"tasks": [{{"action": "update", "task_id": "3", "new_description": "התקשר לרופא"}}]}}
- "דחה משימה 1 ביומיים" → {{"tasks": [{{"action": "reschedule", "task_id": "1", "due_date": "מחרתיים"}}]}}
- "עדכן משימה 5 קנה חלב מחר ב-10" → {{"tasks": [{{"action": "update", "task_id": "5", "new_description": "קנה חלב", "due_date": "מחר ב-10:00"}}]}}

English:
- "Move task 2 to tomorrow" → {{"tasks": [{{"action": "reschedule", "task_id": "2", "due_date": "tomorrow"}}]}}
- "Change task 3 to call dentist" → {{"tasks": [{{"action": "update", "task_id": "3", "new_description": "call dentist"}}]}}
- "Postpone task 1 by 2 days" → {{"tasks": [{{"action": "reschedule", "task_id": "1", "due_date": "in 2 days"}}]}}

Previous examples still valid:
- "Done with task 2" → {{"tasks": [{{"action": "complete", "description": "2"}}]}}
- "Remind me to buy milk tomorrow morning" → {{"tasks": [{{"action": "add", "description": "buy milk", "due_date": "tomorrow morning"}}]}}

Message to analyze: {message}"""
        }
    
    def get_response(self, user_id: int, user_message: str, conversation_history: List = None) -> str:
        """Get AI response from Gemini"""
        # Check rate limiting
        allowed, error_msg = self.rate_limiter.is_allowed()
        if not allowed:
            return f"⚠️ AI service temporarily unavailable: {error_msg}"
        
        # Check circuit breaker
        available, status_msg = self.circuit_breaker.is_available()
        if not available:
            return f"⚠️ AI service temporarily unavailable: {status_msg}"
        
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
            return "Sorry, I'm having trouble processing your request right now. Please try again in a moment."
    
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
            
            # ------------------------------------------------------------------
            # === SIMPLE & EFFECTIVE FIX START ===
            # This robustly finds and extracts the JSON from the raw response.
            # ------------------------------------------------------------------
            
            # Use regex to find the JSON block, ignoring the ```json ... ```
            # re.DOTALL makes '.' match newlines, which is crucial here.
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            
            if not match:
                print(f"Failed to find any JSON in the AI response.")
                print(f"Raw response: {response_text}")
                return []

            # Extract the matched JSON string
            cleaned_response = match.group(0)
            
            # ------------------------------------------------------------------
            # === SIMPLE & EFFECTIVE FIX END ===
            # ------------------------------------------------------------------

            # Parse JSON response
            try:
                # Parse the *cleaned* text
                parsed_data = json.loads(cleaned_response) 
                tasks = parsed_data.get('tasks', [])
                
                # Validate and clean tasks - INCLUDING action field
                valid_tasks = []
                for task in tasks:
                    if task.get('description') and len(task['description'].strip()) > 0:
                        valid_tasks.append({
                            'action': task.get('action', 'add'),  # Include action field
                            'description': task['description'].strip(),
                            'due_date': task.get('due_date'),
                            'status': task.get('status', 'pending')  # Include status field
                        })
                
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
