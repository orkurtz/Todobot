# References for Add Date to Dateless Tasks Command

## Similar Implementations

### Delay All Overdue to Next Hour

- **Location:** `src/services/task_service.py:L577` and `src/routes/webhook.py:L712`
- **Relevance:** This is the command "דחה משימות שעברו" that moves expired tasks to the next hour.
- **Key patterns:**
  - Standard timezone calculations for target hour in Israel:
    ```python
    now_israel = datetime.now(self.israel_tz)
    start_of_hour = now_israel.replace(minute=0, second=0, microsecond=0)
    target_israel = start_of_hour + timedelta(hours=1)
    new_due_utc = target_israel.astimezone(pytz.UTC).replace(tzinfo=None)
    ```
  - Querying tasks and sorting them.
  - Updating task values using `update_task`.
  - Aggregating list of successful updates versus failed ones.
