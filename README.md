# 🤖 WhatsApp Todo Bot

<div align="center">
  <img src="assets/images/todo.png" alt="WhatsApp Todo Bot" width="400">
  
  <p><strong>An intelligent AI-powered personal assistant that helps you manage tasks and stay organized through WhatsApp.</strong></p>
  
  <p>The bot understands natural Hebrew and English language, extracts actionable tasks from text AND voice messages, and provides smart reminders optimized for Israeli users.</p>

  <p>
    <a href="#-try-it-now---live-demo"><strong>🚀 Try Now</strong></a> •
    <a href="#-demo"><strong>Demo</strong></a> •
    <a href="#-quick-start"><strong>Get Started</strong></a> •
    <a href="#-features"><strong>Features</strong></a> •
    <a href="#-usage"><strong>Usage</strong></a> •
    <a href="#-deployment"><strong>Deploy</strong></a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python" alt="Python">
    <img src="https://img.shields.io/badge/Flask-Framework-green?style=for-the-badge&logo=flask" alt="Flask">
    <img src="https://img.shields.io/badge/WhatsApp-Business%20API-25D366?style=for-the-badge&logo=whatsapp" alt="WhatsApp">
    <img src="https://img.shields.io/badge/AI-Google%20Gemini%202.5%20Flash-4285F4?style=for-the-badge&logo=google" alt="Google Gemini">
  </p>
  
  <p>
    <a href="https://wa.me/972559664336" target="_blank">
      <img src="https://img.shields.io/badge/🚀_TRY_LIVE_DEMO-FF6B6B?style=for-the-badge&logoColor=white&logo=whatsapp" alt="Try Live Demo">
    </a>
  </p>
</div>

---

## 📱 Demo

<div align="center">
  <h3>See WhatsApp Todo Bot in Action</h3>
  
  <table>
    <tr>
      <td align="center">
        <strong>📝 Natural Language Input</strong><br>
        <em>"Call mom tomorrow at 3pm"</em><br>
        <em>"תזכיר לי לקנות חלב בעוד 10 דקות"</em><br>
        <em>🎤 Voice: "פגישה עם יוחנן מחר בבוקר"</em>
      </td>
      <td align="center">
        <strong>🤖 AI Processing</strong><br>
        ✅ Task extracted<br>
        📅 Due date parsed (Hebrew & English)<br>
        🎤 Voice transcribed & understood<br>
        🔔 Reminder scheduled
      </td>
      <td align="center">
        <strong>📲 WhatsApp Response</strong><br>
        <em>"נוצרה משימה: Call mom"</em><br>
        <em>"🎤 שמעתי: 'לקנות חלב'"</em><br>
        <em>"✅ תזכורת נקבעה ל-14:30"</em>
      </td>
    </tr>
  </table>

  <p><strong>🇮🇱 Hebrew Language Support:</strong> Optimized for Hebrew speakers with Israeli timezone!</p>
  <p><strong>🎤 Voice Message Support:</strong> Send voice notes in Hebrew or English - they'll be transcribed and understood!</p>
  
  <p>
    <a href="https://wa.me/972559664336" target="_blank">
      <img src="https://img.shields.io/badge/💬_Try_Live_Demo-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" alt="Try Live Demo">
    </a>
  </p>
  
  <p><em>Click above to test the bot directly on WhatsApp! Just send a text message like "לקנות חלב מחר בחמש" or a voice note and see the magic happen! ✨</em></p>
</div>

## 🚀 Try It Now - Live Demo!

<div align="center">
  <h3>🎯 Ready to experience the magic? Test our live WhatsApp Todo Bot!</h3>
  
  <p>
    <a href="https://wa.me/972559664336?text=שלום%20בוט%20המשימות!%20אני%20רוצה%20לנסות%20אותך." target="_blank">
      <img src="https://img.shields.io/badge/💬%20Start%20Chat%20Now-25D366?style=for-the-badge&logo=whatsapp&logoColor=white&labelColor=25D366" alt="Start WhatsApp Chat" height="60">
    </a>
  </p>
  
  <h4>📝 Try These Example Messages:</h4>
  <table>
    <tr>
      <td><strong>📝 Basic Tasks</strong></td>
      <td><strong>⏰ With Relative Times</strong></td>
      <td><strong>🔧 Task Management</strong></td>
    </tr>
    <tr>
      <td>
        • "לקנות חלב מחר"<br>
        • "פגישה עם מנהל ביום ראשון"<br>
        • 🎤 <em>Voice: "להתקשר לאמא"</em><br>
        • "Meeting with John next Monday"
      </td>
      <td>
        • "תזכיר לי בעוד 5 דקות"<br>
        • "דחה משימה 2 בשעתיים"<br>
        • "remind me in 10 minutes"<br>
        • "העבר משימה 3 למחר ב-15:00"
      </td>
      <td>
        • "סיימתי משימה 2"<br>
        • "שנה משימה 1 לקנות לחם"<br>
        • "המשימות שלי"<br>
        • "סטטיסטיקה"<br>
        • "עזרה"
      </td>
    </tr>
  </table>
  
  <p><strong>⚡ What happens next?</strong><br>
  The bot will instantly parse your message (text or voice!), extract tasks, understand due dates in Hebrew or English, and create reminders - all through natural conversation!</p>
  
  <p><em>💡 Tip: Try sending a voice message in Hebrew - the bot transcribes AND understands it!</em></p>
