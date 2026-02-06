#!/usr/bin/env python3
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
