#!/usr/bin/env python3
"""
Railway Deployment Setup for ChatGPT SMS System
"""

import os

def setup_railway_deployment():
    """Create all necessary files for Railway deployment"""

    print("🚂 SETTING UP RAILWAY DEPLOYMENT")
    print("=" * 50)

    # 1. Create requirements.txt
    requirements = """flask==3.0.0
python-dotenv==1.0.0
openai==1.3.0
sqlalchemy==2.0.23
flask-sqlalchemy==3.1.1
flask-migrate==4.0.5
psycopg2-binary==2.9.9
twilio==8.10.0
celery==5.3.4
redis==5.0.1
requests==2.31.0
gunicorn==21.2.0
alembic==1.12.1
python-dateutil==2.8.2
numpy==1.24.3
pandas==2.0.3
scipy==1.11.4
scikit-learn==1.3.2
anthropic==0.7.7
aiohttp==3.9.1
aiohttp-retry==2.8.3
mysqlclient==2.2.0
"""

    with open('requirements.txt', 'w') as f:
        f.write(requirements.strip())
    print("✅ Created requirements.txt")

    # 2. Create Procfile for Railway
    procfile = """web: gunicorn app:app --host 0.0.0.0 --port $PORT
worker: celery -A tasks.celery_app worker --loglevel=info
"""

    with open('Procfile', 'w') as f:
        f.write(procfile.strip())
    print("✅ Created Procfile")

    # 3. Create railway.json for configuration
    railway_config = """{
  "build": {
    "builder": "nixpacks"
  },
  "deploy": {
    "startCommand": "gunicorn app:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "on_failure"
  }
}"""

    with open('railway.json', 'w') as f:
        f.write(railway_config)
    print("✅ Created railway.json")

    # 4. Create environment variables template
    env_template = """# Railway Environment Variables Template
# Copy these to Railway dashboard → Variables

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Database Configuration (Railway PostgreSQL)
DATABASE_URL=postgresql://username:password@hostname:port/database

# Redis Configuration (Railway Redis)
REDIS_URL=redis://username:password@hostname:port

# Environment
ENVIRONMENT=production
FLASK_ENV=production
PORT=8000
"""

    with open('railway_env_template.txt', 'w') as f:
        f.write(env_template)
    print("✅ Created railway_env_template.txt")

    # 5. Update app.py for Railway
    railway_app_code = '''#!/usr/bin/env python3
"""
Ultrahuman Lifestyle Agent - Railway Version
ChatGPT-powered SMS health assistant
"""

import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    """Application factory for Railway deployment"""
    app = Flask(__name__)

    # Railway-specific configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'railway-ultrahuman-secret-key')

    # Database configuration - Railway PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Railway PostgreSQL URL format
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback to SQLite for local testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ultrahuman_railway.db'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    from app import db, migrate
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Health check endpoint for Railway
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'ultrahuman-chatgpt-sms'}, 200

    # Root endpoint
    @app.route('/')
    def index():
        return {
            'service': 'Ultrahuman ChatGPT SMS Assistant',
            'status': 'operational',
            'platform': 'Railway',
            'webhook': '/webhook/sms'
        }

    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
'''

    with open('app_railway.py', 'w') as f:
        f.write(railway_app_code)
    print("✅ Created app_railway.py")

    # 6. Create database migration setup
    migration_setup = '''#!/usr/bin/env python3
"""
Database setup for Railway deployment
"""

import os
import sys

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

def setup_railway_database():
    """Set up database schema on Railway"""

    app = Flask(__name__)

    # Database configuration
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db = SQLAlchemy()
    migrate = Migrate()

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        # Import models to register them
        from app.models import User, Metric, Alert, Intervention, HealthInsight

        print("📊 Creating database tables...")

        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")

            # Create test user
            test_user = User(
                id='user_7000',
                phone_number='+15875452951',
                timezone='America/Edmonton'
            )

            db.session.add(test_user)
            db.session.commit()

            print("✅ Test user created: user_7000 (+15875452951)")

            return True

        except Exception as e:
            print(f"❌ Database setup failed: {str(e)}")
            return False

if __name__ == '__main__':
    success = setup_railway_database()
    if success:
        print("🎉 Railway database setup complete!")
    else:
        print("❌ Railway database setup failed")
'''

    with open('setup_railway_db.py', 'w') as f:
        f.write(migration_setup)
    print("✅ Created setup_railway_db.py")

    # 7. Create Railway deployment instructions
    instructions = """
🚂 RAILWAY DEPLOYMENT INSTRUCTIONS
==================================

1. PREPARE YOUR CODE:
   ✅ requirements.txt created
   ✅ Procfile created
   ✅ railway.json created
   ✅ app_railway.py created
   ✅ Environment template created

2. DEPLOY TO RAILWAY:

   a) Go to https://railway.app
   b) Sign up/Login with GitHub
   c) Click "New Project"
   d) Choose "Deploy from GitHub repo"
   e) Select your ultrahuman_agent repository

3. ADD SERVICES:

   a) Add PostgreSQL Database:
      - Click "New" → "Database" → "Add PostgreSQL"
      - Railway will provide DATABASE_URL automatically

   b) Add Redis (for Celery):
      - Click "New" → "Database" → "Add Redis"
      - Railway will provide REDIS_URL automatically

4. SET ENVIRONMENT VARIABLES:

   In Railway dashboard → Variables, add:

   OPENAI_API_KEY=your_openai_api_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_number
   ENVIRONMENT=production

   (DATABASE_URL and REDIS_URL are auto-generated)

5. CONFIGURE DEPLOYMENT:

   - Start Command: gunicorn app_railway:app --host 0.0.0.0 --port $PORT
   - Build Command: pip install -r requirements.txt

6. DEPLOY AND TEST:

   a) Railway will auto-deploy from your GitHub repo
   b) Get your Railway app URL (like: https://yourapp.up.railway.app)
   c) Set Twilio webhook: https://yourapp.up.railway.app/webhook/sms
   d) Test SMS: Send "Hello" to your Twilio number

7. DATABASE SETUP:

   Once deployed, run the database setup:
   - Railway dashboard → your service → Connect
   - Run: python setup_railway_db.py

🎯 ADVANTAGES OF RAILWAY:
✅ Full OpenAI API support (including function calling)
✅ Automatic HTTPS
✅ Built-in PostgreSQL and Redis
✅ GitHub auto-deployment
✅ Environment variables management
✅ No network restrictions
✅ Generous free tier

Your ChatGPT SMS system will work perfectly on Railway!
"""

    with open('RAILWAY_INSTRUCTIONS.md', 'w') as f:
        f.write(instructions)
    print("✅ Created RAILWAY_INSTRUCTIONS.md")

    print()
    print("🎯 RAILWAY SETUP COMPLETE!")
    print("📋 Check RAILWAY_INSTRUCTIONS.md for step-by-step deployment")
    print()
    print("🚀 NEXT STEPS:")
    print("1. Push code to GitHub repository")
    print("2. Deploy to Railway using the instructions")
    print("3. Your ChatGPT SMS system will work perfectly!")

    return True

if __name__ == '__main__':
    setup_railway_deployment()
    print("\n🎉 Ready for Railway deployment!")