</div>

---

## ✨ Features

### 🎯 Smart Task Management
- **Natural Language Processing**: Just tell the bot what you need to do (text or voice!)
- **Automatic Task Extraction**: AI identifies actionable items from your messages
- **Voice Message Support**: 🎤 Send voice notes in Hebrew or English - automatic transcription + task extraction
- **Task Updates**: Change task descriptions with `"שנה משימה 2 להתקשר לרופא"`
- **Task Rescheduling**: Move due dates with `"דחה משימה 3 למחר"` or `"postpone task 5 by 2 hours"`
- **Task Status Tracking**: Pending, completed, and progress tracking
- **Smart Task Queries**: Ask questions like `"מתי הפגישה עם יוחנן?"` and get real-time answers

### ⏱️ Advanced Date & Time Understanding
- **Hebrew Relative Times**: `"בעוד 5 דקות"`, `"בעוד שעתיים"`, `"בעוד שבוע"`
- **English Relative Times**: `"in 2 minutes"`, `"in half an hour"`, `"next week"`
- **Hebrew Dates**: `"היום"`, `"מחר"`, `"מחרתיים"`, `"יום ראשון"`
- **English Dates**: `"today"`, `"tomorrow"`, `"next Monday at 3pm"`
- **Exact Times**: `"מחר ב-15:00"`, `"tomorrow at 3pm"`

### 🇮🇱 Hebrew Language Optimization
- **Natural Hebrew**: מבין עברית בצורה טבעית ומדויקת
- **Israeli Context**: מותאם לזמן ישראלי ותרבות מקומית
- **Hebrew Date Parsing**: מבין תאריכים בעברית כמו "היום", "מחר", "בעוד שעה"
- **Local Timezone**: עובד לפי שעון ישראל (Asia/Jerusalem)

### 🎤 Voice Message Features
- **Automatic Transcription**: Voice-to-text in Hebrew and English
- **Direct Task Extraction**: AI understands tasks from voice in one go
- **Powered by Gemini 2.5 Flash**: Latest Google AI for multimodal processing
- **No External Services**: All processing happens in one API call

### 🛡️ Reliability & Performance
- **Circuit Breaker Pattern**: Automatic API failure detection and recovery
- **Advanced Rate Limiting**: Multi-tier protection (per minute/hour/day)
- **Redis-Backed Caching**: Fast and reliable with fallback to in-memory storage
- **Exponential Backoff**: Automatic retry logic for transient failures
- **Robust Error Handling**: Graceful degradation and user-friendly error messages

### 🔒 Privacy & Security
- **End-to-End Encryption**: All user data encrypted at rest (AES-256)
- **No Data Mining**: Your conversations are private and secure
- **GDPR Compliant**: Built with privacy regulations in mind
- **Secure Hash Lookups**: Phone numbers hashed for database searches

### 📊 Productivity Insights
- **Statistics Dashboard**: Track your productivity over time
- **Completion Rates**: See how well you're doing with your goals
- **Usage Analytics**: Understand your task management patterns
- **Due Date Tracking**: Overdue and today's tasks highlighted

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Redis (optional, for caching and rate limiting)
- WhatsApp Business API access
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/buzagloidan/Todobot.git
   cd Todobot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (including hidden files like .env)
   ```

5. **Initialize database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/whatsapp_todo

# WhatsApp API
WHATSAPP_TOKEN=your-whatsapp-business-api-token
WEBHOOK_VERIFY_TOKEN=your-webhook-verify-token

# Google Gemini AI (2.5 Flash)
GEMINI_API_KEY=your-gemini-api-key

# Redis (Optional but recommended for rate limiting)
REDIS_URL=redis://localhost:6379

# Encryption
ENCRYPTION_KEY=your-base64-encryption-key

# Rate Limiting (API protection)
RATE_LIMIT_REQUESTS_PER_MINUTE=30
RATE_LIMIT_REQUESTS_PER_HOUR=1000
RATE_LIMIT_REQUESTS_PER_DAY=10000
```

