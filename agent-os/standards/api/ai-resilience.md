# AI Service Parsing & Resilience

Establish robust interaction patterns with the Google Gemini API, ensuring error tolerance, rate control, and prompt safety.

## Rules

- **Regex JSON Extraction**: Always extract JSON payloads from LLM responses using `re.search(r"\{.*\}", response_text, re.DOTALL)` to clean formatting artifacts, markdown wrappers (e.g., ` ```json `), or conversational chatter.
- **Circuit Breaker Fail-Safe**: Guard AI API requests with a custom circuit breaker pattern (`CLOSED`, `OPEN`, `HALF_OPEN`) to fail fast during consecutive outages, protecting server performance.
- **API Rate Limiting**: Check service limits prior to execution using Redis rate counters (with in-memory default fallback) to stay within Gemini API tier boundaries.
- **Input Sanitization & Injection Prevention**: Scan input text for common prompt injection phrases (e.g., "ignore previous instructions") or script tags, rejecting unsafe payloads before sending them to the LLM.

## Code Example

```python
# 1. Regex JSON parsing
match = re.search(r"\{.*\}", response_content, re.DOTALL)
if match:
    tasks_data = json.loads(match.group(0))

# 2. Resilience checks
allowed, limit_msg = rate_limiter.is_allowed()
if not allowed:
    return {"success": False, "error": limit_msg}

available, cb_msg = circuit_breaker.is_available()
if not available:
    return {"success": False, "error": cb_msg}
```

## Rationale
- Regex extraction prevents JSON parsing failures caused by conversational leading/trailing output from Gemini.
- Wrapping external dependencies in circuit breakers and rate limiters prevents API bans and server hangs when services are slow or offline.
