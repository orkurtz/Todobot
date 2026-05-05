"""
WhatsApp webhook routes for handling incoming messages
"""
import json
import base64
import threading
import requests
import pytz
import unicodedata
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

from ..models.database import db, User, Message, Task
from ..services.encryption import encryption_service
from ..utils.validation import InputValidator

bp = Blueprint('webhook', __name__)
# task_service will be imported from app.py when needed

def _normalize_command_text(text):
    """
    Strip invisible bidi/zero-width chars and trailing punctuation so
    'עזרה', 'עזרה!', 'עזרה\u200f' etc. match the same as 'תפריט'.

    Must not strip a lone '?' (list command) — rstrip('?.') would erase it entirely.
    """
    if not text or not isinstance(text, str):
        return ''
    s = unicodedata.normalize('NFC', text.strip())
    for ch in ('\u200f', '\u200e', '\ufeff', '\u202a', '\u202b', '\u202c', '\u202d'):
        s = s.replace(ch, '')
    s = s.strip()
    trimmed = s.rstrip('!.?…,:;').strip()
    if trimmed:
        s = trimmed
    elif len(s) == 1:
        pass  # keep e.g. "?" or "!"
    else:
        s = ''
    return s.lower()


def get_or_create_user(phone_number):
    """Get existing user or create new one"""
    try:
        # Hash phone number for lookup
        phone_hash = encryption_service.hash_for_search(phone_number)
        user = User.query.filter_by(phone_number_hash=phone_hash).first()
        
        if not user:
            user = User()
            user.phone_number = phone_number  # This will encrypt and hash automatically
            user.created_at = datetime.utcnow()
            user.last_active = datetime.utcnow()
            
            db.session.add(user)
            db.session.commit()
            
            print(f"✅ Created new user: {phone_number}")
        else:
            # Update last active time
            user.last_active = datetime.utcnow()
            db.session.commit()
            
        return user
        
    except Exception as e:
        print(f"❌ Error getting/creating user: {e}")
        db.session.rollback()
        raise e

def save_message(user_id, message_type, content, ai_response, parsed_tasks=None, whatsapp_message_id=None):
    """Save message to database"""
    try:
        message = Message(
            user_id=user_id,
            message_type=message_type,
            whatsapp_message_id=whatsapp_message_id
        )
        
        # Use property setters for encryption
        message.content = content
        message.ai_response = ai_response
        message.parsed_tasks = json.dumps(parsed_tasks) if parsed_tasks else None
        
        db.session.add(message)
        db.session.commit()
        
        return message
        
    except Exception as e:
        print(f"❌ Error saving message: {e}")
        db.session.rollback()
        return None

@bp.route('/webhook', methods=['GET'])
def verify():
    """Webhook verification endpoint"""
    try:
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        expected_token = "TodoBotWebhook2024"  # Should match your webhook configuration
        
        if verify_token == expected_token:
            print("✅ Webhook verified successfully")
            return challenge
        else:
            print(f"❌ Webhook verification failed. Expected: {expected_token}, Got: {verify_token}")
            return "Verification failed", 403
            
    except Exception as e:
        print(f"❌ Webhook verification error: {e}")
        return "Verification error", 500

def _process_webhook_payload(app, data):
    """Run AI/DB work outside the HTTP request so WhatsApp gets 200 OK immediately."""
    with app.app_context():
        try:
            for entry in data['entry']:
                if 'changes' not in entry:
                    continue

                for change in entry['changes']:
                    if change.get('field') != 'messages':
                        continue

                    value = change.get('value', {})

                    if 'messages' in value:
                        for message in value['messages']:
                            process_incoming_message(message, value)

                    if 'statuses' in value:
                        for status in value['statuses']:
                            process_message_status(status)
        except Exception as e:
            print(f"❌ Background webhook processing error: {e}")


@bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages — ack fast; heavy work runs in a background thread."""
    try:
        data = request.get_json(silent=True) or {}

        if not data or 'entry' not in data:
            return jsonify({"status": "ok"}), 200

        app = current_app._get_current_object()
        threading.Thread(
            target=_process_webhook_payload,
            args=(app, data),
            daemon=True,
        ).start()

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def _build_overdue_nudge(user_id: int, last_active) -> str:
    """
    Returns a 1-line overdue nudge if the user has overdue tasks AND has been
    away for more than 24 hours. Returns empty string otherwise.
    """
    try:
        from ..models.database import Task
        from datetime import timedelta as _td

        now = datetime.utcnow()
        # Only nudge when returning after a gap (> 24 hours away)
        if last_active and (now - last_active) < _td(hours=24):
            return ""

        overdue_count = Task.query.filter(
            Task.user_id == user_id,
            Task.status == 'pending',
            Task.is_recurring == False,
            Task.due_date < now,
            Task.due_date.isnot(None),
        ).count()

        if overdue_count == 0:
            return ""

        task_word = "משימה שעבר זמנה" if overdue_count == 1 else f"משימות שעבר זמנן"
        return (
            f"⚠️ יש לך {overdue_count} {task_word}.\n"
            "כתוב \"דחה משימות שעברו\" להעברה מהירה לשעה הקרובה."
        )
    except Exception:
        return ""


def process_incoming_message(message, value):
    """Process a single incoming message"""
    try:
        from ..app import ai_service, whatsapp_service
        
        if not ai_service or not whatsapp_service:
            print("⚠️ Services not available, skipping message processing")
            return
        
        message_type = message.get('type')
        from_number = message.get('from')
        message_id = message.get('id')
        timestamp = message.get('timestamp')
        
        # --- FIX: Idempotency Check ---
        # Check if we already processed this specific message ID
        # Import Message model locally to ensure it's available if not global (though it is global)
        from ..models.database import Message
        existing_msg = Message.query.filter_by(whatsapp_message_id=message_id).first()
        if existing_msg:
            print(f"⚠️ Message {message_id} already processed. Skipping duplicate.")
            return
        # ------------------------------
        
        print(f"📱 Incoming {message_type} message from {from_number}")
        print(f"🔍 Message structure: {json.dumps(message, indent=2)}")
        
        # Get or create user
        user = get_or_create_user(from_number)
        
        # Check if this is a new user (created_at == last_active means just created)
        is_new_user = (user.created_at == user.last_active)
        
        if is_new_user:
            # Send welcome message to new user
            welcome_msg = """👋 היי! אני הבוט שלך לרשימת המטלות — ישירות בוואטסאפ.

