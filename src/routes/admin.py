"""
Admin routes for system management and monitoring
"""
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
import os

from ..models.database import db, User, Message, Task
from ..services.task_service import TaskService

bp = Blueprint('admin', __name__, url_prefix='/admin')
task_service = TaskService()

@bp.route('/')
def landing():
    """Landing page"""
    return """
    <html>
        <head><title>WhatsApp Todo Bot</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
            <h1>🤖 WhatsApp Todo Bot</h1>
            <p>An AI-powered personal assistant for task management via WhatsApp.</p>
            
            <h2>🚀 Features</h2>
            <ul>
                <li>📝 Smart task extraction from natural language</li>
                <li>🗓️ Due date parsing and reminders</li>
                <li>🌐 Multi-language support (Hebrew, English, Arabic)</li>
                <li>📊 Productivity statistics and insights</li>
                <li>🔒 End-to-end encryption for user data</li>
            </ul>
            
            <h2>🔗 Links</h2>
            <ul>
                <li><a href="/admin/dashboard">📊 Admin Dashboard</a></li>
                <li><a href="/admin/health">🏥 Health Check</a></li>
                <li><a href="/admin/stats">📈 System Stats</a></li>
            </ul>
            
            <p><em>Add the bot to WhatsApp to get started!</em></p>
        </body>
    </html>
    """

@bp.route('/dashboard')
def dashboard():
    """Admin dashboard"""
    try:
        # Get basic stats
        total_users = User.query.count()
        total_messages = Message.query.count()
        total_tasks = Task.query.count()
        pending_tasks = Task.query.filter_by(status='pending').count()
        completed_tasks = Task.query.filter_by(status='completed').count()
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        new_users_today = User.query.filter(User.created_at >= yesterday).count()
        messages_today = Message.query.filter(Message.created_at >= yesterday).count()
        tasks_created_today = Task.query.filter(Task.created_at >= yesterday).count()
        
        stats = {
            'total_users': total_users,
            'total_messages': total_messages,
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
            'new_users_today': new_users_today,
            'messages_today': messages_today,
            'tasks_created_today': tasks_created_today
        }
        
        # Check service availability
        from ..app import ai_service, whatsapp_service, redis_client
        
        template_data = {
            'stats': stats,
            'redis_available': redis_client is not None,
            'ai_service_available': ai_service is not None,
            'whatsapp_service_available': whatsapp_service is not None,
            'uptime': 'Unknown'  # TODO: Implement uptime tracking
        }
        
        return render_template('dashboard.html', **template_data)
        
    except Exception as e:
        return f"<h1>❌ Dashboard Error</h1><p>{str(e)}</p>", 500

@bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute("SELECT 1")
        db_status = "✅ Connected"
    except Exception as e:
        db_status = f"❌ Error: {str(e)}"
    
    # Check services
    from ..app import ai_service, whatsapp_service
    ai_status = "✅ Active" if ai_service else "⚠️ Not initialized"
    whatsapp_status = "✅ Active" if whatsapp_service else "⚠️ Not initialized"
    
    health_data = {
        "status": "healthy" if "❌" not in f"{db_status}{ai_status}{whatsapp_status}" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_status,
            "ai_service": ai_status,
            "whatsapp_service": whatsapp_status
        }
    }
    
    status_code = 200 if health_data["status"] == "healthy" else 503
    return jsonify(health_data), status_code

@bp.route('/stats')
def get_stats():
    """Get system statistics"""
    try:
        # Basic counts
        stats = {
            "users": {
                "total": User.query.count(),
                "active_last_24h": User.query.filter(User.last_active >= datetime.utcnow() - timedelta(days=1)).count(),
                "new_last_7d": User.query.filter(User.created_at >= datetime.utcnow() - timedelta(days=7)).count()
            },
            "messages": {
                "total": Message.query.count(),
                "last_24h": Message.query.filter(Message.created_at >= datetime.utcnow() - timedelta(days=1)).count(),
                "last_7d": Message.query.filter(Message.created_at >= datetime.utcnow() - timedelta(days=7)).count()
            },
            "tasks": {
                "total": Task.query.count(),
                "pending": Task.query.filter_by(status='pending').count(),
                "completed": Task.query.filter_by(status='completed').count(),
                "created_last_24h": Task.query.filter(Task.created_at >= datetime.utcnow() - timedelta(days=1)).count()
            }
        }
        
        # Add completion rate
        total_tasks = stats["tasks"]["total"]
        completed_tasks = stats["tasks"]["completed"]
        stats["tasks"]["completion_rate"] = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/users')
def get_users():
    """Get user list (limited info for privacy)"""
    try:
        users = User.query.order_by(User.created_at.desc()).limit(100).all()
        
        user_data = []
        for user in users:
            user_info = {
                "id": user.id,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_active": user.last_active.isoformat() if user.last_active else None,
                "message_count": user.get_message_count(),
                "task_count": user.get_task_count(),
                "pending_tasks": user.get_pending_tasks_count(),
                "completed_tasks": user.get_completed_tasks_count()
            }
            user_data.append(user_info)
        
        return jsonify({
            "users": user_data,
            "total_count": User.query.count()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500