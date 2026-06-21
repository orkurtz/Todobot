# Standards for Add Date to Dateless Tasks Command

The following standards apply to this work.

---

## global/minimalist-code (Minimalist Code / Ponytail Rule)

Maintain a "YAGNI" (You Ain't Gonna Need It) mindset. The best code is the code you never wrote.

### The Ponytail Decision Ladder

Before writing any new code or creating new files, you MUST run through this ladder:
1. **Necessity Check:** Does this feature or code absolutely need to exist to fulfill the task?
2. **Platform Native:** Does the standard library or runtime platform already handle this?
3. **Reusability:** Can we reuse an existing utility, helper, or package in the codebase instead of writing new code?
4. **Minimization:** Can the task be implemented in a simple, minimal way with fewer lines/files?

### Anti-Patterns (NEVER Do This)
- Do NOT add placeholder code, empty files, or unused helper functions for future use.
- Do NOT over-engineer solutions or create complex abstractions (interfaces, classes, wrapper layers) when a simple function is sufficient.
- Do NOT run refactors unless explicitly instructed by the user or required for task success.

---

## api/whatsapp (WhatsApp Integration & Webhook Handling)

Standardize webhook lifecycles, background message processing, and Hebrew command string normalization.

### Rules

- **Immediate Webhook ACK**: Return a HTTP `200 OK` immediately (within 1-2 seconds) to prevent WhatsApp from retrying the request. Process the actual task logic asynchronously on a background daemon thread.
- **Deduplication Check**: Store and query incoming `whatsapp_message_id`s in the database, ignoring any retried payloads that have already been logged.
- **BiDi & Zero-Width Sanitization**: Strip hidden Right-to-Left (RTL) marks (`\u200f`), Left-to-Right (LTR) marks (`\u200e`), zero-width spaces, and trailing punctuation when parsing Hebrew commands.
- **Rate-Limiting**: Reject user traffic that exceeds a burst limit (e.g., 10 messages per minute) at the entry point to protect processing limits.
Rational:
- WhatsApp retries payloads if the response takes longer than 5 seconds, causing redundant executions and duplicated tasks.
- Mobile WhatsApp inputs often inject hidden RTL control characters when typing mixed English and Hebrew commands, which breaks simple string matching.
