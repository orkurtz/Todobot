"""
Application configuration settings
"""
import os
import redis
from typing import Optional

class Config:
    """Base configuration"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Database settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:AXtAYtrWslXxwKUBmKpWRjOLcFWgrnli@centerbeam.proxy.rlwy.net:52364/railway')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # WhatsApp API settings
    WHATSAPP_API_URL = "https://graph.facebook.com/v22.0/928083353711261/messages"
    WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
    WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN', 'default_verify_token')
    
    # AI settings
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Redis settings
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # System limits
    DAILY_MESSAGE_LIMIT = 1000
    MAX_VOICE_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE = 10
    RATE_LIMIT_REQUESTS_PER_HOUR = 100
    RATE_LIMIT_REQUESTS_PER_DAY = 500
    
    # Monitoring
    ADMIN_PHONE_NUMBERS = ["972542607800"]  # Add admin phone numbers here
    
    # Google Calendar OAuth settings
    BASE_URL = os.getenv('BASE_URL', '')  # Railway app URL
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = f"{os.getenv('BASE_URL', '')}/calendar/oauth/callback" if os.getenv('BASE_URL') else None
    GOOGLE_CALENDAR_SCOPES = [
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/calendar'
    ]
    CALENDAR_DEFAULT_EVENT_DURATION_MINUTES = 60
    
    @classmethod
    def init_redis(cls) -> tuple[Optional[redis.Redis], bool]:
        """Initialize Redis connection"""
        try:
            redis_client = redis.from_url(
                Config.REDIS_URL,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=15,
                max_connections=10
            )
            redis_client.ping()
            print("Redis connected successfully")
            return redis_client, True
        except Exception as e:
            print(f"Redis not available, falling back to in-memory storage: {e}")
            return None, False

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}