### WhatsApp Business API Setup

1. Create a WhatsApp Business account
2. Set up webhook URL: `https://yourdomain.com/webhook`
3. Configure webhook verification token
4. Add your phone number to the allowed list

## 📁 Project Structure

```
Todobot/
├── src/                    # Source code
│   ├── models/            # Database models
│   │   └── database.py    # SQLAlchemy models with encryption
│   ├── services/          # Business logic services
│   │   ├── ai_service.py      # AI/Gemini integration (with voice support)
│   │   ├── whatsapp_service.py # WhatsApp API client
│   │   ├── task_service.py     # Task management (CRUD + update/reschedule)
│   │   ├── encryption.py      # Data encryption (AES-256)
│   │   ├── scheduler_service.py # Background task scheduling
│   │   └── monitoring_service.py # System monitoring
│   ├── utils/             # Utility functions
│   │   ├── rate_limiter.py    # Rate limiting (Redis-backed)
│   │   ├── circuit_breaker.py # Circuit breaker pattern
│   │   ├── media_handler.py   # WhatsApp media downloads
│   │   └── validation.py      # Input validation
│   ├── routes/            # Flask routes
│   │   ├── webhook.py     # WhatsApp webhook handler (text + voice)
│   │   ├── admin.py       # Admin dashboard
│   │   └── api.py         # REST API endpoints
│   ├── config/            # Configuration
│   │   └── settings.py    # App configuration
│   └── app.py            # Flask application factory
├── app.py                # Main application entry point
├── worker_simple.py      # Background worker process
├── requirements.txt      # Python dependencies
├── Procfile             # Railway/Heroku deployment
└── README.md            # This file
```

## 🔧 Usage

### Basic Commands

Send these messages to the bot:

- `עזרה` or `help` - Get help and available commands
- `משימות` or `המשימות שלי` - View your pending tasks
- `סטטיסטיקה` or `stats` - See your productivity statistics
- `הושלמו` or `completed` - View recently completed tasks

### Natural Language Examples

#### 📝 Hebrew Text Examples
- **Create Tasks:**
  - "להתקשר לאמא מחר ב-15:00"
  - "לקנות מצרכים היום"
  - "פגישה עם יוחנן ביום ראשון ב-10:00"
  - "תזכיר לי בעוד 5 דקות לצאת"
  - "בעוד שעה תזכיר לי לסגור את המחשב"

- **Update Tasks:**
  - "שנה משימה 2 להתקשר לרופא"
  - "עדכן משימה 3 קנה לחם"

- **Reschedule Tasks:**
  - "דחה משימה 1 למחר"
  - "העבר משימה 2 בעוד שעתיים"
  - "דחה 3 ביומיים"

- **Complete Tasks:**
  - "סיימתי משימה 2"
  - "גמרתי את 1"

#### 🎤 Hebrew Voice Examples
- **Send voice notes saying:**
  - "תזכיר לי לקנות חלב מחר בשעה חמש"
  - "סיימתי את משימה שתיים"
  - "פגישה עם הרופא ביום רביעי בעשר"
  - "בעוד עשר דקות תזכיר לי לצאת מהבית"

#### 📝 English Text Examples
- "remind me in 2 minutes to call John"
- "meeting with Sarah tomorrow at 3pm"
- "postpone task 2 by 2 hours"
- "change task 1 to buy bread"

#### 🎤 English Voice Examples
- **Send voice notes saying:**
  - "remind me to call mom tomorrow at three PM"
  - "done with task number two"

### Task Management Actions

#### ✅ Complete Tasks
- React with 👍 to any message
- "סיימתי משימה 2" / "done with task 2"
- "גמרתי את 1" / "finished 1"

#### 📝 Update Tasks
- "שנה משימה 3 להתקשר לרופא" (change description)
- "עדכן משימה 5 קנה חלב מחר ב-10" (change description + due date)

#### ⏰ Reschedule Tasks
- "דחה משימה 2 למחר" / "postpone task 2 to tomorrow"
- "העבר משימה 1 בעוד שעתיים" / "move task 1 in 2 hours"
- "דחה 3 ליום שלישי" / "reschedule 3 to Tuesday"

#### ❓ Query Tasks
- "מתי הפגישה עם יוחנן?" / "when is the meeting with John?"
- "כמה משימות יש לי?" / "how many tasks do I have?"

### Task Reminders

