#!/usr/bin/env python3.11
"""
Setup script for PythonAnywhere deployment
Run this once after uploading your code
"""

import sys
import os
from datetime import datetime

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def setup_database():
    """Initialize database and create tables"""
    try:
        from app import create_app
        from utils.database import db

        app = create_app()

        with app.app_context():
            print("Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully")

            # Test database connection
            from app.models import User
            test_query = User.query.first()
            print("✅ Database connection test successful")

    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False

    return True

def test_sms_service():
    """Test SMS service configuration"""
    try:
        from services.sms_service import SMSService

        sms_service = SMSService()
        test_result = sms_service.test_connectivity()

        if test_result['success']:
            print("✅ SMS service configured correctly")
            print(f"Account: {test_result.get('account_name', 'Unknown')}")
            print(f"Phone: {test_result.get('phone_number', 'Unknown')}")
        else:
            print(f"❌ SMS service configuration issue: {test_result.get('error', 'Unknown')}")

    except Exception as e:
        print(f"❌ SMS service test failed: {str(e)}")

def test_llm_services():
    """Test LLM service configuration"""
    try:
        from services.llm_service import LLMService

        llm_service = LLMService()
        status = llm_service.get_provider_status()

        print("🧠 LLM Provider Status:")
        for provider, info in status.items():
            status_icon = "✅" if info['available'] else "❌"
            print(f"  {status_icon} {provider}: {info}")

    except Exception as e:
        print(f"❌ LLM service test failed: {str(e)}")

def create_sample_user():
    """Create a sample user for testing"""
    try:
        from app import create_app
        from app.models import User
        from utils.database import db

        app = create_app()

        with app.app_context():
            # Check if sample user already exists
            sample_user = User.query.filter_by(id='sample_user').first()

            if sample_user:
                print("📝 Sample user already exists")
                return

            # Create sample user
            sample_user = User(
                id='sample_user',
                ultrahuman_user_id='sample_uh_user',
                phone_number='+1234567890',  # Update with test number
                timezone='UTC',
                preferences={'test_user': True}
            )

            db.session.add(sample_user)
            db.session.commit()

            print("✅ Sample user created successfully")
            print("📝 User ID: sample_user")
            print("📱 Phone: +1234567890 (update in database)")

    except Exception as e:
        print(f"❌ Sample user creation failed: {str(e)}")

def check_dependencies():
    """Check if all required dependencies are installed"""
    # Updated package mapping (import_name: package_name)
    required_packages = {
        'flask': 'flask',
        'psycopg2': 'psycopg2',
        'redis': 'redis',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'scipy': 'scipy',
        'sklearn': 'scikit-learn',  # Import name is 'sklearn', package is 'scikit-learn'
        'statsmodels': 'statsmodels',
        'twilio': 'twilio',
        'openai': 'openai',
        'anthropic': 'anthropic',
        'dotenv': 'python-dotenv'  # Import name is 'dotenv', package is 'python-dotenv'
    }

    missing_packages = []

    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name} - MISSING")

    if missing_packages:
        print(f"\n📦 Install missing packages:")
        print(f"pip3.11 install --user {' '.join(missing_packages)}")
        return False
    else:
        print("\n✅ All dependencies installed")
        return True

def main():
    """Main setup function"""
    print("🚀 Setting up Ultrahuman Lifestyle Agent on PythonAnywhere")
    print("=" * 60)

    # Check dependencies
    print("\n1️⃣ Checking Dependencies...")
    deps_ok = check_dependencies()

    if not deps_ok:
        print("\n❌ Please install missing dependencies first")
        return

    # Setup database
    print("\n2️⃣ Setting up Database...")
    db_ok = setup_database()

    if not db_ok:
        print("\n❌ Database setup failed - check your DATABASE_URL")
        return

    # Test services
    print("\n3️⃣ Testing Services...")
    test_sms_service()
    test_llm_services()

    # Create sample user
    print("\n4️⃣ Creating Sample User...")
    create_sample_user()

    print("\n" + "=" * 60)
    print("🎉 Setup Complete!")
    print("\n📋 Next Steps:")
    print("1. Update .env file with your API keys")
    print("2. Set up scheduled tasks in PythonAnywhere:")
    print("   - Daily reports: run_daily_reports.py at 04:00")
    print("   - Data sync: run_data_sync.py every hour")
    print("3. Configure web app to use wsgi.py")
    print("4. Test with sample user")
    print("\n📱 SMS Commands to test:")
    print("- Text: 'meal chicken 7pm' to +YOUR_TWILIO_NUMBER")
    print("- Text: 'supplement magnesium 400mg 9pm'")
    print("- Text: 'workout strength 45min'")

if __name__ == "__main__":
    main()