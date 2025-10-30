"""
WhatsApp webhook routes for handling incoming messages
"""
import json
import base64
import requests
from flask import Blueprint, request, jsonify
from datetime import datetime

from ..models.database import db, User, Message, Task
from ..services.encryption import encryption_service
from ..services.task_service import TaskService
from ..utils.validation import InputValidator

bp = Blueprint('webhook', __name__)
task_service = TaskService()

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

@bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.json
        
        if not data or 'entry' not in data:
            return jsonify({"status": "ok"}), 200
        
        # Process each entry
        for entry in data['entry']:
            if 'changes' not in entry:
                continue
                
            for change in entry['changes']:
                if change.get('field') != 'messages':
                    continue
                
                value = change.get('value', {})
                
                # Handle incoming messages
                if 'messages' in value:
                    for message in value['messages']:
                        process_incoming_message(message, value)
                
                # Handle message status updates
                if 'statuses' in value:
                    for status in value['statuses']:
                        process_message_status(status)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

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
        
        print(f"📱 Incoming {message_type} message from {from_number}")
        print(f"🔍 Message structure: {json.dumps(message, indent=2)}")
        
        # Get or create user
        user = get_or_create_user(from_number)
        
        # Validate rate limits
        if not InputValidator.validate_user_rate_limit(user.id):
            whatsapp_service.send_message(
                from_number,
                "⚠️ אתה שולח הודעות מהר מדי. חכה רגע לפני שליחת הודעה נוספת."
            )
            return
        
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
        
        # Get AI response and parse tasks
        ai_response = ai_service.get_response(user.id, sanitized_text)
        parsed_tasks = ai_service.parse_tasks(sanitized_text)
        
        # Debug: Show what AI parsed
        print(f"🔥 DEBUG - Parsed {len(parsed_tasks) if parsed_tasks else 0} tasks from text message")
        if parsed_tasks:
            for idx, task in enumerate(parsed_tasks):
                print(f"   Task {idx+1}: action={task.get('action')}, task_id={task.get('task_id')}, description={task.get('description')}, due_date={task.get('due_date')}")
        else:
            print(f"   ⚠️ No tasks parsed! AI response was: {ai_response[:100]}")
        
        # Execute parsed tasks
        task_summary = ""
        has_action = False
        
        if parsed_tasks:
            task_summary = task_service.execute_parsed_tasks(user.id, parsed_tasks, sanitized_text)
            print(f"🔥 DEBUG - Execution result: {task_summary[:200] if task_summary else '(empty)'}")
            # Check if there's an action (not query)
            has_action = any(task.get('action') in ['complete', 'delete', 'add', 'update', 'reschedule'] for task in parsed_tasks)
        
        # Build response intelligently
        if has_action and task_summary:
            # For actions (complete/delete/add) - only show execution result
            full_response = task_summary
            print(f"🔥 DEBUG - Sending execution result only")
        elif task_summary:
            # For queries - combine AI response with data
            full_response = f"{ai_response}\n\n{task_summary}"
            print(f"🔥 DEBUG - Sending AI response + task summary")
        else:
            # No task operations - just AI response
            full_response = ai_response
            print(f"🔥 DEBUG - ⚠️ Sending AI response only (no execution)!")
        
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
            "🤖 מצטער, אני מתקשה לעבד את ההודעה שלך כרגע. אנא נסה שוב בעוד רגע."
        )

