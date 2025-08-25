"""
Rate limiting utilities for API calls
"""
import time
from typing import Tuple, Optional
from collections import defaultdict

class APIRateLimiter:
    """Rate limiter for external APIs with Redis backend"""
    
    def __init__(self, service_name: str, requests_per_minute: int, redis_client=None, 
                 requests_per_hour: int = None, requests_per_day: int = None):
        self.service_name = service_name
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.redis_client = redis_client
        
        # Fallback in-memory storage when Redis unavailable
        self._fallback_storage = defaultdict(list)
    
    def is_allowed(self) -> Tuple[bool, Optional[str]]:
        """Check if API request is allowed based on rate limits"""
        current_time = int(time.time())
        
        if self.redis_client:
            return self._check_redis_limits(current_time)
        else:
            return self._check_memory_limits(current_time)
    
    def _check_redis_limits(self, current_time: int) -> Tuple[bool, Optional[str]]:
        """Redis-based rate limit checking"""
        try:
            # Check per-minute limit
            minute_key = f"api_rate:{self.service_name}:minute:{current_time // 60}"
            minute_count = self.redis_client.get(minute_key) or 0
            minute_count = int(minute_count)
            
            if minute_count >= self.requests_per_minute:
                return False, f"{self.service_name} rate limit exceeded: {minute_count}/{self.requests_per_minute} per minute"
            
            # Check per-hour limit if configured
            if self.requests_per_hour:
                hour_key = f"api_rate:{self.service_name}:hour:{current_time // 3600}"
                hour_count = self.redis_client.get(hour_key) or 0
                hour_count = int(hour_count)
                
                if hour_count >= self.requests_per_hour:
                    return False, f"{self.service_name} hourly rate limit exceeded: {hour_count}/{self.requests_per_hour} per hour"
            
            # Check per-day limit if configured
            if self.requests_per_day:
                day_key = f"api_rate:{self.service_name}:day:{current_time // 86400}"
                day_count = self.redis_client.get(day_key) or 0
                day_count = int(day_count)
                
                if day_count >= self.requests_per_day:
                    return False, f"{self.service_name} daily rate limit exceeded: {day_count}/{self.requests_per_day} per day"
            
            # All checks passed - increment counters
            pipe = self.redis_client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)  # Keep for 2 minutes
            
            if self.requests_per_hour:
                pipe.incr(hour_key)
                pipe.expire(hour_key, 7200)  # Keep for 2 hours
            
            if self.requests_per_day:
                pipe.incr(day_key)
                pipe.expire(day_key, 172800)  # Keep for 2 days
            
            pipe.execute()
            return True, None
            
        except Exception as e:
            print(f"Redis rate limiter error: {e}, falling back to memory")
            return self._check_memory_limits(current_time)
    
    def _check_memory_limits(self, current_time: int) -> Tuple[bool, Optional[str]]:
        """Fallback in-memory rate limit checking"""
        minute_window = current_time // 60
        
        # Clean old entries and check limits
        self._fallback_storage[f"{self.service_name}_minute"] = [
            t for t in self._fallback_storage[f"{self.service_name}_minute"] 
            if t >= minute_window - 1  # Keep last 2 minutes
        ]
        
        minute_count = len([t for t in self._fallback_storage[f"{self.service_name}_minute"] if t == minute_window])
        
        if minute_count >= self.requests_per_minute:
            return False, f"{self.service_name} rate limit exceeded: {minute_count}/{self.requests_per_minute} per minute"
        
        # Add current request
        self._fallback_storage[f"{self.service_name}_minute"].append(minute_window)
        return True, None
    
    def get_usage_stats(self) -> dict:
        """Get current usage statistics"""
        current_time = int(time.time())
        stats = {'service': self.service_name}
        
        if self.redis_client:
            try:
                minute_key = f"api_rate:{self.service_name}:minute:{current_time // 60}"
                hour_key = f"api_rate:{self.service_name}:hour:{current_time // 3600}"
                day_key = f"api_rate:{self.service_name}:day:{current_time // 86400}"
                
                stats['minute_usage'] = f"{self.redis_client.get(minute_key) or 0}/{self.requests_per_minute}"
                
                if self.requests_per_hour:
                    stats['hour_usage'] = f"{self.redis_client.get(hour_key) or 0}/{self.requests_per_hour}"
                
                if self.requests_per_day:
                    stats['day_usage'] = f"{self.redis_client.get(day_key) or 0}/{self.requests_per_day}"
                    
            except Exception:
                stats['error'] = 'Redis unavailable'
        else:
            minute_window = current_time // 60
            minute_count = len([t for t in self._fallback_storage[f"{self.service_name}_minute"] if t == minute_window])
            stats['minute_usage'] = f"{minute_count}/{self.requests_per_minute}"
        
        return stats