פשוט כתוב לי מה אתה צריך לעשות:
📌 "לקנות חלב מחר ב-17:00"
📌 "להתקשר למוטי ביום שלישי"
📌 "להגיש דוח עד יום שישי ב-12:00"

אני אדאג לתזכורות, ואפשר להשלים משימה בלחיצת 👍.

כדי לראות את כל מה שאפשר לעשות → כתוב *עזרה*"""
            
            whatsapp_service.send_message(from_number, welcome_msg)
        
        # Validate rate limits
        if not InputValidator.validate_user_rate_limit(user.id):
            whatsapp_service.send_message(
                from_number,
                "⚠️ אתה שולח הודעות מהר מדי. חכה רגע לפני שליחת הודעה נוספת."
            )
            return

        # Proactive overdue nudge — shown once per session (user away > 6 hours), skip for new users
        if not is_new_user and message_type in ('text', 'audio', 'voice'):
            _nudge = _build_overdue_nudge(user.id, user.last_active)
            if _nudge:
                whatsapp_service.send_message(from_number, _nudge)

        # Process different message types
        if message_type == 'text':
            process_text_message(message, user, whatsapp_service, ai_service)
        elif message_type in ['audio', 'voice']:  # Support both audio and voice
            process_voice_message(message, user, whatsapp_service, ai_service)
        elif message_type == 'button':
            process_button_message(message, user, whatsapp_service)
        elif message_type == 'interactive':
            process_interactive_message(message, user, whatsapp_service)
        elif message_type == 'reaction':
            process_reaction_message(message, user, whatsapp_service)
        else:
            # Handle unsupported message types
            whatsapp_service.send_message(
                from_number,
                f"🤖 קיבלתי את הודעת ה-{message_type} שלך, אבל אני יכול לעבד רק הודעות טקסט וקול כרגע. אנא שלח לי הודעת טקסט!"
            )
            
    except Exception as e:
        print(f"❌ Error processing message: {e}")

def process_text_message(message, user, whatsapp_service, ai_service):
    """Process text message"""
    try:
        from ..app import task_service
        text_body = message['text']['body']
        from_number = user.phone_number
        
        # Validate and sanitize input
        sanitized_text = InputValidator.validate_and_sanitize(user.id, text_body)
        if not sanitized_text:
            whatsapp_service.send_message(
                from_number,
                "⚠️ ההודעה שלך מכילה תוכן לא חוקי. אנא שלח הודעה אחרת."
            )
            return
        
        # Check for basic commands first
        command_response = handle_basic_commands(user.id, sanitized_text)
        if command_response:
            whatsapp_service.send_message(from_number, command_response)
            save_message(user.id, 'text', sanitized_text, command_response)
            return
        
        # Step 1: Parse first to detect intent
        parsed_tasks = ai_service.parse_tasks(sanitized_text)
        
        # Debug: Show what AI parsed
        print(f"🔥 DEBUG - Parsed {len(parsed_tasks) if parsed_tasks else 0} tasks from text message")
        if parsed_tasks:
            for idx, task in enumerate(parsed_tasks):
                print(f"   Task {idx+1}: action={task.get('action')}, task_id={task.get('task_id')}, description={task.get('description')}, due_date={task.get('due_date')}")
        
        # Step 2: Execute parsed tasks (query database FIRST for queries)
        task_summary = ""
        has_action = False
        is_query = False
        
        if parsed_tasks:
            task_summary = task_service.execute_parsed_tasks(user.id, parsed_tasks, sanitized_text)
            print(f"🔥 DEBUG - Execution result: {task_summary[:200] if task_summary else '(empty)'}")
            # Check if there's an action (not query)
            has_action = any(task.get('action') in ['complete', 'delete', 'add', 'update', 'reschedule', 'stop_series', 'complete_series'] for task in parsed_tasks)
            is_query = any(task.get('action') == 'query' for task in parsed_tasks)
        
        # Step 3: Generate AI response WITH query results as context (for queries only)
        if is_query and task_summary:
            # Check if query already returned "no tasks" message to avoid duplication
            is_no_tasks_message = (
                task_summary.startswith("📋 אין לך משימות") or 
                task_summary.startswith("📋 אין לך משימות פתוחות")
            )
            
            if is_no_tasks_message:
                # Query result is sufficient, skip AI to avoid duplicate "no tasks" message
                ai_response = ""
                print(f"🔥 DEBUG - Skipping AI response (query already returned 'no tasks')")
            else:
                # Query detected - pass database results to AI so it knows what was found
                ai_response = ai_service.get_response(user.id, sanitized_text, query_results=task_summary)
                print(f"🔥 DEBUG - Generated AI response with query context")
        elif not parsed_tasks:
            # Pure conversation - no tasks detected
            ai_response = ai_service.get_response(user.id, sanitized_text)
            print(f"🔥 DEBUG - Generated AI response for pure conversation")
        else:
            # Actions (add/complete/etc.) - AI response not needed (we show task_summary only)
            ai_response = ""
            print(f"🔥 DEBUG - Skipping AI response for action")
        
        # Step 4: Build response intelligently
        if has_action and task_summary:
            # For actions (complete/delete/add) - only show execution result
            full_response = task_summary
            print(f"🔥 DEBUG - Sending execution result only")
        elif task_summary:
            # For queries - combine AI response (now context-aware) with data
            if ai_response:
                full_response = f"{ai_response}\n\n{task_summary}"
            else:
                # Fallback if AI response failed
                full_response = task_summary
            print(f"🔥 DEBUG - Sending AI response + task summary")
        else:
            # No task operations - just AI response (pure conversation)
            if ai_response:
                full_response = ai_response
            else:
                full_response = (
                    f"לא הצלחתי להבין בדיוק מה לעשות עם:\n\"{sanitized_text}\"\n\n"
                    "💡 נסה לנסח כך: \"להתקשר לדוד מחר ב-10\"\n"
                    "או כתוב *עזרה* לדוגמאות נוספות."
                )
            print(f"🔥 DEBUG - ⚠️ Sending AI response only (no execution)!")
        
        # Add help text footer for responses that are not commands or actions
        # Add footer if: no parsed tasks (pure conversation) OR parsed tasks but no actions (queries only)
        if not parsed_tasks or (parsed_tasks and not has_action):
            # This is either a conversational response or a query (not an action), add help footer
            full_response += "\n\nלתפריט ועזרה עם הבוט הגב 'עזרה' בצאט"
        
        # Send response
        whatsapp_service.send_message(from_number, full_response)
        
        # Save to database
        save_message(
            user.id, 
            'text', 
            sanitized_text, 
            full_response, 
            parsed_tasks,
            message.get('id')
        )
        
    except Exception as e:
        print(f"❌ Error processing text message: {e}")
        whatsapp_service.send_message(
            user.phone_number,
            "משהו השתבש בעיבוד ההודעה שלך. אנא נסה שוב, ואם הבעיה חוזרת — כתוב *עזרה* לרשימת הפקודות."
        )

def process_voice_message(message, user, whatsapp_service, ai_service):
    """Process voice message using Gemini multimodal API"""
    try:
        from ..app import ai_service, task_service
        from ..utils.media_handler import media_handler
        
        # Get audio details from message
        audio = message.get('audio', {})
        voice = message.get('voice', {})
        
        # Try both possible field names
        media_id = audio.get('id') or voice.get('id')
        
        if not media_id:
            print(f"❌ No media ID in voice message")
            print(f"Message data: {json.dumps(message, indent=2)}")
            whatsapp_service.send_message(
                user.phone_number,
                "❌ לא הצלחתי לקבל את ההודעה הקולית. נסה שוב."
            )
            return
        
        print(f"🎤 Processing voice message, media ID: {media_id}")
        
        # Send "processing" acknowledgment
        whatsapp_service.send_message(
            user.phone_number,
            "🎤 מעבד את ההודעה הקולית..."
        )
        
        # Download audio from WhatsApp
        media_result = media_handler.download_whatsapp_media(media_id)
        
        if not media_result:
            whatsapp_service.send_message(
                user.phone_number,
                "❌ לא הצלחתי להוריד את ההודעה הקולית. נסה שוב."
            )
            return
        
        audio_data, mime_type = media_result
        
        # Process with Gemini (transcribe + extract tasks in one call)
        parsed_tasks = ai_service.parse_tasks_from_audio(audio_data, mime_type)
        
        if not parsed_tasks:
            transcription_hint = ""
            if parsed_tasks is not None:
                # We got a response but no tasks — show what was heard
                first_task = (parsed_tasks or [{}])
                heard_text = first_task[0].get('transcription', '') if first_task else ''
                if heard_text:
                    transcription_hint = f"🎤 שמעתי: \"{heard_text}\"\n\n"
            whatsapp_service.send_message(
                user.phone_number,
                f"{transcription_hint}לא זיהיתי משימה בהודעה הקולית.\n\n"
                "רוצה ליצור משימה? אפשר לנסח כך:\n"
                "👉 \"להתקשר לדוד מחר ב-10\"\n"
                "👉 \"לקנות מצרכים היום\"\n\n"
                "או פשוט כתוב לי בטקסט."
            )
            return
        
        # Get transcription from first task (Gemini includes it)
        transcription = parsed_tasks[0].get('transcription', '') if parsed_tasks else ''
        
        print(f"🎤 Transcription: {transcription}")
        print(f"📋 Parsed {len(parsed_tasks)} tasks from voice")
        
        # Execute the parsed tasks
        task_summary = task_service.execute_parsed_tasks(user.id, parsed_tasks, transcription)
        
        # Build response with transcription
        response_parts = []
        
        if transcription:
            response_parts.append(f"🎤 שמעתי: \"{transcription}\"")
        
        if task_summary:
            response_parts.append(task_summary)
        else:
            response_parts.append("✅ קיבלתי את ההודעה")
        
        full_response = "\n\n".join(response_parts)
        
        # Send response
        whatsapp_service.send_message(user.phone_number, full_response)
        
        # Save to database
        save_message(
            user.id,
            'audio',
            transcription,
            full_response,
            parsed_tasks,
            message.get('id')
        )
        
    except Exception as e:
        print(f"❌ Error processing voice message: {e}")
        import traceback
        traceback.print_exc()
        whatsapp_service.send_message(
            user.phone_number,
            "לא הצלחתי לעבד את ההודעה הקולית הפעם.\nאפשר לנסות שוב, או לכתוב את המשימה בטקסט."
        )

def process_button_message(message, user, whatsapp_service):
    """Process button click"""
    try:
        button_payload = message.get('button', {}).get('payload', '')
        response = handle_button_click(user.id, button_payload)
        
        if response:
            whatsapp_service.send_message(user.phone_number, response)
            
    except Exception as e:
        print(f"❌ Error processing button message: {e}")

def process_interactive_message(message, user, whatsapp_service):
    """Process interactive message (button reply)"""
    try:
        interactive_data = message.get('interactive', {})
        button_reply = interactive_data.get('button_reply', {})
        button_id = button_reply.get('id', '')
        
        response = handle_button_click(user.id, button_id)
        
        if response:
            whatsapp_service.send_message(user.phone_number, response)
            
    except Exception as e:
        print(f"❌ Error processing interactive message: {e}")

def process_reaction_message(message, user, whatsapp_service):
    """Process emoji reaction to complete tasks"""
    try:
        from ..app import task_service
        from ..models.database import Message, Task, db
        
        reaction = message.get('reaction', {})
        emoji = reaction.get('emoji')
        message_id = reaction.get('message_id')
        
        print(f"👍 Reaction: {emoji} on message {message_id}")
        
        if emoji != '👍' or not message_id:
            return
        
        # Find task ID from message mapping
        msg_record = Message.query.filter_by(
            user_id=user.id,
            whatsapp_message_id=message_id,
            message_type='task_reference'
        ).first()
        
        if not msg_record:
            print(f"No task mapping for message {message_id}")
            return
        
        task_id = int(msg_record.content)
        
        # Get task details before completing
        task = Task.query.get(task_id)
        
        # Complete the task
        success, result_msg = task_service.complete_task(task_id, user.id)
        
        if success:
            # Build response with recurring info
            response_text = f"✅ #{task.id if task else '?'}: \"{task.description if task else 'משימה'}\" — בוצע!"
            
            # Add recurring info if applicable
            if task and task.parent_recurring_id:
                pattern = task.get_recurring_pattern()
                if pattern:
                    pattern_desc = task_service._format_recurrence_pattern(pattern)
                    response_text += f"\n🔄 חוזר: {pattern_desc}"
                    # Show next occurrence date if available
                    if pattern.due_date:
                        import pytz as _pytz
                        _israel_tz = _pytz.timezone('Asia/Jerusalem')
                        next_local = pattern.due_date.replace(tzinfo=_pytz.UTC).astimezone(_israel_tz)
                        response_text += f"\n📅 המופע הבא: {next_local.strftime('%d/%m %H:%M')} (יופיע ברשימה אוטומטית)"
                    else:
                        response_text += "\n📅 המופע הבא יופיע ברשימה אוטומטית בחצות"
            
            whatsapp_service.send_message(user.phone_number, response_text)
        else:
            whatsapp_service.send_message(
                user.phone_number,
                f"❌ לא הצלחתי להשלים: {result_msg}"
            )
            
    except Exception as e:
        print(f"❌ Error processing reaction: {e}")
        import traceback
        traceback.print_exc()

def process_message_status(status):
    """Process message status update"""
    try:
        status_type = status.get('status')
        recipient_id = status.get('recipient_id')
        message_id = status.get('id')
        
        print(f"📊 Message {message_id} to {recipient_id}: {status_type}")
        
    except Exception as e:
        print(f"❌ Error processing message status: {e}")

def handle_basic_commands(user_id, text):
    """Handle basic bot commands"""
    text_lower = _normalize_command_text(text)
    
    # Full help command (all commands + examples)
    if text_lower in ['עזרה מלאה', 'full help', '/fullhelp', 'help full', 'כל הפקודות']:
        return """🤖 *כל הפקודות — מדריך מלא*

