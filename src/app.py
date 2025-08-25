"""
Main Flask application for WhatsApp Todo Bot
"""
import os
from flask import Flask
from flask_migrate import Migrate

from .config.settings import config
from .models.database import db, init_database
from .services.encryption import encryption_service
from .services.ai_service import AIService
from .services.whatsapp_service import WhatsAppService
from .services.task_service import TaskService
from .services.scheduler_service import SchedulerService
from .services.monitoring_service import MonitoringService

# Global service instances
ai_service = None
whatsapp_service = None  
task_service = None
scheduler_service = None
monitoring_service = None
redis_client = None

def create_app(config_name=None):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize database
    with app.app_context():
        init_database(app)
    
    # Initialize Redis
    global redis_client
    redis_client, redis_available = config[config_name].init_redis()
    
    # Initialize services
    global ai_service, whatsapp_service, task_service, scheduler_service, monitoring_service
    try:
        ai_service = AIService(redis_client=redis_client)
        whatsapp_service = WhatsAppService(redis_client=redis_client) 
        task_service = TaskService()
        
        # Initialize monitoring service
        monitoring_service = MonitoringService(
            whatsapp_service=whatsapp_service,
            alert_phone_numbers=app.config.get('ADMIN_PHONE_NUMBERS', ["972542607800"])
        )
        
        # Initialize scheduler service (only in worker processes)
        process_type = os.getenv('PROCESS_TYPE', '').lower()
        if process_type == 'worker':
            scheduler_service = SchedulerService(
                redis_client=redis_client, 
                whatsapp_service=whatsapp_service
            )
            scheduler_service.initialize_scheduler(app)
            print("Scheduler service initialized for worker process")
        
        print("Services initialized successfully")
    except Exception as e:
        print(f"Service initialization warning: {e}")
        # Create fallback instances
        ai_service = None
        whatsapp_service = None
        task_service = TaskService()
        scheduler_service = None
        monitoring_service = None
    
    # Register blueprints
    from .routes import webhook, admin, api
    app.register_blueprint(webhook.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(api.bp)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Internal server error"}, 500
    
    return app

# For backwards compatibility with existing deployment
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)