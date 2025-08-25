"""
API routes for external integrations and data access
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta

from ..models.database import db, User, Message, Task
from ..services.task_service import TaskService

bp = Blueprint('api', __name__, url_prefix='/api')
task_service = TaskService()

@bp.route('/stats/system')
def system_stats():
    """Get system-wide statistics"""
    try:
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        stats = {
            "timestamp": now.isoformat(),
            "users": {
                "total": User.query.count(),
                "new_today": User.query.filter(User.created_at >= yesterday).count(),
                "new_this_week": User.query.filter(User.created_at >= week_ago).count(),
                "active_today": User.query.filter(User.last_active >= yesterday).count()
            },
            "messages": {
                "total": Message.query.count(),
                "today": Message.query.filter(Message.created_at >= yesterday).count(),
                "this_week": Message.query.filter(Message.created_at >= week_ago).count()
            },
            "tasks": {
                "total": Task.query.count(),
                "pending": Task.query.filter_by(status='pending').count(),
                "completed": Task.query.filter_by(status='completed').count(),
                "created_today": Task.query.filter(Task.created_at >= yesterday).count(),
                "completed_today": Task.query.filter(
                    Task.completed_at >= yesterday,
                    Task.status == 'completed'
                ).count()
            }
        }
        
        # Calculate completion rate
        if stats["tasks"]["total"] > 0:
            stats["tasks"]["completion_rate"] = round(
                stats["tasks"]["completed"] / stats["tasks"]["total"] * 100, 2
            )
        else:
            stats["tasks"]["completion_rate"] = 0
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/health')
def api_health():
    """API health check"""
    try:
        # Test database
        db.session.execute("SELECT 1")
        
        # Check services
        from ..app import ai_service, whatsapp_service
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "connected",
                "ai_service": "active" if ai_service else "inactive",
                "whatsapp_service": "active" if whatsapp_service else "inactive"
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 500

@bp.route('/tasks/due-soon')
def get_due_tasks():
    """Get tasks due soon for monitoring"""
    try:
        # Get tasks due in the next 24 hours
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        
        due_tasks = Task.query.filter(
            Task.status == 'pending',
            Task.due_date >= now,
            Task.due_date <= tomorrow
        ).order_by(Task.due_date.asc()).all()
        
        # Get overdue tasks
        overdue_tasks = Task.query.filter(
            Task.status == 'pending',
            Task.due_date < now
        ).order_by(Task.due_date.asc()).limit(50).all()
        
        return jsonify({
            "due_soon": [{
                "id": task.id,
                "user_id": task.user_id,
                "description": task.description[:100],
                "due_date": task.due_date.isoformat() if task.due_date else None
            } for task in due_tasks],
            "overdue": [{
                "id": task.id,
                "user_id": task.user_id,
                "description": task.description[:100],
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "days_overdue": (now - task.due_date).days if task.due_date else 0
            } for task in overdue_tasks],
            "count": {
                "due_soon": len(due_tasks),
                "overdue": len(overdue_tasks)
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/users/<int:user_id>/tasks')
def get_user_tasks(user_id):
    """Get tasks for a specific user"""
    try:
        status = request.args.get('status', 'pending')
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        tasks = task_service.get_user_tasks(user_id, status, limit)
        
        task_data = [{
            "id": task.id,
            "description": task.description,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        } for task in tasks]
        
        return jsonify({
            "user_id": user_id,
            "status_filter": status,
            "tasks": task_data,
            "count": len(task_data)
        })
        
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/users/<int:user_id>/stats')
def get_user_stats(user_id):
    """Get statistics for a specific user"""
    try:
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        stats = task_service.get_task_stats(user_id)
        
        return jsonify({
            "user_id": user_id,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_active": user.last_active.isoformat() if user.last_active else None,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/metrics')
def get_metrics():
    """Get metrics in Prometheus format (for monitoring)"""
    try:
        # Basic metrics
        total_users = User.query.count()
        total_messages = Message.query.count()
        total_tasks = Task.query.count()
        pending_tasks = Task.query.filter_by(status='pending').count()
        completed_tasks = Task.query.filter_by(status='completed').count()
        
        # Recent activity
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        messages_24h = Message.query.filter(Message.created_at >= yesterday).count()
        tasks_created_24h = Task.query.filter(Task.created_at >= yesterday).count()
        
        metrics = f"""# HELP whatsapp_bot_users_total Total number of users
# TYPE whatsapp_bot_users_total gauge
whatsapp_bot_users_total {total_users}

# HELP whatsapp_bot_messages_total Total number of messages
# TYPE whatsapp_bot_messages_total gauge
whatsapp_bot_messages_total {total_messages}

# HELP whatsapp_bot_messages_24h Messages in last 24 hours
# TYPE whatsapp_bot_messages_24h gauge
whatsapp_bot_messages_24h {messages_24h}

# HELP whatsapp_bot_tasks_total Total number of tasks
# TYPE whatsapp_bot_tasks_total gauge
whatsapp_bot_tasks_total {total_tasks}

# HELP whatsapp_bot_tasks_pending Pending tasks
# TYPE whatsapp_bot_tasks_pending gauge
whatsapp_bot_tasks_pending {pending_tasks}

# HELP whatsapp_bot_tasks_completed Completed tasks
# TYPE whatsapp_bot_tasks_completed gauge
whatsapp_bot_tasks_completed {completed_tasks}

# HELP whatsapp_bot_tasks_created_24h Tasks created in last 24 hours
# TYPE whatsapp_bot_tasks_created_24h gauge
whatsapp_bot_tasks_created_24h {tasks_created_24h}
"""
        
        return metrics, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        return f"# Error getting metrics: {str(e)}", 500, {'Content-Type': 'text/plain'}