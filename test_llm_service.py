#!/usr/bin/env python3
"""
Test LLM service configuration and functionality
"""

import requests
import json

def test_llm_via_webhook():
    """Test LLM service by sending a correlation query and checking response format"""

    print("🔍 TESTING LLM SERVICE INTEGRATION")
    print("=" * 50)

    # Send correlation query that should trigger LLM
    webhook_url = "https://health-bphlite.pythonanywhere.com/webhook/sms"

    payload = {
        'From': '+15875452951',
        'Body': 'debug correlation heart rate and temperature last 21 days',
        'MessageSid': 'test_llm_debug',
        'AccountSid': 'test_account',
        'ToCountry': 'US',
        'ToState': '',
        'FromCountry': 'US',
        'FromState': '',
        'To': '+18775551234'
    }

    print(f"📱 Testing query: '{payload['Body']}'")
    print("🔄 Checking LLM response format...")

    try:
        response = requests.post(webhook_url, data=payload, timeout=30)

        if response.status_code == 200:
            print(f"✅ Webhook processed successfully")
            print(f"📤 Response should include LLM-generated insights")
            print(f"📊 Check SMS for detailed correlation analysis")

            # The actual LLM response will be sent via SMS
            # This test confirms the webhook processes the request
            print(f"\n🎯 WHAT TO LOOK FOR IN SMS:")
            print(f"✅ GOOD: Detailed explanation of what r=-0.023 means")
            print(f"✅ GOOD: Health implications and recommendations")
            print(f"✅ GOOD: Context about normal vs abnormal correlations")
            print(f"❌ BAD: Just 'r=-0.023, p=0.000, 174914 data points'")

            return True
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_api_endpoints():
    """Test API endpoints that might show LLM service status"""

    print(f"\n🔍 TESTING API ENDPOINTS")
    print("=" * 30)

    endpoints_to_test = [
        ("/health", "System health check"),
        ("/health/celery", "Background task system"),
        ("/users/sample_user", "User data access"),
    ]

    base_url = "https://health-bphlite.pythonanywhere.com"

    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            print(f"📡 {endpoint}: {response.status_code} - {description}")

            if endpoint == "/health" and response.status_code == 200:
                data = response.json()
                print(f"   Components: {', '.join(data.get('components', {}).keys())}")

        except Exception as e:
            print(f"❌ {endpoint}: Error - {str(e)}")

def create_manual_llm_test():
    """Create a test that simulates what the LLM should produce"""

    print(f"\n🤖 EXPECTED LLM OUTPUT EXAMPLE")
    print("=" * 40)

    # Example of what LLM should generate for correlation r=-0.023
    expected_output = """📊 Your heart rate and temperature show a very weak negative correlation (r=-0.023).

This means as your body temperature increases slightly, your heart rate tends to decrease marginally. This is actually normal physiological behavior - your cardiovascular system adjusts heart rate as part of thermal regulation.

With 174,914 data points over 21 days, this pattern is statistically significant but practically minimal. This suggests your autonomic nervous system is functioning normally.

💡 Key insight: This correlation is too weak to be actionable, but the large sample size confirms your body's temperature regulation is consistent and healthy."""

    print("🎯 WHAT YOUR SMS SHOULD LOOK LIKE:")
    print(expected_output)

    print(f"\n❌ INSTEAD OF JUST:")
    print("📉 Found a very weak negative correlation between heart rate and temperature (r=-0.023, p=0.000). Pattern is significant with 174914 data points.")

def run_llm_diagnostic():
    """Run comprehensive LLM diagnostic"""

    print("🚀 LLM SERVICE DIAGNOSTIC")
    print("=" * 60)
    print("This will test if LLM integration is working properly")
    print("Check your SMS for the actual response content")
    print("=" * 60)

    # Test LLM via webhook
    webhook_success = test_llm_via_webhook()

    # Test API endpoints
    test_api_endpoints()

    # Show expected output
    create_manual_llm_test()

    print(f"\n" + "=" * 60)
    print("🎯 DIAGNOSTIC COMPLETE")
    print("=" * 60)

    if webhook_success:
        print("✅ Webhook processing: WORKING")
        print("🔍 Check your SMS for LLM-generated insights")
        print("📱 If SMS only shows statistics, LLM integration needs fixing")
    else:
        print("❌ Webhook processing: FAILED")

    print(f"\n📋 NEXT STEPS:")
    print("1. Check SMS response content")
    print("2. If only statistics shown, LLM service needs configuration")
    print("3. May need to add API keys (Anthropic/OpenAI) to environment")
    print("4. Check server logs for LLM service errors")

if __name__ == "__main__":
    run_llm_diagnostic()