- Tasks with due dates will send reminders 15 minutes before
- Overdue tasks are highlighted with ⚠️
- Tasks due today show 🔥

## 🚀 Deployment

### Railway (Recommended)

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically with git push
4. Enable Redis add-on for rate limiting

### Docker

```bash
# Build image
docker build -t whatsapp-todo-bot .

# Run container
docker run -d --name todo-bot -p 5000:5000 --env-file .env whatsapp-todo-bot
```

## 🔧 Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

## 📊 Monitoring

### Health Checks

- **Application Health**: `GET /admin/health`
- **API Health**: `GET /api/health`
- **Metrics**: `GET /api/metrics` (Prometheus format)

### Admin Dashboard

Access the admin dashboard at `/admin/dashboard` to monitor:

- User statistics
- Message volume (text + voice)
- Task completion rates
- System health status
- API rate limit usage
- Circuit breaker status

## 🔐 Security

### Data Protection

- All user data encrypted using AES-256
- Phone numbers hashed for lookups
- Messages encrypted at rest
- No conversation data logged
- Voice messages processed and immediately discarded

### API Protection

- Circuit breaker pattern for API resilience
- Multi-tier rate limiting (minute/hour/day)
- Redis-backed rate limit tracking
- Exponential backoff for retries
- Input validation and sanitization

### Best Practices

- Use HTTPS in production
- Regularly rotate encryption keys
- Monitor for suspicious activity
- Keep dependencies updated

## 🐛 Troubleshooting

### Common Issues

1. **Voice Message Processing Failures**
   ```bash
   # Check WhatsApp media permissions
   # Verify WHATSAPP_TOKEN has media download rights
   # Check Gemini API quota for multimodal requests
   ```

2. **Database Connection Issues**
   ```bash
   # Check database connection
   python -c "from src.models.database import db; print('Connected')"
   ```

3. **WhatsApp API Issues**
   - Verify webhook URL is accessible
   - Check token permissions
   - Ensure phone number is verified

4. **AI Service Issues**
   - Verify Gemini API key is valid
   - Check API quota limits
   - Monitor rate limiting and circuit breaker status

### Logs

Application logs include:
- Request/response details
- Voice transcription results
- Task extraction results
- Error messages with context
- Performance metrics
- Circuit breaker state changes
- Rate limit violations

## 🆕 What's New

### Recent Updates (Past 3 Days)

#### 🎤 Voice Message Support (NEW!)
- Full voice message transcription using Gemini 2.5 Flash multimodal API
- Automatic task extraction from Hebrew and English voice notes
- Single API call for transcription + task parsing
- Media download handler for WhatsApp audio files

#### ⏰ Advanced Time Parsing (NEW!)
- Hebrew relative times: "בעוד 5 דקות", "בעוד שעתיים"
- English relative times: "in 2 minutes", "in half an hour"
- Enhanced natural language understanding for dates

#### 🔄 Task Update & Reschedule (NEW!)
- Update task descriptions: "שנה משימה 2 להתקשר לרופא"
- Reschedule tasks: "דחה משימה 3 למחר"
- Combined updates: change description + due date together

#### 🛡️ Reliability Improvements (NEW!)
- Circuit breaker pattern for API failure recovery
- Advanced rate limiting with Redis backend
- Improved JSON parsing from AI responses
- Better error handling throughout

#### 🤖 AI Enhancements (NEW!)
- Upgraded to Gemini 2.5 Flash model
- Better prompt engineering for task actions
- Support for task queries with real-time database results
- Fixed JSON parsing issues with code blocks

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Google Gemini 2.5 Flash](https://ai.google.dev/) for powerful AI capabilities (text + voice)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp) for messaging platform
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) for database management
- [Redis](https://redis.io/) for caching and rate limiting

---

<div align="center">
  <p>Made with ❤️ for Israeli productivity enthusiasts</p>
  
  <p>
    <a href="https://wa.me/972559664336?text=שלום!%20מצאתי%20את%20הבוט%20שלך%20ב-GitHub!" target="_blank">
      <img src="https://img.shields.io/badge/💬%20Chat%20with%20Bot-25D366?style=flat&logo=whatsapp" alt="Chat with Bot">
    </a>
    <img src="https://img.shields.io/badge/Made%20with-❤️-red?style=flat" alt="Made with Love">
    <img src="https://img.shields.io/badge/Open%20Source-✨-blue?style=flat" alt="Open Source">
    <img src="https://img.shields.io/badge/Voice%20Enabled-🎤-purple?style=flat" alt="Voice Enabled">
  </p>
  
  <p><em>⭐ Star this repo if you find it useful!</em></p>
</div>
