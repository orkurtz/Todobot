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
    WHATSAPP_API_URL = "https://graph.facebook.com/v20.0/456933577513253/messages"
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