━━━━━━━━━━━━━━━━━━━━
📝 *יצירת משימות*
━━━━━━━━━━━━━━━━━━━━
• "להתקשר לאמא מחר ב-15:00"
• "פגישה ביום ראשון ב-10:00"
• "לקנות מצרכים היום"
• 🎤 אפשר להקליט — הבוט מבין קול

*תאריכים יחסיים:*
• "מחר ב-15:00" · "בעוד שעתיים" · "ביום ראשון ב-10:00"

*תאריכים מדויקים:*
• "31/10 בשעה 14:30" · "15/11/2025 ב-09:00"

━━━━━━━━━━━━━━━━━━━━
✅ *השלמת משימות*
━━━━━━━━━━━━━━━━━━━━
• לפי מספר: "סיימתי משימה 2"
• לפי שם: "סיימתי להתקשר לאמא"
• תגובת 👍 על הודעת משימה (לאחר "פירוט")
• "done with task 2" (אנגלית)

━━━━━━━━━━━━━━━━━━━━
✏️ *עדכון ומחיקה*
━━━━━━━━━━━━━━━━━━━━
• "שנה משימה 2 להתקשר לרופא" — שינוי תיאור
• "דחה משימה 1 למחר" — דחייה
• "העבר משימה 3 בעוד שעתיים" — דחייה
• "מחק משימה 3" — מחיקה
• "דחה משימות שעברו" — דחה את כולם לשעה הקרובה

