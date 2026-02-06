#!/usr/bin/env python3
"""
Test your SMS webhook directly
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_production_webhook():
    """Test your actual production webhook"""

    # Your PythonAnywhere webhook URL - CORRECT ONE!
    webhook_url = "https://health-bphlite.pythonanywhere.com/webhook/sms"

    # Mock Twilio SMS data with YOUR real phone number
    sms_data = {
        'From': '+15875452951',  # Your real phone
        'Body': 'What is my average HRV this week?',  # Test question
        'MessageSid': 'SM_test_123456789',
        'AccountSid': 'ACe63a78547cabf2cb8d98edcc5acdffd0'  # Your real Twilio SID
    }

    print(f"🧪 Testing SMS webhook...")
    print(f"URL: {webhook_url}")
    print(f"From: {sms_data['From']}")
    print(f"Message: {sms_data['Body']}")
    print("-" * 50)

    try:
        response = requests.post(
            webhook_url,
            data=sms_data,
            timeout=30,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        print(f"✅ Response Status: {response.status_code}")
        print(f"✅ Response Headers: {dict(response.headers)}")
        print(f"✅ Response Body: {response.text}")

        if response.status_code == 200:
            print("\n🎉 Webhook is responding!")
            if 'Response' in response.text:
                print("📱 Check your phone for SMS response")
            else:
                print("⚠️  Webhook responded but may have processing issues")
        else:
            print(f"\n❌ Webhook failed with status {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_production_webhook()
