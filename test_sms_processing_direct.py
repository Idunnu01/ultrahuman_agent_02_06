#!/usr/bin/env python3
"""
Test SMS processing directly to see where it fails
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from services.metrics_service import MetricsService
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on PythonAnywhere in your project directory")
    sys.exit(1)

def test_sms_processing():
    """Test SMS processing directly"""

    app = create_app()

    with app.app_context():
        print("🧪 TESTING SMS PROCESSING DIRECTLY")
        print("=" * 40)
        print()

        service = MetricsService()

        test_message = "supplement magnesium 400mg 10pm"
        user_id = "user_7000"

        print(f"📱 Testing: '{test_message}'")
        print(f"👤 User: {user_id}")
        print()

        try:
            print("🔍 Step 1: Calling process_sms_input...")
            result = service.process_sms_input(user_id, test_message)

            print("✅ process_sms_input completed!")
            print(f"Result: {result}")
            print()

            if result.get('success'):
                print("🎉 Success! SMS processed correctly")
                insights = result.get('immediate_insights', {}).get('insights', [])
                if insights:
                    for insight in insights:
                        print(f"💬 Message: {insight.get('message', 'No message')}")
                        print(f"🏷️  Type: {insight.get('type', 'No type')}")
            else:
                print("❌ Processing failed")
                print(f"Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"❌ Exception occurred: {e}")
            import traceback
            print("📋 Full traceback:")
            traceback.print_exc()

def test_parsing_step_by_step():
    """Test parsing step by step"""

    app = create_app()

    with app.app_context():
        print("🔬 TESTING PARSING STEP BY STEP")
        print("=" * 35)
        print()

        service = MetricsService()

        test_message = "supplement magnesium 400mg 10pm"

        print(f"📱 Testing: '{test_message}'")
        print()

        try:
            print("🔍 Step 1: Check if lifestyle event...")
            is_lifestyle = service._is_lifestyle_event(test_message.lower())
            print(f"   Is lifestyle event: {is_lifestyle}")

            if is_lifestyle:
                print()
                print("🔍 Step 2: Parse lifestyle SMS...")
                from datetime import datetime
                current_time = datetime.utcnow()

                event_type, details, timestamp = service._parse_lifestyle_sms(test_message, current_time)
                print(f"   Event type: {event_type}")
                print(f"   Details: {details}")
                print(f"   Timestamp: {timestamp}")

                print()
                print("🔍 Step 3: Process lifestyle event record...")
                metrics = service._process_lifestyle_event_record("user_7000", event_type, details, timestamp)
                print(f"   Generated metrics: {len(metrics)}")
                for i, metric in enumerate(metrics):
                    print(f"   Metric {i+1}: {metric}")

        except Exception as e:
            print(f"❌ Exception in step-by-step: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_sms_processing()
    print()
    test_parsing_step_by_step()