━━━━━━━━━━━━━━━━━━━━
🔄 *משימות חוזרות*
━━━━━━━━━━━━━━━━━━━━
• "תזכיר לי כל יום ב-9 לקחת ויטמינים"
• "כל יום שני ורביעי ב-10 להתקשר"
• "כל שבוע פגישה עם המנהל"
• "כל יומיים להשקות צמחים"
• "כל ה-15 בחודש להעביר שכירות"

*ניהול סדרות:*
• "משימות חוזרות" — הצג סדרות פעילות
• "עצור סדרה [מספר]" — עצור ומחק עתידיות
• "השלם סדרה [מספר]" — סיים ושמור קיימות

━━━━━━━━━━━━━━━━━━━━
📅 *יומן Google*
━━━━━━━━━━━━━━━━━━━━
• "חבר יומן" — חיבור ל-Google Calendar
• "נתק יומן" — ניתוק
• "סטטוס יומן" — בדיקת חיבור
• "הצג יומן" — משימות + אירועים להיום
• "הגדרות יומן" — הגדר צבע / # לסנכרון
• "קבע צבע [1-11]" — איזה צבע יומן → משימה
• "הפעל #" / "כבה #" — זיהוי # בכותרת אירוע

━━━━━━━━━━━━━━━━━━━━
📋 *רשימות ושאילתות*
━━━━━━━━━━━━━━━━━━━━
• "משימות" / "?" — רשימה פתוחה
• "פירוט" — משימה לכל הודעה (לתגובות 👍)
• "הושלמו" — היסטוריה
• "סטטיסטיקה" — אחוז השלמה ונתונים
• "סיכום יומי" — סיכום המשימות להיום
• "מתי הפגישה עם יוחנן?" — חיפוש חכם
• "כמה משימות יש לי?" — ספירה

