# Centralized Health Monitoring & WhatsApp Alerting

Standardize tracking of system component failures and developer notification policies.

## Rules

- **WhatsApp Alerting**: Deliver critical system alerts (e.g., database down, consecutive worker failures, circuit breaker openings) to admin phone numbers directly via WhatsApp.
- **Alert Cooldown**: Implement a 5-minute (300 seconds) alert cooldown per category to avoid spamming admin channels during cascading failures.
- **Graceful Redis Fallback Alerting**: Notify admins when Redis fails and the system downgrades to in-memory state tracking.
- **Fail-Fast Reset**: Clear consecutive failure counters immediately upon a successful component operation.

## Code Example

```python
def send_alert(self, message: str, alert_type: str = "general") -> bool:
    # Ensure cooldown is respected to avoid notification floods
    now = time.time()
    if now - self.last_alerts.get(alert_type, 0) < self.alert_cooldown:
        return False
        
    self.last_alerts[alert_type] = now
    # Send message to admin list via WhatsApp...
```

## Rationale
- Using WhatsApp for admin alerts consolidates communications within the bot's native channel for immediate attention.
- Cooldown thresholds prevent notification exhaustion when high-frequency errors occur.
