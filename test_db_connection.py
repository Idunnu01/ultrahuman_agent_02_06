#!/usr/bin/env python3
"""
Test database connection from Flask app context
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test database connection in Flask app context"""

    print("🔍 Testing Database Connection from Flask App")
    print("="*50)

    try:
        from app import create_app
        from utils.database import db

        # Create Flask app
        app = create_app()

        with app.app_context():
            print("✅ Flask app context established")

            # Check environment variables
            database_url = os.getenv('DATABASE_URL')
            print(f"📊 DATABASE_URL: {database_url[:50]}..." if database_url else "❌ DATABASE_URL not found")

            # Test basic database connection
            print("\n1️⃣  Testing basic database connection...")
            try:
                # Try to execute a simple query (updated for modern SQLAlchemy)
                with db.engine.connect() as connection:
                    result = connection.execute(db.text("SELECT 1 as test_value"))
                    test_value = result.scalar()
                print(f"   ✅ Database query successful: {test_value}")
            except Exception as e:
                print(f"   ❌ Database connection failed: {str(e)}")
                return False

            # Test table access
            print("\n2️⃣  Testing table access...")
            try:
                from app.models import User
                user_count = db.session.query(User).count()
                print(f"   ✅ Can access User table: {user_count} users")
            except Exception as e:
                print(f"   ❌ Table access failed: {str(e)}")
                return False

            # Test metric insertion
            print("\n3️⃣  Testing metric insertion...")
            try:
                from utils.database import bulk_insert_metrics
                from app.models import User

                # First, create test user if doesn't exist
                test_user_id = 'test_db_connection'
                existing_user = db.session.query(User).filter_by(id=test_user_id).first()
                if not existing_user:
                    test_user = User(
                        id=test_user_id,
                        ultrahuman_user_id=f'ultrahuman_{test_user_id}',
                        phone_number='+1234567890',
                        timezone='UTC'
                    )
                    db.session.add(test_user)
                    db.session.commit()
                    print(f"   ✅ Created test user: {test_user_id}")
                else:
                    print(f"   ✅ Test user already exists: {test_user_id}")

                # Create test metrics
                test_metrics = [{
                    'user_id': test_user_id,
                    'metric_type': 'test_connection',
                    'value': 1.0,
                    'unit': 'test',
                    'timestamp': datetime.utcnow(),
                    'source': 'test',
                    'meta_data': {'test': True}
                }]

                success = bulk_insert_metrics(test_metrics)
                if success:
                    print(f"   ✅ Metric insertion successful")
                else:
                    print(f"   ❌ Metric insertion failed")
                    return False

            except Exception as e:
                print(f"   ❌ Metric insertion error: {str(e)}")
                import traceback
                traceback.print_exc()
                return False

            return True

    except Exception as e:
        print(f"❌ Flask app setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_lifestyle_event_with_db():
    """Test the complete lifestyle event flow with database"""

    print(f"\n🧪 Testing Complete Lifestyle Event Flow")
    print("="*45)

    try:
        from app import create_app
        from services.metrics_service import MetricsService

        # Create Flask app
        app = create_app()

        with app.app_context():
            print("✅ Flask app context established")

            from utils.database import db
            from app.models import User

            service = MetricsService()

            # Test the exact failing message
            test_message = "supplement magnesium 400mg at 10pm"
            test_user_id = "test_lifestyle_db"

            print(f"📱 Testing message: '{test_message}'")
            print(f"👤 User ID: {test_user_id}")

            # First, create test user if doesn't exist
            existing_user = db.session.query(User).filter_by(id=test_user_id).first()
            if not existing_user:
                test_user = User(
                    id=test_user_id,
                    ultrahuman_user_id=f'ultrahuman_{test_user_id}',
                    phone_number='+1234567891',
                    timezone='UTC'
                )
                db.session.add(test_user)
                db.session.commit()
                print(f"   ✅ Created test user: {test_user_id}")
            else:
                print(f"   ✅ Test user already exists: {test_user_id}")

            # Test the complete flow
            result = service.process_sms_input(test_user_id, test_message)

            print(f"\n📊 SMS Processing Result:")
            print(f"   Success: {result.get('success')}")
            print(f"   Events processed: {result.get('events_processed', 0)}")
            print(f"   Error: {result.get('error', 'None')}")

            insights = result.get('immediate_insights', {}).get('insights', [])
            if insights:
                response_message = insights[0].get('message', 'No message')
                print(f"   Response: '{response_message}'")

            if result.get('success'):
                print(f"   🎉 SUCCESS! SMS processing is working!")
                return True
            else:
                print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
                return False

    except Exception as e:
        print(f"❌ Lifestyle event test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_environment():
    """Check environment configuration"""

    print(f"\n🔧 Checking Environment Configuration")
    print("="*40)

    env_vars = [
        'DATABASE_URL',
        'FLASK_ENV',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_PHONE_NUMBER'
    ]

    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive info
            if 'TOKEN' in var or 'KEY' in var or 'PASSWORD' in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: NOT SET")

if __name__ == "__main__":
    print("🚀 Testing Database Connection in Flask App")
    print("="*60)

    # Check environment first
    check_environment()

    # Run tests
    tests = [
        ("Database Connection", test_database_connection),
        ("Lifestyle Event Flow", test_lifestyle_event_with_db)
    ]

    passed = 0
    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        result = test_func()
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\n{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 RESULTS:")
    print(f"Tests passed: {passed}/{len(tests)}")

    if passed == len(tests):
        print("🎉 Database is working! Your SMS should work now.")
    else:
        print("🔧 Database issues found. Check the errors above.")