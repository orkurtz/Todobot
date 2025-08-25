"""
Input validation and security utilities
"""
import re
import time
from typing import Tuple, Optional
from collections import defaultdict

class InputValidator:
    """Input validation and sanitization"""
    
    # In-memory rate limiting storage
    _user_requests = defaultdict(list)
    
    @staticmethod
    def validate_and_sanitize(user_id: int, message_text: str, message_type: str = "text") -> str:
        """Validate and sanitize user input"""
        if not message_text or not isinstance(message_text, str):
            return None
        
        # Length validation
        if len(message_text) > 4000:  # WhatsApp message limit
            return None
        
        if len(message_text.strip()) == 0:
            return None
        
        # Check content safety
        if not InputValidator._check_content_safety(message_text):
            return None
        
        # Check for prompt injection
        if InputValidator._detect_prompt_injection(message_text):
            return None
        
        # Sanitize text
        sanitized = InputValidator._sanitize_text(message_text)
        
        return sanitized
    
    @staticmethod
    def validate_user_rate_limit(user_id: int, max_per_minute: int = 10) -> bool:
        """Check if user is within rate limits"""
        current_time = time.time()
        user_key = f"user_{user_id}"
        
        # Clean old entries (older than 1 minute)
        cutoff_time = current_time - 60
        InputValidator._user_requests[user_key] = [
            timestamp for timestamp in InputValidator._user_requests[user_key]
            if timestamp > cutoff_time
        ]
        
        # Check if user exceeded limit
        if len(InputValidator._user_requests[user_key]) >= max_per_minute:
            return False
        
        # Add current request
        InputValidator._user_requests[user_key].append(current_time)
        return True
    
    @staticmethod
    def _check_content_safety(text: str) -> bool:
        """Check if content is safe (basic checks)"""
        # Convert to lowercase for checking
        text_lower = text.lower()
        
        # Block potentially harmful patterns
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'on\w+\s*=',  # onclick, onload, etc.
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text_lower):
                print(f"⚠️ Blocked potentially dangerous content: {pattern}")
                return False
        
        return True
    
    @staticmethod
    def _detect_prompt_injection(text: str) -> bool:
        """Detect potential prompt injection attempts"""
        text_lower = text.lower().strip()
        
        # Common prompt injection patterns
        injection_patterns = [
            r'ignore previous instructions',
            r'ignore all previous',
            r'forget everything',
            r'new instructions:',
            r'system:',
            r'assistant:',
            r'human:',
            r'###',
            r'---',
            r'override',
            r'reprogram',
            r'jailbreak',
            r'act as (?:a )?(?:different|new)',
            r'pretend (?:to be|you are)',
            r'roleplay as',
            r'simulate',
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, text_lower):
                print(f"⚠️ Detected potential prompt injection: {pattern}")
                return True
        
        return False
    
    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Sanitize text input"""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Trim whitespace
        text = text.strip()
        
        # Limit length
        if len(text) > 4000:
            text = text[:4000]
        
        return text
    
    @staticmethod
    def validate_voice_message_size(file_size_bytes: int) -> Tuple[bool, Optional[str]]:
        """Validate voice message file size"""
        max_size = 16 * 1024 * 1024  # 16MB limit
        
        if file_size_bytes > max_size:
            return False, f"File too large: {file_size_bytes / (1024*1024):.1f}MB (max: 16MB)"
        
        if file_size_bytes < 1024:  # 1KB minimum
            return False, "File too small"
        
        return True, None
    
    @staticmethod
    def validate_transcribed_voice(transcribed_text: str) -> str:
        """Validate and clean transcribed voice text"""
        if not transcribed_text:
            return None
        
        # Remove common transcription artifacts
        text = transcribed_text.strip()
        
        # Remove transcription confidence markers
        text = re.sub(r'\[.*?\]', '', text)  # Remove [unclear], [music], etc.
        text = re.sub(r'\(.*?\)', '', text)  # Remove (background noise), etc.
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) < 3:  # Too short to be meaningful
            return None
        
        return text