def process_voice_message(message, user, whatsapp_service, ai_service):
    """Process voice message using Gemini multimodal API"""
    try:
        from ..app import ai_service
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
            whatsapp_service.send_message(
                user.phone_number,
                "🎤 קיבלתי את ההודעה הקולית, אבל לא זיהיתי משימות. אם רצית ליצור משימה, נסה שוב או כתוב הודעת טקסט."
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
            "❌ שגיאה בעיבוד ההודעה הקולית. אפשר לנסות שוב או לכתוב הודעה."
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
        
        # Complete the task
        success, result_msg = task_service.complete_task(task_id, user.id)
        
        if success:
            task = Task.query.get(task_id)
            whatsapp_service.send_message(
                user.phone_number,
                f"✅ השלמתי: {task.description if task else 'משימה'}"
            )
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
    text_lower = text.lower().strip()
    
    # Help command
    if text_lower in ['help', '/help', 'תפריט', 'עזרה']:
        return """🤖 עזרה - בוט המשימות בוואטסאפ

📝 **ניהול משימות:**
• פשוט ספר לי מה אתה צריך לעשות ואני אצור משימות
• כתוב "המשימות שלי" או ? כדי לראות משימות ממתינות
• כתוב "סטטיסטיקה" לנתוני ביצועים שלך
• הגב עם 👍 כדי לסמן משימות כהושלמו
• אפשר להקליט כדי ליצור משימות

📅 **תאריכי יעד:**
• "להתקשר לאמא מחר ב-15:00"
• "פגישה ביום ראשון ב-10:00" 
• "לקנות מצרכים היום"

💬 **שפות:** אני תומך בעברית, אנגלית, ערבית ועוד!

🔧 **פקודות:**
• עזרה - הצג עזרה זו
• המשימות שלי \ ? - הצג רשימת משימות
• פירוט - הצג כל משימה בנפרד (לתגובות 👍)
• סטטיסטיקה - הצג נתונים
• הושלמו - הצג משימות שהושלמו"""
    
    # Task list commands
    elif text_lower in ['tasks', 'my tasks', 'list', '/tasks', 'המשימות שלי', 'רשימה','משימות','?']:
        return handle_task_list_command(user_id)
    
    # NEW: Separate messages per task (for reactions)
    elif text_lower in ['משימות מפורד', 'משימות נפרד', 'tasks separate', 'פרט משימות','פירוט']:
        return handle_task_list_separate(user_id)
    
    elif text_lower in ['stats', 'statistics', '/stats', 'סטטיסטיקה']:
        return handle_stats_command(user_id)
    
    elif text_lower in ['completed', 'done', '/completed', 'הושלמו']:
        return handle_completed_tasks_command(user_id)
    
    return None

def handle_task_list_command(user_id):
    """Handle task list command"""
    try:
        tasks = task_service.get_user_tasks(user_id, status='pending', limit=20)
        
        if not tasks:
            return "📋 אין לך משימות ממתינות! שלח לי הודעה על משהו שאתה צריך לעשות."
        
        response = f"📋 **המשימות הממתינות שלך ({len(tasks)}):**\n\n"
        response += task_service.format_task_list(tasks)
        response += "\n\n💡 הגב עם 👍 לכל הודעת משימה כדי לסמן כהושלמה!"
        
        return response
        
    except Exception as e:
        print(f"❌ Error getting task list: {e}")
        return "❌ שגיאה בשליפת המשימות. נסה שוב."

def handle_task_list_separate(user_id):
    """Send each task as separate message for emoji reactions"""
    try:
        from ..app import whatsapp_service
        from ..models.database import User
        
        user = User.query.get(user_id)
        tasks = task_service.get_user_tasks(user_id, status='pending', limit=20)
        
        if not tasks:
            return "📋 אין לך משימות ממתינות!"
        
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
        
        return "לסיום משימה הגב עליה עם האימוגי  👍 "
        
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
        tasks = task_service.get_user_tasks(user_id, status='completed', limit=10)
        
        if not tasks:
            return "✅ עדיין לא השלמת משימות. המשך לעבוד על המשימות הממתינות!"
        
        response = f"✅ **המשימות האחרונות שהושלמו ({len(tasks)}):**\n\n"
        response += task_service.format_task_list(tasks, show_due_date=False)
        response += f"\n\n🎉 עבודה מצוינת! השלמת {len(tasks)} משימות!"
        
        return response
        
    except Exception as e:
        print(f"❌ Error getting completed tasks: {e}")
        return "❌ שגיאה בשליפת המשימות שהושלמו. נסה שוב."

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
