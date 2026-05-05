# Privacy Policy

**Application Name:** WhatsApp Todo Bot  
**Developer / Data Controller:** Or Kurtz  
**Contact:** [orkurtz@gmail.com](mailto:orkurtz@gmail.com)  
**Last Updated:** May 5, 2026  
**Effective Date:** May 5, 2026

---

## 1. Overview

WhatsApp Todo Bot ("the Bot", "we", "us") is a personal productivity assistant that helps users manage tasks through WhatsApp and optionally sync those tasks to their own Google Calendar. This Privacy Policy explains what data we collect, how we use it, and the rights you have over your information.

We are committed to transparency. We collect the minimum data necessary to operate the Bot and never use it for advertising, profiling, or any purpose beyond the functionality described below.

---

## 2. Scope of This Policy

This policy applies to all users of the WhatsApp Todo Bot, including:

- Users who interact with the Bot via WhatsApp text and voice messages.
- Users who optionally connect their Google Calendar account.

---

## 3. Data We Collect

### 3.1 WhatsApp Interaction Data

When you use the Bot we receive and store:

| Data | Purpose | Retention |
|---|---|---|
| **Phone number** (hashed + encrypted) | Identify your account; route messages back to you | Until you delete your account |
| **Message content** (task descriptions, voice transcripts) | Create and manage your tasks | Until you delete the task or account |
| **Task metadata** (due date, status, recurrence pattern) | Remind you and sync to calendar | Until you delete the task or account |

Your phone number is **never stored in plain text**. We store a one-way cryptographic hash (HMAC-SHA256) for lookups and an AES-256-encrypted copy for outbound messaging.

### 3.2 Google Calendar OAuth Data

If you choose to connect Google Calendar (the feature is entirely optional), we store:

| Data | Purpose | Retention |
|---|---|---|
| **OAuth access token** | Create and update calendar events on your behalf | Until you disconnect the calendar or delete your account |
| **OAuth refresh token** | Silently refresh the access token so you stay connected without re-authorizing | Until you disconnect the calendar or delete your account |
| **Google account email** (optional, if returned by Google) | Display in the calendar status command | Until you disconnect the calendar |

**All OAuth tokens are encrypted at rest using AES-256.**

We do **not** store calendar events in our database. Events are fetched on demand and discarded after each sync cycle.

---

## 4. Google Calendar Scopes and How We Use Them

We request the following Google OAuth 2.0 scopes:

| Scope | Why We Need It |
|---|---|
| `https://www.googleapis.com/auth/calendar.events` | Create calendar events for tasks you add to the Bot; update those events when you reschedule or complete tasks; delete events when you delete tasks |
| `https://www.googleapis.com/auth/calendar` | Read your calendar's time zone settings; list events in the optional two-way sync feature so calendar events you create can become Bot tasks |

**We request nothing beyond these two scopes.**

We use these scopes exclusively to:
- Create a calendar event when you add a task with a due date.
- Update or delete that event when you change or complete the task.
- Optionally read events you create in Google Calendar so they can appear as Bot tasks (two-way sync, configurable by you).

We do **not**:
- Read, modify, or delete calendar events that were not created by the Bot (except for reading purposes in two-way sync, which is user-configurable and can be disabled).
- Share your calendar data with any third party.
- Use calendar data to train machine learning models.
- Store individual calendar event details in our database beyond the Google event ID (used for linking to the corresponding Bot task).

---

## 5. Data We Do NOT Collect

- We do **not** collect your real name, email address (unless returned as part of Google OAuth), or any demographic information.
- We do **not** read WhatsApp messages from other contacts or chats — we only receive messages sent directly to the Bot's phone number via the WhatsApp Business API.
- We do **not** track your location.
- We do **not** use cookies or web tracking technologies.
- We do **not** build user profiles for advertising purposes.

---

## 6. How We Process Your Data

