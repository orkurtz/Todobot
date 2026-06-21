# Fuzzy & Semantic Hebrew Task Matching

Retrieve and identify tasks from conversational inputs using a hybrid approach combining fuzzy text comparison and date-based urgency.

## Rules

- **Fuzzy Text Scorer**: Use `rapidfuzz.fuzz.partial_ratio` to compute similarity scores for Hebrew and English task text. This accommodates suffixes, prefixes, and common mobile typos.
- **Typo Tolerance Thresholds**:
  - **60 (Minimum Match)**: Below this, inputs are ignored.
  - **80 (Good Match)**: High-probability matches.
  - **90 (Excellent Match)**: Perfect or near-perfect matches.
- **Smart Date Tiebreaker**: If multiple tasks score within a 2-point similarity range, break the tie using the following priority order:
  1. **Overdue tasks** (sorted oldest to newest).
  2. **Tasks due today** (sorted earliest to latest).
  3. **Upcoming tasks** (sorted closest to furthest).
  4. **Tasks without a due date** (fallback).

## Code Example

```python
# 1. Fuzzy match candidates
matches = process.extract(
    search_term,
    descriptions,
    scorer=fuzz.partial_ratio,
    limit=10,
    score_cutoff=60
)

# 2. Select closest scoring group (within 2 points) and apply date priority
best_score = matches[0][1]
top_candidates = [tasks[idx] for desc, score, idx in matches if score >= best_score - 2]

if len(top_candidates) > 1:
    matched_task = select_by_due_date_urgency(top_candidates)
```

## Rationale
- Tasks with explicit dates represent higher user urgency. Prioritizing overdue and daily tasks for completion tiebreaks matches typical human task habits.
- Threshold limits are tuned for RTL Hebrew keyboards where key-misses and spacing variations are frequent.