💬 תומך בעברית ואנגלית"""

    # Short help command — overview with link to full help
    elif text_lower in ['help', '/help', 'תפריט', 'עזרה']:
        return """🤖 *מה אתה רוצה לעשות?*

📝 *משימות*
• "לקנות חלב מחר ב-17:00" — יצירה
• "סיימתי משימה 2" — השלמה
• "מחק משימה 3" — מחיקה
• "דחה משימה 1 למחר" — דחייה
• "שנה משימה 2 להתקשר לרופא" — עריכה
• 🎤 אפשר גם להקליט במקום לכתוב

✅ *סימון השלמה מהיר (👍)*
כתוב "פירוט" → קבל משימה בהודעה נפרדת → הגב 👍

🔄 *משימות חוזרות*
• "תזכיר לי כל יום ב-9 לקחת ויטמינים"
• "כל שני ורביעי ב-10 פגישת צוות"
• "כל ה-15 בחודש להעביר שכירות"
ניהול: "משימות חוזרות" · "עצור סדרה [מספר]"

📅 *יומן Google*
• "חבר יומן" — חיבור ל-Google Calendar
• "הצג יומן" — מבט על היום (משימות + אירועים)
• "הגדרות יומן" — אילו אירועים הופכים למשימות

📋 *רשימות ונתונים*
• "משימות" — רשימה מלאה
• "סיכום יומי" — סיכום המשימות להיום
• "סטטיסטיקה" — נתוני ביצועים
• "הושלמו" — היסטוריה
• "דחה משימות שעברו" — העבר כולם לשעה הקרובה