All data processing takes place on our application server hosted on [Railway](https://railway.app). The processing pipeline is:

1. **Receive** an incoming WhatsApp message via Meta's WhatsApp Business Cloud API.
2. **Validate and sanitize** the input (XSS protection, prompt-injection detection).
3. **Parse** the message using the Google Gemini 2.5 Flash AI model to extract task intent, description, and date.
4. **Store** the resulting task in a PostgreSQL database with encryption at rest.
5. **Optionally sync** the task to Google Calendar if you have connected your calendar.
6. **Respond** to you via the WhatsApp Business API.

Voice messages are transcribed using Google Gemini's multimodal API. The audio file is downloaded temporarily for processing and is **not** persistently stored by us.

---

## 7. Third-Party Services

We share data with the following third-party services solely to operate the Bot:

| Service | Data Shared | Purpose | Privacy Policy |
|---|---|---|---|
| **Meta (WhatsApp Business API)** | Phone number, message content | Deliver messages to and from users | [Meta Privacy Policy](https://www.facebook.com/privacy/policy/) |
| **Google Gemini AI** | Message text / audio for transcription | AI parsing of task intent | [Google Privacy Policy](https://policies.google.com/privacy) |
| **Google Calendar API** | Task description, due date, completion status | Create and sync calendar events | [Google Privacy Policy](https://policies.google.com/privacy) |
| **Railway (hosting)** | Encrypted database and application logs | Host the application and database | [Railway Privacy Policy](https://railway.app/legal/privacy) |

We do not sell your data to any third party. We do not share your data beyond what is required to operate the services listed above.

---

## 8. Data Security

We apply the following technical safeguards:

- **AES-256 encryption at rest** for all sensitive fields: phone numbers, task descriptions, and Google OAuth tokens.
- **HMAC-SHA256 hashing** for phone number lookups, so the database contains no recoverable plain-text identifiers.
- **HTTPS / TLS in transit** for all API communications.
- **Input validation** to prevent injection attacks.
- **Rate limiting** to protect against abuse.

No method of electronic storage or transmission is 100% secure. We take reasonable measures to protect your information, but we cannot guarantee absolute security.

---

## 9. Data Retention

| Data Category | Retention Period |
|---|---|
| User account and tasks | Until you send `"מחק חשבון"` / `"delete account"` to the Bot, or upon request via email |
| Completed tasks | 90 days after completion, then automatically purged |
| Google OAuth tokens | Until you send `"נתק יומן"` / `"disconnect calendar"` to the Bot, or upon account deletion |
| Application logs | 30 days, then automatically rotated |

---

## 10. Your Rights

You have the right to:

- **Access** the data we hold about you — contact us at [orkurtz@gmail.com](mailto:orkurtz@gmail.com).
- **Delete** your account and all associated data — send `"מחק חשבון"` to the Bot or email us.
- **Disconnect** Google Calendar at any time — send `"נתק יומן"` to the Bot; all stored tokens are immediately and permanently deleted.
- **Withdraw consent** at any time by stopping use of the Bot. Because the Bot has no standing subscription, simply not sending messages effectively ends data collection.

If you are located in the European Economic Area (EEA), you also have rights under the General Data Protection Regulation (GDPR), including the right to data portability, the right to restrict processing, and the right to lodge a complaint with a supervisory authority.

---

## 11. Children's Privacy

The Bot is not directed at children under the age of 13. We do not knowingly collect personal information from children under 13. If you believe a child has used the Bot, please contact us so we can delete the relevant data.

---

## 12. Changes to This Policy

We may update this Privacy Policy from time to time. When we do, we will revise the "Last Updated" date at the top of this page. For material changes, we will send a notification via the Bot. Continued use of the Bot after changes are posted constitutes acceptance of the updated policy.

---

## 13. Contact Us

If you have any questions, concerns, or requests regarding this Privacy Policy or your personal data, please contact:

**Or Kurtz**  
Email: [orkurtz@gmail.com](mailto:orkurtz@gmail.com)  
GitHub: [https://github.com/orkurtz/Todobot](https://github.com/orkurtz/Todobot)

---

*This Privacy Policy was written to meet Google's OAuth API verification requirements and to comply with applicable data protection laws.*
