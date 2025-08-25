"""
Circuit breaker pattern for API resilience
"""
import time
from enum import Enum
from typing import Tuple

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker pattern for API resilience"""
    
    def __init__(self, service_name: str, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: type = Exception):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.next_attempt_time = None
    
    def is_available(self) -> Tuple[bool, str]:
        """Check if service is available according to circuit breaker"""
        current_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True, "Service available"
        
        elif self.state == CircuitState.OPEN:
            if current_time >= self.next_attempt_time:
                self.state = CircuitState.HALF_OPEN
                return True, "Testing service recovery"
            else:
                remaining = int(self.next_attempt_time - current_time)
                return False, f"Circuit breaker OPEN - retry in {remaining}s"
        
        elif self.state == CircuitState.HALF_OPEN:
            return True, "Testing service recovery"
        
        return False, "Unknown circuit breaker state"
    
    def record_success(self):
        """Record successful API call"""
        if self.state == CircuitState.HALF_OPEN:
            print(f"🔄 {self.service_name} circuit breaker: Service recovered, closing circuit")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.next_attempt_time = None
    
    def record_failure(self, exception: Exception):
        """Record failed API call"""
        if not isinstance(exception, self.expected_exception):
            return  # Only count expected failures
        
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                print(f"🔴 {self.service_name} circuit breaker: OPENING due to {self.failure_count} failures")
                self.state = CircuitState.OPEN
                self.next_attempt_time = time.time() + self.recovery_timeout
        
        print(f"⚠️ {self.service_name} failure {self.failure_count}/{self.failure_threshold}: {str(exception)}")