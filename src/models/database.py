"""
Database models and initialization for WhatsApp Todo Bot
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

class User(db.Model):
    """User model with encrypted phone number storage"""
    id = db.Column(db.Integer, primary_key=True)
    phone_number_encrypted = db.Column(db.Text, nullable=False)  # Encrypted phone number
    phone_number_hash = db.Column(db.String(64), unique=True, nullable=False)  # Hash for searching
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Calendar integration fields
    google_calendar_enabled = db.Column(db.Boolean, default=False, nullable=False)
    google_access_token_encrypted = db.Column(db.Text, nullable=True)
    google_refresh_token_encrypted = db.Column(db.Text, nullable=True)
    google_token_expiry = db.Column(db.DateTime, nullable=True)
    google_calendar_id = db.Column(db.String(255), nullable=True)  # Default calendar ID
    
    @property
    def phone_number(self):
        """Decrypt and return phone number"""
        from ..services.encryption import encryption_service
        return encryption_service.decrypt_data(self.phone_number_encrypted)
    
    @phone_number.setter
    def phone_number(self, value):
        """Encrypt and store phone number"""
        from ..services.encryption import encryption_service
        self.phone_number_encrypted = encryption_service.encrypt_data(value)
        self.phone_number_hash = encryption_service.hash_for_search(value)
    
    @property
    def google_access_token(self):
        """Decrypt and return Google access token"""
        from ..services.encryption import encryption_service
        if self.google_access_token_encrypted:
            return encryption_service.decrypt_data(self.google_access_token_encrypted)
        return None
    
    @google_access_token.setter
    def google_access_token(self, value):
        """Encrypt and store Google access token"""
        from ..services.encryption import encryption_service
        if value:
            self.google_access_token_encrypted = encryption_service.encrypt_data(value)
        else:
            self.google_access_token_encrypted = None
    
    @property
    def google_refresh_token(self):
        """Decrypt and return Google refresh token"""
        from ..services.encryption import encryption_service
        if self.google_refresh_token_encrypted:
            return encryption_service.decrypt_data(self.google_refresh_token_encrypted)
        return None
    
    @google_refresh_token.setter
    def google_refresh_token(self, value):
        """Encrypt and store Google refresh token"""
        from ..services.encryption import encryption_service
        if value:
            self.google_refresh_token_encrypted = encryption_service.encrypt_data(value)
        else:
            self.google_refresh_token_encrypted = None
    
    # Optimized relationships with lazy loading options
    messages = db.relationship('Message', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    # Strategic indexes for performance
    __table_args__ = (
        db.Index('idx_user_phone_hash', 'phone_number_hash'),
        db.Index('idx_user_created', 'created_at'),
    )
    
    def get_message_count(self):
        return self.messages.count()
    
    def get_task_count(self):
        return self.tasks.count()
    
    def get_pending_tasks_count(self):
        return self.tasks.filter_by(status='pending').count()
    
    def get_completed_tasks_count(self):
        return self.tasks.filter_by(status='completed').count()

class Message(db.Model):
    """Message model with encrypted content storage"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # 'text', 'audio', 'image', etc.
    content_encrypted = db.Column(db.Text)  # Encrypted user message content
    ai_response_encrypted = db.Column(db.Text)  # Encrypted AI response
    parsed_tasks = db.Column(db.Text)  # JSON string of extracted tasks
    whatsapp_message_id = db.Column(db.String(255))  # Store WhatsApp message ID for reaction matching
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def content(self):
        """Decrypt and return message content"""
        from ..services.encryption import encryption_service
        return encryption_service.decrypt_data(self.content_encrypted)
    
    @content.setter
    def content(self, value):
        """Encrypt and store message content"""
        from ..services.encryption import encryption_service
        self.content_encrypted = encryption_service.encrypt_data(value)
    
    @property
    def ai_response(self):
        """Decrypt and return AI response"""
        from ..services.encryption import encryption_service
        return encryption_service.decrypt_data(self.ai_response_encrypted)
    
    @ai_response.setter
    def ai_response(self, value):
        """Encrypt and store AI response"""
        from ..services.encryption import encryption_service
        self.ai_response_encrypted = encryption_service.encrypt_data(value)
    
    # Strategic indexes for performance
    __table_args__ = (
        db.Index('idx_message_user_created', 'user_id', 'created_at'),
        db.Index('idx_message_user_type', 'user_id', 'message_type'),
        db.Index('idx_message_whatsapp_id', 'whatsapp_message_id'),
    )

class Task(db.Model):
    """Task model for todo items"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in_progress', 'completed', 'cancelled'
    due_date = db.Column(db.DateTime)
    reminder_date = db.Column(db.DateTime)  # Keep for backward compatibility
    reminder_sent = db.Column(db.Boolean, default=False, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Recurring task fields
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_pattern = db.Column(db.String(50))  # 'daily', 'weekly', 'specific_days', 'interval', 'monthly'
    recurrence_interval = db.Column(db.Integer)
    recurrence_days_of_week = db.Column(db.String(100))  # JSON array as string
    recurrence_day_of_month = db.Column(db.Integer, nullable=True)  # Day of month (1-31) for monthly patterns
    recurrence_end_date = db.Column(db.DateTime)
    parent_recurring_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    recurring_instance_count = db.Column(db.Integer, default=0)
    recurring_max_instances = db.Column(db.Integer, default=100)
    
    # Calendar sync fields
    calendar_event_id = db.Column(db.String(255), nullable=True)
    calendar_synced = db.Column(db.Boolean, default=False, nullable=False)
    calendar_sync_error = db.Column(db.Text, nullable=True)
    
    # Recurring relationship (self-referential)
    recurring_instances = db.relationship('Task',
        backref=db.backref('parent_pattern', remote_side=[id]),
        foreign_keys=[parent_recurring_id],
        lazy='dynamic')
    
    # Strategic indexes for performance
    __table_args__ = (
        db.Index('idx_task_user_status', 'user_id', 'status'),
        db.Index('idx_task_user_created', 'user_id', 'created_at'),
        db.Index('idx_task_due_date', 'due_date'),
        db.Index('idx_task_status_due', 'status', 'due_date'),
        db.Index('idx_task_status', 'status'),
        db.Index('idx_task_created', 'created_at'),
        db.Index('idx_task_is_recurring', 'is_recurring'),
        db.Index('idx_task_parent_recurring', 'parent_recurring_id'),
        db.Index('idx_task_calendar_event', 'calendar_event_id'),
    )
    
    def is_recurring_pattern(self):
        """Check if this is a recurring pattern (not instance)"""
        return self.is_recurring is True
    
    def is_recurring_instance(self):
        """Check if this is an instance of a recurring pattern"""
        return self.parent_recurring_id is not None
    
    def get_recurring_pattern(self):
        """Get the parent pattern if this is an instance"""
        if self.parent_recurring_id:
            return Task.query.get(self.parent_recurring_id)
        return None

def init_database(app):
    """Initialize database with Flask app"""
    # Check if db is already initialized
    if not hasattr(app, 'extensions') or 'sqlalchemy' not in app.extensions:
        db.init_app(app)
    
    # Check if migrate is already initialized
    if not hasattr(app, 'extensions') or 'migrate' not in app.extensions:
        migrate.init_app(app, db)
    
    # Only create tables in development/new setups
    with app.app_context():
        try:
            # Check if tables exist
            with db.engine.connect() as connection:
                connection.execute(db.text("SELECT 1 FROM user LIMIT 1"))
            print("Database already initialized")
        except Exception:
            print("Creating database tables...")
            db.create_all()
            print("Database tables created successfully")