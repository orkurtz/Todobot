# Minimalist Code (Ponytail Rule)

Maintain a "YAGNI" (You Ain't Gonna Need It) mindset. The best code is the code you never wrote.

## The Ponytail Decision Ladder

Before writing any new code or creating new files, you MUST run through this ladder:
1. **Necessity Check:** Does this feature or code absolutely need to exist to fulfill the task?
2. **Platform Native:** Does the standard library or runtime platform already handle this?
3. **Reusability:** Can we reuse an existing utility, helper, or package in the codebase instead of writing new code?
4. **Minimization:** Can the task be implemented in a simple, minimal way with fewer lines/files?

## Anti-Patterns (NEVER Do This)
- Do NOT add placeholder code, empty files, or unused helper functions for future use.
- Do NOT over-engineer solutions or create complex abstractions (interfaces, classes, wrapper layers) when a simple function is sufficient.
- Do NOT run refactors unless explicitly instructed by the user or required for task success.
