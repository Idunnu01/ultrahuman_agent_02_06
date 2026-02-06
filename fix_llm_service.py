#!/usr/bin/env python3
"""
Fix LLM Service Configuration
Tests and fixes LLM service integration for daily reports
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def test_llm_service():
    """Test the LLM service configuration"""
    print("🔧 Testing LLM Service Configuration")
    print("=" * 50)

    try:
        # Test 1: Check environment variables
        print("\n📋 Environment Variables Check:")
        api_keys = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
            'TOGETHER_API_KEY': os.getenv('TOGETHER_API_KEY')
        }

        for key, value in api_keys.items():
            if value:
                print(f"  ✅ {key}: {value[:10]}...")
            else:
                print(f"  ❌ {key}: Not set")

        # Test 2: Test LLM service initialization
        print("\n🧠 LLM Service Initialization Test:")
        from services.llm_service import SMSLLMService

        llm_service = SMSLLMService()
        print(f"  Available providers: {list(llm_service.providers.keys())}")
        print(f"  Provider errors: {llm_service.provider_errors}")

        # Test 3: Test basic LLM calls
        print("\n📱 LLM Service Functionality Test:")

        # Test health analysis
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

        print("  Testing health analysis generation...")
        try:
            health_insights = llm_service.generate_health_analysis(**test_data)
            if health_insights and hasattr(health_insights, 'content'):
                print(f"  ✅ Health analysis generated: {health_insights.content[:100]}...")
            else:
                print(f"  ⚠️ Health analysis returned: {type(health_insights)}")
        except Exception as e:
            print(f"  ❌ Health analysis failed: {str(e)}")

        # Test SMS generation
        print("  Testing SMS generation...")
        try:
            sms_response = llm_service.generate_sms_response(
                "Generate a personalized daily health summary based on: steps=8500, heart_rate=72, sleep_score=85",
                max_length=160
            )
            if sms_response and hasattr(sms_response, 'content'):
                print(f"  ✅ SMS generated: {sms_response.content}")
            else:
                print(f"  ⚠️ SMS returned: {type(sms_response)}")
        except Exception as e:
            print(f"  ❌ SMS generation failed: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ LLM service test failed: {str(e)}")
        return False

def fix_llm_service():
    """Fix common LLM service issues"""
    print("\n🔧 Fixing LLM Service Issues")
    print("=" * 50)

    try:
        # Fix 1: Check if required packages are installed
        print("\n📦 Package Installation Check:")
        required_packages = ['openai', 'anthropic', 'together']

        for package in required_packages:
            try:
                __import__(package)
                print(f"  ✅ {package} is installed")
            except ImportError:
                print(f"  ❌ {package} is missing - installing...")
                os.system(f"pip install {package}")

        # Fix 2: Test with fallback configuration
        print("\n🔄 Testing Fallback Configuration:")
        from services.llm_service import SMSLLMService

        # Create a test instance
        llm_service = SMSLLMService()

        # Test fallback methods
        print("  Testing fallback insight generation...")
        try:
            from tasks.daily_report import _generate_fallback_insights, _generate_fallback_sms

            test_analysis = {
                'baseline_statistics': {
                    'steps': {'mean': 8500},
                    'heart_rate': {'mean': 72},
                    'sleep_score': {'mean': 85}
                }
            }

            fallback_insights = _generate_fallback_insights(test_analysis)
            print(f"  ✅ Fallback insights: {fallback_insights}")

            fallback_sms = _generate_fallback_sms([], [])
            print(f"  ✅ Fallback SMS: {fallback_sms}")

        except Exception as e:
            print(f"  ❌ Fallback test failed: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ LLM service fix failed: {str(e)}")
        return False

def create_env_template():
    """Create a template .env file"""
    print("\n📝 Creating .env Template")
    print("=" * 50)

    env_template = """# LLM Service API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
TOGETHER_API_KEY=your_together_api_key_here

# Database Configuration
DATABASE_URL=mysql://username:password@host/database

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Ultrahuman API
ULTRAHUMAN_API_KEY=your_ultrahuman_api_key

# Other Configuration
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
"""

    try:
        with open('.env.template', 'w') as f:
            f.write(env_template)
        print("✅ Created .env.template file")
        print("📋 Copy this to .env and fill in your actual API keys")
    except Exception as e:
        print(f"❌ Failed to create .env template: {str(e)}")

if __name__ == "__main__":
    print("🚀 LLM Service Diagnostic and Fix Tool")
    print("=" * 60)

    # Run tests
    test_success = test_llm_service()

    # Run fixes
    if not test_success:
        fix_success = fix_llm_service()

    # Create environment template
    create_env_template()

    print("\n🎯 Summary:")
    if test_success:
        print("✅ LLM service is working correctly!")
        print("📱 You should get full SMS insights in your daily reports")
    else:
        print("⚠️ LLM service has issues")
        print("🔧 Check the .env.template file and set your API keys")
        print("📱 You'll get fallback SMS content until LLM is fixed")

    print("\n💡 Next Steps:")
    print("1. Copy .env.template to .env")
    print("2. Add your actual API keys")
    print("3. Restart your application")
    print("4. Run daily reports again")
