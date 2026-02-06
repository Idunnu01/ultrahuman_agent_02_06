#!/usr/bin/env python3
"""
Debug Daily Report Generation
Identify the exact issue causing daily report failures
"""

import os
import sys
import traceback
from datetime import timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def debug_daily_report():
    """Debug the daily report generation step by step"""
    print("🔍 Debugging Daily Report Generation")
    print("=" * 50)

    try:
        from app import create_app
        from app.models import User
        from utils.database import db

        app = create_app()
        with app.app_context():
            print("✅ Flask app context created successfully")

            # Step 1: Check user exists
            print("\n📱 Step 1: Checking user...")
            user = User.query.get('sample_user')
            if user:
                print(f"✅ User found: {user.id}")
                print(f"   Phone: {user.phone_number}")
                print(f"   Active: {user.is_active}")
            else:
                print("❌ User not found")
                return

            # Step 2: Check if user has data
            print("\n📊 Step 2: Checking user data...")
            from app.models import Metric
            metrics = Metric.query.filter_by(user_id='sample_user').all()
            print(f"✅ Found {len(metrics)} metrics for user")

            if metrics:
                print("   Sample metrics:")
                for i, metric in enumerate(metrics[:3]):
                    print(f"     {i+1}. {metric.metric_type}: {metric.value} at {metric.timestamp}")
            else:
                print("⚠️ No metrics found - this might cause issues")

            # Step 3: Test statistical analyzer
            print("\n🧮 Step 3: Testing statistical analyzer...")
            try:
                from services.statistical_analyzer import StatisticalAnalyzer
                analyzer = StatisticalAnalyzer()
                print("✅ Statistical analyzer created successfully")

                # Test data retrieval
                user_data = analyzer._get_user_data('sample_user', timedelta(days=30))
                if user_data:
                    print(f"✅ User data retrieved: {len(user_data)} metric types")
                    for metric_type, data in user_data.items():
                        print(f"   {metric_type}: {len(data['values'])} values, {len(data['timestamps'])} timestamps")
                else:
                    print("❌ No user data retrieved")

            except Exception as e:
                print(f"❌ Statistical analyzer failed: {str(e)}")
                print(f"   Traceback: {traceback.format_exc()}")

            # Step 4: Test LLM service
            print("\n🧠 Step 4: Testing LLM service...")
            try:
                from services.llm_service import SMSLLMService
                llm_service = SMSLLMService()
                print(f"✅ LLM service created with providers: {list(llm_service.providers.keys())}")

                # Test basic LLM call
                test_response = llm_service.generate_sms_response("Test message", max_length=160)
                print(f"✅ LLM test successful: {test_response.content[:50]}...")

            except Exception as e:
                print(f"❌ LLM service failed: {str(e)}")
                print(f"   Traceback: {traceback.format_exc()}")

            # Step 5: Test daily report generation step by step
            print("\n📋 Step 5: Testing daily report generation...")
            try:
                from tasks.daily_report import generate_daily_report
                print("✅ Daily report module imported successfully")

                # Try to generate report
                print("   Attempting to generate daily report...")
                result = generate_daily_report('sample_user')

                if result.get('success'):
                    print("✅ Daily report generated successfully!")
                    print(f"   SMS Content: {result.get('sms_content', 'No SMS content')}")
                    print(f"   Insights Count: {result.get('insights_count', 0)}")
                    print(f"   Recommendations Count: {result.get('recommendations_count', 0)}")
                else:
                    print(f"❌ Daily report failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                print(f"❌ Daily report generation failed: {str(e)}")
                print(f"   Full traceback:")
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Debug script failed: {str(e)}")
        print(f"   Full traceback:")
        traceback.print_exc()

def test_individual_components():
    """Test individual components in isolation"""
    print("\n🔧 Testing Individual Components")
    print("=" * 50)

    try:
        # Test 1: Database connection
        print("\n📊 Test 1: Database Connection")
        from app import create_app
        app = create_app()
        with app.app_context():
            from utils.database import db
            result = db.session.execute("SELECT 1").scalar()
            print(f"✅ Database connection: {result}")

        # Test 2: Model imports
        print("\n📋 Test 2: Model Imports")
        from app.models import User, Metric, DailyReport
        print("✅ All models imported successfully")

        # Test 3: Service imports
        print("\n⚙️ Test 3: Service Imports")
        from services.statistical_analyzer import StatisticalAnalyzer
        from services.llm_service import SMSLLMService
        from services.sms_service import SMSService
        print("✅ All services imported successfully")

        # Test 4: Task imports
        print("\n📝 Test 4: Task Imports")
        from tasks.daily_report import generate_daily_report
        print("✅ Daily report task imported successfully")

        print("\n✅ All components imported successfully!")

    except Exception as e:
        print(f"❌ Component test failed: {str(e)}")
        print(f"   Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Daily Report Debug Tool")
    print("=" * 40)

    # Test individual components first
    test_individual_components()

    # Then debug the full process
    debug_daily_report()

    print("\n🎯 Debug Complete!")
    print("Check the output above for any errors or issues.")
