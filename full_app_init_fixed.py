"""
Flask Application Factory - PythonAnywhere Version
"""
import os
from pathlib import Path
from datetime import datetime

from flask import Flask, request, has_request_context, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import text

from utils.database import db
from utils.cache import cache

migrate = Migrate()

# Load .env (project root)
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

def _ensure_instance_dir():
    inst = Path(__file__).resolve().parents[1] / "instance"
    inst.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{inst}/ultrahuman_agent.db"

def create_app(config_name=None):
    app = Flask(__name__)

    # Configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'production')

    # DB URL normalization (mostly for old postgres URLs)
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Redis (Upstash requires TLS → rediss://)
    redis_url = os.getenv('REDIS_URL') or None

    app.config.update(
        # Database
        SQLALCHEMY_DATABASE_URI=database_url or _ensure_instance_dir(),
        SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping': True, 'pool_recycle': 300},

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

        # SMS (Twilio)
        TWILIO_ACCOUNT_SID=os.getenv('TWILIO_ACCOUNT_SID'),
        TWILIO_AUTH_TOKEN=os.getenv('TWILIO_AUTH_TOKEN'),
        TWILIO_PHONE_NUMBER=os.getenv('TWILIO_PHONE_NUMBER'),

        # Optional vector DB
        QDRANT_URL=os.getenv('QDRANT_URL'),
        QDRANT_API_KEY=os.getenv('QDRANT_API_KEY'),

        # Security
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-change-in-production'),

        # App
        DAILY_REPORT_TIME=os.getenv('DAILY_REPORT_TIME', '04:00'),
        TIMEZONE=os.getenv('TIMEZONE', 'UTC'),

        # Static & uploads
        SEND_FILE_MAX_AGE_DEFAULT=31536000,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,

        # Logging
        LOG_LEVEL=os.getenv('LOG_LEVEL', 'INFO'),
    )

    # Production logging (rotating file)
    if config_name == 'production':
        import logging
        from logging.handlers import RotatingFileHandler
        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler('logs/ultrahuman_agent.log', maxBytes=10_240_000, backupCount=10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Ultrahuman Lifestyle Agent startup')

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Init cache (Redis → fallback to memory)
    try:
        cache.init_app(app)
    except Exception as e:
        app.logger.warning(f"Redis cache unavailable, using fallback: {str(e)}")

    CORS(app, origins=['*'])

    # Blueprints (ensure this path matches your tree)
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Errors
    @app.errorhandler(404)
    def not_found_error(error): return {'error': 'Resource not found'}, 404

    @app.errorhandler(500)
    def internal_error(error): return {'error': 'Internal server error'}, 500

    @app.errorhandler(413)
    def file_too_large(error): return {'error': 'File too large'}, 413

    @app.errorhandler(429)
    def rate_limit_exceeded(error): return {'error': 'Rate limit exceeded'}, 429

    # Health (DB + cache)
    @app.route('/health')
    def health_check():
        try:
            db.session.execute(text('SELECT 1'))
            db_status = 'healthy'
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'
        try:
            if getattr(cache, 'redis_client', None):
                cache.redis_client.ping()
                cache_status = 'healthy'
            else:
                cache_status = 'fallback_mode'
        except Exception as e:
            cache_status = f'fallback_mode: {str(e)}'

        status = 'healthy' if db_status == 'healthy' else 'degraded'
        return {
            'status': status,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'components': {'database': db_status, 'cache': cache_status, 'environment': config_name}
        }, (200 if status == 'healthy' else 503)

    # Redis health check
    @app.route("/health/redis")
    def health_redis():
        """Check Redis cache/connection health"""
        try:
            if getattr(cache, "redis_client", None):
                pong = cache.redis_client.ping()
                return {"redis": "healthy", "ping": bool(pong)}, 200
            else:
                return {"redis": "fallback_mode"}, 200
        except Exception as e:
            return {"redis": f"unhealthy: {str(e)}"}, 503

    # Celery health check (robust even if Celery isn't running)
    @app.route("/health/celery")
    def health_celery():
        """Check Celery worker health via heartbeat task"""
        try:
            try:
                from celery.result import AsyncResult
                from celery_app import celery_app  # adjust import if celery_app is in a package
            except Exception as imp_err:
                return {"celery": f"unhealthy: import_failed: {imp_err}"}, 503

            try:
                result = celery_app.send_task("heartbeat_task")
                async_res = AsyncResult(result.id, app=celery_app)
                async_res.get(timeout=10)  # wait up to 10s
                return {"celery": "healthy"}, 200
            except Exception as run_err:
                return {"celery": f"unhealthy: {run_err}"}, 503
        except Exception as e:
            return {"celery": f"unhealthy: {e}"}, 503

    # Twilio SMS webhook - FIXED VERSION WITH PROPER ERROR HANDLING
    @app.route('/webhook/sms', methods=['POST'])
    def sms_webhook():
        try:
            from services.metrics_service import MetricsService
            from app.models import User

            sms_data = {
                'From': request.form.get('From'),
                'Body': request.form.get('Body'),
                'MessageSid': request.form.get('MessageSid'),
                'AccountSid': request.form.get('AccountSid')
            }
            app.logger.info(f"SMS received from {sms_data['From']}: {sms_data['Body'][:50]}...")

            # Find user by phone number
            user = User.query.filter_by(phone_number=sms_data['From']).first()

            if not user:
                app.logger.warning(f"No user found for phone number: {sms_data['From']}")
                return '<Response></Response>', 200, {'Content-Type': 'text/xml'}

            # Process the SMS message
            try:
                metrics_service = MetricsService()
                result = metrics_service.process_sms_input(user.id, sms_data['Body'])

                if result.get('success'):
                    insights = (result.get('immediate_insights') or {}).get('insights') or []
                    if insights:
                        response_text = (insights[0].get('message', '') or '').strip() or "✅ Message processed successfully!"
                    elif result.get('events_processed', 0) > 0:
                        response_text = f"✅ Logged {result['events_processed']} event(s). Thanks!"
                    else:
                        response_text = "📊 Message processed successfully!"
                else:
                    response_text = "👍 Message received, processing..."

            except Exception as e:
                app.logger.error(f"Metrics processing failed: {str(e)}")
                response_text = "📊 Thanks for your message! Data is being processed."

            # CRITICAL FIX: Send SMS with proper error handling
            try:
                from services.sms_service import SMSService
                sms_service = SMSService()

                # Check the SMS service response properly
                sms_result = sms_service.send_immediate_response(user.id, sms_data['From'], response_text)

                if sms_result.get('success'):
                    app.logger.info(f"✅ SMS sent successfully to {sms_data['From']}: {response_text}")
                else:
                    # SMS FAILED - Log the real error
                    error = sms_result.get('error', 'Unknown SMS error')
                    app.logger.error(f"❌ SMS FAILED to {sms_data['From']}: {error}")

                    # Handle different error types
                    if 'rate limit' in error.lower() or 'daily' in error.lower():
                        app.logger.warning(f"⚠️  Rate limit hit for user {user.id} - SMS blocked")
                    elif 'twilio' in error.lower():
                        app.logger.error(f"🚨 Twilio API error: {error}")
                    else:
                        app.logger.error(f"🔧 SMS service error: {error}")

            except Exception as e:
                app.logger.error(f"💥 SMS service exception: {str(e)}")

            return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>', 200, {'Content-Type': 'text/xml'}

        except Exception as e:
            app.logger.error(f"💥 SMS webhook error: {str(e)}")
            return '<Response></Response>', 200, {'Content-Type': 'text/xml'}

    @app.after_request
    def after_request(response):
        try:
            if has_request_context():
                p = request.path or ""
                if p.startswith("/api/") or p.startswith("/users/"):
                    response.headers.setdefault("Cache-Control", "no-store")
                    response.headers.setdefault("Pragma", "no-cache")
        except Exception as e:
            current_app.logger.debug(f"after_request guard: {e}")
        return response

    # CLI helpers
    @app.cli.command()
    def init_db():
        db.create_all(); print("Database initialized.")

    @app.cli.command()
    def create_sample_user():
        from app.models import User
        u = User(id='sample_user', ultrahuman_user_id='sample_uh_user',
                 phone_number='+1234567890', timezone='UTC', preferences={'test_user': True})
        try:
            db.session.add(u); db.session.commit(); print("Sample user created.")
        except Exception as e:
            print(f"Error creating sample user: {e}"); db.session.rollback()

    @app.cli.command()
    def test_services():
        print("Testing services...")
        try:
            from services.sms_service import SMSService
            ok = SMSService().test_connectivity()
            print(f"SMS Service: {'✅' if ok.get('success') else '❌'}")
        except Exception as e:
            print(f"SMS Service: ❌ {e}")
        try:
            from services.llm_service import LLMService
            llm_status = LLMService().get_provider_status()
            for provider, status in llm_status.items():
                print(f"LLM {provider}: {'✅' if status['available'] else '❌'}")
        except Exception as e:
            print(f"LLM Services: ❌ {e}")
        print("Service test completed.")
    return app