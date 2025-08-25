"""
Monitoring and alerting service for system health
"""
import os
import time
import logging
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MonitoringService:
    """Centralized monitoring and alerting system"""
    
    def __init__(self, whatsapp_service=None, alert_phone_numbers=None):
        self.whatsapp_service = whatsapp_service
        self.alert_phone_numbers = alert_phone_numbers or ["972542607800"]
        self.last_alerts = {}  # Track last alert times to prevent spam
        self.alert_cooldown = 300  # 5 minutes between same type of alerts
        self.health_status = {
            'worker_failures': 0,
            'consecutive_worker_failures': 0,
            'redis_failures': 0,
            'consecutive_redis_failures': 0,
            'database_failures': 0,
            'consecutive_database_failures': 0,
            'last_worker_success': None,
            'last_redis_success': None,
            'last_database_success': None,
            'system_start_time': time.time()
        }
        self.critical_failure_threshold = 3
        self.redis_failure_threshold = 2
        self.database_failure_threshold = 2
        
    def should_send_alert(self, alert_type: str) -> bool:
        """Check if we should send an alert based on cooldown period"""
        now = time.time()
        last_alert_time = self.last_alerts.get(alert_type, 0)
        
        if now - last_alert_time >= self.alert_cooldown:
            self.last_alerts[alert_type] = now
            return True
        return False
    
    def send_alert(self, message: str, alert_type: str = "general") -> bool:
        """Send alert message to configured phone numbers"""
        if not self.should_send_alert(alert_type):
            logger.info(f"Alert cooldown active for {alert_type}, skipping...")
            return False
        
        if not self.whatsapp_service:
            logger.warning("WhatsApp service not available for alerts")
            return False
        
        try:
            alert_message = f"🚨 SYSTEM ALERT\n\n{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            success_count = 0
            for phone_number in self.alert_phone_numbers:
                try:
                    result = self.whatsapp_service.send_message(phone_number, alert_message)
                    if result.get("success"):
                        success_count += 1
                        logger.info(f"Alert sent to {phone_number}")
                    else:
                        logger.error(f"Failed to send alert to {phone_number}: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Error sending alert to {phone_number}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp alert: {e}")
            return False
    
    def record_worker_success(self):
        """Record successful worker operation"""
        self.health_status['last_worker_success'] = time.time()
        self.health_status['consecutive_worker_failures'] = 0
        logger.debug("Worker success recorded")
    
    def record_worker_failure(self, error_message: str):
        """Record worker failure and send alert if threshold exceeded"""
        self.health_status['worker_failures'] += 1
        self.health_status['consecutive_worker_failures'] += 1
        
        logger.error(f"Worker failure recorded: {error_message}")
        
        if self.health_status['consecutive_worker_failures'] >= self.critical_failure_threshold:
            alert_message = f"""Worker System Critical Failure
            
Consecutive Failures: {self.health_status['consecutive_worker_failures']}
Total Failures: {self.health_status['worker_failures']}
Last Error: {error_message}

The worker system may be down and requires immediate attention."""
            
            self.send_alert(alert_message, "worker_critical")
    
    def record_redis_success(self):
        """Record successful Redis operation"""
        self.health_status['last_redis_success'] = time.time()
        self.health_status['consecutive_redis_failures'] = 0
    
    def record_redis_failure(self, error_message: str):
        """Record Redis failure and send alert if threshold exceeded"""
        self.health_status['redis_failures'] += 1
        self.health_status['consecutive_redis_failures'] += 1
        
        logger.error(f"Redis failure recorded: {error_message}")
        
        if self.health_status['consecutive_redis_failures'] >= self.redis_failure_threshold:
            alert_message = f"""Redis System Failure
            
Consecutive Failures: {self.health_status['consecutive_redis_failures']}
Total Failures: {self.health_status['redis_failures']}
Last Error: {error_message}

Redis may be unavailable. System is falling back to in-memory storage."""
            
            self.send_alert(alert_message, "redis_failure")
    
    def record_database_success(self):
        """Record successful database operation"""
        self.health_status['last_database_success'] = time.time()
        self.health_status['consecutive_database_failures'] = 0
    
    def record_database_failure(self, error_message: str):
        """Record database failure and send alert if threshold exceeded"""
        self.health_status['database_failures'] += 1
        self.health_status['consecutive_database_failures'] += 1
        
        logger.error(f"Database failure recorded: {error_message}")
        
        if self.health_status['consecutive_database_failures'] >= self.database_failure_threshold:
            alert_message = f"""Database System Critical Failure
            
Consecutive Failures: {self.health_status['consecutive_database_failures']}
Total Failures: {self.health_status['database_failures']}
Last Error: {error_message}

Database may be unavailable. System functionality is severely impacted."""
            
            self.send_alert(alert_message, "database_critical")
    
    def record_api_rate_limit(self, service_name: str, limit_type: str):
        """Record API rate limit hit"""
        alert_message = f"""API Rate Limit Exceeded
        
Service: {service_name}
Limit Type: {limit_type}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The {service_name} service has hit rate limits and may experience delays."""
        
        self.send_alert(alert_message, f"rate_limit_{service_name}")
    
    def record_circuit_breaker_open(self, service_name: str):
        """Record circuit breaker opening"""
        alert_message = f"""Circuit Breaker Opened
        
Service: {service_name}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The {service_name} circuit breaker has opened due to repeated failures. Service is temporarily unavailable."""
        
        self.send_alert(alert_message, f"circuit_breaker_{service_name}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current system health status"""
        now = time.time()
        uptime = now - self.health_status['system_start_time']
        
        # Check if components are healthy based on recent success
        worker_healthy = (
            self.health_status['consecutive_worker_failures'] < self.critical_failure_threshold and
            (self.health_status['last_worker_success'] is None or 
             now - self.health_status['last_worker_success'] < 300)  # 5 minutes
        )
        
        redis_healthy = (
            self.health_status['consecutive_redis_failures'] < self.redis_failure_threshold
        )
        
        database_healthy = (
            self.health_status['consecutive_database_failures'] < self.database_failure_threshold and
            (self.health_status['last_database_success'] is None or 
             now - self.health_status['last_database_success'] < 60)  # 1 minute
        )
        
        overall_health = "healthy" if all([worker_healthy, redis_healthy, database_healthy]) else "degraded"
        
        return {
            'overall_health': overall_health,
            'uptime_seconds': int(uptime),
            'uptime_formatted': self._format_uptime(uptime),
            'components': {
                'worker': {
                    'healthy': worker_healthy,
                    'total_failures': self.health_status['worker_failures'],
                    'consecutive_failures': self.health_status['consecutive_worker_failures'],
                    'last_success': self.health_status['last_worker_success']
                },
                'redis': {
                    'healthy': redis_healthy,
                    'total_failures': self.health_status['redis_failures'],
                    'consecutive_failures': self.health_status['consecutive_redis_failures'],
                    'last_success': self.health_status['last_redis_success']
                },
                'database': {
                    'healthy': database_healthy,
                    'total_failures': self.health_status['database_failures'],
                    'consecutive_failures': self.health_status['consecutive_database_failures'],
                    'last_success': self.health_status['last_database_success']
                }
            },
            'thresholds': {
                'worker_critical': self.critical_failure_threshold,
                'redis_failure': self.redis_failure_threshold,
                'database_critical': self.database_failure_threshold
            }
        }
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"
    
    def send_startup_alert(self):
        """Send system startup notification"""
        message = f"""System Started Successfully
        
WhatsApp Todo Bot is now online and ready to serve users.
Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

All systems are operational."""
        
        self.send_alert(message, "system_startup")
    
    def send_shutdown_alert(self):
        """Send system shutdown notification"""
        uptime = time.time() - self.health_status['system_start_time']
        
        message = f"""System Shutdown Initiated
        
WhatsApp Todo Bot is shutting down.
Uptime: {self._format_uptime(uptime)}
Shutdown Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

System will be unavailable until restart."""
        
        self.send_alert(message, "system_shutdown")
    
    def periodic_health_check(self):
        """Perform periodic health check and send summary if needed"""
        health = self.get_health_status()
        
        # Send health summary if system is degraded
        if health['overall_health'] == 'degraded':
            unhealthy_components = [
                comp for comp, status in health['components'].items() 
                if not status['healthy']
            ]
            
            message = f"""System Health Check - Degraded
            
Unhealthy Components: {', '.join(unhealthy_components)}
Uptime: {health['uptime_formatted']}

Please check the system logs for more details."""
            
            self.send_alert(message, "health_check")