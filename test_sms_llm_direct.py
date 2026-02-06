#!/usr/bin/env python3
"""
Test SMS processing directly with your actual phone number
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_direct_sms():
    """Test SMS processing with your actual phone number"""

    print("📱 Testing Direct SMS Processing")
    print("="*40)

    your_phone = "+15875452951"  # Your actual phone number
    test_message = "supplement magnesium 400mg at 10pm"

    try:
        from app import create_app
        from utils.database import db
        from app.models import User
        from services.metrics_service import MetricsService

        app = create_app()

        with app.app_context():
            print(f"📞 Testing with phone: {your_phone}")
            print(f"💬 Message: {test_message}")

            # Check if user exists
            user = User.query.filter_by(phone_number=your_phone).first()
            if not user:
                print(f"❌ No user found for phone: {your_phone}")
                return False

            print(f"✅ Found user: {user.id}")

            # Test the same method the webhook uses
            metrics_service = MetricsService()
            result = metrics_service.process_sms_input_with_context(user.id, test_message)

            print(f"\n📊 Processing Result:")
            print(f"   Success: {result.get('success')}")
            print(f"   Events processed: {result.get('events_processed', 0)}")
            print(f"   Error: {result.get('error', 'None')}")

            if result.get('success'):
                insights = (result.get('immediate_insights') or {}).get('insights') or []
                if insights:
                    response_text = (insights[0].get('message', '') or '').strip() or "✅ Logged."
                    print(f"   Response: {response_text}")
                elif result.get('events_processed', 0) > 0:
                    print(f"   Response: ✅ Logged {result['events_processed']} event(s). Thanks!")
                else:
                    print(f"   Response: 👍 Received. Try: 'meal chicken 7pm' or 'supplement magnesium 400mg 9pm'")
            else:
                print(f"   Response: ❌ Couldn't process. Try: 'meal [food] [time]' or 'supplement [name] [dose] [time]'")

            return result.get('success', False)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_direct_sms()
    if success:
        print("\n🎉 SMS processing should work! Try texting again.")
    else:
        print("\n🔧 Still having issues - check the error above.")