📖 לרשימת *כל* הפקודות עם דוגמאות → כתוב *עזרה מלאה*"""
    
    # Task list commands - Enhanced to catch natural language variations
    elif (text_lower in ['tasks', 'my tasks', 'list', '/tasks', 'המשימות שלי', 'רשימה','משימות','?'] or
          any(word in text_lower for word in ['what are my tasks', 'show me tasks', 'what tasks do i have',
                                               'מה המשימות שלי', 'הצג משימות', 'איזה משימות יש לי',
                                               'show tasks', 'list tasks', 'my todo', 'הצג לי משימות'])):
        return handle_task_list_command(user_id)
    
    # NEW: Separate messages per task (for reactions)
    elif text_lower in ['משימות מפורד', 'משימות נפרד', 'tasks separate', 'פרט משימות','פירוט']:
        return handle_task_list_separate(user_id)
    
    elif text_lower in ['stats', 'statistics', '/stats', 'סטטיסטיקה']:
        return handle_stats_command(user_id)
    
    elif text_lower in ['completed', 'done', '/completed', 'הושלמו']:
        return handle_completed_tasks_command(user_id)
    
    elif text_lower in ['recurring', 'recurring tasks', 'משימות קבועות', 'משימות חוזרות', 'סדרות']:
        return handle_recurring_patterns_command(user_id)
    
    elif text_lower in (
        'delay_all_expired_tasks_to_today',
        '/delay_expired',
        'delay expired tasks',
        'דחה משימות שעברו',
        'הזז משימות שעברו להיום',
    ):
        from ..app import task_service
        return task_service.delay_all_overdue_to_next_hour(user_id)
    
    elif text_lower in ('סיכום יומי', 'סיכום משימות יומי', 'daily summary'):
        return handle_daily_summary_command(user_id)
    
    # Calendar integration commands
    elif any(cmd in text_lower for cmd in ['חבר יומן', 'חיבור יומן', 'connect calendar', 'link calendar']):
        return handle_calendar_connect_command(user_id)
    
    elif any(cmd in text_lower for cmd in ['נתק יומן', 'disconnect calendar', 'ניתוק יומן']):
        return handle_calendar_disconnect_command(user_id)
    
    elif any(cmd in text_lower for cmd in ['סטטוס יומן', 'calendar status', 'מצב יומן']):
        return handle_calendar_status_command(user_id)
    
    # Phase 2: Calendar settings (CHECK THIS FIRST - more specific than "יומן")
    elif any(cmd in text_lower for cmd in ['הגדרות יומן', 'calendar settings', 'הגדרות סנכרון', 'settings calendar']):
        return handle_calendar_settings_command(user_id)
    
    # Phase 2: Show full schedule (tasks + calendar events)
    elif any(cmd in text_lower for cmd in ['הצג יומן', 'show calendar', 'יומן', 'calendar']):
        return handle_show_calendar_command(user_id)
    
    # Phase 2: Set calendar color
    elif text_lower.startswith('קבע צבע ') or text_lower.startswith('set color '):
        return handle_set_calendar_color_command(user_id, text)
    
    # Phase 2: Toggle hashtag detection
    elif any(cmd in text_lower for cmd in ['כבה #', 'disable #', 'הפעל #', 'enable #', 'כבה סולמית', 'הפעל סולמית']):
        return handle_toggle_hashtag_command(user_id, text_lower)
    
    return None

def handle_daily_summary_command(user_id):
    """On-demand daily summary (same builder as 9 AM push; always returns a message)."""
    try:
        from ..models.database import User
        from ..services.daily_summary_service import DailySummaryService

        user = User.query.get(user_id)
        if not user:
            return "❌ שגיאה: משתמש לא נמצא"
        return DailySummaryService().build(user, source="on_demand")
    except Exception as e:
        print(f"❌ Error building daily summary: {e}")
        return "❌ שגיאה ביצירת הסיכום היומי. נסה שוב."

def handle_task_list_command(user_id):
    """Handle task list command"""
    try:
        from ..app import task_service
        tasks = task_service.get_user_tasks(user_id, status='pending', limit=20)
        
        if not tasks:
            return "📋 רשימתך ריקה — כתוב לי מה אתה צריך לעשות ואני אוסיף מיד.\nלמשל: \"להתקשר לאמא מחר ב-15:00\""
        
        # UX IMPROVEMENT: Use separate messages for small lists (< 10 items)
        if len(tasks) <= 5:
             return handle_task_list_separate(user_id)
             
        response = f"📋 **המשימות הממתינות שלך ({len(tasks)}):**\n\n"
        response += task_service.format_task_list(tasks)
        response += "\n\n💡 לסיום משימה עם תגובה: כתוב 'פירוט', ואז הגב עם 👍 על כל הודעת משימה"
        
        return response
        
    except Exception as e:
        print(f"❌ Error getting task list: {e}")
        return "❌ שגיאה בשליפת המשימות. נסה שוב."

def handle_task_list_separate(user_id):
    """Send each task as separate message for emoji reactions"""
    try:
        from ..app import whatsapp_service, task_service
        from ..models.database import User
        
        user = User.query.get(user_id)
        tasks = task_service.get_user_tasks(user_id, status='pending', limit=20)
        
        if not tasks:
            return "📋 רשימתך ריקה — כתוב לי מה אתה צריך לעשות ואני אוסיף מיד."
        
        # Send header
        whatsapp_service.send_message(
            user.phone_number,
            f"📋 המשימות שלך ({len(tasks)}):"
        )
        
        # Send each task separately
        for i, task in enumerate(tasks, 1):
            msg = f"{i}. {task.description} [#{task.id}]"
            
            if task.due_date:
                import pytz
                israel_tz = pytz.timezone('Asia/Jerusalem')
                local_time = task.due_date.replace(tzinfo=pytz.UTC).astimezone(israel_tz)
                msg += f"\n📅 {local_time.strftime('%d/%m %H:%M')}"
            
            result = whatsapp_service.send_message(user.phone_number, msg)
            
            # Store message ID mapping in Message table
            if result.get('success') and 'response' in result:
                messages = result['response'].get('messages', [])
                if messages:
                    msg_id = messages[0].get('id')
                    if msg_id:
                        save_task_message_mapping(user_id, msg_id, task.id)
        
        return "💡 לסיום משימה עם תגובה: כתוב 'פירוט', ואז הגב עם 👍 על כל הודעת משימה"
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return "❌ שגיאה בשליפת המשימות"

def save_task_message_mapping(user_id, whatsapp_message_id, task_id):
    """Store mapping between WhatsApp message and task ID"""
    try:
        from ..models.database import Message, db
        
        # Use Message table to store the mapping
        mapping = Message(
            user_id=user_id,
            message_type='task_reference',
            whatsapp_message_id=whatsapp_message_id
        )
        mapping.content = str(task_id)  # Store task ID
        db.session.add(mapping)
        db.session.commit()
    except Exception as e:
        print(f"Error saving message mapping: {e}")

def handle_stats_command(user_id):
    """Handle stats command"""
    try:
        from ..app import task_service
        stats = task_service.get_task_stats(user_id)
        
        return f"""📊 **הסטטיסטיקות שלך:**

📝 סה"כ משימות: {stats['total']}
⏳ ממתינות: {stats['pending']}
✅ הושלמו: {stats['completed']}
📅 יעד להיום: {stats['due_today']}
⚠️ באיחור: {stats['overdue']}
🎯 אחוז השלמה: {stats['completion_rate']}%

המשך כך! עבודה מצוינת! 🚀"""
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return "❌ שגיאה בשליפת הסטטיסטיקה. נסה שוב."

def handle_completed_tasks_command(user_id):
    """Handle completed tasks command"""
    try:
        from ..app import task_service
        tasks = task_service.get_user_tasks(user_id, status='completed', limit=10, include_patterns_when_completed=True)
        
        if not tasks:
            return "✅ עדיין לא השלמת משימות — כתוב \"משימות\" לרשימה הפתוחה."
        
        response = f"✅ **המשימות האחרונות שהושלמו ({len(tasks)}):**\n\n"
        response += task_service.format_task_list(tasks, show_due_date=False)
        response += f"\n\n🎉 עבודה מצוינת! השלמת {len(tasks)} משימות!"
        
        return response
        
    except Exception as e:
        print(f"❌ Error getting completed tasks: {e}")
        return "❌ שגיאה בשליפת המשימות שהושלמו. נסה שוב."

def handle_recurring_patterns_command(user_id):
    """Show active recurring patterns"""
    try:
        from ..app import task_service
        patterns = task_service.get_recurring_patterns(user_id, active_only=True)
        
        if not patterns:
            return "📋 אין לך משימות חוזרות פעילות"
        
        response = f"🔄 **המשימות החוזרות שלך ({len(patterns)}):**\n\n(הזמן בתבנית = המופע הבא)\n\n"
        for i, pattern in enumerate(patterns, 1):
            pattern_desc = task_service._format_recurrence_pattern(pattern)
            response += f"{i}. {pattern.description} - {pattern_desc} [#{pattern.id}]\n"
            if pattern.due_date:
                lt = pattern.due_date.replace(tzinfo=pytz.UTC).astimezone(task_service.israel_tz)
                response += f"   שעה: {lt.strftime('%H:%M')}\n"
            response += f"   נוצרו {pattern.recurring_instance_count} מופעים\n"
        
        response += "\n💡 **לניהול:**"
        response += "\n• 'עצור סדרה [מספר]' - עצור ומחק עתידיות"
        response += "\n• 'השלם סדרה [מספר]' - סיים ושמור קיימות"
        
        return response
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return "❌ שגיאה בשליפת משימות חוזרות"

def handle_calendar_connect_command(user_id):
    """Handle calendar connect command"""
    try:
        from ..config.settings import Config
        from ..models.database import User
        
        user = User.query.get(user_id)
        if not user:
            return "❌ שגיאה: משתמש לא נמצא"
        
        base_url = Config.BASE_URL
        if not base_url:
            return "❌ שגיאה: BASE_URL לא מוגדר. אנא פנה לתמיכה."
        
        connect_url = f"{base_url}/calendar/connect/{user_id}"
        
        response = f"""📅 *חיבור ל-Google Calendar*

