# Background Jobs & Lock Management

Configure and run background tasks reliably in resource-constrained environments (e.g., 512MB RAM limits).

## Rules

- **Limit Thread Count**: Constrain APScheduler's `ThreadPoolExecutor` to a maximum of 4 threads to prevent Out-Of-Memory (OOM) failures and database connection pool exhaustion.
- **Context Wrapping**: Always execute DB transactions in background jobs within a Flask application context (`with app.app_context():`).
- **Concurrent Execution Lock**: Wrap critical/external side-effect actions (like sending notifications) in a lock (`reminder_lock:<id>` via Redis or in-memory fallback) to ensure that duplicate jobs do not trigger duplicate messages.
- **Transactional Atomicity**: Perform changes and commits within a single transaction block, calling `db.session.rollback()` in `except` blocks to prevent lockups and dirty database states.

## Code Example

```python
def send_task_reminder(task, app):
    lock_key = f"reminder_lock:{task.id}"
    lock_acquired = redis_client.set(lock_key, "locked", nx=True, ex=30) if redis_client else True
    
    if not lock_acquired:
        return  # Skip processing if another worker has the lock
        
    try:
        with app.app_context():
            current_task = Task.query.get(task.id)
            if current_task.status == 'pending' and not current_task.reminder_sent:
                # Send message and make database updates
                current_task.reminder_sent = True
                db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    finally:
        if redis_client and lock_acquired:
            redis_client.delete(lock_key)
```

## Rationale
- Thread limits prevent resource exhaustion on entry-level hosting environments like Railway or Heroku.
- Explicit locks prevent race conditions when multiple jobs run close to each other.
- Proper transaction error handling avoids stale DB sessions.
