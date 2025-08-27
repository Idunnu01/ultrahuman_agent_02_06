"""
Flask Application Factory
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from utils.database import db
from utils.cache import cache

migrate = Migrate()

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app.config.update(
        # Database
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL',
            'postgresql://user:password@localhost:5432/ultrahuman_agent'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,

        # Redis
        REDIS_URL=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),

        # Celery
        CELERY_BROKER_URL=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        CELERY_RESULT_BACKEND=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),

        # API Keys
        ULTRAHUMAN_API_KEY=os.getenv('ULTRAHUMAN_API_KEY'),
        ULTRAHUMAN_API_BASE=os.getenv('ULTRAHUMAN_API_BASE', 'https://api.ultrahuman.com'),

        # LLM Providers
        OPENAI_API_KEY=os.getenv('OPENAI_API_KEY'),
        ANTHROPIC_API_KEY=os.getenv('ANTHROPIC_API_KEY'),
        TOGETHER_API_KEY=os.getenv('TOGETHER_API_KEY'),
        OLLAMA_BASE_URL=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),

        # SMS
        TWILIO_ACCOUNT_SID=os.getenv('TWILIO_ACCOUNT_SID'),
        TWILIO_AUTH_TOKEN=os.getenv('TWILIO_AUTH_TOKEN'),
        TWILIO_PHONE_NUMBER=os.getenv('TWILIO_PHONE_NUMBER'),

        # Vector Database
        QDRANT_URL=os.getenv('QDRANT_URL', 'http://localhost:6333'),
        QDRANT_API_KEY=os.getenv('QDRANT_API_KEY'),

        # Security
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-change-in-production'),

        # Application
        DAILY_REPORT_TIME=os.getenv('DAILY_REPORT_TIME', '04:00'),
        TIMEZONE=os.getenv('TIMEZONE', 'UTC')
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    CORS(app)

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return {'error': 'Resource not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500

    return app