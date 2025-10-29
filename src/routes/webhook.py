"""
WhatsApp webhook routes for handling incoming messages
"""
import json
import base64
import requests
from flask import Blueprint, request, jsonify
from datetime import datetime

from ..models.database import db, User, Message
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
                "⚠️ You're sending messages too quickly. Please wait a moment before sending another message."
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
        else:
            # Handle unsupported message types
            whatsapp_service.send_message(
                from_number,
                f"🤖 I received your {message_type} message, but I can only process text and voice messages right now. Please send me a text message!"
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
                "⚠️ Your message contains invalid content. Please send a different message."
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
        
        # Execute parsed tasks
        task_summary = ""
        has_action = False
        
        if parsed_tasks:
            task_summary = task_service.execute_parsed_tasks(user.id, parsed_tasks, sanitized_text)
            # Check if there's an action (not query)
            has_action = any(task.get('action') in ['complete', 'delete', 'add', 'update', 'reschedule'] for task in parsed_tasks)
        
        # Build response intelligently
        if has_action and task_summary:
            # For actions (complete/delete/add) - only show execution result
            full_response = task_summary
        elif task_summary:
            # For queries - combine AI response with data
            full_response = f"{ai_response}\n\n{task_summary}"
        else:
            # No task operations - just AI response
            full_response = ai_response
        
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
            "🤖 Sorry, I'm having trouble processing your message right now. Please try again in a moment."
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
    if text_lower in ['help', '/help', '?', 'עזרה']:
        return """🤖 WhatsApp Todo Bot Help

📝 **Task Management:**
• Just tell me what you need to do and I'll create tasks
• Say "my tasks" to see pending tasks  
• Say "stats" for your productivity stats
• React with 👍 to mark tasks as done

📅 **Due Dates:**
• "Call mom tomorrow at 3pm"
• "Meeting on Sunday at 10am" 
• "Buy groceries today"

💬 **Languages:** I support Hebrew, English, Arabic and more!

🔧 **Commands:**
• help - Show this help
• tasks - List pending tasks
• stats - Show statistics
• completed - Show completed tasks"""
    
    # Task list commands
    elif text_lower in ['tasks', 'my tasks', 'list', '/tasks', 'המשימות שלי', 'רשימה']:
        return handle_task_list_command(user_id)
    
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
            return "📋 You don't have any pending tasks! Send me a message about something you need to do."
        
        response = f"📋 **Your Pending Tasks ({len(tasks)}):**\n\n"
        response += task_service.format_task_list(tasks)
        response += "\n\n💡 React with 👍 to any task message to mark it as completed!"
        
        return response
        
    except Exception as e:
        print(f"❌ Error getting task list: {e}")
        return "❌ Error retrieving your tasks. Please try again."

def handle_stats_command(user_id):
    """Handle stats command"""
    try:
        stats = task_service.get_task_stats(user_id)
        
        return f"""📊 **Your Productivity Stats:**

📝 Total Tasks: {stats['total']}
⏳ Pending: {stats['pending']}
✅ Completed: {stats['completed']}
📅 Due Today: {stats['due_today']}
⚠️ Overdue: {stats['overdue']}
🎯 Completion Rate: {stats['completion_rate']}%

Keep up the great work! 🚀"""
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return "❌ Error retrieving your statistics. Please try again."

def handle_completed_tasks_command(user_id):
    """Handle completed tasks command"""
    try:
        tasks = task_service.get_user_tasks(user_id, status='completed', limit=10)
        
        if not tasks:
            return "✅ You haven't completed any tasks yet. Keep working on your pending tasks!"
        
        response = f"✅ **Your Recently Completed Tasks ({len(tasks)}):**\n\n"
        response += task_service.format_task_list(tasks, show_due_date=False)
        response += f"\n\n🎉 Great job completing {len(tasks)} tasks!"
        
        return response
        
    except Exception as e:
        print(f"❌ Error getting completed tasks: {e}")
        return "❌ Error retrieving your completed tasks. Please try again."

def handle_button_click(user_id, button_id):
    """Handle button click"""
    if button_id == 'help':
        return handle_basic_commands(user_id, 'help')
    elif button_id == 'tasks':
        return handle_task_list_command(user_id)
    elif button_id == 'stats':
        return handle_stats_command(user_id)
    else:
        return "🤖 Button clicked! How can I help you today?"
