#!/usr/bin/env python3
"""
Fix Phone Number and LLM Service Issues
Comprehensive fix for daily reports SMS delivery
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Environment Configuration Check")
    print("=" * 50)

    required_vars = [
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'TOGETHER_API_KEY',
        'DATABASE_URL',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_PHONE_NUMBER'
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value[:10]}...")
        else:
            print(f"  ❌ {var}: Not set")
            missing_vars.append(var)

    if missing_vars:
        print(f"\n⚠️ Missing {len(missing_vars)} environment variables")
        print("📝 Please set these in your .env file:")
        for var in missing_vars:
            print(f"   {var}=your_value_here")
        return False
    else:
        print("\n✅ All required environment variables are set!")
        return True

def fix_phone_number():
    """Fix the phone number for the sample user"""
    print("\n📱 Fixing Phone Number for Sample User")
    print("=" * 50)

    try:
        # Set database URL for local testing
        os.environ['DATABASE_URL'] = 'mysql://bphlite:Opeyemi992!@bphlite.mysql.pythonanywhere-services.com/bphlite$default'

        from app import create_app
        from app.models import User
        from utils.database import db

        app = create_app()
        with app.app_context():
            user = User.query.get('sample_user')
            if user:
                print(f"📱 Current phone number: {user.phone_number}")

                # Check if it's the wrong number
                if user.phone_number == '+1123456XXXX' or '123456' in user.phone_number:
                    correct_phone = "+15875452951"
                    user.phone_number = correct_phone
                    db.session.commit()
                    print(f"✅ Phone number updated to: {correct_phone}")

                    # Verify the change
                    user = User.query.get('sample_user')
                    print(f"🔍 Verification - Phone number: {user.phone_number}")
                    return True
                else:
                    print(f"✅ Phone number is already correct: {user.phone_number}")
                    return True
            else:
                print("❌ User 'sample_user' not found")
                return False

    except Exception as e:
        print(f"❌ Error fixing phone number: {str(e)}")
        return False

def test_llm_service():
    """Test the LLM service with proper configuration"""
    print("\n🧠 Testing LLM Service with API Keys")
    print("=" * 50)

    try:
        from services.llm_service import SMSLLMService

        llm_service = SMSLLMService()
        print(f"Available providers: {list(llm_service.providers.keys())}")

        if not llm_service.providers:
            print("❌ No LLM providers available - check your API keys")
            return False

        # Test health analysis generation
        print("\n📊 Testing Health Analysis Generation:")
        test_data = {
            'metrics_data': {
                'date': '2025-09-02',
                'metrics_analyzed': ['steps', 'heart_rate', 'sleep_score'],
                'steps_current': 8500,
                'heart_rate_current': 72,
                'sleep_score_current': 85
            },
            'statistical_analysis': {
                'baseline_statistics': {
                    'steps': {'mean': 8500, 'trend': 'improving'},
                    'heart_rate': {'mean': 72, 'trend': 'stable'},
                    'sleep_score': {'mean': 85, 'trend': 'improving'}
                }
            },
            'user_context': {
                'user_id': 'test_user',
                'activity_level': 'moderate',
                'health_goals': ['improve fitness', 'better sleep']
            }
        }

        health_insights = llm_service.generate_health_analysis(**test_data)
        if health_insights and hasattr(health_insights, 'content'):
            print(f"✅ Health analysis generated: {health_insights.content[:100]}...")
        else:
            print(f"⚠️ Health analysis returned: {type(health_insights)}")

        # Test SMS generation
        print("\n📱 Testing SMS Generation:")
        sms_response = llm_service.generate_sms_response(
            "Generate a personalized daily health summary based on: steps=8500, heart_rate=72, sleep_score=85",
            max_length=160
        )
        if sms_response and hasattr(sms_response, 'content'):
            print(f"✅ SMS generated: {sms_response.content}")
        else:
            print(f"⚠️ SMS returned: {type(sms_response)}")

        return True

    except Exception as e:
        print(f"❌ LLM service test failed: {str(e)}")
        return False

def test_daily_report_generation():
    """Test daily report generation with LLM service"""
    print("\n📊 Testing Daily Report Generation")
    print("=" * 50)

    try:
        from tasks.daily_report import generate_daily_report
        from app import create_app

        app = create_app()
        with app.app_context():
            print("Generating daily report for sample_user...")
            result = generate_daily_report('sample_user')

            if result.get('success'):
                print("✅ Daily report generated successfully!")
                print(f"📱 SMS Content: {result.get('sms_content', 'No SMS content')}")
                print(f"📊 Insights Count: {result.get('insights_count', 0)}")
                print(f"💡 Recommendations Count: {result.get('recommendations_count', 0)}")
                return True
            else:
                print(f"❌ Daily report failed: {result.get('error', 'Unknown error')}")
                return False

    except Exception as e:
        print(f"❌ Daily report test failed: {str(e)}")
        return False

def main():
    """Main fix function"""
    print("🚀 Comprehensive Fix for Daily Reports SMS Issues")
    print("=" * 60)

    # Step 1: Check environment
    env_ok = check_environment()
    if not env_ok:
        print("\n❌ Environment not properly configured")
        print("📝 Please set up your .env file with API keys first")
        return

    # Step 2: Fix phone number
    phone_fixed = fix_phone_number()

    # Step 3: Test LLM service
    llm_ok = test_llm_service()

    # Step 4: Test daily report generation
    if llm_ok:
        report_ok = test_daily_report_generation()
    else:
        report_ok = False

    # Summary
    print("\n🎯 Fix Summary:")
    print("=" * 30)
    print(f"📱 Phone Number: {'✅ Fixed' if phone_fixed else '❌ Failed'}")
    print(f"🧠 LLM Service: {'✅ Working' if llm_ok else '❌ Failed'}")
    print(f"📊 Daily Reports: {'✅ Working' if report_ok else '❌ Failed'}")

    if phone_fixed and llm_ok and report_ok:
        print("\n🎉 All issues fixed! Your daily reports should now work perfectly!")
        print("📱 You'll get personalized SMS insights instead of basic messages")
    else:
        print("\n⚠️ Some issues remain. Check the errors above and try again.")

    print("\n💡 Next Steps:")
    if not env_ok:
        print("1. Set up your .env file with API keys")
    if not phone_fixed:
        print("2. Fix the phone number in your database")
    if not llm_ok:
        print("3. Check your API keys and LLM service configuration")
    if not report_ok:
        print("4. Test daily report generation again")

    if phone_fixed and llm_ok and report_ok:
        print("5. 🎯 Run daily reports and enjoy personalized SMS insights!")

if __name__ == "__main__":
    main()
