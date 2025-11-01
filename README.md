# 🤖 WhatsApp Todo Bot

<div align="center">
  <h1>WhatsApp Todo Bot - Or Kurtz version</h1>
  <p><strong>An intelligent AI-powered personal assistant for task management through WhatsApp</strong></p>
  
  <p>The bot understands natural language (Hebrew & English), extracts tasks from text and voice messages, manages recurring tasks, and provides smart reminders - all optimized for Israeli users.</p>

  <p>
    <a href="#-credits--project-evolution"><strong>Credits</strong></a> •
    <a href="#-what-is-this"><strong>About</strong></a> •
    <a href="#-features"><strong>Features</strong></a> •
    <a href="#-how-it-works"><strong>How It Works</strong></a> •
    <a href="#-quick-start"><strong>Quick Start</strong></a> •
    <a href="#-usage-examples"><strong>Examples</strong></a> •
    <a href="#-deployment"><strong>Deploy</strong></a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python" alt="Python">
    <img src="https://img.shields.io/badge/Flask-Framework-green?style=for-the-badge&logo=flask" alt="Flask">
    <img src="https://img.shields.io/badge/WhatsApp-Business%20API-25D366?style=for-the-badge&logo=whatsapp" alt="WhatsApp">
    <img src="https://img.shields.io/badge/AI-Google%20Gemini%202.5%20Flash-4285F4?style=for-the-badge&logo=google" alt="Google Gemini">
    <img src="https://img.shields.io/badge/PostgreSQL-Database-336791?style=for-the-badge&logo=postgresql" alt="PostgreSQL">
  </p>
  
</div>

---

## 🙏 Credits & Project Evolution

### Original Creator

