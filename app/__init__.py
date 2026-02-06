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

    def get_engine_options(database_url):
        options = {
            'pool_pre_ping': True,
            'pool_recycle': 300
        }

        # Only add charset for MySQL connections
        if database_url and 'mysql' in database_url.lower():
            options['connect_args'] = {'charset': 'utf8mb4'}

        return options

    app.config.update(
        # Database
        SQLALCHEMY_DATABASE_URI=database_url or _ensure_instance_dir(),
        SQLALCHEMY_ENGINE_OPTIONS=get_engine_options(database_url),

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

    def check_database_health():
        """Check if database is accessible"""
        try:
            db.session.execute(text('SELECT 1'))
            return True
        except Exception as e:
            app.logger.error(f"Database health check failed: {e}")
            return False

    def test_llm_connectivity():
        """Test LLM service connectivity"""
        try:
            from services.llm_service import LLMService
            llm_status = LLMService().get_provider_status()
            return any(status['available'] for status in llm_status.values())
        except Exception as e:
            app.logger.error(f"LLM connectivity test failed: {e}")
            return False

    # Health (DB + cache + services)
    @app.route('/health')
    def health_check():
        """Comprehensive health check"""

        checks = {
            'database': check_database_health(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Cache health
        try:
            if getattr(cache, 'redis_client', None):
                cache.redis_client.ping()
                checks['cache'] = True
            else:
                checks['cache'] = 'fallback_mode'
        except Exception as e:
            checks['cache'] = 'fallback_mode'

        # SMS service health
        try:
            from services.sms_service import SMSService
            sms_health = SMSService().test_connectivity()
            checks['sms_service'] = sms_health.get('success', False)
        except Exception as e:
            checks['sms_service'] = False

        # LLM service health
        try:
            checks['llm_service'] = test_llm_connectivity()
        except Exception as e:
            checks['llm_service'] = False

        checks['environment'] = config_name

        all_healthy = checks['database'] and checks['sms_service'] and checks['llm_service']
        status = 'healthy' if all_healthy else 'degraded'
        status_code = 200 if all_healthy else 503

        return {
            'status': status,
            'timestamp': checks['timestamp'],
            'components': checks
        }, status_code

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

    # Twilio SMS webhook
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
            # Check primary phone number first
            user = User.query.filter_by(phone_number=sms_data['From']).first()

            # If not found, check additional phone numbers in preferences
            if not user:
                users_with_additional_phones = User.query.filter(
                    User.preferences.op('JSON_EXTRACT')(User.preferences, '$.additional_phone_numbers').isnot(None)
                ).all()

                for potential_user in users_with_additional_phones:
                    additional_phones = potential_user.preferences.get('additional_phone_numbers', [])
                    if sms_data['From'] in additional_phones:
                        user = potential_user
                        break
            if not user:
                app.logger.warning(f"No user found for phone number: {sms_data['From']}")
                return '<Response></Response>', 200, {'Content-Type': 'text/xml'}

            metrics_service = MetricsService()

            try:
                app.logger.info(f"Processing SMS for user {user.id} with message: {sms_data['Body']}")
                result = metrics_service.process_sms_input_with_context(user.id, sms_data['Body'])
                app.logger.info(f"SMS processing result: {result}")

                # Store which phone sent the message for response routing
                response_phone = sms_data['From']

                if result.get('success'):
                    app.logger.info("SMS processing was successful")
                    insights = (result.get('immediate_insights') or {}).get('insights') or []
                    if insights:
                        response_text = (insights[0].get('message', '') or '').strip() or "✅ Logged."
                    elif result.get('events_processed', 0) > 0:
                        response_text = f"✅ Logged {result['events_processed']} event(s). Thanks!"
                    else:
                        response_text = "👍 Received. Try: 'meal chicken 7pm' or 'supplement magnesium 400mg 9pm'"
                else:
                    app.logger.error(f"SMS processing failed: {result.get('error', 'Unknown error')}")
                    response_text = "❌ Couldn't process. Try: 'meal [food] [time]' or 'supplement [name] [dose] [time]'"

            except Exception as e:
                app.logger.error(f"Exception in SMS processing: {str(e)}")
                app.logger.error(f"Exception type: {type(e)}")
                import traceback
                app.logger.error(f"Traceback: {traceback.format_exc()}")
                response_text = "❌ System error. Please try again."

            # Send immediate response to the phone that texted
            try:
                from services.sms_service import SMSService
                sms_service = SMSService()
                sms_service.send_immediate_response(user.id, response_phone, response_text)
                app.logger.info(f"Immediate response sent to {response_phone} for user {user.id}")
            except Exception as e:
                app.logger.error(f"Failed to send immediate response: {str(e)}")

            # Return empty TwiML (response sent via separate API call)
            return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>', 200, {'Content-Type': 'text/xml'}

        except Exception as e:
            app.logger.error(f"SMS webhook error: {str(e)}")
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
