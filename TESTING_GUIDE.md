# WhatsApp Todo Bot - Comprehensive Testing Guide

**Version:** 1.0  
**Last Updated:** November 2025  
**Coverage Target:** 95%+

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Task Management Testing](#2-core-task-management-testing)
3. [Recurring Tasks Testing](#3-recurring-tasks-testing)
4. [Google Calendar Integration Testing](#4-google-calendar-integration-testing)
5. [Voice Message Testing](#5-voice-message-testing)
6. [Natural Language Processing Testing](#6-natural-language-processing-testing)
7. [Fuzzy Matching Testing](#7-fuzzy-matching-testing)
8. [Reminder System Testing](#8-reminder-system-testing)
9. [User Commands Testing](#9-user-commands-testing)
10. [User Experience Flows](#10-user-experience-flows)
11. [Error Handling & Edge Cases](#11-error-handling--edge-cases)
12. [Performance & Scale Testing](#12-performance--scale-testing)
13. [Security Testing](#13-security-testing)
14. [Integration Testing](#14-integration-testing)
15. [Scheduler Testing](#15-scheduler-testing)
16. [Testing Methodology](#16-testing-methodology)
17. [Appendix](#17-appendix)

---

## 1. Introduction

### 1.1 Purpose

This document serves as the **definitive testing guide** for the WhatsApp Todo Bot. It provides comprehensive test scenarios covering all features, user flows, and edge cases to ensure:

- **Feature Completeness**: All advertised features work as expected
- **Reliability**: System handles errors gracefully
- **User Experience**: Natural and intuitive interactions
- **Data Integrity**: No data loss or corruption
- **Performance**: Acceptable response times under load

### 1.2 How to Use This Guide

**For Manual Testers:**
1. Follow test scenarios sequentially within each section
2. Mark results using the pass/fail criteria (✅ ⚠️ ❌ 🐛)
3. Document any deviations from expected behavior
4. Log bugs with reproduction steps

**For Automated Testing:**
1. Use scenarios as specification for test scripts
2. Implement test cases for each scenario
3. Run full suite after every deployment
4. Track coverage metrics

**For Regression Testing:**
1. Run full test suite after any code change
2. Focus on affected areas first
3. Verify no existing functionality broke
4. Sign off before production deployment

### 1.3 Test Environment Setup

#### Prerequisites

**WhatsApp Business API:**
- Active WhatsApp Business API account
- Verified business phone number
- Webhook configured and verified
- Valid API token

**Test User Accounts:**
- Minimum 3 test phone numbers
- Access to WhatsApp on test devices
- Different user states (new, existing, with data)

**Database:**
- Test database (separate from production)
- Backup mechanism for test data
- Ability to reset to clean state

**Google Calendar (for integration tests):**
- Test Google account
- Calendar API enabled
- OAuth credentials configured
- Test calendar created

**Environment Variables:**
- All required env vars configured
- Test/staging configuration
- Redis available (or memory fallback)

#### Test Data Preparation

**Sample Tasks:**
- 10-20 pre-created tasks per test user
- Mix of statuses (pending, completed)
- Various due dates (past, today, future)
- Some with no due dates
- Mix of Hebrew and English descriptions

**Sample Recurring Patterns:**
- Daily pattern
- Weekly pattern
- Specific days pattern
- Interval pattern
- Monthly pattern

### 1.4 Pass/Fail Criteria

- ✅ **Pass**: Expected behavior occurs exactly as documented
- ⚠️ **Partial Pass**: Core functionality works but minor issues exist (e.g., formatting)
- ❌ **Fail**: Expected behavior does not occur or incorrect behavior
- 🐛 **Bug**: Unexpected error, crash, or data corruption

### 1.5 Coverage Tracking

This guide targets **95%+ coverage** across:
- Feature coverage (all documented features)
- User flow coverage (complete user journeys)
- Edge case coverage (boundary conditions)
- Error scenario coverage (failure handling)

---

## 2. Core Task Management Testing

### 2.1 Task Creation

#### 2.1.1 Text Message Task Creation - Hebrew

**Test Case ID:** TC-CREATE-001

**Objective:** Verify task creation from Hebrew text messages

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Simple task | "לקנות חלב" | Task created: "לקנות חלב", no due date | |
| Task with tomorrow | "לקנות חלב מחר" | Task created with due date = tomorrow 09:00 | |
| Task with specific time | "לקנות חלב מחר ב-15:00" | Task created with due date = tomorrow 15:00 | |
| Task with day name | "לקנות חלב ביום ראשון" | Task created with due date = next Sunday 09:00 | |
| Task with day and time | "לקנות חלב ביום ראשון ב-10:30" | Task created with due date = next Sunday 10:30 | |
| Task with "today" | "לקנות חלב היום" | Task created with due date = today 09:00 | |
| Task with "in X hours" | "לקנות חלב בעוד 2 שעות" | Task created with due date = now + 2 hours | |
| Task with "in X minutes" | "תזכיר לי בעוד 5 דקות" | Task created with due date = now + 5 minutes | |
| Task with DD/MM format | "פגישה 31/10" | Task created with due date = Oct 31 09:00 | |
| Task with DD/MM/YYYY | "פגישה 31/10/2025 בשעה 14:00" | Task created with due date = Oct 31, 2025 14:00 | |
| Long description | 300-character Hebrew text | Task created, description truncated to 500 chars | |

**Verification Steps:**
1. Send message to bot
2. Verify confirmation message received
3. Send "משימות" to list tasks
4. Verify task appears with correct description
5. Verify due date is correct (if specified)
6. Verify timezone is Israel (Asia/Jerusalem)

#### 2.1.2 Text Message Task Creation - English

**Test Case ID:** TC-CREATE-002

**Objective:** Verify task creation from English text messages

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Simple task | "buy milk" | Task created: "buy milk", no due date | |
| Task with tomorrow | "buy milk tomorrow" | Task created with due date = tomorrow 09:00 | |
| Task with specific time | "buy milk tomorrow at 3pm" | Task created with due date = tomorrow 15:00 | |
| Task with day name | "buy milk on Monday" | Task created with due date = next Monday 09:00 | |
| Task with "in X hours" | "buy milk in 2 hours" | Task created with due date = now + 2 hours | |
| Task with formal date | "meeting on October 31st at 2:30 PM" | Task created with correct date/time | |

#### 2.1.3 Voice Message Task Creation

**Test Case ID:** TC-CREATE-003

**Objective:** Verify task creation from voice messages

**Test Scenarios:**

| Test | Voice Input (Hebrew) | Expected Result | Pass/Fail |
|------|----------------------|-----------------|-----------|
| Simple voice task | "תזכיר לי לקנות חלב" | Transcription shown, task created | |
| Voice with time | "תזכיר לי לקנות חלב מחר בשעה חמש" | Transcription + task with tomorrow 17:00 | |
| Voice with day | "תזכיר לי ביום ראשון לקחת ויטמינים" | Transcription + task on Sunday | |

| Test | Voice Input (English) | Expected Result | Pass/Fail |
|------|----------------------|-----------------|-----------|
| Simple voice task | "remind me to buy milk" | Transcription shown, task created | |
| Voice with time | "remind me tomorrow at 3pm to call mom" | Transcription + task with tomorrow 15:00 | |

**Verification Steps:**
1. Record and send voice message
2. Wait for "🎤 מעבד את ההודעה הקולית..." message
3. Verify transcription is shown
4. Verify task creation confirmation
5. Verify task details are correct

#### 2.1.4 Multiple Tasks from Single Message

**Test Case ID:** TC-CREATE-004

**Objective:** Verify multiple tasks can be created from one message

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Two tasks with "and" | "buy milk and call mom" | 2 tasks created separately | |
| Three tasks comma-separated | "buy milk, call mom, doctor appointment" | 3 tasks created | |
| Tasks with mixed dates | "buy milk tomorrow, call mom today" | 2 tasks with different due dates | |

#### 2.1.5 Edge Cases - Task Creation

**Test Case ID:** TC-CREATE-005

**Test Scenarios:**

| Test | Input | Expected Result | Pass/Fail |
|------|-------|-----------------|-----------|
| Empty message | "" (empty string) | Error message or AI response | |
| Only whitespace | "   " | Error message or AI response | |
| Very long description (1000 chars) | Hebrew/English 1000 chars | Task created, truncated to 500 | |
| Special characters | "Task with !@#$%^&*()" | Task created with special chars | |
| Emoji in description | "לקנות חלב 🥛" | Task created with emoji | |
| Mixed Hebrew/English | "buy חלב tomorrow" | Task created correctly | |
| Invalid date | "buy milk on 32/13" | Task created without due date OR error | |
| Ambiguous date | "buy milk" (no date) | Task created without due date | |

---

### 2.2 Task Completion

#### 2.2.1 Complete by Task Number (Position)

**Test Case ID:** TC-COMPLETE-001

**Objective:** Verify task completion by position in list

**Prerequisites:** User has 5 pending tasks

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Complete first task | "סיימתי משימה 1" | Task #1 marked as completed | |
| Complete middle task | "סיימתי משימה 3" | Task #3 marked as completed | |
| Complete last task | "סיימתי משימה 5" | Task #5 marked as completed | |
| English syntax | "done with task 2" | Task #2 marked as completed | |
| Alternative Hebrew | "גמרתי את 4" | Task #4 marked as completed | |
| Invalid number | "סיימתי משימה 100" | Error: task not found | |
| Number 0 | "סיימתי משימה 0" | Error: invalid task number | |
| Negative number | "סיימתי משימה -1" | Error: invalid task number | |

**Verification Steps:**
1. Send "משימות" to get task list
2. Note task positions and IDs
3. Send completion message
4. Verify confirmation message
5. Send "משימות" again
6. Verify task removed from pending list
7. Send "הושלמו" to verify in completed list

#### 2.2.2 Complete by Task ID

**Test Case ID:** TC-COMPLETE-002

**Objective:** Verify task completion by database ID

**Prerequisites:** Know task IDs from database or messages

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Complete by ID | "סיימתי משימה #123" | Task ID 123 completed | |
| Complete by ID (no #) | "סיימתי משימה 123" | Task ID 123 completed (if exists) OR position 123 | |
| Non-existent ID | "סיימתי משימה #99999" | Error: task not found | |

#### 2.2.3 Complete by Description (Exact Match)

**Test Case ID:** TC-COMPLETE-003

**Objective:** Verify task completion by exact description

**Prerequisites:** Task exists with description "לקנות חלב"

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Exact Hebrew match | "סיימתי לקנות חלב" | Task "לקנות חלב" completed | |
| Exact English match | "done with buy milk" | Task "buy milk" completed | |
| Partial match | "סיימתי לקנות" | Best matching task completed | |

#### 2.2.4 Complete by Description (Fuzzy Match with Typos)

**Test Case ID:** TC-COMPLETE-004

**Objective:** Verify fuzzy matching handles typos

**Prerequisites:** Task exists with description "לקנות חלב"

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew typo (extra letter) | "סיימתי לקנות חלבב" | Task "לקנות חלב" completed (95% match) | |
| Hebrew typo (wrong letter) | "סיימתי לקנות הלב" | Task "לקנות חלב" completed (~85% match) | |
| English typo | "done with bu milk" | Task "buy milk" completed | |
| Word order variation | "סיימתי חלב לקנות" | Task "לקנות חלב" completed | |
| Multiple typos | "סיימתי לקנות הלבב" | Task matched if confidence >65% | |

**Verification Steps:**
1. Create task "לקנות חלב"
2. Send completion message with typo
3. Verify correct task completed
4. If confidence <85%, verify match confidence shown (e.g., "התאמה: 75%")

#### 2.2.5 Complete via Emoji Reaction

**Test Case ID:** TC-COMPLETE-005

**Objective:** Verify task completion via 👍 reaction

**Prerequisites:** User has pending tasks

**Test Scenarios:**

| Step | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| 1 | Send "פירוט" or "משימות נפרד" | Each task sent as separate message | |
| 2 | React with 👍 to first task message | Confirmation: "✅ השלמתי: [task description]" | |
| 3 | Send "משימות" | Task removed from pending list | |
| 4 | React with 👍 to recurring task instance | Confirmation includes "🔄 משימה חוזרת..." | |

**Special Cases:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| React with wrong emoji | React with ❤️ | No action (only 👍 supported) | |
| React to non-task message | React to bot's help message | No action | |
| React to already completed | React to completed task reference | Error or no action | |

#### 2.2.6 Complete Recurring Task Instance

**Test Case ID:** TC-COMPLETE-006

**Objective:** Verify completing recurring task instance

**Prerequisites:** Active recurring pattern with today's instance

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Complete today's instance | "סיימתי משימה 1" (instance) | Instance completed, confirmation with 🔄 indicator | |
| Verify next instance | Wait or check next day | Next instance generated at midnight | |
| Complete via description | "סיימתי [recurring task desc]" | Today's instance completed (not pattern) | |

#### 2.2.7 Completion with Calendar Sync

**Test Case ID:** TC-COMPLETE-007

**Objective:** Verify calendar event updated on completion

**Prerequisites:** Calendar connected, task with due date

**Test Scenarios:**

| Test | Setup | Action | Expected Result | Pass/Fail |
|------|-------|--------|-----------------|-----------|
| Complete task with event | Task synced to calendar | Complete task | Calendar event marked with ✅ and gray color | |
| Complete task (sync failed) | Task created but sync error | Complete task | Task completed, calendar unchanged | |

#### 2.2.8 Edge Cases - Task Completion

**Test Case ID:** TC-COMPLETE-008

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Complete already completed | "סיימתי משימה 1" (already done) | Error: "המשימה כבר הושלמה" | |
| Complete non-existent | "סיימתי משימה 999" | Error: task not found | |
| Complete recurring pattern | "סיימתי משימה [pattern ID]" | Error: cannot complete pattern directly | |
| Multiple matches (ambiguous) | "סיימתי רופא" (multiple tasks) | Best match by due date OR error requesting specificity | |
| Complete after delete | Delete task, then try complete | Error: task not found | |

---

### 2.3 Task Deletion

#### 2.3.1 Delete by Task Number

**Test Case ID:** TC-DELETE-001

**Objective:** Verify task deletion by position

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Delete first task | "מחק משימה 1" | Task #1 deleted | |
| Delete middle task | "מחק משימה 3" | Task #3 deleted | |
| Delete last task | "מחק משימה 5" | Task #5 deleted | |
| English syntax | "delete task 2" | Task #2 deleted | |

#### 2.3.2 Delete by Task ID

**Test Case ID:** TC-DELETE-002

**Objective:** Verify task deletion by database ID

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Delete by ID | "מחק משימה #123" | Task ID 123 deleted | |
| Delete by ID (no #) | "מחק משימה 123" | Task ID 123 deleted OR position 123 | |

#### 2.3.3 Delete by Description (Fuzzy Match)

**Test Case ID:** TC-DELETE-003

**Objective:** Verify task deletion by description with typo tolerance

**Prerequisites:** Task exists "פגישה עם יוחנן"

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Exact match | "מחק פגישה עם יוחנן" | Task deleted | |
| With typo | "מחק פגישה עם יוהנן" | Task deleted (fuzzy match) | |
| Partial match | "מחק פגישה" | Best matching task deleted | |
| English | "delete meeting with john" | Task deleted | |

#### 2.3.4 Delete Recurring Pattern vs Instance

**Test Case ID:** TC-DELETE-004

**Objective:** Verify correct handling of recurring patterns

**Test Scenarios:**

| Test | Target | Action | Expected Result | Pass/Fail |
|------|--------|--------|-----------------|-----------|
| Try delete pattern | Pattern (is_recurring=true) | "מחק משימה [pattern ID]" | Error: use "עצור סדרה" instead | |
| Delete instance | Instance (parent_recurring_id set) | "מחק משימה [instance ID]" | Instance deleted, pattern unchanged | |

#### 2.3.5 Deletion with Calendar Sync

**Test Case ID:** TC-DELETE-005

**Objective:** Verify calendar event deleted

**Prerequisites:** Calendar connected, task with synced event

**Test Scenarios:**

| Test | Setup | Action | Expected Result | Pass/Fail |
|------|-------|--------|-----------------|-----------|
| Delete task with event | Task synced to calendar | Delete task | Task deleted, calendar event removed | |
| Delete task (sync error) | Orphaned event in calendar | Delete task | Task deleted (best effort on event) | |

#### 2.3.6 Edge Cases - Task Deletion

**Test Case ID:** TC-DELETE-006

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Delete non-existent | "מחק משימה 999" | Error: task not found | |
| Delete completed task | "מחק משימה [completed ID]" | Error: task not found (or success if allowed) | |
| Delete after completion | Complete then try delete | Error: already completed | |

---

### 2.4 Task Update & Reschedule

#### 2.4.1 Update Task Description

**Test Case ID:** TC-UPDATE-001

**Objective:** Verify task description can be changed

**Prerequisites:** Task exists with ID/position known

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Update by position | "שנה משימה 2 להתקשר לרופא" | Task #2 description updated | |
| Update by ID | "עדכן משימה #123 ל קנה לחם" | Task #123 description updated | |
| Update by description | "שנה 'לקנות חלב' ל 'לקנות חלב ולחם'" | Matched task updated | |
| English syntax | "change task 3 to call dentist" | Task #3 description updated | |
| Alternative Hebrew | "עדכן את משימה 1 ל..." | Task #1 updated | |

**Verification Steps:**
1. Note original task description
2. Send update message
3. Verify confirmation: "✅ משימה #[ID] עודכנה: • תיאור: '...' → '...'"
4. List tasks to verify change
5. If calendar synced, verify event title updated

#### 2.4.2 Reschedule Task (Change Due Date)

**Test Case ID:** TC-UPDATE-002

**Objective:** Verify task due date can be changed

**Prerequisites:** Task with due date exists

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Reschedule to tomorrow | "דחה משימה 1 למחר" | Due date = tomorrow (same time) | |
| Reschedule with new time | "דחה משימה 2 למחר ב-14:00" | Due date = tomorrow 14:00 | |
| Reschedule to day name | "דחה משימה 3 ליום רביעי" | Due date = next Wednesday | |
| Reschedule "in X hours" | "העבר משימה 1 בעוד 2 שעות" | Due date = now + 2 hours | |
| Flexible word order | "דחה ל-31/10 את משימה 12" | Due date = Oct 31 | |
| Alternative order | "דחה את משימה 5 ליום שני" | Due date = next Monday | |
| English | "move task 2 to tomorrow" | Due date = tomorrow | |
| English | "postpone task 3 in 2 hours" | Due date = now + 2 hours | |

**Verification Steps:**
1. Note original due date
2. Send reschedule message
3. Verify confirmation shows old → new date
4. List tasks to verify change
5. Verify reminder_sent reset to false
6. If calendar synced, verify event time updated

#### 2.4.3 Update Recurring Pattern

**Test Case ID:** TC-UPDATE-003

**Objective:** Verify recurring pattern can be updated

**Prerequisites:** Active recurring pattern exists

**Test Scenarios:**

| Test | Target | Action | Expected Result | Pass/Fail |
|------|--------|--------|-----------------|-----------|
| Update pattern description | Pattern | "עדכן משימה [ID] ל..." | Description updated, future instances updated | |
| Update pattern time | Pattern | "דחה משימה [ID] ל-10:00" | Time updated, future instances adjusted | |
| Update pattern days | Pattern with days_of_week | Change via message | Pattern updated, future instances follow new schedule | |

#### 2.4.4 Mixed Updates (Description + Time)

**Test Case ID:** TC-UPDATE-004

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Update both | "עדכן משימה 2 ל'פגישה חשובה' מחר ב-15:00" | Both description and due date updated | |

#### 2.4.5 Various Date Format Handling

**Test Case ID:** TC-UPDATE-005

**Objective:** Verify all date formats work in reschedule

**Test Scenarios:**

| Test | Date Format | Example | Expected Result | Pass/Fail |
|------|-------------|---------|-----------------|-----------|
| DD/MM | "31/10" | "דחה משימה 1 ל-31/10" | Due date = Oct 31, 09:00 | |
| DD/MM/YYYY | "31/10/2025" | "דחה משימה 1 ל-31/10/2025" | Due date = Oct 31, 2025, 09:00 | |
| DD/MM HH:MM | "31/10 בשעה 14:30" | "דחה משימה 1 ל-31/10 בשעה 14:30" | Due date = Oct 31, 14:30 | |
| Relative | "מחרתיים" | "דחה משימה 1 למחרתיים" | Due date = day after tomorrow | |
| Interval | "בעוד שבוע" | "דחה משימה 1 לבעוד שבוע" | Due date = +7 days | |

#### 2.4.6 Edge Cases - Update/Reschedule

**Test Case ID:** TC-UPDATE-006

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Update non-existent | "עדכן משימה 999 ל..." | Error: task not found | |
| Update completed task | "עדכן משימה [completed] ל..." | Error: cannot update completed | |
| Reschedule task with no date | "דחה משימה 1 למחר" (task has no date) | Due date added | |
| Invalid date in reschedule | "דחה משימה 1 ל-99/99" | Error OR no date change | |
| Reschedule pattern instance | Reschedule instance of recurring | Instance rescheduled, pattern unchanged | |

---

### 2.5 Task Queries

#### 2.5.1 List All Tasks

**Test Case ID:** TC-QUERY-001

**Objective:** Verify task listing commands

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew command | "משימות" | List of pending tasks with numbers, IDs, due dates | |
| Question mark | "?" | Same as "משימות" | |
| Alternative Hebrew | "המשימות שלי" | Same result | |
| English | "tasks" | Same result | |
| Natural language | "what are my tasks" | Task list OR AI response + task list | |
| Natural language Hebrew | "מה המשימות שלי" | Task list OR AI response + task list | |

**Expected Format:**
```
📋 המשימות הממתינות שלך (3):

1. לקנות חלב [#123] 🔥 (יעד היום 15:00)
2. 🔄 לקחת ויטמינים [#124] (כל יום) 📅 (יעד היום 09:00)
3. פגישה עם רופא [#125] 📅 (יעד 31/10 14:00)

💡 לסיום משימה עם תגובה: כתוב 'פירוט', ואז הגב עם 👍 על כל הודעת משימה
```

**Verification:**
- Each task numbered sequentially
- Task ID shown in [#123] format
- Recurring instances show 🔄 indicator
- Due dates formatted correctly
- Overdue tasks show ⚠️
- Today's tasks show 🔥
- Footer with help text included

#### 2.5.2 List Tasks Separately (For Reactions)

**Test Case ID:** TC-QUERY-002

**Objective:** Verify separate message listing for emoji reactions

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "פירוט" | Each task as separate WhatsApp message | |
| Alternative | "משימות נפרד" | Same result | |
| Alternative | "פרט משימות" | Same result | |
| English | "tasks separate" | Same result | |

**Expected Behavior:**
1. Header message: "📋 המשימות שלך (3):"
2. Message 1: "1. לקנות חלב [#123]\n📅 31/10 15:00"
3. Message 2: "2. פגישה [#124]\n📅 01/11 10:00"
4. Message 3: "3. ..."
5. Footer: "💡 לסיום משימה עם תגובה: הגב עם 👍..."

**Verification:**
- Each task in separate message
- Message IDs stored for reaction mapping
- Can react with 👍 to complete

#### 2.5.3 Query Tasks by Date

**Test Case ID:** TC-QUERY-003

**Objective:** Verify date-filtered task queries

**Test Scenarios:**

| Test | Input Query | Expected Result | Pass/Fail |
|------|-------------|-----------------|-----------|
| Today's tasks | "מה המשימות שלי להיום" | Tasks due today | |
| Tomorrow's tasks | "מה המשימות למחר" | Tasks due tomorrow | |
| Specific date | "מה יש לי ב-31/10" | Tasks due Oct 31 | |
| This week | "מה המשימות שלי השבוע" | Tasks due this week | |
| English - today | "what tasks for today" | Tasks due today | |
| English - tomorrow | "tasks tomorrow" | Tasks due tomorrow | |

**Expected Format:**
```
📋 המשימות שלך להיום (2):

1. לקנות חלב [#123] (יעד היום 15:00)
2. פגישה [#124] (יעד היום 10:00)
```

#### 2.5.4 Count Queries

**Test Case ID:** TC-QUERY-004

**Objective:** Verify task count queries

**Test Scenarios:**

| Test | Input Query | Expected Result | Pass/Fail |
|------|-------------|-----------------|-----------|
| How many tasks | "כמה משימות יש לי" | "📋 יש לך [N] משימות פתוחות" | |
| Alternative Hebrew | "כמה משימות יש לי פתוחות" | Same response | |
| English | "how many tasks do I have" | "📋 You have [N] pending tasks" | |
| When no tasks | "כמה משימות" (0 tasks) | "📋 אין לך משימות פתוחות כרגע!" | |
| When 1 task | "כמה משימות" (1 task) | "📋 יש לך משימה פתוחה אחת" | |

#### 2.5.5 "When is..." Queries

**Test Case ID:** TC-QUERY-005

**Objective:** Verify task search and due date queries

**Prerequisites:** Task exists "פגישה עם יוחנן" due Oct 31, 14:00

**Test Scenarios:**

| Test | Input Query | Expected Result | Pass/Fail |
|------|-------------|-----------------|-----------|
| Exact description | "מתי הפגישה עם יוחנן" | "📅 פגישה עם יוחנן\nתאריך יעד: 31/10/2025 בשעה 14:00" | |
| With typo | "מתי הפגישה עם יוהנן" | Same result (fuzzy match) | |
| Partial match | "מתי הפגישה" | Matching task(s) shown with due date | |
| English | "when is the meeting with john" | Due date shown | |
| No due date | "מתי [task with no date]" | "📋 [task]\n(אין תאריך יעד מוגדר)" | |
| Multiple matches | "מתי הפגישה" (3 matches) | All matching tasks listed with dates | |

#### 2.5.6 Statistics Queries

**Test Case ID:** TC-QUERY-006

**Objective:** Verify statistics command

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "סטטיסטיקה" | Statistics display | |
| English | "stats" | Same result | |
| Natural language | "מה המצב שלי" | Statistics OR AI response | |

**Expected Format:**
```
📊 **הסטטיסטיקות שלך:**

📝 סה"כ משימות: 50
⏳ ממתינות: 15
✅ הושלמו: 35
📅 יעד להיום: 3
⚠️ באיחור: 2
🎯 אחוז השלמה: 70.0%

המשך כך! עבודה מצוינת! 🚀
```

#### 2.5.7 Completed Tasks List

**Test Case ID:** TC-QUERY-007

**Objective:** Verify completed tasks display

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "הושלמו" | Last 10 completed tasks | |
| English | "completed" | Same result | |
| Alternative | "done" | Same result | |
| When none completed | "הושלמו" (no completed) | "✅ עדיין לא השלמת משימות..." | |

**Expected Format:**
```
✅ **המשימות האחרונות שהושלמו (5):**

1. לקנות חלב [#123]
2. פגישה עם רופא [#124]
3. ...

🎉 עבודה מצוינת! השלמת 5 משימות!
```

#### 2.5.8 Edge Cases - Queries

**Test Case ID:** TC-QUERY-008

**Test Scenarios:**

| Test | Scenario | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| No tasks at all | "משימות" when 0 tasks | "📋 אין לך משימות ממתינות!..." | |
| Many tasks (100+) | "משימות" with 100+ tasks | First 20 shown OR paginated | |
| Query non-existent date | "מה יש לי ב-99/99" | Error OR "אין משימות" | |
| Ambiguous query | "מתי רופא" (multiple matches) | All matches shown OR best match | |

---

## 3. Recurring Tasks Testing

### 3.1 Recurring Task Creation

#### 3.1.1 Daily Recurring Tasks

**Test Case ID:** TC-RECUR-001

**Objective:** Verify daily recurring task creation

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Daily (Hebrew) | "תזכיר לי כל יום ב-9 לקחת ויטמינים" | Pattern created, description: "לקחת ויטמינים", daily pattern, due time 09:00 | |
| Daily (English) | "every day at 9am take vitamins" | Pattern created, daily pattern, due time 09:00 | |
| Daily with interval | "כל יום בשעה 8 בבוקר" | Pattern created, daily at 08:00 | |
| Daily without time | "תזכיר לי כל יום לקחת ויטמינים" | Pattern created, default time (09:00) | |

**Verification Steps:**
1. Send creation message
2. Verify confirmation: "✅ נוצרה משימה: [desc] 🔄 (כל יום ב-XX:XX)"
3. Send "משימות חוזרות" to list patterns
4. Verify pattern appears with correct details
5. Check if first instance generated (if due today/past)
6. Wait until midnight and verify instance generated

**Expected Pattern Properties:**
- `is_recurring = True`
- `recurrence_pattern = "daily"`
- `recurrence_interval = 1`
- `recurrence_days_of_week` contains all days
- `status = "pending"`

#### 3.1.2 Weekly Recurring Tasks

**Test Case ID:** TC-RECUR-002

**Objective:** Verify weekly recurring task creation

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Weekly (Hebrew) | "כל שבוע פגישה עם המנהל" | Pattern created, weekly on same day | |
| Weekly (English) | "every week meeting with manager" | Pattern created, weekly | |
| Every Monday | "every Monday team meeting at 10am" | Pattern created, weekly on Monday 10:00 | |
| Hebrew with day | "כל יום שני בשעה 10 ישיבת צוות" | Pattern created, weekly on Monday 10:00 | |

**Expected Pattern Properties:**
- `is_recurring = True`
- `recurrence_pattern = "weekly"` OR `"specific_days"`
- `recurrence_interval = 1`
- `recurrence_days_of_week` contains relevant day(s)

#### 3.1.3 Specific Days of Week

**Test Case ID:** TC-RECUR-003

**Objective:** Verify recurring tasks on specific days

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Monday and Thursday | "every Monday and Thursday call mom" | Pattern with Monday, Thursday | |
| Hebrew multiple days | "כל יום שני ורביעי ב-10 להתקשר" | Pattern with Monday, Wednesday at 10:00 | |
| Three days | "every Monday, Wednesday, Friday workout" | Pattern with 3 specific days | |

**Expected Pattern Properties:**
- `recurrence_pattern = "specific_days"`
- `recurrence_days_of_week = ["monday", "thursday"]` (example)

#### 3.1.4 Interval-Based Recurring (Every X Days)

**Test Case ID:** TC-RECUR-004

**Objective:** Verify interval-based recurring tasks

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Every 2 days | "כל יומיים להשקות צמחים" | Pattern with interval=2 | |
| Every 3 days | "every 3 days water plants" | Pattern with interval=3 | |
| Every week (7 days) | "כל 7 ימים לנקות" | Pattern with interval=7 | |

**Expected Pattern Properties:**
- `recurrence_pattern = "interval"`
- `recurrence_interval = X` (specified number)

#### 3.1.5 Monthly Recurring Tasks

**Test Case ID:** TC-RECUR-005

**Objective:** Verify monthly recurring tasks

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Monthly (Hebrew) | "כל חודש ב-1 לשלם שכר דירה" | Pattern with day_of_month=1 | |
| Monthly (English) | "every month on the 15th pay bills" | Pattern with day_of_month=15 | |
| Last day of month | "כל חודש ב-31" | Pattern with day_of_month=31 (handles Feb) | |

**Expected Pattern Properties:**
- `recurrence_pattern = "monthly"`
- `recurrence_day_of_month = X` (1-31)

#### 3.1.6 Recurring Tasks with End Dates

**Test Case ID:** TC-RECUR-006

**Objective:** Verify recurring tasks can have end dates

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| With end date | "כל יום ב-9 לקחת תרופה עד 31/12" | Pattern with end_date=Dec 31 | |
| English with end | "every day at 9am until December 31st" | Pattern with end_date | |

**Verification:**
- Pattern stops generating after end date
- Existing instances remain

#### 3.1.7 Edge Cases - Recurring Creation

**Test Case ID:** TC-RECUR-007

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| No time specified | "כל יום לקחת ויטמינים" | Pattern with default time (09:00) | |
| Invalid day name | "every Blursday" | Error OR pattern not created | |
| Conflicting patterns | "every day and every 2 days" | One pattern OR error | |
| Very long description | 500+ char recurring task | Pattern created, description truncated | |

---

### 3.2 Recurring Instance Management

#### 3.2.1 Automatic Instance Generation (Midnight)

**Test Case ID:** TC-RECUR-008

**Objective:** Verify instances generated automatically at midnight

**Prerequisites:** Active recurring patterns exist

**Test Scenarios:**

| Pattern Type | Test | Expected Result | Pass/Fail |
|--------------|------|-----------------|-----------|
| Daily | Pattern due today | Instance generated at midnight (00:00 Israel time) | |
| Weekly | Pattern due today (correct day) | Instance generated at midnight | |
| Specific days | Today matches pattern days | Instance generated at midnight | |
| Interval | Enough days passed since last | Instance generated at midnight | |
| Monthly | Today matches day_of_month | Instance generated at midnight | |
| Daily | Pattern due tomorrow | No instance generated today | |

**Verification Steps:**
1. Create recurring pattern before midnight
2. Verify pattern exists with "משימות חוזרות"
3. Wait until after midnight (00:01)
4. Send "משימות" to list tasks
5. Verify instance appears with:
   - 🔄 indicator
   - Pattern description
   - Today's date with pattern's time
   - `parent_recurring_id` set

**Background Job:**
- Runs at 00:00 Israel time
- Processes all active patterns (`is_recurring=True`, `status='pending'`)
- Checks if today matches pattern criteria
- Creates instance with today's date + pattern time

#### 3.2.2 Complete Recurring Instance

**Test Case ID:** TC-RECUR-009

**Objective:** Verify completing instance doesn't affect pattern

**Prerequisites:** Recurring pattern with today's instance

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Complete by number | "סיימתי משימה 1" (instance) | Instance completed, shows 🔄 message | |
| Complete by description | "סיימתי לקחת ויטמינים" | Instance completed (not pattern) | |
| Via emoji reaction | 👍 on instance message | Instance completed | |

**Expected Confirmation:**
```
✅ השלמתי: לקחת ויטמינים
🔄 משימה חוזרת (כל יום ב-09:00)
💡 המשימה הבאה תופיע בחצות
```

**Verification:**
1. Complete instance
2. Verify confirmation includes 🔄 indicator
3. Send "משימות" - instance removed
4. Send "משימות חוזרות" - pattern still active
5. Wait until next occurrence - new instance appears

#### 3.2.3 Delete Recurring Instance

**Test Case ID:** TC-RECUR-010

**Objective:** Verify deleting instance doesn't affect pattern

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Delete instance by number | "מחק משימה 1" (instance) | Instance deleted, pattern unchanged | |
| Delete instance by description | "מחק לקחת ויטמינים" | Instance deleted | |

**Verification:**
- Instance removed from task list
- Pattern remains in "משימות חוזרות"
- Next instance still generates at midnight

#### 3.2.4 Instance Appears in Task List with Indicator

**Test Case ID:** TC-RECUR-011

**Objective:** Verify recurring instances display correctly

**Expected Format:**
```
📋 המשימות הממתינות שלך (2):

1. 🔄 לקחת ויטמינים [#124] (כל יום) 📅 (יעד היום 09:00)
2. לקנות חלב [#125] 📅 (יעד מחר 15:00)
```

**Verification:**
- 🔄 emoji present
- Pattern description shown (e.g., "כל יום", "כל יום שני ורביעי")
- Due date shows today's date with pattern time
- Task ID is instance ID (not pattern ID)

#### 3.2.5 Next Instance Generation After Completion

**Test Case ID:** TC-RECUR-012

**Objective:** Verify next instance generates on schedule

**Test Scenarios:**

| Pattern Type | Test | Expected Result | Pass/Fail |
|--------------|------|-----------------|-----------|
| Daily | Complete today's instance | Tomorrow's instance at midnight | |
| Weekly Monday | Complete Monday's instance | Next Monday's instance at midnight Monday | |
| Every 3 days | Complete instance | Next instance in 3 days at midnight | |
| Specific days (Mon/Wed) | Complete Monday | Wednesday's instance at midnight Wednesday | |

---

### 3.3 Recurring Pattern Management

#### 3.3.1 View All Recurring Patterns

**Test Case ID:** TC-RECUR-013

**Objective:** Verify pattern listing command

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "משימות חוזרות" | List of active patterns | |
| Alternative | "משימות קבועות" | Same result | |
| Alternative | "סדרות" | Same result | |
| English | "recurring tasks" | Same result | |

**Expected Format:**
```
🔄 **המשימות החוזרות שלך (3):**

(הזמן בתבנית = המופע הבא)

1. לקחת ויטמינים - כל יום [#120]
   שעה: 09:00
   נוצרו 15 מופעים

2. פגישת צוות - כל יום שני [#121]
   שעה: 10:00
   נוצרו 8 מופעים

3. שכר דירה - כל חודש ב-1 [#122]
   שעה: 09:00
   נוצרו 3 מופעים

💡 **לניהול:**
• 'עצור סדרה [מספר]' - עצור ומחק עתידיות
• 'השלם סדרה [מספר]' - סיים ושמור קיימות
```

**Verification:**
- Only patterns shown (not instances)
- Pattern descriptions clear
- Pattern ID shown
- Instance count shown
- Management instructions included

#### 3.3.2 Stop Recurring Series

**Test Case ID:** TC-RECUR-014

**Objective:** Verify stopping/canceling recurring series

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Stop series | "עצור סדרה 5" | Pattern status='cancelled', future instances deleted | |
| Alternative Hebrew | "עצור את סדרה 3" | Same result | |
| English | "stop series 2" | Same result | |
| With "delete" keyword | "מחק סדרה 5" | Pattern cancelled + instances deleted | |
| Without delete | "עצור סדרה 5" (no "מחק") | Pattern cancelled, existing instances kept | |

**Expected Confirmation:**
```
✅ הסדרה החוזרת נעצרה ו-X משימות עתידיות נמחקו
```
OR
```
✅ הסדרה החוזרת נעצרה (משימות קיימות נשמרו)
```

**Verification:**
1. Stop series
2. Pattern no longer in "משימות חוזרות"
3. No new instances generated
4. Existing completed instances remain (history)
5. Pending instances deleted (if "מחק" used)

#### 3.3.3 Complete Recurring Series

**Test Case ID:** TC-RECUR-015

**Objective:** Verify completing entire series

**Test Scenarios:**

| Test | Input Message | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Complete series | "השלם סדרה 3" | Pattern status='completed', instances remain | |
| Alternative | "סיים סדרה 2" | Same result | |
| English | "complete series 4" | Same result | |

**Expected Confirmation:**
```
✅ הסדרה החוזרת הושלמה (כל המשימות הקיימות נשמרו)
```

**Verification:**
- Pattern marked completed
- Pattern removed from "משימות חוזרות"
- No new instances generated
- All existing instances (pending/completed) remain

#### 3.3.4 Update Recurring Pattern

**Test Case ID:** TC-RECUR-016

**Objective:** Verify pattern updates propagate to future instances

**Prerequisites:** Active pattern with multiple future instances

**Test Scenarios:**

| Test | Update Type | Action | Expected Result | Pass/Fail |
|------|-------------|--------|-----------------|-----------|
| Update description | Change pattern text | "עדכן משימה [pattern ID] ל..." | Pattern + future instances updated | |
| Update time | Change due time | "דחה משימה [pattern ID] ל-10:00" | Pattern time + all instance times updated | |
| Update recurrence | Change days/interval | Update via message | Pattern updated, instances follow new schedule | |

**Verification:**
1. Update pattern
2. Verify pattern shows new values in "משימות חוזרות"
3. List "משימות" and verify future instance(s) updated
4. Verify calendar events updated (if synced)

#### 3.3.5 Edge Cases - Pattern Management

**Test Case ID:** TC-RECUR-017

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Stop non-existent series | "עצור סדרה 999" | Error: series not found | |
| Stop already stopped | "עצור סדרה [stopped ID]" | Error: already stopped | |
| Complete by instance ID | "השלם סדרה [instance ID]" | Error: not a pattern OR instance completed | |
| Stop pattern with no instances | Stop newly created pattern | Pattern stopped, no instances to delete | |
| Update cancelled pattern | "עדכן משימה [cancelled ID]" | Error: pattern not active | |

---

## 4. Google Calendar Integration Testing

### 4.1 Connection Flow

#### 4.1.1 Initial Connection (OAuth Flow)

**Test Case ID:** TC-CAL-001

**Objective:** Verify calendar connection process

**Test Scenarios:**

| Step | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| 1 | Send "חבר יומן" | OAuth URL provided in message | |
| 2 | Click URL | Redirect to Google authorization page | |
| 3 | Authorize (accept) | Redirect to success page | |
| 4 | View success page | "✅ היומן חובר בהצלחה!" message | |
| 5 | Return to WhatsApp | Can close browser, bot ready | |
| 6 | Send "סטטוס יומן" | Shows "✅ היומן שלך מחובר!" | |

**Alternative Flow - English:**

| Step | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| 1 | Send "connect calendar" | OAuth URL provided | |
| 2-6 | Same as above | Same results | |

**Verification:**
- User record has `google_calendar_enabled = True`
- Tokens stored encrypted in database
- `google_refresh_token` present for future refreshes

#### 4.1.2 Authorization Failure

**Test Case ID:** TC-CAL-002

**Objective:** Verify handling of authorization rejection

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| User denies permission | Click URL, deny | Error page shown, calendar not connected | |
| Invalid OAuth state | Manipulate URL state parameter | Error: invalid state | |
| Expired authorization | Wait 10+ min before accepting | Error OR re-initiate flow | |

#### 4.1.3 Token Refresh

**Test Case ID:** TC-CAL-003

**Objective:** Verify automatic token refresh

**Test Scenarios:**

| Test | Scenario | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| Token near expiry | Token expires in <5 min | Auto-refreshed on next calendar operation | |
| Token expired | Token already expired | Auto-refreshed when needed | |
| Refresh token invalid | Revoked from Google | Calendar auto-disconnected, user notified | |

**Notification Message (on failure):**
```
⚠️ החיבור ליומן Google נפסק

החיבור נפסק מסיבה טכנית. כדי לחדש את החיבור:
כתוב 'חבר יומן' כדי להתחבר מחדש.
```

#### 4.1.4 Disconnection

**Test Case ID:** TC-CAL-004

**Objective:** Verify calendar disconnection

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "נתק יומן" | Calendar disconnected, confirmation message | |
| English | "disconnect calendar" | Same result | |

**Expected Confirmation:**
```
✅ היומן נותק בהצלחה
```

**Verification:**
- `google_calendar_enabled = False`
- Tokens removed from database
- Existing tasks retain `calendar_event_id` (for history)
- New tasks don't sync to calendar

#### 4.1.5 Reconnection After Expiry

**Test Case ID:** TC-CAL-005

**Objective:** Verify reconnection and sync recovery

**Prerequisites:** Calendar previously connected, then token expired

**Test Scenarios:**

| Step | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| 1 | Token expires/revokes | Auto-disconnect, user notified | |
| 2 | Send "חבר יומן" | New OAuth flow initiated | |
| 3 | Complete authorization | Connection successful | |
| 4 | Automatic | Bot syncs tasks created during downtime | |
| 5 | Automatic | Bot ensures completed tasks marked on calendar | |

**Verification:**
- Tasks created while offline now have `calendar_event_id`
- Completed tasks marked with ✅ on calendar
- No duplicate events created

#### 4.1.6 Status Check

**Test Case ID:** TC-CAL-006

**Objective:** Verify calendar status command

**Test Scenarios:**

| Test | State | Input | Expected Result | Pass/Fail |
|------|-------|-------|-----------------|-----------|
| Connected | Calendar enabled | "סטטוס יומן" | "✅ היומן שלך מחובר!\n📅 Calendar ID: primary\n..." | |
| Not connected | Calendar disabled | "סטטוס יומן" | "❌ היומן שלך לא מחובר.\nכתוב 'חבר יומן'..." | |
| English | Calendar enabled | "calendar status" | Status shown | |

---

### 4.2 Bot → Calendar Sync (Phase 1)

#### 4.2.1 Task Creation Syncs to Calendar

**Test Case ID:** TC-CAL-007

**Objective:** Verify task creation creates calendar event

**Prerequisites:** Calendar connected

**Test Scenarios:**

| Test | Task Input | Expected Result | Pass/Fail |
|------|------------|-----------------|-----------|
| Task with due date | "לקנות חלב מחר ב-15:00" | Task created + calendar event created | |
| Task without due date | "לקנות חלב" | Task created, NO calendar event (no date) | |
| Hebrew task with date | "פגישה 31/10 בשעה 14:00" | Event on Oct 31, 14:00-15:00 | |
| English task with date | "meeting tomorrow at 3pm" | Event tomorrow, 15:00-16:00 | |

**Verification:**
1. Create task with due date
2. Verify confirmation message
3. Check task has `calendar_event_id` populated
4. Open Google Calendar
5. Verify event exists:
   - Title = task description
   - Start time = task due_date
   - End time = start + 1 hour (default duration)
   - Timezone = Asia/Jerusalem
   - Description contains "Task ID: [ID]"

**Expected Event Properties:**
```
Summary: לקנות חלב
Start: 2025-10-31T15:00:00+03:00
End: 2025-10-31T16:00:00+03:00
TimeZone: Asia/Jerusalem
Description: Created by TodoBot\nTask ID: 123
```

#### 4.2.2 Task Update Syncs to Calendar

**Test Case ID:** TC-CAL-008

**Objective:** Verify task updates reflect in calendar

**Prerequisites:** Calendar connected, task with synced event

**Test Scenarios:**

| Test | Update Action | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Update description | "שנה משימה 2 לקנות לחם" | Event title updated to "לקנות לחם" | |
| Update time | "דחה משימה 2 למחר" | Event moved to tomorrow (same time) | |
| Update both | "עדכן משימה 2 ל'פגישה' מחר ב-10:00" | Event title + time updated | |

**Verification:**
1. Update task
2. Verify confirmation
3. Refresh Google Calendar
4. Verify event reflects new values
5. Event ID remains same (update, not recreate)

#### 4.2.3 Task Reschedule Syncs to Calendar

**Test Case ID:** TC-CAL-009

**Objective:** Verify rescheduling updates event time

**Prerequisites:** Calendar connected, task with synced event

**Test Scenarios:**

| Test | Reschedule Input | Expected Result | Pass/Fail |
|------|------------------|-----------------|-----------|
| Tomorrow | "דחה משימה 1 למחר" | Event moved to tomorrow | |
| Specific date/time | "דחה משימה 1 ל-31/10 בשעה 14:00" | Event on Oct 31, 14:00-15:00 | |
| Relative time | "דחה משימה 1 בעוד 2 שעות" | Event moved to now+2h | |

#### 4.2.4 Task Completion Marks Event as Done

**Test Case ID:** TC-CAL-010

**Objective:** Verify completing task marks calendar event

**Prerequisites:** Calendar connected, task with synced event

**Test Scenarios:**

| Test | Completion Method | Expected Result | Pass/Fail |
|------|-------------------|-----------------|-----------|
| Complete by number | "סיימתי משימה 1" | Event title → "✅ [title]", color → gray | |
| Complete by description | "סיימתי לקנות חלב" | Same result | |
| Complete via 👍 | React to task message | Same result | |

**Expected Calendar Event Changes:**
- Title: "לקנות חלב" → "✅ לקנות חלב"
- Color ID: default → "8" (gray, completed)

**Verification:**
1. Complete task
2. Refresh Google Calendar
3. Verify event shows ✅ prefix
4. Verify event is gray color
5. Event not deleted (preserved for history)

#### 4.2.5 Task Deletion Removes Calendar Event

**Test Case ID:** TC-CAL-011

**Objective:** Verify deleting task removes event

**Prerequisites:** Calendar connected, task with synced event

**Test Scenarios:**

| Test | Deletion Method | Expected Result | Pass/Fail |
|------|-----------------|-----------------|-----------|
| Delete by number | "מחק משימה 1" | Task deleted, event removed from calendar | |
| Delete by description | "מחק לקנות חלב" | Same result | |

**Verification:**
1. Note event ID before deletion
2. Delete task
3. Refresh Google Calendar
4. Verify event no longer appears
5. Task `calendar_event_id` cleared

#### 4.2.6 Recurring Instance Sync

**Test Case ID:** TC-CAL-012

**Objective:** Verify recurring instances sync individually

**Prerequisites:** Calendar connected, recurring pattern with instances

**Test Scenarios:**

| Test | Scenario | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| Pattern creates instance | Instance generated at midnight | New calendar event created for instance | |
| Complete instance | "סיימתי משימה 1" (instance) | Instance's event marked ✅ | |
| Next instance | Generated next day | New separate event created | |

**Verification:**
- Each instance gets own `calendar_event_id`
- Pattern itself has NO event (only instances)
- Multiple instances = multiple separate events
- Event descriptions contain instance details

#### 4.2.7 Sync Failure Recovery

**Test Case ID:** TC-CAL-013

**Objective:** Verify graceful handling of sync failures

**Test Scenarios:**

| Test | Failure Scenario | Expected Result | Pass/Fail |
|------|------------------|-----------------|-----------|
| Calendar API down | Create task while API failing | Task created, sync error logged, no crash | |
| Token expired during sync | Create task with expired token | Task created, auto-reconnect attempted | |
| Network timeout | Sync times out | Task created, error logged, retry on reconnect | |
| Rate limit hit | Too many requests | Task created, sync deferred | |

**Verification:**
- Task always created successfully (sync is non-fatal)
- `calendar_sync_error` field populated on failure
- Sync retried on reconnection
- User not blocked by calendar issues

---

### 4.3 Calendar → Bot Sync (Phase 2)

#### 4.3.1 Event with Configured Color Becomes Task

**Test Case ID:** TC-CAL-014

**Objective:** Verify calendar events sync to bot based on color

**Prerequisites:** Calendar connected, color configured (e.g., color 9 = Blueberry)

**Setup:**
1. Send "קבע צבע 9" to configure color

**Test Scenarios:**

| Test | Action in Google Calendar | Expected Result | Pass/Fail |
|------|---------------------------|-----------------|-----------|
| Create event with color 9 | Create event, set color to Blueberry | Task created in bot within 10 min | |
| Create event with other color | Create event, color 3 (not configured) | No task created | |
| Event has due time | Event 31/10 14:00-15:00 | Task with due_date = Oct 31, 14:00 | |
| All-day event | Event Oct 31 (all day) | Task with due_date = Oct 31, 09:00 | |

**Verification:**
1. Create event in Google Calendar with configured color
2. Wait up to 10 minutes (sync interval)
3. Send "משימות" to bot
4. Verify task appears with:
   - Description = event title
   - Due date = event start time
   - `created_from_calendar = True`
   - `calendar_event_id` = event ID
5. Complete/modify task → calendar updates
6. Complete/modify event → bot updates

#### 4.3.2 Event with '#' in Title Becomes Task

**Test Case ID:** TC-CAL-015

**Objective:** Verify hashtag detection for task creation

**Prerequisites:** Calendar connected, hashtag detection enabled (default)

**Test Scenarios:**

| Test | Event Title in Calendar | Expected Result | Pass/Fail |
|------|-------------------------|-----------------|-----------|
| Title with # | "# לקנות חלב" | Task created: "לקנות חלב" | |
| Title with # anywhere | "לקנות # חלב" | Task created | |
| Title without # | "לקנות חלב" | No task created (unless color matches) | |
| Multiple # | "## urgent meeting" | Task created | |

**Hashtag Toggle Test:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Disable hashtag | Send "כבה #" | Confirmation, hashtag detection off | |
| Create event with # | Create "# task" in calendar | No task created | |
| Enable hashtag | Send "הפעל #" | Confirmation, hashtag detection on | |
| Create event with # | Create "# task" in calendar | Task created | |

#### 4.3.3 Event Update Syncs to Bot

**Test Case ID:** TC-CAL-016

**Objective:** Verify event changes sync to task

**Prerequisites:** Calendar connected, event→task exists

**Test Scenarios:**

| Test | Change in Calendar | Expected Result in Bot | Pass/Fail |
|------|-------------------|------------------------|-----------|
| Change title | Edit event title | Task description updated | |
| Change time | Reschedule event | Task due_date updated | |
| Change color (remove match) | Change from color 9 to color 3 | Task unchanged (already created) | |
| Add color match | Change from color 3 to color 9 | New task created | |

**Verification:**
- Changes detected within 10 minutes
- `calendar_last_modified` timestamp updated
- Last write wins (most recent change prevails)

#### 4.3.4 Event Deletion Syncs to Bot

**Test Case ID:** TC-CAL-017

**Objective:** Verify deleting calendar event deletes task

**Prerequisites:** Calendar connected, event→task exists

**Test Scenarios:**

| Test | Action in Calendar | Expected Result in Bot | Pass/Fail |
|------|-------------------|------------------------|-----------|
| Delete event | Delete event from calendar | Task deleted/marked cancelled | |
| Delete recurring event | Delete recurring series | Pattern stopped OR instances removed | |

**Verification:**
- Task no longer appears in "משימות"
- Deletion detected within 10 minutes

#### 4.3.5 Recurring Event Handling

**Test Case ID:** TC-CAL-018

**Objective:** Verify recurring calendar events handled properly

**Test Scenarios:**

| Test | Calendar Event Type | Expected Result | Pass/Fail |
|------|---------------------|-----------------|-----------|
| Daily recurring event | Daily event with color 9 | Pattern created in bot OR instances created | |
| Weekly recurring event | Weekly event with # | Pattern OR instances | |
| Recurring event instance | Modify single instance | That instance's task updated | |

**Note:** Implementation may vary - either:
- Create recurring pattern in bot
- OR create individual tasks for each instance
- Document actual behavior

#### 4.3.6 Deduplication (Event Already Linked)

**Test Case ID:** TC-CAL-019

**Objective:** Verify no duplicate tasks from same event

**Prerequisites:** Task created in bot, synced to calendar

**Test Scenarios:**

| Test | Scenario | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| Task→Event→Task | Bot task creates event, sync runs | No duplicate task created | |
| Event exists | Event already has task | Sync skips (checks calendar_event_id) | |
| Same event ID | Multiple sync passes | Task created only once | |

**Verification:**
- Check task has `calendar_event_id`
- Sync queries exclude events with existing task links
- No duplicates in "משימות"

#### 4.3.7 Last Write Wins Conflict Resolution

**Test Case ID:** TC-CAL-020

**Objective:** Verify conflict resolution when both sides change

**Scenario:** Task and event both modified between sync cycles

**Test Scenarios:**

| Test | Timeline | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| Bot change newer | Task updated 10:01, Event updated 10:00, Sync 10:05 | Event updated to match task | |
| Calendar change newer | Task updated 10:00, Event updated 10:01, Sync 10:05 | Task updated to match event | |
| Same timestamp | Both updated 10:00 | Either wins (consistent behavior) | |

**Mechanism:**
- Compare `last_modified_at` (bot) vs `calendar_last_modified` (event updated timestamp)
- Apply most recent change to other side
- No merge conflicts - simple last-write-wins

---

### 4.4 Calendar Settings

#### 4.4.1 View Settings

**Test Case ID:** TC-CAL-021

**Objective:** Verify calendar settings display

**Prerequisites:** Calendar connected

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "הגדרות יומן" | Settings display with current values | |
| English | "calendar settings" | Same result | |

**Expected Format:**
```
⚙️ **הגדרות סנכרון יומן**

🎨 **צבע אירועים למשימות:** Blueberry (כחול)
#️⃣ **זיהוי סימן # בכותרת:** מופעל ✅

**איך זה עובד?**
אירועים שיוצרים ב-Google Calendar עם הצבע שבחרת או עם # בכותרת יהפכו אוטומטית למשימות בבוט (תוך 10 דקות).

**שינוי צבע:**
כתוב "קבע צבע [מספר]" - למשל:
• "קבע צבע 1" - Lavender
• "קבע צבע 9" - Blueberry
...

**זיהוי סימן #:**
• "כבה #" - כיבוי זיהוי אוטומטי של #
• "הפעל #" - הפעלה מחדש

💡 **טיפ:** אם לא מגדיר צבע, רק אירועים עם # בכותרת יהפכו למשימות.
```

**Verification:**
- Current color shown (if set)
- Hashtag status shown (enabled/disabled)
- Instructions clear and complete

#### 4.4.2 Set Event Color (1-11)

**Test Case ID:** TC-CAL-022

**Objective:** Verify color configuration

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Valid color (Hebrew) | "קבע צבע 9" | "✅ צבע עודכן בהצלחה! 🎨 צבע: Blueberry..." | |
| Valid color (English) | "set color 9" | Same result | |
| Valid color 1 | "קבע צבע 1" | Color set to Lavender | |
| Valid color 11 | "קבע צבע 11" | Color set to Tomato | |
| Invalid color 0 | "קבע צבע 0" | Error: invalid color, show valid range (1-11) | |
| Invalid color 12 | "קבע צבע 12" | Error: invalid color | |
| Invalid format | "קבע צבע blue" | Error: must be number 1-11 | |
| No calendar | "קבע צבע 9" (not connected) | Error: connect calendar first | |

**Color Reference Table:**

| ID | Name | Hebrew |
|----|------|--------|
| 1 | Lavender | סגול בהיר |
| 2 | Sage | ירוק חכם |
| 3 | Grape | ענבים |
| 4 | Flamingo | ורוד |
| 5 | Banana | צהוב |
| 6 | Tangerine | כתום |
| 7 | Peacock | טורקיז |
| 8 | Graphite | אפור |
| 9 | Blueberry | כחול |
| 10 | Basil | ירוק |
| 11 | Tomato | אדום |

**Verification:**
- User record `calendar_sync_color` updated
- New events with that color sync to bot
- Old events not affected (not retroactive)

#### 4.4.3 Toggle Hashtag Detection

**Test Case ID:** TC-CAL-023

**Objective:** Verify hashtag detection toggle

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Disable (Hebrew) | "כבה #" | "✅ זיהוי # כובה" message | |
| Disable (English) | "disable #" | Same result | |
| Alternative | "כבה סולמית" | Same result | |
| Enable (Hebrew) | "הפעל #" | "✅ זיהוי # הופעל!" message | |
| Enable (English) | "enable #" | Same result | |
| Alternative | "הפעל סולמית" | Same result | |

**Verification After Disable:**
- User record `calendar_sync_hashtag = False`
- New events with # don't create tasks
- Events with configured color still create tasks

**Verification After Enable:**
- User record `calendar_sync_hashtag = True`
- New events with # create tasks
- Combined with color setting (OR logic)

#### 4.4.4 Settings Validation

**Test Case ID:** TC-CAL-024

**Objective:** Verify settings validation and edge cases

**Test Scenarios:**

| Test | Scenario | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| Settings without calendar | "הגדרות יומן" (not connected) | Error: connect calendar first | |
| Color without calendar | "קבע צבע 9" (not connected) | Error: connect calendar first | |
| No color + hashtag off | Both disabled | Warning: no events will sync | |
| View after color set | "הגדרות יומן" after "קבע צבע 9" | Shows color 9 | |
| View after hashtag off | "הגדרות יומן" after "כבה #" | Shows hashtag disabled | |

---

### 4.5 Calendar Display

#### 4.5.1 Show Schedule (Tasks + Events)

**Test Case ID:** TC-CAL-025

**Objective:** Verify unified schedule display

**Prerequisites:** Calendar connected, has tasks and events

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "הצג יומן" | Tasks section + events section | |
| Alternative | "יומן" | Same result | |
| English | "show calendar" | Same result | |
| Alternative | "calendar" | Same result | |

**Expected Format:**
```
📋 המשימות שלך (2):

1. לקנות חלב [#123] 📅 (יעד היום 15:00)
2. פגישה [#124] 📅 (יעד מחר 10:00)

📅 אירועים ביומן (2):
🗓️ 10:00-11:00 פגישה עם לקוח
🗓️ 14:00-15:00 ישיבת צוות
```

**Verification:**
- Two separate sections clearly labeled
- Tasks formatted with task service formatter (shows IDs, icons)
- Events show time range + title
- No duplicates (events already linked to tasks excluded from events section)

#### 4.5.2 Deduplication in Display

**Test Case ID:** TC-CAL-026

**Objective:** Verify events linked to tasks not shown twice

**Prerequisites:** Calendar connected, task with synced event

**Setup:**
1. Create task "לקנות חלב מחר ב-15:00"
2. Task syncs to calendar (has `calendar_event_id`)

**Test Scenarios:**

| Test | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| Show schedule | "הצג יומן" | Task shown in tasks section, NOT in events section | |
| Both sections | Multiple tasks + unlinked events | Correct items in each section | |

**Deduplication Logic:**
- Get task `calendar_event_id` values
- Filter events: exclude if `event.id` in task event IDs
- Events without corresponding tasks shown in events section

#### 4.5.3 Daily Summary with Calendar Events

**Test Case ID:** TC-CAL-027

**Objective:** Verify 9 AM daily summary includes calendar events

**Prerequisites:** Calendar connected

**Test Scenarios:**

| Test | Scenario | Expected in 9 AM Summary | Pass/Fail |
|------|----------|--------------------------|-----------|
| Tasks only | User has tasks, no events | Tasks section only | |
| Events only | User has events, no tasks | Events section only | |
| Both | User has tasks + events | Both sections with deduplication | |
| Neither | No tasks or events | Motivational message OR no summary | |

**Expected Format:**
```
📋 סיכום משימות יומי

⚠️ באיחור (1):
  • משימה ישנה (30/10 10:00)

📅 משימות להיום (2):
  • לקנות חלב (15:00)
  • פגישה (10:00)

📆 אירועים ביומן (2):
  • ישיבת צוות (14:00-15:00)
  • שיחת טלפון (16:00-16:30)

💪 בהצלחה היום!
```

#### 4.5.4 Edge Cases - Calendar Display

**Test Case ID:** TC-CAL-028

**Test Scenarios:**

| Test | Scenario | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| No calendar connected | "הצג יומן" (not connected) | Error: connect calendar first | |
| Many events (50+) | Calendar has 50+ events today | First 20 shown OR paginated | |
| Events outside timeframe | Has events next week | Not shown (today only) | |
| All-day events | Calendar has all-day events | Shown in events section | |
| Recurring events | Calendar has recurring events | Each instance shown separately | |

---

## 5. Voice Message Testing

### 5.1 Voice Input Processing

#### 5.1.1 Hebrew Voice Messages

**Test Case ID:** TC-VOICE-001

**Objective:** Verify Hebrew voice transcription and task extraction

**Test Scenarios:**

| Test | Voice Input (Hebrew) | Expected Result | Pass/Fail |
|------|----------------------|-----------------|-----------|
| Simple task | "תזכיר לי לקנות חלב" | Transcription shown, task created "לקנות חלב" | |
| With tomorrow | "תזכיר לי מחר לקנות חלב" | Transcription + task with tomorrow 09:00 | |
| With specific time | "תזכיר לי מחר בשעה חמש לקנות חלב" | Task with tomorrow 17:00 | |
| With day name | "תזכיר לי ביום ראשון לקחת ויטמינים" | Task on next Sunday | |
| Multiple tasks | "תזכיר לי לקנות חלב ולהתקשר לרופא" | 2 tasks created | |
| Task completion | "סיימתי את המשימה לקנות חלב" | Task "לקנות חלב" completed | |
| Task query | "מה המשימות שלי להיום" | Today's tasks listed | |

**Verification Steps:**
1. Record Hebrew voice message (clear audio)
2. Send to bot
3. Verify processing message: "🎤 מעבד את ההודעה הקולית..."
4. Wait for response (5-15 seconds)
5. Verify transcription shown first
6. Verify task operation executed
7. Verify confirmation message

**Expected Flow:**
```
User: [Voice: "תזכיר לי לקנות חלב מחר בשעה חמש"]
Bot: 🎤 מעבד את ההודעה הקולית...
Bot: [Transcription]
     📝 שמעתי: "תזכיר לי לקנות חלב מחר בשעה חמש"
     
     ✅ נוצרה משימה: לקנות חלב
     📅 תאריך יעד: 30/11/2025 בשעה 17:00
```

#### 5.1.2 English Voice Messages

**Test Case ID:** TC-VOICE-002

**Objective:** Verify English voice transcription and task extraction

**Test Scenarios:**

| Test | Voice Input (English) | Expected Result | Pass/Fail |
|------|----------------------|-----------------|-----------|
| Simple task | "remind me to buy milk" | Transcription + task "buy milk" | |
| With tomorrow | "remind me tomorrow to buy milk" | Task with tomorrow 09:00 | |
| With time | "remind me tomorrow at 3pm to call mom" | Task with tomorrow 15:00 | |
| With day | "remind me on Monday to take vitamins" | Task on next Monday | |
| Complete task | "I finished buy milk" | Task "buy milk" completed | |

#### 5.1.3 Task Creation via Voice

**Test Case ID:** TC-VOICE-003

**Objective:** Verify all task creation features work via voice

**Test Scenarios:**

| Test | Voice Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Without date | "תזכיר לי לקנות חלב" (no date) | Task created without due date | |
| Multiple tasks | "תזכיר לי לקנות חלב ולחם" | 2 separate tasks | |
| Long description | 100+ word description | Task created, description captured | |
| With emoji | "תזכיר לי לקנות חלב 🥛" | Task created with emoji (if transcribed) | |

#### 5.1.4 Task Completion via Voice

**Test Case ID:** TC-VOICE-004

**Objective:** Verify task completion commands work via voice

**Prerequisites:** Existing tasks

**Test Scenarios:**

| Test | Voice Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew completion | "סיימתי לקנות חלב" | Task "לקנות חלב" completed | |
| English completion | "I finished buy milk" | Task "buy milk" completed | |
| With typo (fuzzy) | "סיימתי לקנות הלב" | Task "לקנות חלב" completed (fuzzy match) | |
| By number | "סיימתי משימה אחת" | Task #1 completed | |

#### 5.1.5 Task Updates via Voice

**Test Case ID:** TC-VOICE-005

**Objective:** Verify task updates work via voice

**Test Scenarios:**

| Test | Voice Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Update description | "שנה את משימה אחת להתקשר לרופא" | Task #1 description updated | |
| Reschedule | "דחה את משימה שניים למחר" | Task #2 rescheduled to tomorrow | |

#### 5.1.6 Queries via Voice

**Test Case ID:** TC-VOICE-006

**Objective:** Verify query commands work via voice

**Test Scenarios:**

| Test | Voice Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| List tasks | "מה המשימות שלי" | Task list returned | |
| Today's tasks | "מה המשימות שלי להיום" | Today's tasks listed | |
| Statistics | "תראה לי סטטיסטיקה" | Statistics displayed | |
| When query | "מתי הפגישה עם יוחנן" | Due date shown | |

#### 5.1.7 Transcription Accuracy

**Test Case ID:** TC-VOICE-007

**Objective:** Verify transcription quality

**Test Scenarios:**

| Test | Audio Quality | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Clear audio | Clean recording, no background noise | Accurate transcription (95%+) | |
| Background noise | Some noise present | Transcription mostly accurate (80%+) | |
| Fast speech | Rapid speaking | Transcription captures most words | |
| Slow speech | Deliberate, clear speech | Very accurate transcription | |
| Hebrew dialects | Different Hebrew accents | Recognizes most words | |

#### 5.1.8 Edge Cases - Voice Messages

**Test Case ID:** TC-VOICE-008

**Test Scenarios:**

| Test | Scenario | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| Unclear audio | Very noisy/muffled | Transcription + "לא הצלחתי להבין..." message | |
| Long message (5+ min) | Very long voice note | Transcription + task extraction (or timeout) | |
| Empty audio | Silence | Error or "לא שמעתי כלום" | |
| Non-speech sounds | Music, beeping | Transcription attempts or error | |
| Mixed language | Hebrew + English in same message | Both transcribed, task extracted | |
| Unsupported language | Russian/Arabic | Transcription attempts or error | |
| Corrupted audio | Broken audio file | Error message, no crash | |

---

## 6. Natural Language Processing Testing

### 6.1 Hebrew Date Parsing

#### 6.1.1 Relative Dates (Hebrew)

**Test Case ID:** TC-NLP-001

**Objective:** Verify Hebrew relative date parsing

**Test Scenarios:**

| Test | Input Text | Expected Due Date | Pass/Fail |
|------|------------|-------------------|-----------|
| מחר | "לקנות חלב מחר" | Tomorrow, 09:00 | |
| מחרתיים | "לקנות חלב מחרתיים" | Day after tomorrow, 09:00 | |
| היום | "לקנות חלב היום" | Today, 09:00 | |
| הערב | "לקנות חלב הערב" | Today, 19:00 | |
| בבוקר | "לקנות חלב מחר בבוקר" | Tomorrow, 08:00 | |
| אחר הצהריים | "לקנות חלב אחר הצהריים" | Today, 14:00 | |
| בלילה | "לקנות חלב בלילה" | Today/tonight, 22:00 | |
| בעוד שעה | "תזכיר לי בעוד שעה" | Now + 1 hour | |
| בעוד שעתיים | "תזכיר לי בעוד שעתיים" | Now + 2 hours | |
| בעוד 5 דקות | "תזכיר לי בעוד 5 דקות" | Now + 5 minutes | |
| בעוד שבוע | "פגישה בעוד שבוע" | Now + 7 days | |
| בעוד חודש | "פגישה בעוד חודש" | Now + 30 days | |
| השבוע | "פגישה השבוע" | This week (next business day) | |
| החודש | "פגישה החודש" | This month (reasonable date) | |

**Verification for Each:**
1. Create task with input
2. Verify due date matches expected
3. Verify timezone is Israel (Asia/Jerusalem)
4. Verify hour/minute correct

#### 6.1.2 Day Names (Hebrew)

**Test Case ID:** TC-NLP-002

**Objective:** Verify Hebrew day name parsing

**Test Scenarios:**

| Test | Input Text | Expected Due Date | Pass/Fail |
|------|------------|-------------------|-----------|
| יום ראשון | "פגישה ביום ראשון" | Next Sunday, 09:00 | |
| יום שני | "פגישה ביום שני" | Next Monday, 09:00 | |
| יום שלישי | "פגישה ביום שלישי" | Next Tuesday, 09:00 | |
| יום רביעי | "פגישה ביום רביעי" | Next Wednesday, 09:00 | |
| יום חמישי | "פגישה ביום חמישי" | Next Thursday, 09:00 | |
| יום שישי | "פגישה ביום שישי" | Next Friday, 09:00 | |
| שבת | "פגישה בשבת" | Next Saturday, 09:00 | |
| ראשון הבא | "פגישה ביום ראשון הבא" | Next Sunday (even if today is Sunday → next week) | |

**Current Day Logic:**
- If today is Monday and input is "יום שני":
  - Expected: NEXT Monday (7 days ahead), NOT today
  - OR: Could be today if time not passed yet (implementation dependent)

#### 6.1.3 Absolute Dates (Hebrew Input)

**Test Case ID:** TC-NLP-003

**Objective:** Verify absolute date parsing

**Test Scenarios:**

| Test | Input Text | Expected Due Date | Pass/Fail |
|------|------------|-------------------|-----------|
| DD/MM | "פגישה 31/10" | October 31, current year, 09:00 | |
| DD/MM/YYYY | "פגישה 31/10/2025" | October 31, 2025, 09:00 | |
| D/M | "פגישה 5/7" | July 5, current year, 09:00 | |
| DD-MM | "פגישה 31-10" | October 31, 09:00 | |
| DD.MM | "פגישה 31.10" | October 31, 09:00 | |

**Edge Cases:**

| Test | Input | Expected Result | Pass/Fail |
|------|-------|-----------------|-----------|
| Invalid day | "פגישה 32/10" | Error OR task without date | |
| Invalid month | "פגישה 31/13" | Error OR task without date | |
| Past date (no year) | "פגישה 01/01" (in December) | Next year January 1 | |
| Past date (with year) | "פגישה 01/01/2020" | Error OR year 2020 (allow for history?) | |

#### 6.1.4 Time Expressions (Hebrew)

**Test Case ID:** TC-NLP-004

**Objective:** Verify time parsing in Hebrew

**Test Scenarios:**

| Test | Input Text | Expected Time | Pass/Fail |
|------|------------|---------------|-----------|
| ב-9 | "פגישה מחר ב-9" | 09:00 | |
| ב-15 | "פגישה מחר ב-15" | 15:00 | |
| בשעה 9 | "פגישה מחר בשעה 9" | 09:00 | |
| בשעה 15:00 | "פגישה מחר בשעה 15:00" | 15:00 | |
| בשעה 15:30 | "פגישה מחר בשעה 15:30" | 15:30 | |
| 9 בבוקר | "פגישה 9 בבוקר" | 09:00 | |
| 3 אחר הצהריים | "פגישה 3 אחר הצהריים" | 15:00 | |
| חצות | "תזכיר לי בחצות" | 00:00 (midnight) | |
| חצי היום | "תזכיר לי בחצי היום" | 12:00 (noon) | |

#### 6.1.5 Combined Expressions (Hebrew)

**Test Case ID:** TC-NLP-005

**Objective:** Verify combined date+time parsing

**Test Scenarios:**

| Test | Input Text | Expected Due Date | Pass/Fail |
|------|------------|-------------------|-----------|
| מחר ב-9 | "פגישה מחר ב-9" | Tomorrow, 09:00 | |
| יום שני בשעה 10:30 | "פגישה יום שני בשעה 10:30" | Next Monday, 10:30 | |
| 31/10 בשעה 14:00 | "פגישה 31/10 בשעה 14:00" | Oct 31, 14:00 | |
| מחרתיים ב-15:00 | "פגישה מחרתיים ב-15:00" | Day after tomorrow, 15:00 | |
| בעוד שעתיים | "תזכיר לי בעוד שעתיים" | Now + 2 hours (exact) | |

---

### 6.2 English Date Parsing

#### 6.2.1 Relative Dates (English)

**Test Case ID:** TC-NLP-006

**Objective:** Verify English relative date parsing

**Test Scenarios:**

| Test | Input Text | Expected Due Date | Pass/Fail |
|------|------------|-------------------|-----------|
| tomorrow | "buy milk tomorrow" | Tomorrow, 09:00 | |
| today | "buy milk today" | Today, 09:00 | |
| tonight | "buy milk tonight" | Today, 19:00 or 22:00 | |
| in 1 hour | "remind me in 1 hour" | Now + 1 hour | |
| in 2 hours | "remind me in 2 hours" | Now + 2 hours | |
| in 30 minutes | "remind me in 30 minutes" | Now + 30 minutes | |
| in a week | "meeting in a week" | Now + 7 days | |
| next week | "meeting next week" | Next week (Monday or similar) | |

#### 6.2.2 Day Names (English)

**Test Case ID:** TC-NLP-007

**Objective:** Verify English day name parsing

**Test Scenarios:**

| Test | Input Text | Expected Due Date | Pass/Fail |
|------|------------|-------------------|-----------|
| Monday | "meeting on Monday" | Next Monday, 09:00 | |
| Tuesday | "meeting on Tuesday" | Next Tuesday, 09:00 | |
| Wednesday | "meeting on Wednesday" | Next Wednesday, 09:00 | |
| Thursday | "meeting on Thursday" | Next Thursday, 09:00 | |
| Friday | "meeting on Friday" | Next Friday, 09:00 | |
| Saturday | "meeting on Saturday" | Next Saturday, 09:00 | |
| Sunday | "meeting on Sunday" | Next Sunday, 09:00 | |
| next Friday | "meeting next Friday" | Next Friday (explicit) | |

#### 6.2.3 Absolute Dates (English)

**Test Case ID:** TC-NLP-008

**Objective:** Verify English absolute date parsing

**Test Scenarios:**

| Test | Input Text | Expected Due Date | Pass/Fail |
|------|------------|-------------------|-----------|
| October 31st | "meeting October 31st" | Oct 31, 09:00 | |
| Oct 31 | "meeting Oct 31" | Oct 31, 09:00 | |
| 10/31 | "meeting 10/31" | Oct 31, 09:00 (US format if configured) | |
| December 25, 2025 | "meeting December 25, 2025" | Dec 25, 2025, 09:00 | |

#### 6.2.4 Time Expressions (English)

**Test Case ID:** TC-NLP-009

**Objective:** Verify English time parsing

**Test Scenarios:**

| Test | Input Text | Expected Time | Pass/Fail |
|------|------------|---------------|-----------|
| at 9am | "meeting tomorrow at 9am" | 09:00 | |
| at 9 AM | "meeting tomorrow at 9 AM" | 09:00 | |
| at 3pm | "meeting tomorrow at 3pm" | 15:00 | |
| at 3 PM | "meeting tomorrow at 3 PM" | 15:00 | |
| at 14:30 | "meeting tomorrow at 14:30" | 14:30 | |
| at 2:30 PM | "meeting tomorrow at 2:30 PM" | 14:30 | |

#### 6.2.5 Combined Expressions (English)

**Test Case ID:** TC-NLP-010

**Objective:** Verify combined English date+time parsing

**Test Scenarios:**

| Test | Input Text | Expected Due Date | Pass/Fail |
|------|------------|-------------------|-----------|
| tomorrow at 3pm | "meeting tomorrow at 3pm" | Tomorrow, 15:00 | |
| Monday at 10:30 | "meeting Monday at 10:30" | Next Monday, 10:30 | |
| October 31st at 2pm | "meeting October 31st at 2pm" | Oct 31, 14:00 | |
| in 2 hours | "remind me in 2 hours" | Now + 2 hours (exact) | |

---

### 6.3 Timezone Handling

#### 6.3.1 Israel Timezone Calculations

**Test Case ID:** TC-NLP-011

**Objective:** Verify all calculations use Israel timezone (Asia/Jerusalem)

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| Task created | Any task with due date | Stored with Asia/Jerusalem timezone | |
| "Tomorrow" calculation | Create task "מחר" at 11pm | Tomorrow = next day, not in 1 hour | |
| Midnight rollover | Create "היום" at 11:59pm | Today = current day until midnight | |
| Hour calculation | "בעוד שעה" at 23:30 | Tomorrow 00:30 (crosses midnight) | |
| Display format | List tasks | Times shown in 24h format (HH:MM) | |

#### 6.3.2 DST Transitions

**Test Case ID:** TC-NLP-012

**Objective:** Verify DST handling (Israel switches in March/October)

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| Spring forward | Task created before DST, due after | Correct time after DST change | |
| Fall back | Task created before DST, due after | Correct time after DST change | |
| Recurring daily | Daily task spans DST change | Maintains local time (e.g., 9am stays 9am) | |

#### 6.3.3 Display Formatting

**Test Case ID:** TC-NLP-013

**Objective:** Verify date/time display format

**Expected Formats:**

| Context | Format | Example | Pass/Fail |
|---------|--------|---------|-----------|
| Date only | DD/MM/YYYY | "31/10/2025" | |
| Date with time | DD/MM/YYYY HH:MM | "31/10/2025 14:30" | |
| Today's tasks | "היום HH:MM" | "היום 15:00" | |
| Tomorrow's tasks | "מחר HH:MM" | "מחר 10:00" | |
| This week | Day name + time | "יום שני 14:00" | |
| Future weeks | DD/MM HH:MM | "31/10 14:00" | |

---

## 7. Fuzzy Matching Testing

### 7.1 Hebrew Fuzzy Matching

#### 7.1.1 Typos in Hebrew

**Test Case ID:** TC-FUZZY-001

**Objective:** Verify typo tolerance for Hebrew task descriptions

**Prerequisites:** Task exists "לקנות חלב"

**Test Scenarios:**

| Test | Input (with typo) | Original Task | Match Confidence | Expected Result | Pass/Fail |
|------|-------------------|---------------|------------------|-----------------|-----------|
| Extra letter | "סיימתי לקנות חלבב" | "לקנות חלב" | ~95% | Task matched and completed | |
| Wrong letter | "סיימתי לקנות הלב" | "לקנות חלב" | ~85% | Task matched and completed | |
| Missing letter | "סיימתי לקנות חלב" → "לקנות הלב" | "לקנות חלב" | ~90% | Task matched | |
| Two typos | "סיימתי לקנות הלבב" | "לקנות חלב" | ~75% | Task matched (if >65%) | |
| Letter swap | "סיימתי לקונת חלב" | "לקנות חלב" | ~90% | Task matched | |
| Similar word | "סיימתי לקנות חולב" | "לקנות חלב" | ~80% | Task matched | |

**Confidence Thresholds:**
- **High confidence (≥85%)**: Match without notification
- **Medium confidence (65-84%)**: Match with confidence shown
- **Low confidence (<65%)**: Fallback to ILIKE search

#### 7.1.2 Partial Matches (Hebrew)

**Test Case ID:** TC-FUZZY-002

**Objective:** Verify partial description matching

**Prerequisites:** Tasks exist:
- "לקנות חלב מהסופר"
- "לקנות לחם"
- "פגישה עם רופא שיניים"

**Test Scenarios:**

| Test | Input | Expected Match | Pass/Fail |
|------|-------|----------------|-----------|
| Partial start | "סיימתי לקנות חלב" | "לקנות חלב מהסופר" | |
| Partial middle | "סיימתי חלב" | "לקנות חלב מהסופר" | |
| Partial end | "סיימתי עם רופא" | "פגישה עם רופא שיניים" | |
| Single word | "סיימתי רופא" | "פגישה עם רופא שיניים" | |

#### 7.1.3 Word Order Variations (Hebrew)

**Test Case ID:** TC-FUZZY-003

**Objective:** Verify word order flexibility

**Prerequisites:** Task exists "פגישה עם רופא שיניים"

**Test Scenarios:**

| Test | Input (different order) | Original Task | Expected Result | Pass/Fail |
|------|-------------------------|---------------|-----------------|-----------|
| Reversed | "סיימתי רופא עם פגישה" | "פגישה עם רופא שיניים" | Matched (fuzzy) | |
| Partial order | "סיימתי רופא שיניים" | "פגישה עם רופא שיניים" | Matched | |

#### 7.1.4 Multiple Similar Tasks - Tiebreaking by Due Date

**Test Case ID:** TC-FUZZY-004

**Objective:** Verify due date tiebreaking when multiple tasks match similarly

**Prerequisites:** Multiple tasks:
- Task A: "לקנות חלב" - due yesterday (overdue)
- Task B: "לקנות חלב" - due today
- Task C: "לקנות חלב" - due tomorrow

**Test Scenarios:**

| Test | Input | Expected Match | Reason | Pass/Fail |
|------|-------|----------------|--------|-----------|
| Complete "לקנות חלב" | "סיימתי לקנות חלב" | Task A (overdue) | Overdue prioritized | |
| After A completed | "סיימתי לקנות חלב" | Task B (today) | Today prioritized over tomorrow | |
| After A & B completed | "סיימתי לקנות חלב" | Task C (tomorrow) | Only one left | |

**Tiebreaking Priority:**
1. Overdue tasks (earliest first)
2. Today's tasks
3. Upcoming tasks (nearest first)
4. Tasks with no due date (last)

---

### 7.2 English Fuzzy Matching

#### 7.2.1 Typos in English

**Test Case ID:** TC-FUZZY-005

**Objective:** Verify typo tolerance for English task descriptions

**Prerequisites:** Task exists "buy milk"

**Test Scenarios:**

| Test | Input (with typo) | Original Task | Expected Result | Pass/Fail |
|------|-------------------|---------------|-----------------|-----------|
| Missing letter | "done with by milk" | "buy milk" | Task matched | |
| Extra letter | "done with buyy milk" | "buy milk" | Task matched | |
| Wrong letter | "done with buy molk" | "buy milk" | Task matched | |
| Two typos | "done with bu molk" | "buy milk" | Task matched (if >65%) | |

#### 7.2.2 Partial Matches (English)

**Test Case ID:** TC-FUZZY-006

**Prerequisites:** Task exists "buy milk from the supermarket"

**Test Scenarios:**

| Test | Input | Expected Match | Pass/Fail |
|------|-------|----------------|-----------|
| Partial start | "done with buy milk" | "buy milk from the supermarket" | |
| Partial middle | "done with milk from" | "buy milk from the supermarket" | |
| Single word | "done with milk" | "buy milk from the supermarket" | |

#### 7.2.3 Word Order Variations (English)

**Test Case ID:** TC-FUZZY-007

**Prerequisites:** Task exists "meeting with doctor"

**Test Scenarios:**

| Test | Input | Original Task | Expected Result | Pass/Fail |
|------|-------|---------------|-----------------|-----------|
| Reversed | "done with doctor meeting" | "meeting with doctor" | Matched | |
| Partial order | "done with doctor" | "meeting with doctor" | Matched | |

---

### 7.3 Confidence Levels & Fallback

#### 7.3.1 High Confidence Matches (≥85%)

**Test Case ID:** TC-FUZZY-008

**Objective:** Verify high-confidence matches proceed without notification

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| 95% match | Very close match | Task completed, no confidence shown | |
| 90% match | Close match | Task completed, no confidence shown | |
| 85% match | Good match | Task completed, no confidence shown | |

**Expected Confirmation:**
```
✅ השלמתי: לקנות חלב
```
(No mention of confidence)

#### 7.3.2 Medium Confidence Matches (65-84%)

**Test Case ID:** TC-FUZZY-009

**Objective:** Verify medium-confidence matches show confidence level

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| 80% match | Reasonable match | Task completed, confidence shown | |
| 70% match | Fair match | Task completed, confidence shown | |
| 65% match | Low-medium match | Task completed, confidence shown | |

**Expected Confirmation:**
```
✅ השלמתי: לקנות חלב
📊 התאמה: 75%
```

#### 7.3.3 Low Confidence (<65%)

**Test Case ID:** TC-FUZZY-010

**Objective:** Verify fallback to ILIKE search for low confidence

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| 50% match | Poor fuzzy match | Fallback to ILIKE (partial string match) | |
| 30% match | Very poor match | ILIKE search, possibly no result | |
| No fuzzy match | Completely different | ILIKE search only | |

**Verification:**
- RapidFuzz returns <65% score
- System tries `ILIKE '%search_term%'` query
- If found via ILIKE, task matched
- If not found, "לא נמצאה משימה" error

#### 7.3.4 Edge Cases - Fuzzy Matching

**Test Case ID:** TC-FUZZY-011

**Test Scenarios:**

| Test | Scenario | Expected Result | Pass/Fail |
|------|----------|-----------------|-----------|
| Empty search | "סיימתי " (only action, no description) | Error: specify task | |
| Very short query | "סיימתי א" (single letter) | Low confidence OR error | |
| Special characters | "סיימתי !!!!" | No match (or matches task with !!!!) | |
| Emoji in search | "סיימתי 🥛" | Match task with/without emoji | |
| Mixed language | "סיימתי buy milk" | Match "buy milk" task | |
| Multiple matches (same confidence) | 2 tasks, both 90% match | Use due date tiebreaker | |
| No tasks exist | "סיימתי anything" (no tasks) | Error: no tasks found | |

---

## 8. Reminder System Testing

### 8.1 Task-Specific Reminders (30-Minute Advance)

#### 8.1.1 Basic Reminder Functionality

**Test Case ID:** TC-REMIND-001

**Objective:** Verify 30-minute advance reminders

**Prerequisites:** Task with due date in future

**Test Scenarios:**

| Test | Task Due Time | Expected Reminder Time | Expected Result | Pass/Fail |
|------|---------------|------------------------|-----------------|-----------|
| Task due 14:00 | Task created for 14:00 | 13:30 | Reminder sent at 13:30 | |
| Task due 09:00 | Task created for 09:00 | 08:30 | Reminder sent at 08:30 | |
| Task due 00:30 | Task created for 00:30 | 00:00 (midnight) | Reminder sent at 00:00 | |
| Task due 10:15 | Task created for 10:15 | 09:45 | Reminder sent at 09:45 | |

**Verification Steps:**
1. Create task with specific due time
2. Calculate expected reminder time (due - 30 min)
3. Wait until reminder time
4. Verify reminder message received
5. Check reminder format and content
6. Verify `reminder_sent = True` in database

**Expected Reminder Format:**
```
⏰ תזכורת משימה!

📋 לקנות חלב
🕐 יעד: 14:00

בהצלחה! 💪
```

#### 8.1.2 One-Time Only (No Duplicates)

**Test Case ID:** TC-REMIND-002

**Objective:** Verify reminder sent only once

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| Task created early | Task due in 2 hours, wait | Single reminder at due-30min | |
| Multiple scheduler runs | Scheduler runs every 30s | Only 1 reminder sent total | |
| Task rescheduled after reminder | Reminder sent, then task rescheduled | New reminder for new time | |
| Task rescheduled before reminder | Task rescheduled before reminder sent | Reminder at new time only | |

**Verification:**
- `reminder_sent = False` initially
- `reminder_sent = True` after reminder sent
- Subsequent scheduler runs skip task (WHERE reminder_sent = False)
- Rescheduling resets `reminder_sent = False`

#### 8.1.3 Status Validation (Only Pending Tasks)

**Test Case ID:** TC-REMIND-003

**Objective:** Verify reminders only for pending tasks

**Test Scenarios:**

| Test | Task Status | Expected Behavior | Pass/Fail |
|------|-------------|-------------------|-----------|
| Pending | status = 'pending' | Reminder sent at due-30min | |
| Completed | status = 'completed' | No reminder sent | |
| Cancelled | status = 'cancelled' | No reminder sent | |
| Completed before reminder time | Pending → completed before due-30min | No reminder sent | |

**Verification:**
- Query: `WHERE status = 'pending' AND reminder_sent = False`
- Completed/cancelled tasks excluded

#### 8.1.4 Reminder Message Format

**Test Case ID:** TC-REMIND-004

**Objective:** Verify reminder message content and formatting

**Expected Components:**
- ⏰ emoji indicator
- "תזכורת משימה!" heading
- 📋 Task description
- 🕐 Due time (formatted)
- Encouragement message

**Test Scenarios:**

| Test | Task Details | Expected Format | Pass/Fail |
|------|--------------|-----------------|-----------|
| Hebrew task | "לקנות חלב" due 14:00 | Hebrew format with task details | |
| English task | "buy milk" due 14:00 | Hebrew format with task details | |
| Long description | 200-char description | Truncated if needed OR full text | |
| Task with emoji | "לקנות חלב 🥛" | Emoji preserved | |

#### 8.1.5 Timezone Correctness

**Test Case ID:** TC-REMIND-005

**Objective:** Verify reminders respect Israel timezone

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| Task due 14:00 Israel time | Created with 14:00 | Reminder at 13:30 Israel time | |
| DST transition | Task spans DST change | Reminder at correct local time | |
| Midnight crossing | Task due 00:15 | Reminder at 23:45 previous day | |

#### 8.1.6 Edge Cases - Task-Specific Reminders

**Test Case ID:** TC-REMIND-006

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| Task due in <30 min | Task created at 13:50, due 14:00 | No reminder (already within window) OR immediate | |
| Task due in past | Task created with past due date | No reminder | |
| Task without due date | Task has no due_date | No reminder | |
| Task deleted before reminder | Task deleted before due-30min | No reminder (task doesn't exist) | |
| User blocks bot | Reminder time arrives, user blocked | Log error, mark sent (avoid retry) | |
| WhatsApp API down | Reminder time, API failure | Log error, retry OR mark failed | |

---

### 8.2 Daily Proactive Reminders

#### 8.2.1 11 AM Reminder

**Test Case ID:** TC-REMIND-007

**Objective:** Verify 11 AM daily reminder

**Test Scenarios:**

| Test | User Situation | Expected Message | Pass/Fail |
|------|----------------|------------------|-----------|
| Has pending tasks | 5 pending tasks | "⏰ תזכורת יומית!\n\nיש לך 5 משימות ממתינות..." + task list | |
| Has today's tasks | 3 tasks due today | Emphasize today's tasks | |
| No tasks | 0 pending tasks | "⏰ תזכורת יומית!\n\nאין לך משימות ממתינות כרגע!" | |
| Inactive user | User hasn't messaged in 30+ days | No reminder sent (optional filter) | |

**Expected Format (with tasks):**
```
⏰ תזכורת יומית!

יש לך 5 משימות ממתינות:

1. לקנות חלב [#123] 🔥 (יעד היום 15:00)
2. פגישה [#124] 📅 (יעד מחר 10:00)
3. ...

💪 בהצלחה היום!
```

**Timing:**
- Runs at exactly 11:00 Israel time
- All active users receive reminder

#### 8.2.2 3 PM Reminder

**Test Case ID:** TC-REMIND-008

**Objective:** Verify 3 PM (15:00) daily reminder

**Test Scenarios:**

| Test | User Situation | Expected Message | Pass/Fail |
|------|----------------|------------------|-----------|
| Has pending tasks | Tasks exist | Reminder with task list | |
| Completed all since 11 AM | 0 pending tasks | "אין משימות!" OR no message | |
| New tasks created | Tasks created after 11 AM | Includes new tasks | |

**Timing:**
- Runs at exactly 15:00 Israel time

#### 8.2.3 7 PM Reminder

**Test Case ID:** TC-REMIND-009

**Objective:** Verify 7 PM (19:00) daily reminder

**Test Scenarios:**

| Test | User Situation | Expected Message | Pass/Fail |
|------|----------------|------------------|-----------|
| Has pending tasks | Tasks exist | Reminder with task list | |
| Evening focus | Tasks due tonight/tomorrow | Emphasize upcoming tasks | |

**Timing:**
- Runs at exactly 19:00 Israel time

#### 8.2.4 Task List Truncation (Max 10)

**Test Case ID:** TC-REMIND-010

**Objective:** Verify task list limits in proactive reminders

**Test Scenarios:**

| Test | User Has | Expected Display | Pass/Fail |
|------|----------|------------------|-----------|
| 5 tasks | 5 pending tasks | All 5 shown | |
| 10 tasks | 10 pending tasks | All 10 shown | |
| 15 tasks | 15 pending tasks | First 10 shown + "ועוד 5..." | |
| 100 tasks | 100 pending tasks | First 10 shown + "ועוד 90..." | |

**Format with truncation:**
```
⏰ תזכורת יומית!

יש לך 15 משימות ממתינות:

1. משימה 1
2. משימה 2
...
10. משימה 10

ועוד 5 משימות נוספות.
כתוב "משימות" לצפייה מלאה.
```

#### 8.2.5 Edge Cases - Daily Proactive Reminders

**Test Case ID:** TC-REMIND-011

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| New user (no tasks yet) | First day, 0 tasks | Reminder sent (encouraging message) OR skipped | |
| User in different timezone | User actually abroad | Reminder at 11 AM Israel time (may be night for user) | |
| Scheduler down | Scheduler offline during 11 AM | Missed (not sent retroactively) | |
| Multiple reminders same day | 11 AM, 3 PM, 7 PM | All 3 sent independently | |
| User blocks bot mid-day | Receives 11 AM, blocks, 3 PM time arrives | 3 PM fails gracefully | |

---

### 8.3 Daily Summary (9 AM)

#### 8.3.1 Daily Summary Content

**Test Case ID:** TC-REMIND-012

**Objective:** Verify 9 AM daily summary structure and content

**Test Scenarios:**

| Test | User Situation | Expected Sections | Pass/Fail |
|------|----------------|-------------------|-----------|
| Has overdue + today's | 2 overdue, 3 today, 5 future | ⚠️ Overdue + 📅 Today + 📆 Upcoming | |
| Only today's tasks | 0 overdue, 5 today | 📅 Today's tasks | |
| Only overdue | 3 overdue, 0 today | ⚠️ Overdue only | |
| Only future | 0 overdue, 0 today, 10 future | 📆 Upcoming OR "אין משימות להיום" | |
| No tasks | 0 total | "בוקר טוב! אין משימות להיום..." | |

**Expected Format (full example):**
```
📋 **סיכום משימות יומי - 29/11/2025**

⚠️ **באיחור (2):**
  • לקנות חלב [#123] (28/11 15:00)
  • פגישה עם רופא [#124] (27/11 10:00)

📅 **משימות להיום (3):**
  • לקחת ויטמינים (09:00)
  • התקשר לבנק (14:00)
  • ישיבת צוות (16:00)

📆 **אירועים ביומן (2):** *(if calendar connected)*
  • ישיבת צוות (14:00-15:00)
  • שיחת טלפון (16:00-16:30)

💪 בהצלחה היום!
```

**Verification:**
- Runs at 09:00 Israel time
- All active users receive summary
- Sections shown only if content exists
- Date shown in header

#### 8.3.2 Overdue Tasks Section

**Test Case ID:** TC-REMIND-013

**Objective:** Verify overdue tasks highlighted

**Test Scenarios:**

| Test | Overdue Count | Expected Display | Pass/Fail |
|------|---------------|------------------|-----------|
| 1 overdue | 1 task | ⚠️ section with 1 task | |
| 5 overdue | 5 tasks | All 5 shown with due dates | |
| 20 overdue | 20 tasks | First 10 shown + "ועוד 10..." | |

**Format:**
```
⚠️ **באיחור (5):**
  • לקנות חלב [#123] (28/11 15:00)
  • פגישה [#124] (27/11 10:00)
  ...
```

#### 8.3.3 Today's Tasks Section

**Test Case ID:** TC-REMIND-014

**Objective:** Verify today's tasks section

**Test Scenarios:**

| Test | Today's Count | Expected Display | Pass/Fail |
|------|---------------|------------------|-----------|
| 0 today | No tasks today | Section omitted OR "אין משימות להיום" | |
| 3 today | 3 tasks due today | All 3 with times | |
| 15 today | 15 tasks due today | First 10 + "ועוד 5..." | |

**Format:**
```
📅 **משימות להיום (3):**
  • לקחת ויטמינים (09:00)
  • התקשר לבנק (14:00)
  • ישיבת צוות (16:00)
```

#### 8.3.4 Calendar Events in Summary

**Test Case ID:** TC-REMIND-015

**Objective:** Verify Google Calendar events included (if connected)

**Prerequisites:** Calendar connected

**Test Scenarios:**

| Test | Scenario | Expected Display | Pass/Fail |
|------|----------|------------------|-----------|
| Calendar connected + events | Has events today | 📆 section with events | |
| Calendar connected, no events | 0 events today | Section omitted | |
| Calendar not connected | Calendar disabled | No calendar section | |
| Events + tasks (deduplication) | Events linked to tasks | Linked events NOT in events section | |

**Format:**
```
📆 **אירועים ביומן (2):**
  • ישיבת צוות (14:00-15:00)
  • שיחת טלפון (16:00-16:30)
```

#### 8.3.5 Edge Cases - Daily Summary

**Test Case ID:** TC-REMIND-016

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| New user (never created task) | First day, 0 tasks | Welcome message OR standard "אין משימות" | |
| User has only recurring patterns | 5 patterns, 0 instances today | "אין משימות להיום" | |
| Very long task descriptions | Tasks with 200+ char | Descriptions truncated in summary | |
| Emoji in task descriptions | Tasks contain emoji | Emoji preserved | |
| Mixed Hebrew/English tasks | Some Hebrew, some English | All displayed correctly | |

---

## 9. User Commands Testing

### 9.1 Basic Commands

#### 9.1.1 Help Command

**Test Case ID:** TC-CMD-001

**Objective:** Verify help command displays usage instructions

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "עזרה" | Help message with instructions | |
| English | "help" | Same help message | |
| Alternative | "Help" (capital) | Same help message (case-insensitive) | |
| In question | "איך משתמשים בבוט?" | AI response + help info | |

**Expected Help Format:**
```
👋 **ברוך הבא לבוט המשימות!**

🎯 **פקודות עיקריות:**

**ניהול משימות:**
• צור משימה: "תזכיר לי לקנות חלב מחר ב-15:00"
• הצג משימות: ? או "משימות"
• סיים משימה: "סיימתי משימה 1" או "סיימתי לקנות חלב"
• מחק משימה: "מחק משימה 2"
• עדכן משימה: "שנה משימה 1 ל..."
• דחה משימה: "דחה משימה 3 למחר"

**משימות חוזרות:**
• צור: "כל יום ב-9 תזכיר לי לקחת ויטמינים"
• הצג: "משימות חוזרות"
• עצור: "עצור סדרה [מספר]"

**מידע וסטטיסטיקות:**
• סטטיסטיקה
• הושלמו
• "מתי [משימה]"

**יומן Google:**
• חבר יומן
• נתק יומן
• סטטוס יומן
• הצג יומן
• הגדרות יומן

💡 **טיפים:**
• אפשר להשתמש בהקלטות קוליות!
• השב עם 👍 על משימה להשלמה מהירה
• כל הזמנים באזור הזמן של ישראל

🆘 לעזרה נוספת, שלח "עזרה"
```

**Verification:**
- All major features mentioned
- Hebrew and English commands shown
- Examples provided
- Clear and organized

#### 9.1.2 Tasks List Command

**Test Case ID:** TC-CMD-002

**Objective:** Verify task list commands

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "משימות" | Pending tasks list | |
| Question mark | "?" | Same as "משימות" | |
| English | "tasks" | Same result | |
| Natural language | "מה המשימות שלי" | Task list OR AI response + list | |

*Detailed scenarios covered in Section 2.5.1*

#### 9.1.3 Separate Tasks Command

**Test Case ID:** TC-CMD-003

**Objective:** Verify separate task listing (for reactions)

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "פירוט" | Tasks sent as separate messages | |
| Alternative | "משימות נפרד" | Same result | |
| Alternative | "פרט משימות" | Same result | |
| English | "tasks separate" | Same result | |

*Detailed scenarios covered in Section 2.5.2*

#### 9.1.4 Statistics Command

**Test Case ID:** TC-CMD-004

**Objective:** Verify statistics display

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "סטטיסטיקה" | Statistics with counts and percentages | |
| English | "stats" | Same result | |
| Alternative | "statistics" | Same result | |

*Detailed scenarios covered in Section 2.5.6*

#### 9.1.5 Completed Tasks Command

**Test Case ID:** TC-CMD-005

**Objective:** Verify completed tasks display

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "הושלמו" | Last 10 completed tasks | |
| English | "completed" | Same result | |
| Alternative | "done" | Same result | |

*Detailed scenarios covered in Section 2.5.7*

#### 9.1.6 Recurring Patterns Command

**Test Case ID:** TC-CMD-006

**Objective:** Verify recurring patterns display

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "משימות חוזרות" | Active recurring patterns list | |
| Alternative | "משימות קבועות" | Same result | |
| Alternative | "סדרות" | Same result | |
| English | "recurring tasks" | Same result | |

*Detailed scenarios covered in Section 3.3.1*

---

### 9.2 Calendar Commands

#### 9.2.1 Connect Calendar Command

**Test Case ID:** TC-CMD-007

**Objective:** Verify calendar connection initiation

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "חבר יומן" | OAuth URL provided | |
| Alternative | "התחבר ליומן" | Same result | |
| Alternative | "חבר גוגל קלנדר" | Same result | |
| English | "connect calendar" | Same result | |
| English alternative | "link calendar" | Same result | |

**Expected Response:**
```
🔗 **חיבור ליומן Google**

לחבר את היומן שלך:
1. לחץ על הקישור למטה
2. אשר הרשאות
3. חזור לווטסאפ

[OAuth URL]

💡 זה מאפשר סנכרון אוטומטי של משימות ואירועים
```

*Detailed flow covered in Section 4.1.1*

#### 9.2.2 Disconnect Calendar Command

**Test Case ID:** TC-CMD-008

**Objective:** Verify calendar disconnection

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "נתק יומן" | Confirmation + calendar disconnected | |
| Alternative | "התנתק מיומן" | Same result | |
| English | "disconnect calendar" | Same result | |
| English alternative | "unlink calendar" | Same result | |

**Expected Response:**
```
✅ היומן נותק בהצלחה

לחיבור מחדש, כתוב "חבר יומן"
```

*Detailed scenarios in Section 4.1.4*

#### 9.2.3 Calendar Status Command

**Test Case ID:** TC-CMD-009

**Objective:** Verify calendar status check

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "סטטוס יומן" | Connection status + details | |
| Alternative | "מצב יומן" | Same result | |
| English | "calendar status" | Same result | |

**Expected Response (Connected):**
```
✅ **היומן שלך מחובר!**

📅 Calendar ID: primary
🔄 סנכרון אוטומטי: פעיל
🎨 צבע: Blueberry (9)
#️⃣ זיהוי #: מופעל

לשינוי הגדרות: "הגדרות יומן"
```

**Expected Response (Not Connected):**
```
❌ **היומן שלך לא מחובר.**

כדי לחבר את היומן:
כתוב "חבר יומן"

💡 חיבור יומן מאפשר:
• סנכרון משימות ליומן Google
• יצירת משימות מאירועים ביומן
• עדכון דו-כיווני אוטומטי
```

*Detailed scenarios in Section 4.1.6*

#### 9.2.4 Show Calendar Command

**Test Case ID:** TC-CMD-010

**Objective:** Verify calendar/schedule display

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "הצג יומן" | Tasks + Calendar events | |
| Alternative | "יומן" | Same result | |
| Alternative | "לוח שנה" | Same result | |
| English | "show calendar" | Same result | |
| English alternative | "calendar" | Same result | |

*Detailed scenarios in Section 4.5.1*

#### 9.2.5 Calendar Settings Command

**Test Case ID:** TC-CMD-011

**Objective:** Verify calendar settings display

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "הגדרות יומן" | Settings with color, hashtag status | |
| Alternative | "הגדרות קלנדר" | Same result | |
| English | "calendar settings" | Same result | |

*Detailed scenarios in Section 4.4.1*

#### 9.2.6 Set Color Command

**Test Case ID:** TC-CMD-012

**Objective:** Verify color configuration command

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Hebrew | "קבע צבע 9" | Color set to 9 (Blueberry) | |
| Alternative | "שנה צבע 9" | Same result | |
| English | "set color 9" | Same result | |
| Invalid color | "קבע צבע 15" | Error: valid range 1-11 | |

*Detailed scenarios in Section 4.4.2*

#### 9.2.7 Toggle Hashtag Command

**Test Case ID:** TC-CMD-013

**Objective:** Verify hashtag detection toggle

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Disable (Hebrew) | "כבה #" | Hashtag detection disabled | |
| Disable alternative | "כבה סולמית" | Same result | |
| Enable (Hebrew) | "הפעל #" | Hashtag detection enabled | |
| Enable alternative | "הפעל סולמית" | Same result | |
| English disable | "disable #" | Same result | |
| English enable | "enable #" | Same result | |

*Detailed scenarios in Section 4.4.3*

---

### 9.3 Edge Cases - Commands

#### 9.3.1 Case Sensitivity

**Test Case ID:** TC-CMD-014

**Objective:** Verify commands are case-insensitive (for English)

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| UPPERCASE | "HELP" | Help message displayed | |
| Lowercase | "help" | Same result | |
| Mixed case | "HeLp" | Same result | |
| Mixed case | "TaSkS" | Task list displayed | |

#### 9.3.2 Whitespace Handling

**Test Case ID:** TC-CMD-015

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Extra spaces | "משימות   " (trailing spaces) | Command recognized | |
| Leading spaces | "   משימות" | Command recognized | |
| Multiple spaces | "משימות    חוזרות" (double space) | Command recognized | |

#### 9.3.3 Typos in Commands

**Test Case ID:** TC-CMD-016

**Objective:** Verify handling of command typos

**Test Scenarios:**

| Test | Input (with typo) | Expected Result | Pass/Fail |
|------|-------------------|-----------------|-----------|
| Hebrew typo | "משימת" (missing ו) | AI might understand OR "לא הבנתי" | |
| English typo | "taks" instead of "tasks" | AI might understand OR error | |
| Close match | "עזרהה" (extra letter) | Help displayed (fuzzy match) OR error | |

**Note:** AI parsing may handle typos naturally

#### 9.3.4 Unknown Commands

**Test Case ID:** TC-CMD-017

**Test Scenarios:**

| Test | Input Command | Expected Result | Pass/Fail |
|------|---------------|-----------------|-----------|
| Nonsense | "kjsdfhksdjfh" | "לא הבנתי..." + suggestion to send "עזרה" | |
| Random words | "hello world" | AI response OR clarification request | |
| Empty message | "" (empty string) | Error or no response | |
| Only emoji | "😀😀😀" | AI response OR "לא הבנתי" | |

---

## 10. User Experience Flows

### 10.1 New User Onboarding

#### 10.1.1 First Message - Welcome Sequence

**Test Case ID:** TC-UX-001

**Objective:** Verify new user receives welcome message

**Test Scenarios:**

| Step | User Action | Expected Bot Response | Pass/Fail |
|------|-------------|----------------------|-----------|
| 1 | New user sends any message | Welcome message triggered | |
| 2 | Bot responds | Introduction, feature overview, help info | |
| 3 | User follows up | Normal operation begins | |

**Expected Welcome Message:**
```
👋 **ברוך הבא לבוט המשימות!**

אני כאן לעזור לך לנהל את המשימות שלך בצורה חכמה ויעילה.

🎯 **מה אני יכול לעשות:**
• ניהול משימות עם תזכורות אוטומטיות
• משימות חוזרות (יומי, שבועי, חודשי)
• סנכרון עם Google Calendar
• תמיכה בהודעות קוליות
• שאילתות בשפה טבעית

💡 **דוגמאות לשימוש:**
• "תזכיר לי לקנות חלב מחר ב-15:00"
• "מה המשימות שלי להיום"
• "כל יום ב-9 תזכיר לי לקחת ויטמינים"

לעזרה מלאה, שלח "עזרה"

בואו נתחיל! מה תרצה לעשות? 🚀
```

**Verification:**
- Triggered only on first message
- User record created in database
- `phone_number` encrypted and stored
- Subsequent messages don't trigger welcome

#### 10.1.2 Help Information Provided

**Test Case ID:** TC-UX-002

**Objective:** Verify help is easily accessible for new users

**Test Scenarios:**

| Test | User Action | Expected Result | Pass/Fail |
|------|-------------|-----------------|-----------|
| Send "עזרה" immediately | After welcome, send "עזרה" | Full help displayed | |
| Natural question | "איך עובד הבוט?" | AI explains + help info | |
| Unknown command | "random text" | "לא הבנתי" + suggestion to send "עזרה" | |

#### 10.1.3 Example Usage Shown

**Test Case ID:** TC-UX-003

**Objective:** Verify new users see clear examples

**Verification:**
- Welcome message includes 3-5 clear examples
- Examples in Hebrew (primary language)
- Examples cover common use cases
- Examples encourage first interaction

---

### 10.2 Daily Usage Flow

#### 10.2.1 Morning: Create Tasks

**Test Case ID:** TC-UX-004

**Objective:** Verify typical morning task creation flow

**Scenario:**
User wakes up, plans day by creating tasks

**Flow Steps:**

| Step | User Action | Bot Response | Expected State | Pass/Fail |
|------|-------------|--------------|----------------|-----------|
| 1 | "תזכיר לי לקנות חלב ב-10" | ✅ Task created | 1 task pending | |
| 2 | "פגישה עם רופא מחר ב-14:00" | ✅ Task created, calendar synced | 2 tasks pending | |
| 3 | Voice: "להתקשר לבנק היום ב-3" | Transcription + ✅ Task created | 3 tasks pending | |
| 4 | "מה המשימות שלי להיום" | Shows tasks due today | Sees 2 of 3 | |

**Verification:**
- All tasks created successfully
- Due dates parsed correctly
- Calendar events created (if connected)
- User can review tasks easily

#### 10.2.2 Midday: Check Tasks, Complete Some

**Test Case ID:** TC-UX-005

**Objective:** Verify typical midday task management flow

**Scenario:**
User receives reminder, completes task, checks remaining

**Flow Steps:**

| Step | Time/Action | Bot Response | Expected State | Pass/Fail |
|------|-------------|--------------|----------------|-----------|
| 1 | 09:30 (30 min before 10:00 task) | ⏰ Reminder for "לקנות חלב" | Reminder received | |
| 2 | User completes shopping | (external action) | No change yet | |
| 3 | "סיימתי לקנות חלב" | ✅ Completed message | 2 tasks remaining | |
| 4 | "משימות" | Shows 2 remaining tasks | Verifies progress | |
| 5 | 11:00 | Daily proactive reminder | Sees remaining tasks | |

**Verification:**
- Reminder delivered on time
- Completion recognized instantly
- Task removed from pending list
- Progress visible

#### 10.2.3 Evening: Review Remaining Tasks

**Test Case ID:** TC-UX-006

**Objective:** Verify typical evening review flow

**Scenario:**
User reviews day's accomplishments and plans tomorrow

**Flow Steps:**

| Step | User Action | Bot Response | Expected State | Pass/Fail |
|------|-------------|--------------|----------------|-----------|
| 1 | 19:00 | Daily proactive reminder | Remaining tasks shown | |
| 2 | "סטטיסטיקה" | Shows completed/pending counts | Reviews progress | |
| 3 | "הושלמו" | Shows completed tasks today | Sees accomplishments | |
| 4 | "דחה משימה 1 למחר" | ✅ Task rescheduled | 1 task moved to tomorrow | |
| 5 | "תזכיר לי מחר ב-9 לקרוא דואר" | ✅ New task for tomorrow | Planning ahead | |

**Verification:**
- Evening reminder received
- Statistics show accurate counts
- Rescheduling works smoothly
- Planning for next day seamless

#### 10.2.4 Reminders Received Throughout Day

**Test Case ID:** TC-UX-007

**Objective:** Verify reminders enhance daily workflow

**Scenario:**
User receives various reminders during the day

**Timeline:**

| Time | Event | User Experience | Pass/Fail |
|------|-------|-----------------|-----------|
| 09:00 | Daily summary | "📋 סיכום יומי..." (5 tasks today) | |
| 09:30 | Task-specific reminder | "⏰ תזכורת: לקנות חלב (10:00)" | |
| 11:00 | Daily proactive reminder | "⏰ תזכורת יומית! יש לך 5 משימות..." | |
| 13:30 | Task-specific reminder | "⏰ תזכורת: פגישה עם רופא (14:00)" | |
| 15:00 | Daily proactive reminder | "⏰ תזכורת יומית! יש לך 3 משימות..." | |
| 19:00 | Daily proactive reminder | "⏰ תזכורת יומית! יש לך 2 משימות..." | |

**Verification:**
- All reminders delivered on time
- Messages not intrusive
- Help user stay on track
- Can be acted upon immediately

---

### 10.3 Calendar Integration Flow

#### 10.3.1 Full Calendar Integration Journey

**Test Case ID:** TC-UX-008

**Objective:** Verify complete calendar integration experience

**Flow Steps:**

| Step | User Action | Bot Response / Result | Pass/Fail |
|------|-------------|----------------------|-----------|
| 1 | "חבר יומן" | OAuth URL provided | |
| 2 | Click URL, authorize | Redirected to success page | |
| 3 | Return to WhatsApp | "✅ היומן חובר בהצלחה!" | |
| 4 | "תזכיר לי לקנות חלב מחר ב-15:00" | Task created + event in Google Calendar | |
| 5 | Open Google Calendar | Verify event exists | |
| 6 | Create event in Google Calendar (with configured color) | Bot creates task within 10 min | |
| 7 | "משימות" | Shows both tasks (bot-created + calendar-created) | |
| 8 | "סיימתי לקנות חלב" | Task completed + event marked ✅ | |
| 9 | Update event in Google Calendar | Task updated in bot | |
| 10 | "סטטוס יומן" | Shows connected status with sync details | |

**Verification:**
- OAuth flow smooth and clear
- Two-way sync works reliably
- Deduplication prevents duplicates
- User sees unified experience

#### 10.3.2 Create Tasks (Sync to Calendar)

**Test Case ID:** TC-UX-009

**Prerequisites:** Calendar connected

**Test Scenarios:**

| Test | User Action | Expected Calendar Result | Pass/Fail |
|------|-------------|--------------------------|-----------|
| Create with date | "פגישה מחר ב-14:00" | Event appears in calendar within seconds | |
| Create without date | "לקנות חלב" | No event created (no date) | |
| Complete task | "סיימתי פגישה" | Event marked ✅ (gray, prefix) | |
| Delete task | "מחק פגישה" | Event removed from calendar | |

#### 10.3.3 Create Events in Calendar (Sync to Bot)

**Test Case ID:** TC-UX-010

**Prerequisites:** Calendar connected, color 9 configured

**Test Scenarios:**

| Test | Calendar Action | Expected Bot Result | Pass/Fail |
|------|-----------------|---------------------|-----------|
| Create event with color 9 | Create "Meeting" with Blueberry color | Task "Meeting" appears in bot within 10 min | |
| Create event with # | Create "# Buy milk" | Task "Buy milk" appears in bot | |
| Update event title | Edit "Meeting" to "Important Meeting" | Task updated in bot | |
| Delete event | Delete event from calendar | Task deleted from bot | |

#### 10.3.4 Modify Both Sides

**Test Case ID:** TC-UX-011

**Objective:** Verify conflict resolution (last write wins)

**Flow:**

| Step | Action Location | Action | Expected Result | Pass/Fail |
|------|-----------------|--------|-----------------|-----------|
| 1 | Bot | Create task "Meeting tomorrow 14:00" | Event created | |
| 2 | Calendar | Change time to 15:00 | Bot updates task to 15:00 (next sync) | |
| 3 | Bot | Change description to "Important Meeting" | Event title updated | |
| 4 | Calendar & Bot simultaneously | Edit both before sync | Last modification wins | |

#### 10.3.5 Verify Consistency

**Test Case ID:** TC-UX-012

**Objective:** Verify data consistency across bot and calendar

**Verification Steps:**

| Step | Action | Expected Result | Pass/Fail |
|------|--------|-----------------|-----------|
| 1 | Create 5 tasks in bot (with dates) | 5 events in calendar | |
| 2 | Complete 2 tasks in bot | 2 events marked ✅ | |
| 3 | Create 3 events in calendar (with color) | 3 tasks in bot | |
| 4 | Send "הצג יומן" | All 8 items shown (no duplicates) | |
| 5 | Verify deduplication | Linked events not in "events" section | |

---

### 10.4 Recurring Task Flow

#### 10.4.1 Complete Recurring Workflow

**Test Case ID:** TC-UX-013

**Objective:** Verify end-to-end recurring task experience

**Flow Steps:**

| Step | User Action | Bot Response | Expected State | Pass/Fail |
|------|-------------|--------------|----------------|-----------|
| 1 | "כל יום ב-9 תזכיר לי לקחת ויטמינים" | ✅ Pattern created | Pattern active, instance for today (if <9am) | |
| 2 | "משימות חוזרות" | Shows pattern with details | Pattern visible | |
| 3 | Wait until midnight | (automatic) | New instance generated | |
| 4 | "משימות" | Shows today's instance with 🔄 | Instance appears | |
| 5 | "סיימתי לקחת ויטמינים" | ✅ Completed (with 🔄 message) | Instance completed | |
| 6 | Wait until next day | (automatic) | New instance generated again | |
| 7 | "משימות חוזרות" | Pattern still active | Pattern continues | |

**Verification:**
- Pattern creation intuitive
- Instances generate automatically
- Completion doesn't stop pattern
- Clear indicators (🔄) throughout

#### 10.4.2 Modify Pattern

**Test Case ID:** TC-UX-014

**Objective:** Verify pattern modification flow

**Flow:**

| Step | User Action | Bot Response | Expected Result | Pass/Fail |
|------|-------------|--------------|----------------|-----------|
| 1 | List patterns: "משימות חוזרות" | Shows pattern #1: "לקחת ויטמינים" | Pattern ID noted | |
| 2 | "שנה משימה [pattern ID] לקחת ויטמינים ואומגה 3" | ✅ Pattern updated | Description changed | |
| 3 | "דחה משימה [pattern ID] ל-10:00" | ✅ Pattern time updated | Time changed to 10:00 | |
| 4 | "משימות חוזרות" | Shows updated pattern | Changes reflected | |
| 5 | Wait for next instance | (automatic) | New instance has updates | |

#### 10.4.3 Stop Series

**Test Case ID:** TC-UX-015

**Objective:** Verify stopping recurring series

**Flow:**

| Step | User Action | Bot Response | Expected State | Pass/Fail |
|------|-------------|--------------|----------------|-----------|
| 1 | "משימות חוזרות" | Shows active patterns | Note pattern number | |
| 2 | "עצור סדרה 1" | ✅ Series stopped | Pattern status = cancelled | |
| 3 | "משימות חוזרות" | Pattern no longer shown | Confirmed stopped | |
| 4 | Wait until next day | (automatic) | No new instance generated | |

---

## 11. Error Handling & Edge Cases

### 11.1 Input Validation

#### 11.1.1 Empty Messages

**Test Case ID:** TC-ERR-001

**Test Scenarios:**

| Test | Input | Expected Result | Pass/Fail |
|------|-------|-----------------|-----------|
| Truly empty | "" (zero characters) | Ignored OR error message | |
| Only whitespace | "   " (only spaces) | Ignored OR error message | |
| Only newlines | "\n\n\n" | Ignored OR error message | |

#### 11.1.2 Very Long Messages

**Test Case ID:** TC-ERR-002

**Test Scenarios:**

| Test | Input Length | Expected Result | Pass/Fail |
|------|--------------|-----------------|-----------|
| 500 characters | 500-char message | Processed normally OR truncated | |
| 1000 characters | 1000-char message | Processed OR "message too long" error | |
| 5000 characters | 5000-char message | Truncated OR rejected | |
| 10000+ characters | Extremely long | Rejected with error message | |

**Verification:**
- System doesn't crash
- Database handles within column limits
- User receives feedback if truncated

#### 11.1.3 Invalid Commands

**Test Case ID:** TC-ERR-003

**Test Scenarios:**

| Test | Input | Expected Result | Pass/Fail |
|------|-------|-----------------|-----------|
| Gibberish | "asdjkfhasjkdfh" | "לא הבנתי..." + help suggestion | |
| Numbers only | "123456789" | Interpreted as context OR "לא הבנתי" | |
| Special chars only | "!@#$%^&*()" | "לא הבנתי" | |
| Mixed nonsense | "123 !@# abc" | Error or AI attempts understanding | |

#### 11.1.4 Malformed Dates

**Test Case ID:** TC-ERR-004

**Test Scenarios:**

| Test | Input | Expected Result | Pass/Fail |
|------|-------|-----------------|-----------|
| Invalid day | "פגישה 32/10" | Task created without date OR error | |
| Invalid month | "פגישה 31/13" | Task created without date OR error | |
| Nonsense date | "פגישה blah/blah" | Task created without date | |
| Ambiguous date | "פגישה 2/3" (Feb 3 or Mar 2?) | Parsed based on locale (DD/MM in Israel) | |

#### 11.1.5 SQL Injection Attempts

**Test Case ID:** TC-ERR-005

**Objective:** Verify SQL injection protection

**Test Scenarios:**

| Test | Malicious Input | Expected Result | Pass/Fail |
|------|-----------------|-----------------|-----------|
| Basic injection | "' OR '1'='1" | Treated as literal string, no SQL executed | |
| UNION attack | "task'; DROP TABLE tasks;--" | Treated as task description, no SQL executed | |
| Comment injection | "task'--" | Treated as literal string | |
| Batch injection | "task'; DELETE FROM users;--" | Treated as literal string | |

**Verification:**
- SQLAlchemy ORM used (parameterized queries)
- No raw SQL execution with user input
- Database tables intact after test
- No data leaked or deleted

#### 11.1.6 XSS Attempts

**Test Case ID:** TC-ERR-006

**Objective:** Verify XSS protection (if web interface exists)

**Test Scenarios:**

| Test | Malicious Input | Expected Result | Pass/Fail |
|------|-----------------|-----------------|-----------|
| Script tag | "<script>alert('XSS')</script>" | Escaped/sanitized, no execution | |
| Image tag | "<img src=x onerror=alert('XSS')>" | Escaped/sanitized | |
| Event handler | "<div onclick='alert(\"XSS\")'>click</div>" | Escaped/sanitized | |

**Note:** Primary interface is WhatsApp (text), but if web dashboard exists, test there

---

### 11.2 Rate Limiting

#### 11.2.1 Per-Minute Limits

**Test Case ID:** TC-ERR-007

**Objective:** Verify per-minute rate limiting

**Test Scenarios:**

| Test | Actions | Expected Result | Pass/Fail |
|------|---------|-----------------|-----------|
| 10 messages in 1 min | Send 10 messages in 60 seconds | All processed | |
| 15 messages in 1 min | Send 15 messages rapidly | All processed OR rate limit warning after 10 | |
| 20 messages in 1 min | Spam 20 messages | Rate limit error after threshold | |

**Expected Rate Limit Message:**
```
⚠️ שלחת יותר מדי הודעות.
נסה שוב בעוד כמה שניות.
```

**Verification:**
- Redis tracks message count per user
- Counter resets after 1 minute
- Legitimate users rarely hit limit

#### 11.2.2 Per-Hour Limits

**Test Case ID:** TC-ERR-008

**Objective:** Verify per-hour rate limiting

**Test Scenarios:**

| Test | Actions | Expected Result | Pass/Fail |
|------|---------|-----------------|-----------|
| 100 messages in 1 hour | Distributed messages | All processed | |
| 200 messages in 1 hour | Rapid messaging | Rate limit after threshold (e.g., 150) | |

#### 11.2.3 Per-Day Limits

**Test Case ID:** TC-ERR-009

**Objective:** Verify per-day rate limiting

**Test Scenarios:**

| Test | Actions | Expected Result | Pass/Fail |
|------|---------|-----------------|-----------|
| 500 messages in 1 day | Normal usage | All processed | |
| 1000+ messages in 1 day | Excessive use | Rate limit warning/block | |

#### 11.2.4 Rate Limit Messages

**Test Case ID:** TC-ERR-010

**Objective:** Verify rate limit communication

**Expected Behavior:**
- Clear message explaining rate limit
- Time until reset shown
- User not blocked permanently

**Test Scenarios:**

| Test | Trigger | Expected Message | Pass/Fail |
|------|---------|------------------|-----------|
| Hit minute limit | 20 msgs/min | "⚠️ שלחת יותר מדי הודעות. נסה שוב בעוד X שניות." | |
| Hit hour limit | 200 msgs/hour | "⚠️ הגעת למגבלת ההודעות לשעה. נסה שוב בעוד X דקות." | |
| Hit day limit | 1000 msgs/day | "⚠️ הגעת למגבלה היומית. נסה שוב מחר." | |

---

### 11.3 Service Failures

#### 11.3.1 AI Service Down (Circuit Breaker)

**Test Case ID:** TC-ERR-011

**Objective:** Verify circuit breaker activates on AI failures

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| Single AI failure | Gemini API returns error | Retry 3 times, then error message | |
| Multiple failures | 5 consecutive failures | Circuit breaker opens | |
| Circuit breaker open | AI unavailable | Immediate error, no API calls | |
| Circuit breaker half-open | After cooldown period | Test call attempted | |
| Service recovered | Test call succeeds | Circuit breaker closes, normal operation | |

**Expected Error Message:**
```
⚠️ המערכת חווה בעיה זמנית.
נסה שוב בעוד מספר דקות.

💡 בינתיים, אפשר להשתמש בפקודות ישירות:
• "משימות" - הצג משימות
• "סטטיסטיקה" - נתונים
• "סטטוס יומן" - מצב יומן
```

**Verification:**
- Circuit breaker prevents cascade failures
- Users receive helpful error message
- System recovers automatically
- Alternative commands available

#### 11.3.2 WhatsApp API Failure

**Test Case ID:** TC-ERR-012

**Objective:** Verify handling of WhatsApp API failures

**Test Scenarios:**

| Test | Failure Type | Expected Behavior | Pass/Fail |
|------|--------------|-------------------|-----------|
| Send message fails | whatsapp_service.send_message() errors | Error logged, operation continues | |
| Webhook down | Incoming messages not received | Messages queued, processed when up | |
| Media download fails | Voice message download fails | Error message to user | |
| Authentication error | Invalid API token | Error logged, admin notified | |

**Verification:**
- System doesn't crash
- Errors logged for debugging
- User notified when their action fails
- Automatic retry for transient errors

#### 11.3.3 Database Connection Issues

**Test Case ID:** TC-ERR-013

**Objective:** Verify database failure handling

**Test Scenarios:**

| Test | Failure Type | Expected Behavior | Pass/Fail |
|------|--------------|-------------------|-----------|
| Connection timeout | DB unreachable | Error logged, user notified | |
| Query timeout | Slow query times out | Error logged, operation aborted | |
| Transaction rollback | Constraint violation | Rollback, error message | |
| Connection pool exhausted | All connections busy | Wait and retry OR error | |

**Expected Error Message:**
```
⚠️ אופס! משהו השתבש.
נסה שוב בעוד רגע.

אם הבעיה נמשכת, פנה לתמיכה.
```

#### 11.3.4 Calendar API Failures

**Test Case ID:** TC-ERR-014

**Objective:** Verify graceful Calendar API error handling

**Test Scenarios:**

| Test | Failure Type | Expected Behavior | Pass/Fail |
|------|--------------|-------------------|-----------|
| API quota exceeded | Daily quota hit | Task created, sync marked failed, retried later | |
| Network timeout | API call times out | Task created, sync error logged | |
| 401 Unauthorized | Token invalid/revoked | Calendar auto-disconnected, user notified | |
| 403 Forbidden | Permissions insufficient | Calendar auto-disconnected | |
| 404 Not Found | Event deleted externally | Sync skips, no error | |
| 500 Server Error | Google Calendar down | Retry with exponential backoff | |

**User Notification (on disconnect):**
```
⚠️ החיבור ליומן Google נפסק

הסיבה: [reason]

כדי לחדש את החיבור:
כתוב 'חבר יומן'

💡 המשימות שלך בבוט לא נפגעו.
```

**Verification:**
- Task operations never fail due to calendar
- Calendar sync is non-fatal
- Errors logged for debugging
- Automatic recovery attempts
- User notified if action needed

#### 11.3.5 Token Expiry/Revocation

**Test Case ID:** TC-ERR-015

**Objective:** Verify OAuth token lifecycle management

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| Token expires | Access token expired | Auto-refresh using refresh token | |
| Refresh token expires | Refresh token invalid | Calendar disconnected, user notified | |
| User revokes access | Permissions revoked in Google | Next API call fails → auto-disconnect + notify | |
| Token refresh during operation | Token expires mid-operation | Refresh, retry operation | |

---

### 11.4 Data Consistency

#### 11.4.1 Duplicate Message Handling (Idempotency)

**Test Case ID:** TC-ERR-016

**Objective:** Verify messages processed only once

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|---------|-------------------|-----------|
| Duplicate webhook | WhatsApp sends same message twice | Processed once (idempotency check) | |
| Same message_id | message_id already in database | Skip processing | |
| Retry after failure | Message failed, WhatsApp retries | Processed only once | |

**Verification:**
- `Message` table has unique constraint on `whatsapp_message_id`
- Check for existing message before processing
- Database prevents duplicates
- User sees response only once

#### 11.4.2 Concurrent Task Operations

**Test Case ID:** TC-ERR-017

**Objective:** Verify concurrent operations don't corrupt data

**Test Scenarios:**

| Test | Concurrent Actions | Expected Result | Pass/Fail |
|------|-------------------|-----------------|-----------|
| Complete same task twice | User sends 2 "סיימתי משימה 1" messages | Task completed once | |
| Delete + complete | Delete and complete task simultaneously | One succeeds, other errors gracefully | |
| Update + reschedule | Update description + reschedule simultaneously | Both changes applied OR last write wins | |

**Verification:**
- Database transactions used correctly
- Row-level locking where needed
- No lost updates
- Consistent final state

#### 11.4.3 Calendar Sync Conflicts

**Test Case ID:** TC-ERR-018

**Objective:** Verify conflict resolution in calendar sync

**Test Scenarios:**

| Test | Conflict Type | Resolution | Pass/Fail |
|------|---------------|------------|-----------|
| Both sides updated | Task and event modified before sync | Last modified timestamp wins | |
| Delete vs. update | Task deleted in bot, event updated in calendar | Task recreated OR stays deleted (last write) | |
| Create race | Task created, calendar event created, sync runs | Deduplication prevents duplicate | |

**Mechanism:**
- Compare `last_modified_at` vs `calendar_last_modified`
- Apply most recent change
- No merge conflicts
- Predictable behavior

#### 11.4.4 Race Conditions in Recurring Generation

**Test Case ID:** TC-ERR-019

**Objective:** Verify recurring instance generation is atomic

**Test Scenarios:**

| Test | Scenario | Expected Behavior | Pass/Fail |
|------|----------|-------------------|-----------|
| Midnight generation | Scheduler runs exactly at 00:00 | Each pattern generates 1 instance | |
| Multiple workers | 2 workers run simultaneously | No duplicate instances (DB constraint) | |
| Manual + automatic generation | User creates + scheduler runs | No duplicates | |

**Verification:**
- Unique constraint on (parent_recurring_id, due_date)
- Atomic transactions
- Idempotent generation logic

---