לחץ על הקישור → אשר גישה ליומן → חזור לכאן ✅

🔗 {connect_url}

אחרי החיבור, כל משימה שיש לה תאריך יעד תופיע אוטומטית ביומן שלך — אין צורך לעשות כלום נוסף.

🔒 הגישה מאובטחת """
        
        return response
        
    except Exception as e:
        print(f"❌ Error handling calendar connect: {e}")
        return "❌ שגיאה ביצירת קישור החיבור. נסה שוב מאוחר יותר."

def handle_calendar_disconnect_command(user_id):
    """Handle calendar disconnect command"""
    try:
        from ..services.calendar_service import CalendarService
        
        calendar_service = CalendarService()
        success, message = calendar_service.disconnect_calendar(user_id)
        
        if success:
            return f"✅ {message}"
        else:
            return f"❌ {message}"
            
    except Exception as e:
        print(f"❌ Error handling calendar disconnect: {e}")
        return "❌ שגיאה בניתוק היומן. נסה שוב מאוחר יותר."

def handle_calendar_status_command(user_id):
    """Handle calendar status command"""
    try:
        from ..models.database import User
        
        user = User.query.get(user_id)
        if not user:
            return "❌ שגיאה: משתמש לא נמצא"
        
        if user.google_calendar_enabled:
            return """✅ *היומן שלך מחובר ופעיל*

• משימות עם תאריך יעד → מופיעות ביומן אוטומטית
• "הצג יומן" → מבט על היום (משימות + אירועים)
• "הגדרות יומן" → הגדר אילו אירועים הופכים למשימות

לניתוק: כתוב "נתק יומן\""""
        else:
            return """❌ *היומן שלך לא מחובר*

כתוב "חבר יומן" כדי לחבר את Google Calendar שלך.
אחרי החיבור, כל משימה עם תאריך יעד תתווסף ליומן אוטומטית."""
            
    except Exception as e:
        print(f"❌ Error handling calendar status: {e}")
        return "❌ שגיאה בבדיקת סטטוס היומן. נסה שוב מאוחר יותר."

def handle_show_calendar_command(user_id):
    """Handle show calendar command - displays tasks + calendar events (Phase 2)"""
    try:
        from ..models.database import User
        from ..app import ai_service
        
        user = User.query.get(user_id)
        if not user:
            return "❌ שגיאה: משתמש לא נמצא"
        
        if not user.google_calendar_enabled:
            return "❌ היומן לא מחובר. כתוב \"חבר יומן\" כדי להתחבר."
        
        # Get full schedule (tasks + events) for today
        if ai_service:
            try:
                schedule = ai_service.get_full_schedule(user, 'today')
                return ai_service.format_schedule_response(schedule)
            except Exception as e:
                print(f"❌ Error getting full schedule: {e}")
                return "❌ שגיאה בהצגת היומן. נסה שוב מאוחר יותר."
        else:
            return "❌ שירות היומן לא זמין כרגע. נסה שוב מאוחר יותר."
            
    except Exception as e:
        print(f"❌ Error handling show calendar: {e}")
        return "❌ שגיאה בהצגת היומן. נסה שוב מאוחר יותר."

def handle_calendar_settings_command(user_id):
    """Handle calendar settings command - show current settings and options (Phase 2)"""
    try:
        from ..models.database import User
        
        user = User.query.get(user_id)
        if not user:
            return "❌ שגיאה: משתמש לא נמצא"
        
        if not user.google_calendar_enabled:
            return "❌ היומן לא מחובר. כתוב \"חבר יומן\" כדי להתחבר."
        
        # Show current settings
        color_names = {
            '1': 'Lavender (סגול בהיר)',
            '2': 'Sage (ירוק חכם)',
            '3': 'Grape (ענבים)',
            '4': 'Flamingo (ורוד)',
            '5': 'Banana (צהוב)',
            '6': 'Tangerine (כתום)',
            '7': 'Peacock (טורקיז)',
            '8': 'Graphite (אפור)',
            '9': 'Blueberry (כחול)',
            '10': 'Basil (ירוק בזיליקום)',
            '11': 'Tomato (אדום)'
        }
        
        current_color = user.calendar_sync_color
        if current_color:
            color_display = f"{color_names.get(current_color, current_color)}"
        else:
            color_display = "לא מוגדר"
        
        hashtag_status = "מופעל ✅" if user.calendar_sync_hashtag else "כבוי ❌"
        
        message = f"""⚙️ **הגדרות סנכרון יומן**

🎨 **צבע אירועים למשימות:** {color_display}
#️⃣ **זיהוי סימן # בכותרת:** {hashtag_status}

**איך זה עובד?**
אירועים שיוצרים ב-Google Calendar עם הצבע שבחרת או עם # בכותרת יהפכו אוטומטית למשימות בבוט (תוך 10 דקות).

**שינוי צבע:**
כתוב "קבע צבע [מספר]" - למשל:
• "קבע צבע 1" - Lavender
• "קבע צבע 9" - Blueberry
• "קבע צבע 11" - Tomato

**זיהוי סימן #:**
• "כבה #" - כיבוי זיהוי אוטומטי של #
• "הפעל #" - הפעלה מחדש

💡 **טיפ:** אם לא מגדיר צבע, רק אירועים עם # בכותרת יהפכו למשימות."""
        
        return message
        
    except Exception as e:
        print(f"❌ Error handling calendar settings: {e}")
        return "❌ שגיאה בהצגת הגדרות. נסה שוב מאוחר יותר."

