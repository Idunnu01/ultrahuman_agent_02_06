#!/usr/bin/env python3
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
