"""
WhatsApp API service for sending messages and handling interactions
"""
import os
import requests
import json
import time
import random
from typing import Dict, Any, List, Optional

from ..utils.rate_limiter import APIRateLimiter
from ..utils.circuit_breaker import CircuitBreaker

class WhatsAppService:
    """Handle WhatsApp API interactions"""
    
    def __init__(self, redis_client=None):
        self.api_url = "https://graph.facebook.com/v22.0/900153549837183/messages"
        self.token = os.getenv('WHATSAPP_TOKEN')
        if not self.token:
            raise ValueError("WHATSAPP_TOKEN environment variable is required")
        
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        # Rate limiting and circuit breaker
        self.rate_limiter = APIRateLimiter(
            service_name="whatsapp",
            requests_per_minute=50,
            requests_per_hour=1000,
            requests_per_day=10000,
            redis_client=redis_client
        )
        
        self.circuit_breaker = CircuitBreaker(
            service_name="whatsapp",
            failure_threshold=5,
            recovery_timeout=60
        )
    
    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        """Send a text message via WhatsApp API"""
        # Check rate limiting
        allowed, error_msg = self.rate_limiter.is_allowed()
        if not allowed:
            return {"success": False, "error": f"Rate limit exceeded: {error_msg}"}
        
        # Check circuit breaker
        available, status_msg = self.circuit_breaker.is_available()
        if not available:
            return {"success": False, "error": f"Service unavailable: {status_msg}"}
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "text": {"body": text}
        }
        
        try:
            response = self._make_api_call_with_retry(payload)
            self.circuit_breaker.record_success()
            return {"success": True, "response": response}
            
        except Exception as e:
            print(f"❌ WhatsApp send message error: {e}")
            self.circuit_breaker.record_failure(e)
            return {"success": False, "error": str(e)}
    
    def send_interactive_message(self, to: str, text: str, buttons: List[Dict] = None) -> Dict[str, Any]:
        """Send an interactive message with buttons"""
        # Check rate limiting
        allowed, error_msg = self.rate_limiter.is_allowed()
        if not allowed:
            return {"success": False, "error": f"Rate limit exceeded: {error_msg}"}
        
        # Check circuit breaker  
        available, status_msg = self.circuit_breaker.is_available()
        if not available:
            return {"success": False, "error": f"Service unavailable: {status_msg}"}
        
        if not buttons:
            # Fallback to regular message if no buttons
            return self.send_message(to, text)
        
        # Build interactive message payload
        interactive_buttons = []
        for i, button in enumerate(buttons[:3]):  # WhatsApp allows max 3 buttons
            interactive_buttons.append({
                "type": "reply",
                "reply": {
                    "id": button.get("id", f"btn_{i}"),
                    "title": button.get("title", "Button")[:20]  # Max 20 chars
                }
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {"buttons": interactive_buttons}
            }
        }
        
        try:
            response = self._make_api_call_with_retry(payload)
            self.circuit_breaker.record_success()
            return {"success": True, "response": response}
            
        except Exception as e:
            print(f"❌ WhatsApp interactive message error: {e}")
            self.circuit_breaker.record_failure(e)
            # Fallback to regular message
            return self.send_message(to, text)
    
    def send_welcome_message_with_button(self, to: str) -> Dict[str, Any]:
        """Send welcome message with quick action buttons"""
        welcome_text = self._get_welcome_message()
        buttons = [
            {"id": "help", "title": "📋 Help"},
            {"id": "tasks", "title": "✅ My Tasks"},
            {"id": "stats", "title": "📊 Stats"}
        ]
        
        return self.send_interactive_message(to, welcome_text, buttons)
    
    def _get_welcome_message(self) -> str:
        """Get welcome message text"""
        messages = [
            "👋 Welcome to your AI-powered Todo Assistant!\n\nI can help you:\n• Create and manage tasks\n• Set reminders\n• Track your productivity\n• Answer questions\n\nJust send me a message and I'll help organize your tasks!",
            
            "🤖 Hello! I'm your personal task manager.\n\n✨ What I can do:\n• Extract tasks from your messages\n• Set due dates and reminders\n• Track your progress\n• Answer questions\n\nTry telling me about something you need to do!",
            
            "🎯 Hi there! Ready to get organized?\n\nI'll help you:\n📝 Turn messages into actionable tasks\n⏰ Never miss a deadline\n📊 Track your productivity\n💬 Answer your questions\n\nWhat would you like to accomplish today?"
        ]
        return random.choice(messages)
    
    def _make_api_call_with_retry(self, payload: Dict, max_retries: int = 3) -> Dict:
        """Make WhatsApp API call with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if response.status_code == 429:  # Rate limit
                        raise Exception(f"Rate limited by WhatsApp: {error_msg}")
                    elif response.status_code >= 500:  # Server errors - retry
                        raise Exception(f"WhatsApp server error: {error_msg}")
                    else:  # Client errors - don't retry
                        raise Exception(f"WhatsApp client error: {error_msg}")
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"WhatsApp API timeout, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    raise Exception("WhatsApp API timeout after retries")
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"WhatsApp API request failed, retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)
                else:
                    raise Exception(f"WhatsApp API request failed: {e}")
                    
            except Exception as e:
                if attempt < max_retries - 1 and "server error" in str(e).lower():
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"WhatsApp API error, retrying in {delay:.1f}s: {e}")
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