This project was originally created by **[buzaglo idan](https://github.com/buzagloidan)**. We extend our sincere gratitude for the foundational work that made this enhanced version possible.

**Original Project:** [https://github.com/buzagloidan/Todobot](https://github.com/buzagloidan/Todobot)

### This Enhanced Version

This repository represents a **complete refactor and significant enhancement** of the original project. While maintaining the core vision, we've added extensive features and improvements:

#### 🆕 Major New Features
- **🔄 Complete Recurring Tasks System**: Full support for daily, weekly, interval, and custom recurring patterns with automatic instance generation
- **🎤 Voice Message Support**: Complete voice transcription and task extraction using Gemini 2.5 Flash multimodal API
- **👍 Emoji Reaction Completion**: Intuitive task completion via WhatsApp emoji reactions
- **🔔 Enhanced Reminder System**: 
  - 30-minute advance warnings before due time
  - 3x daily proactive reminders (11 AM, 3 PM, 7 PM)
  - Smart daily summaries at 9 AM
  - Status validation to prevent reminders for completed tasks

#### 🔧 Code Improvements
- **Complete Architecture Refactoring**: Restructured codebase for maintainability and scalability
- **Enhanced Security**: 
  - Comprehensive input validation and sanitization
  - Prompt injection detection and prevention
  - XSS protection
  - Enhanced rate limiting

#### 📈 Production Enhancements
- Redis-backed rate limiting with in-memory fallback
- Circuit breaker pattern for automatic API failure recovery
- Comprehensive error logging and monitoring with alerts
- Database transaction safety improvements
- Proper timezone handling (Israel timezone throughout the application)
- Worker process separation for scheduler reliability

---

## 📖 What is This?

**WhatsApp Todo Bot** is an AI-powered task management assistant that lives entirely within WhatsApp. Instead of downloading a separate app, users simply send messages (text or voice) to manage their tasks through natural conversation.

### The Problem It Solves

Traditional task management apps require:
- Downloading and installing an app
- Learning a new interface
- Remembering complex commands
- Switching between apps

**Our solution:** Manage tasks directly in WhatsApp using natural language - just like texting a friend.

### How It's Different

- **No App Installation**: Works entirely through WhatsApp
- **Natural Language**: "לקנות חלב מחר ב-15:00" creates a task automatically
- **Voice Support**: Send voice messages - the bot transcribes and understands
- **Hebrew Optimized**: Built specifically for Hebrew speakers with Israeli timezone
- **Smart Reminders**: Proactive nudges and automatic task reminders
- **Recurring Tasks**: "תזכיר לי כל יום ב-9 לקחת ויטמינים" - fully automated
- **Encrypted & Private**: All data encrypted at rest (AES-256)

---

## ✨ Features

### 🎯 Core Task Management

#### Create Tasks
- **Natural Language**: "להתקשר לאמא מחר ב-15:00" → Task created automatically
- **Text Messages**: Full support for Hebrew and English
- **Voice Messages**: 🎤 Speak naturally - bot transcribes and extracts tasks
- **Flexible Dates**: Supports relative ("בעוד שעה") and absolute ("31/10 בשעה 14:30") dates

#### Update & Manage Tasks
- **Update Description**: "שנה משימה 2 להתקשר לרופא"
- **Reschedule**: "דחה משימה 1 למחר" or "העבר משימה 3 בעוד שעתיים"
- **Complete Tasks**: 
  - Text: "סיימתי משימה 2"
  - Emoji: React with 👍 to task messages
- **Delete Tasks**: "מחק משימה 3"
- **Query Tasks**: "מתי הפגישה עם יוחנן?" or "כמה משימות יש לי?"

### 🔄 Recurring Tasks (Advanced Feature)

Create tasks that automatically repeat on a schedule:

#### Recurring Patterns Supported

1. **Daily Tasks**
   - `"תזכיר לי כל יום ב-9 לקחת ויטמינים"` → Every day at 9 AM
   - `"every day at 9am take vitamins"` → Same in English

2. **Weekly Tasks**
   - `"כל שבוע פגישה עם המנהל"` → Every week on the same day
   - `"every Monday meeting with manager"` → Weekly on Monday

3. **Specific Days of Week**
   - `"כל יום שני ורביעי ב-10 להתקשר"` → Monday & Wednesday at 10 AM
   - `"every Monday and Wednesday call mom"` → Multiple days

4. **Interval Tasks**
   - `"כל יומיים להשקות צמחים"` → Every 2 days
   - `"every 3 days water plants"` → Custom intervals

#### Recurring Task Management

- **View Active Patterns**: `"משימות חוזרות"` → Shows all active recurring series
- **Stop Series**: `"עצור סדרה 5"` → Cancels pattern, optionally deletes future instances
- **Complete Series**: `"השלם סדרה 3"` → Marks entire series as done
- **Update Patterns**: Change description, schedule, or end date

#### How Recurring Tasks Work

1. **You create a pattern**: "תזכיר לי כל יום ב-9 לקחת ויטמינים"
2. **Bot creates the pattern**: Stores recurring template (not visible in regular list)
3. **Automatic generation**: At midnight (Israel time), bot creates today's instance
4. **You see the instance**: Instance appears in your task list with 🔄 indicator
5. **Complete normally**: Complete the instance like any other task
6. **Next instance**: Appears automatically at midnight on the next scheduled day

**Example Flow:**
```
You: "תזכיר לי כל יום שני ורביעי ב-10 להתקשר לאמא"
Bot: "✅ נוצרה משימה: להתקשר לאמא 🔄 (כל יום שני ורביעי ב-10:00)"

[Next Monday at midnight]
Bot: [Creates instance automatically]

[You see in task list:]
"1. להתקשר לאמא 🔄 (כל יום שני ורביעי) 📅 (יעד היום 10:00)"

[You complete it with 👍]
Bot: "✅ השלמתי: להתקשר לאמא
🔄 משימה חוזרת (כל יום שני ורביעי ב-10:00)
💡 המשימה הבאה תופיע בחצות"

[Next Wednesday at midnight]
Bot: [Creates next instance automatically]
```

### ⏱️ Smart Date & Time Parsing

#### Hebrew Support
- **Relative Times**: `"בעוד 5 דקות"`, `"בעוד שעתיים"`, `"בעוד שבוע"`
- **Hebrew Dates**: `"היום"`, `"מחר"`, `"מחרתיים"`, `"יום ראשון"`, `"יום שלישי ב-14:00"`
- **Israeli Format**: `"31/10"`, `"15/12/2025"`, `"31/10 בשעה 14:30"`
- **Flexible Word Order**: `"דחה ל-31/10 את משימה 12"` or `"דחה את משימה 12 ל-31/10"` - both work!

#### English Support
- **Relative Times**: `"in 2 minutes"`, `"in half an hour"`, `"next week"`
- **English Dates**: `"today"`, `"tomorrow"`, `"next Monday at 3pm"`
- **Formal Dates**: `"October 31st at 2:30 PM"`

#### Timezone
- **All calculations use Israel timezone** (Asia/Jerusalem)
- "היום" = today in Israel, regardless of server location
- Reminders sent according to Israel local time

### 🔔 Intelligent Reminder System

#### Task-Specific Reminders
- **30-Minute Advance Warning**: Reminders sent 30 minutes before due time
- **Automatic**: No setup needed - works for all tasks with due dates
- **One-Time Only**: Each task gets exactly one reminder (prevents spam)
- **Smart Status Check**: Won't send reminders for completed tasks

#### Daily Proactive Reminders
The bot checks in with you **3 times daily**:
- **11:00 AM** - Morning nudge
- **3:00 PM** - Afternoon reminder  
- **7:00 PM** - Evening check-in

**Smart Behavior:**
- **If you have tasks**: Shows up to 10 tasks due today with times
- **If no tasks**: "כול הכבוד! 🎉 אין לך משימות פתוחות כרגע. תיהנה מהיום! 😊"

#### Daily Summary
- **9:00 AM Daily**: Morning summary of your day
- Shows overdue tasks first (⚠️)
- Then shows tasks due today (📅)
- Helps you prioritize your day

### 🎤 Voice Message Support

#### How It Works
1. **Send voice message**: Speak naturally in Hebrew or English
2. **AI transcription**: Gemini 2.5 Flash transcribes your voice
3. **Task extraction**: AI extracts tasks from transcription
4. **Automatic creation**: Tasks created automatically
5. **Response**: Bot confirms with transcription + task summary

#### Example
```
You: [Voice] "תזכיר לי לקנות חלב מחר בשעה חמש"
Bot: "🎤 שמעתי: 'תזכיר לי לקנות חלב מחר בשעה חמש'
✅ נוצרה משימה: לקנות חלב (יעד: מחר 17:00)"
```

### 👍 Emoji Reaction Completion

**The fastest way to complete tasks:**

1. **Get separate tasks**: Send `פירוט` or `משימות נפרד`
2. **Bot sends each task as separate message**: Easy to react to
3. **React with 👍**: Tap the 👍 emoji on any task message
4. **Automatic completion**: Bot marks task as done instantly

**Why separate messages?**
- WhatsApp allows emoji reactions on individual messages
- Each task = one message = one 👍 reaction
- No need to type task numbers or descriptions

### 📊 Productivity Insights

- **Statistics**: `"סטטיסטיקה"` → See completion rates, task counts
- **Task History**: `"הושלמו"` → View recently completed tasks
- **Completion Tracking**: Track your productivity over time

### 🛡️ Security & Privacy

- **AES-256 Encryption**: All user data encrypted at rest
- **Phone Number Hashing**: Secure lookup without storing plaintext
- **No Data Mining**: Conversations are private and not analyzed
- **GDPR Compliant**: Built with privacy regulations in mind

### 🔧 Reliability Features

- **Circuit Breaker**: Automatic API failure detection and recovery
- **Rate Limiting**: Multi-tier protection (per minute/hour/day)
- **Redis-Backed**: Fast caching with in-memory fallback
- **Error Handling**: Graceful degradation with user-friendly messages
- **Exponential Backoff**: Automatic retry for transient failures

---

## 🏗️ How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    WhatsApp User                        │
│         Sends text or voice message                     │
└────────────────────┬──────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────┐
│              WhatsApp Business API                       │
│              Webhook receives message                    │
└────────────────────┬──────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────┐
│              Flask Application (Webhook)                 │
│  • Input validation & sanitization                      │
│  • User authentication/creation                         │
│  • Rate limiting check                                  │
└────────────────────┬──────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────┐
│              AI Service (Google Gemini 2.5 Flash)        │
│  • Text parsing: Extracts tasks from natural language    │
│  • Voice parsing: Transcription + task extraction       │
│  • Returns: Action, description, due date, etc.         │
└────────────────────┬──────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────┐
│              Task Service                                │
│  • Creates/updates/deletes tasks                        │
│  • Handles recurring task patterns                      │
│  • Manages task lifecycle                               │
└────────────────────┬──────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL Database                         │
│  • Tasks stored with encryption                         │
│  • User data secured (AES-256)                          │
│  • Recurring patterns & instances                       │
└────────────────────┬──────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────┐
│              Scheduler Service (Background Worker)       │
│  • Checks for due reminders (every 30 seconds)          │
│  • Sends daily reminders (11 AM, 3 PM, 7 PM)            │
│  • Daily summary (9 AM)                                  │
│  • Generates recurring instances (midnight)              │
└────────────────────┬──────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────┐
│              WhatsApp Service                            │
│  • Sends responses to user                              │
│  • Handles retries & rate limiting                      │
└─────────────────────────────────────────────────────────┘
```

### Message Flow Example

**User sends:** `"להתקשר לאמא מחר ב-15:00"`

1. **Webhook receives** message from WhatsApp API
2. **Input validation** checks for security threats
3. **User lookup/creation** - finds or creates user in database
4. **AI Service** parses message:
   ```json
   {
     "action": "add",
     "description": "להתקשר לאמא",
     "due_date": "מחר ב-15:00"
   }
   ```
5. **Task Service**:
   - Parses due date: "מחר ב-15:00" → tomorrow at 3 PM (Israel time)
   - Creates task in database
   - Returns confirmation
6. **WhatsApp Service** sends response: `"✅ נוצרה משימה: להתקשר לאמא (יעד: מחר 15:00)"`
7. **Scheduler** (later) schedules reminder for 30 minutes before due time

### Recurring Task Flow

**User sends:** `"תזכיר לי כל יום ב-9 לקחת ויטמינים"`

1. **AI Service** extracts recurring pattern:
   ```json
   {
     "action": "add",
     "description": "לקחת ויטמינים",
     "due_date": "היום ב-9:00",
     "recurrence_pattern": "daily",
     "recurrence_interval": 1
   }
   ```
2. **Task Service** creates recurring pattern:
   - `is_recurring = True`
   - Stores pattern in database (not shown in regular task list)
   - If due_date is today/past → creates first instance immediately
   - Updates pattern's due_date to next occurrence
3. **Scheduler** (at midnight daily):
   - Finds all active recurring patterns
   - Checks if pattern's due_date is today
   - Generates new instance if needed
   - Updates pattern's due_date to next occurrence
4. **User sees instance** in task list: `"1. לקחת ויטמינים 🔄 (כל יום) 📅 (יעד היום 09:00)"`
5. **User completes** instance → Next one appears automatically tomorrow at midnight

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **PostgreSQL** database
- **Redis** (optional but recommended)
- **WhatsApp Business API** access
- **Google Gemini API** key

### Installation

```bash
# 1. Clone repository
git clone https://github.com/orkurtz/Todobot.git
cd Todobot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# 5. Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# 6. Run application
python app.py
```

### Environment Variables

Create a `.env` file:

```env
# Flask
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/whatsapp_todo

# WhatsApp Business API
WHATSAPP_TOKEN=your-whatsapp-business-api-token
WEBHOOK_VERIFY_TOKEN=your-webhook-verify-token

# Google Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Redis (Optional but recommended)
REDIS_URL=redis://localhost:6379

# Encryption
ENCRYPTION_KEY=your-base64-encryption-key
```

---

## 📖 Usage Examples

### Basic Commands

| Command | Hebrew | English | Description |
|---------|--------|---------|-------------|
| **Help** | `עזרה` | `help` | Show help menu |
| **List Tasks** | `משימות` / `?` | `tasks` | View pending tasks |
| **Separate Tasks** | `פירוט` | `tasks separate` | Get each task as separate message (for 👍 reactions) |
| **Statistics** | `סטטיסטיקה` | `stats` | View productivity stats |
| **Completed** | `הושלמו` | `completed` | View completed tasks |
| **Recurring** | `משימות חוזרות` | `recurring tasks` | View active recurring patterns |

### Creating Tasks

#### Hebrew Examples
```
"להתקשר לאמא מחר ב-15:00"
"לקנות מצרכים היום"
"פגישה עם יוחנן ביום ראשון ב-10:00"
"תזכיר לי בעוד 5 דקות לצאת"
"בעוד שעה תזכיר לי לסגור את המחשב"
```

#### English Examples
```
"remind me in 2 minutes to call John"
"meeting with Sarah tomorrow at 3pm"
"buy groceries today"
```

#### Voice Examples
```
[Send voice message saying:]
"תזכיר לי לקנות חלב מחר בשעה חמש"
"remind me to call mom tomorrow at three PM"
```

### Recurring Tasks Examples

#### Daily
```
"תזכיר לי כל יום ב-9 לקחת ויטמינים"
"every day at 9am take vitamins"
```

#### Weekly
```
"כל שבוע פגישה עם המנהל"
"every week meeting with manager"
```

#### Specific Days
```
"כל יום שני ורביעי ב-10 להתקשר"
"every Monday and Wednesday call mom"
```

#### Custom Intervals
```
"כל יומיים להשקות צמחים"
"every 3 days water plants"
```

### Managing Tasks

#### Update Description
```
"שנה משימה 2 להתקשר לרופא"
"change task 3 to call dentist"
```

#### Reschedule
```
"דחה משימה 1 למחר"
"העבר משימה 2 בעוד שעתיים"
"דחה 3 ליום שלישי"
"דחה ל-31/10 את משימה 12"  ← Flexible word order!
"postpone task 2 to tomorrow"
"move task 1 in 2 hours"
```

#### Complete
```
"סיימתי משימה 2"
"גמרתי את 1"
"done with task 2"
[Or use 👍 emoji reaction]
```

#### Delete
```
"מחק משימה 3"
"delete task 2"
```

#### Query
```
"מתי הפגישה עם יוחנן?"
"כמה משימות יש לי?"
"when is the meeting with John?"
"how many tasks do I have?"
```

### Managing Recurring Series

#### View Patterns
```
"משימות חוזרות"
"recurring tasks"
```

#### Stop Series
```
"עצור סדרה 5"
"stop series 3"
"מחק סדרה 5"  ← Stops and deletes future instances
```

#### Complete Series
```
"השלם סדרה 3"
"complete series 2"
```

---

## 📁 Project Structure

```
Todobot/
├── src/                      # Source code
│   ├── models/              # Database models
│   │   └── database.py      # User, Task, Message models with encryption
│   ├── services/            # Business logic
│   │   ├── ai_service.py           # Google Gemini integration (text + voice)
│   │   ├── whatsapp_service.py     # WhatsApp API client
│   │   ├── task_service.py         # Task CRUD + recurring logic
│   │   ├── encryption.py           # AES-256 encryption service
│   │   ├── scheduler_service.py    # Background jobs (reminders, summaries)
│   │   └── monitoring_service.py   # System health monitoring
│   ├── utils/               # Utilities
│   │   ├── rate_limiter.py         # API rate limiting (Redis-backed)
│   │   ├── circuit_breaker.py      # Circuit breaker pattern
│   │   ├── media_handler.py        # WhatsApp media downloads
│   │   └── validation.py           # Input validation & sanitization
│   ├── routes/              # Flask routes
│   │   ├── webhook.py      # WhatsApp webhook (text, voice, reactions)
│   │   ├── admin.py        # Admin dashboard
│   │   └── api.py          # REST API endpoints
│   ├── config/             # Configuration
│   │   └── settings.py     # App configuration
│   └── app.py              # Flask application factory
├── migrations/             # Database migrations
├── app.py                  # Application entry point
├── worker_simple.py        # Background worker process
├── requirements.txt        # Python dependencies
├── Procfile               # Railway/Heroku deployment config
└── README.md              # This file
```

---

## 🚀 Deployment

### Railway (Recommended)

1. Connect GitHub repository to Railway
2. Add environment variables in Railway dashboard
3. Deploy automatically with `git push`
4. Enable Redis add-on for rate limiting
5. Ensure worker process is running separately (for scheduler)

### Docker

```bash
# Build image
docker build -t whatsapp-todo-bot .

# Run container
docker run -d --name todo-bot -p 5000:5000 --env-file .env whatsapp-todo-bot
```

### Worker Process

The scheduler requires a separate worker process. Configure your platform:

**Railway/Heroku:**
```
web: gunicorn app:app
worker: python worker_simple.py
```

---

## 🔧 Development

### Running Locally

```bash
# Start web server
python app.py

# Start worker (in separate terminal)
python worker_simple.py
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade

# Rollback
flask db downgrade
```

---

## 📊 Monitoring

### Health Checks

- **Application**: `GET /admin/health`
- **API**: `GET /api/health`
- **Metrics**: `GET /api/metrics` (Prometheus format)

### Admin Dashboard

Access at `/admin/dashboard`:
- User statistics
- Message volume
- Task completion rates
- System health status
- API rate limit usage

---

## 🔐 Security

- **AES-256 Encryption**: All user data encrypted at rest
- **Phone Number Hashing**: Secure database lookups
- **Input Validation**: XSS and prompt injection protection
- **Rate Limiting**: Multi-tier API protection
- **Circuit Breaker**: Automatic failure recovery
- **HTTPS Required**: All production traffic encrypted

---

## 🐛 Troubleshooting

### Common Issues

1. **Voice messages not processing**
   - Check WhatsApp media permissions
   - Verify `WHATSAPP_TOKEN` has media download rights
   - Check Gemini API quota

2. **Database connection errors**
   - Verify `DATABASE_URL` is correct
   - Check PostgreSQL is running
   - Ensure database exists

3. **Reminders not sending**
   - Verify worker process is running
   - Check Redis connection (if using)
   - Review scheduler logs

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

### Original Project Creator
- **[buzaglo idan](https://github.com/buzagloidan)** - Original creator of the WhatsApp Todo Bot foundation
- Original repository: [https://github.com/buzagloidan/Todobot](https://github.com/buzagloidan/Todobot)

### Technologies & Libraries
- [Google Gemini 2.5 Flash](https://ai.google.dev/) - AI capabilities for text and voice processing
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp) - Messaging platform
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Redis](https://redis.io/) - Caching & rate limiting