def handle_set_calendar_color_command(user_id, text):
    """Handle set calendar color command (Phase 2)"""
    try:
        from ..models.database import User, db
        
        user = User.query.get(user_id)
        if not user:
            return "❌ שגיאה: משתמש לא נמצא"
        
        if not user.google_calendar_enabled:
            return "❌ חבר את היומן קודם (כתוב 'חבר יומן')"
        
        # Extract color ID
        text_lower = text.lower().strip()
        if text_lower.startswith('קבע צבע '):
            color_id = text_lower.replace('קבע צבע ', '').strip()
        elif text_lower.startswith('set color '):
            color_id = text_lower.replace('set color ', '').strip()
        else:
            return "❌ פורמט לא נכון. כתוב: 'קבע צבע [מספר]' (למשל: 'קבע צבע 1')"
        
        # Validate color ID (1-11)
        valid_colors = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11']
        if color_id not in valid_colors:
            return f"""❌ מספר צבע לא תקין. בחר מספר בין 1-11:

1 - Lavender (סגול בהיר)
2 - Sage (ירוק חכם)
3 - Grape (ענבים)
4 - Flamingo (ורוד)
5 - Banana (צהוב)
6 - Tangerine (כתום)
7 - Peacock (טורקיז)
8 - Graphite (אפור)
9 - Blueberry (כחול)
10 - Basil (ירוק)
11 - Tomato (אדום)"""
        
        # Update user settings
        user.calendar_sync_color = color_id
        db.session.commit()
        
        color_names = {
            '1': 'Lavender', '2': 'Sage', '3': 'Grape', '4': 'Flamingo',
            '5': 'Banana', '6': 'Tangerine', '7': 'Peacock', '8': 'Graphite',
            '9': 'Blueberry', '10': 'Basil', '11': 'Tomato'
        }
        
        print(f"✅ User {user_id} set calendar color to {color_id}")
        
        return f"""✅ **צבע עודכן בהצלחה!**

🎨 צבע: {color_names.get(color_id, color_id)}

עכשיו, כל אירוע שתיצור ב-Google Calendar בצבע {color_names.get(color_id, color_id)} יהפוך אוטומטית למשימה בבוט תוך 10 דקות!

💡 זיהוי # עדיין פעיל - אירועים עם # בכותרת גם יהפכו למשימות."""
        
    except Exception as e:
        print(f"❌ Error setting calendar color: {e}")
        db.session.rollback()
        return "❌ שגיאה בעדכון הצבע. נסה שוב."

def handle_toggle_hashtag_command(user_id, text_lower):
    """Handle toggle hashtag detection command (Phase 2)"""
    try:
        from ..models.database import User, db
        
        user = User.query.get(user_id)
        if not user:
            return "❌ שגיאה: משתמש לא נמצא"
        
        if not user.google_calendar_enabled:
            return "❌ חבר את היומן קודם (כתוב 'חבר יומן')"
        
        # Determine if enabling or disabling
        enable = any(cmd in text_lower for cmd in ['הפעל #', 'enable #', 'הפעל סולמית'])
        disable = any(cmd in text_lower for cmd in ['כבה #', 'disable #', 'כבה סולמית'])
        
        if enable:
            user.calendar_sync_hashtag = True
            db.session.commit()
            print(f"✅ User {user_id} enabled hashtag detection")
            return """✅ **זיהוי # הופעל!**

#️⃣ אירועים עם סימן # בכותרת יהפכו אוטומטית למשימות.

דוגמה: אירוע בשם "# לקנות מצרכים" יהפוך למשימה."""
        
        elif disable:
            user.calendar_sync_hashtag = False
            db.session.commit()
            print(f"✅ User {user_id} disabled hashtag detection")
            
            if user.calendar_sync_color:
                return f"""✅ **זיהוי # כובה**

#️⃣ אירועים עם # לא יהפכו יותר למשימות אוטומטית.

💡 רק אירועים בצבע {user.calendar_sync_color} יהפכו למשימות."""
            else:
                return """⚠️ **זיהוי # כובה**

#️⃣ אירועים עם # לא יהפכו יותר למשימות אוטומטית.

⚠️ שים לב: לא הגדרת צבע! אירועים לא יהפכו למשימות.
כתוב 'הגדרות יומן' כדי להגדיר צבע."""
        
        else:
            return "❌ פקודה לא מזוהה. כתוב 'הפעל #' או 'כבה #'"
        
    except Exception as e:
        print(f"❌ Error toggling hashtag: {e}")
        db.session.rollback()
        return "❌ שגיאה בעדכון ההגדרות. נסה שוב."

def handle_button_click(user_id, button_id):
    """Handle button click"""
    if button_id == 'help':
        return handle_basic_commands(user_id, 'help')
    elif button_id == 'tasks':
        return handle_task_list_command(user_id)
    elif button_id == 'stats':
        return handle_stats_command(user_id)
    else:
        return "🤖 איך אוכל לעזור לך היום?"
