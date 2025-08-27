"""
Flask Application Factory - PythonAnywhere Version
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask import Flask, request, has_request_context
from utils.database import db
from utils.cache import cache

migrate = Migrate()

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'production')

    # PythonAnywhere-specific database URL handling
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Redis URL handling for PythonAnywhere
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        # PythonAnywhere free tier doesn't include Redis
        # Will fallback to in-memory cache
        redis_url = None

    app.config.update(
        # Database
        SQLALCHEMY_DATABASE_URI=database_url or 'sqlite:///ultrahuman_agent.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_pre_ping': True,
            'pool_recycle': 300,
        },

        # Cache (Redis optional on PythonAnywhere)
        REDIS_URL=redis_url,

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

        # Vector Database (optional for PythonAnywhere)
        QDRANT_URL=os.getenv('QDRANT_URL'),
        QDRANT_API_KEY=os.getenv('QDRANT_API_KEY'),

        # Security
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-change-in-production'),

        # Application
        DAILY_REPORT_TIME=os.getenv('DAILY_REPORT_TIME', '04:00'),
        TIMEZONE=os.getenv('TIMEZONE', 'UTC'),

        # PythonAnywhere specific settings
        SEND_FILE_MAX_AGE_DEFAULT=31536000,  # 1 year cache for static files
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size

        # Logging configuration
        LOG_LEVEL=os.getenv('LOG_LEVEL', 'INFO'),
    )

    # Configure logging for PythonAnywhere
    if config_name == 'production':
        import logging
        from logging.handlers import RotatingFileHandler

        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/ultrahuman_agent.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Ultrahuman Lifestyle Agent startup')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize cache (with fallback for missing Redis)
    try:
        cache.init_app(app)
    except Exception as e:
        app.logger.warning(f"Redis cache unavailable, using fallback: {str(e)}")

    CORS(app, origins=['*'])  # Configure CORS for API access

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

    @app.errorhandler(413)
    def file_too_large(error):
        return {'error': 'File too large'}, 413

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return {'error': 'Rate limit exceeded'}, 429

    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check for monitoring"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            db_status = 'healthy'
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'

        # Test cache connection
        try:
            if hasattr(cache, 'redis_client') and cache.redis_client:
                cache.redis_client.ping()
                cache_status = 'healthy'
            else:
                cache_status = 'fallback_mode'
        except Exception as e:
            cache_status = f'fallback_mode: {str(e)}'

        health_status = {
            'status': 'healthy' if db_status == 'healthy' else 'degraded',
            'timestamp': '2024-01-01T00:00:00Z',  # Will be updated with actual timestamp
            'components': {
                'database': db_status,
                'cache': cache_status,
                'environment': config_name
            }
        }

        # Update timestamp
        from datetime import datetime
        health_status['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        status_code = 200 if health_status['status'] == 'healthy' else 503
        return health_status, status_code

    # SMS webhook endpoint for real-time processing
    @app.route('/webhook/sms', methods=['POST'])
    def sms_webhook():
        """Handle incoming SMS messages from Twilio"""
        try:
            from flask import request
            from services.metrics_service import MetricsService
            import logging

            # Get SMS data from Twilio
            sms_data = {
                'From': request.form.get('From'),
                'Body': request.form.get('Body'),
                'MessageSid': request.form.get('MessageSid'),
                'AccountSid': request.form.get('AccountSid')
            }

            # Log incoming SMS
            app.logger.info(f"SMS received from {sms_data['From']}: {sms_data['Body'][:50]}...")

            # Find user by phone number
            from app.models import User
            phone_number = sms_data['From']
            user = User.query.filter_by(phone_number=phone_number).first()

            if not user:
                app.logger.warning(f"No user found for phone number: {phone_number}")
                return '<Response></Response>', 200  # Empty TwiML response

            # Process SMS content
            metrics_service = MetricsService()
            result = metrics_service.process_sms_input(user.id, sms_data['Body'])

            # Prepare response message
            if result.get('success'):
                events_processed = result.get('events_processed', 0)
                if events_processed > 0:
                    response_text = f"✅ Logged {events_processed} event(s). Thanks!"

                    # Add immediate insights if available
                    immediate_insights = result.get('immediate_insights', {})
                    if immediate_insights and immediate_insights.get('insights'):
                        insight = immediate_insights['insights'][0]
                        response_text += f" {insight.get('message', '')}"
                else:
                    response_text = "👍 Message received. Use format: 'meal chicken 7pm' or 'supplement magnesium 400mg 9pm'"
            else:
                response_text = "❌ Couldn't process message. Try: 'meal [food] [time]' or 'supplement [name] [dose] [time]'"

            # Return TwiML response
            twiml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_text}</Message>
</Response>'''

            return twiml_response, 200, {'Content-Type': 'text/xml'}

        except Exception as e:
            app.logger.error(f"SMS webhook error: {str(e)}")
            # Return empty response to avoid Twilio retries
            return '<Response></Response>', 200, {'Content-Type': 'text/xml'}

    # Context processors for templates (if using any)
    @app.context_processor
    def inject_config():
        return {
            'APP_NAME': 'Ultrahuman Lifestyle Agent',
            'VERSION': '1.0.0',
            'ENVIRONMENT': config_name
        }

    # Before request hooks
    @app.before_request
    def before_request():
        """Execute before each request"""
        # Add any pre-request logic here
        pass

    # After request hooks
    @app.after_request
    def after_request(response):
        # Add security/CORS/cache headers as you already do...
        try:
            # Only touch request.path if we're actually in a request context
            if has_request_context():
                p = request.path or ""
                if p.startswith("/api/") or p.startswith("/users/"):
                    # Example: cache control for API responses
                    response.headers.setdefault("Cache-Control", "no-store")
                    response.headers.setdefault("Pragma", "no-cache")
            # (You can leave other global headers you set here as-is)
        except Exception as e:
            current_app.logger.debug(f"after_request guard: {e}")
        return response


    # Database initialization
    @app.cli.command()
    def init_db():
        """Initialize the database"""
        db.create_all()
        print("Database initialized.")

    @app.cli.command()
    def create_sample_user():
        """Create a sample user for testing"""
        from app.models import User

        sample_user = User(
            id='sample_user',
            ultrahuman_user_id='sample_uh_user',
            phone_number='+1234567890',  # Update with actual test number
            timezone='UTC',
            preferences={'test_user': True}
        )

        try:
            db.session.add(sample_user)
            db.session.commit()
            print("Sample user created successfully")
        except Exception as e:
            print(f"Error creating sample user: {str(e)}")
            db.session.rollback()

    # Register CLI commands
    @app.cli.command()
    def test_services():
        """Test external service connections"""
        print("Testing services...")

        # Test SMS service
        try:
            from services.sms_service import SMSService
            sms_service = SMSService()
            sms_test = sms_service.test_connectivity()
            print(f"SMS Service: {'✅' if sms_test['success'] else '❌'}")
        except Exception as e:
            print(f"SMS Service: ❌ {str(e)}")

        # Test LLM services
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            llm_status = llm_service.get_provider_status()
            for provider, status in llm_status.items():
                print(f"LLM {provider}: {'✅' if status['available'] else '❌'}")
        except Exception as e:
            print(f"LLM Services: ❌ {str(e)}")

        print("Service test completed.")

    return app